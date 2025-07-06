# booking/serializers.py

from rest_framework import serializers
from .models import Venue, Event, Seat, Order, OrderItem
from decimal import Decimal
from django.utils import timezone 
from datetime import timedelta 
import uuid 

# 再次提醒：最佳實踐是通過 ViewSet 的 context 傳遞 redis_instance
# 這裡繼續假設您可以從 views 導入，或者您已在 ViewSet 中通過 context 傳遞
try:
    from booking.views import redis_instance
except ImportError:
    import redis
    redis_instance = redis.StrictRedis(host='localhost', port=6379, db=0)


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = '__all__'

class EventSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.name', read_only=True)

    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ('venue_name',)

class SeatSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Seat
        fields = '__all__'
        read_only_fields = ('event_name', 'status_display',)

class OrderItemSerializer(serializers.ModelSerializer):
    seat_info = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'seat', 'quantity', 'price_at_purchase', 'seat_info']
        read_only_fields = ('id', 'seat_info',)

    def get_seat_info(self, obj):
        if obj.seat:
            return f"{obj.seat.row}{obj.seat.column}"
        return None

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    # 針對創建訂單的輸入字段
    seat_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), 
        write_only=True, 
        min_length=1, 
        required=True
    )
    event_id = serializers.IntegerField(write_only=True, required=True, min_value=1)


    class Meta:
        model = Order
        fields = [
            'id', 'items', 'order_number', 'total_amount', 'status', 
            'created_at', 'updated_at', 'buyer_name', 'seat_ids', 'event_id' 
        ]
        read_only_fields = (
            'order_number', 'created_at', 'updated_at', 'status',
            'id' 
        )

    # 覆寫 create 方法
    def create(self, validated_data):
        # 從 validated_data 中 pop 掉不屬於 Order 模型本身的字段
        seat_ids = validated_data.pop('seat_ids')
        input_event_id = validated_data.pop('event_id')

        # 這裡從 validated_data 中獲取在 validate 方法中設置的 'event' 實例
        event_instance = validated_data.pop('event') # <-- 這裡也需要 pop 出 event

        # 將 Event 實例賦值給 order 實例的 'event' 字段
        validated_data['event'] = event_instance
        
        # 讓 ModelSerializer 的父類處理 Order 模型的創建
        order = super().create(validated_data)

        # 為了讓 ViewSet 能夠訪問到 validate_data 裡面處理好的數據 (例如 _selected_seats)
        # 我們將這些數據儲存在 Serializer 實例的內部屬性中，供 ViewSet 調用
        if hasattr(self, '_selected_seats'):
            order._selected_seats_for_creation = self._selected_seats
        if hasattr(self, '_total_amount'):
            order._calculated_total_amount = self._total_amount
        if hasattr(self, '_session_id'):
            order._session_id_for_creation = self._session_id

        return order


    def validate(self, data):
        seat_ids = data.get('seat_ids')
        event_id = data.get('event_id')

        # 1. 驗證 event_id 是否存在
        try:
            event = Event.objects.get(id=event_id)
            data['event'] = event # <-- 重要：將 Event 實例儲存到 data 中，供 create 方法使用
        except Event.DoesNotExist:
            raise serializers.ValidationError({"event_id": "Event not found."})

        # 2. 準備 session_id。這裡從 context['request'] 中獲取，這是 ViewSet 傳入的標準方式
        request = self.context.get('request')
        session_id = request.data.get('session_id', request.session.session_key)
        if not session_id:
            if not request.session.session_key:
                request.session.save()
            session_id = request.session.session_key
            if not session_id:
                session_id = str(uuid.uuid4()) 

        # 3. 獲取 Redis 實例。從 context 中獲取是最佳實踐
        redis_instance_from_context = self.context.get('redis_instance')
        if not redis_instance_from_context:
            redis_instance_from_context = globals().get('redis_instance') 
            if not redis_instance_from_context:
                raise serializers.ValidationError({"server_error": "Redis instance not available in serializer context."})

        
        selected_seats = []
        total_amount = Decimal('0.00')
        lock_duration_seconds = 60 * 5 

        # 4. 遍歷 seat_ids，檢查座位狀態並進行初步鎖定檢查
        for seat_id in seat_ids:
            try:
                seat = Seat.objects.get(id=seat_id, event=event) 
            except Seat.DoesNotExist:
                raise serializers.ValidationError({"seat_ids": f"Seat {seat_id} not found for this event."})

            if seat.price is None:
                raise serializers.ValidationError({"seat_ids": f"Seat {seat.id} has no price defined."})

            lock_key = f"seat_lock:{seat.id}"
            current_locker_session = redis_instance_from_context.get(lock_key)

            if seat.status not in ['available', 'cancelled']:
                if seat.status == 'locked':
                    if not current_locker_session or current_locker_session.decode('utf-8') != session_id:
                        raise serializers.ValidationError({"seat_ids": f"Seat {seat.id} is locked by another user."})
                    else:
                        redis_instance_from_context.expire(lock_key, lock_duration_seconds)
                        selected_seats.append(seat)
                        total_amount += seat.price
                        continue 
                elif seat.status == 'registered':
                    raise serializers.ValidationError({"seat_ids": f"Seat {seat.id} is already registered."})
                else:
                    raise serializers.ValidationError({"seat_ids": f"Seat {seat.id} is in an invalid state: {seat.get_status_display()}."})
            
            if seat.status in ['available', 'cancelled']:
                if not redis_instance_from_context.set(lock_key, session_id, ex=lock_duration_seconds, nx=True):
                    if current_locker_session and current_locker_session.decode('utf-8') != session_id:
                         raise serializers.ValidationError({"seat_ids": f"Seat {seat.id} is already locked by another user in Redis."})
                    else:
                        redis_instance_from_context.expire(lock_key, lock_duration_seconds)
                
            selected_seats.append(seat)
            total_amount += seat.price
        
        self._selected_seats = selected_seats
        self._total_amount = total_amount
        self._session_id = session_id
        
        data['total_amount'] = total_amount

        return data