# booking/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
import uuid
import redis
from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404 # 引入 get_object_or_404

# 確保您的 Redis 伺服器已啟動，並在 settings.py 中配置
redis_instance = redis.StrictRedis(host='localhost', port=6379, db=0)

from .models import Venue, Event, Seat, Order, OrderItem
from .serializers import VenueSerializer, EventSerializer, SeatSerializer, OrderSerializer, OrderItemSerializer

class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

    @action(detail=True, methods=['get'], url_path='seats')
    def get_event_seats(self, request, pk=None):
        try:
            event = self.get_object()
        except Event.DoesNotExist:
            return Response({'detail': 'Event not found.'}, status=status.HTTP_404_NOT_FOUND)

        seats = event.seat_set.all().order_by('row', 'column')
        serializer = SeatSerializer(seats, many=True)
        return Response(serializer.data)

class SeatViewSet(viewsets.ModelViewSet):
    queryset = Seat.objects.all()
    serializer_class = SeatSerializer


    @action(detail=False, methods=['post'], url_path='lock')
    def lock_seats(self, request):
        """
        批次鎖定多個座位
        """
        seat_ids = request.data.get('seat_ids', [])
        session_id = request.data.get('session_id', None)
        if not seat_ids or not session_id:
            return Response({'detail': 'seat_ids and session_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        locked_seats = []
        failed_seats = []
        lock_duration_seconds = 60 * 3 # 3分鐘鎖定時間

        for seat_id in seat_ids:
            try:
                seat = Seat.objects.get(id=seat_id)
                lock_key = f"seat_lock:{seat.id}"
                if seat.status in ['available', 'cancelled']:
                    if redis_instance.set(lock_key, session_id, ex=lock_duration_seconds, nx=True):
                        seat.status = 'locked'
                        seat.locked_until = timezone.now() + timedelta(seconds=lock_duration_seconds)
                        seat.locked_by_session = session_id
                        seat.save()
                        locked_seats.append(seat.id)
                    else:
                        failed_seats.append({'id': seat.id, 'reason': 'locked by another user'})
                else:
                    failed_seats.append({'id': seat.id, 'reason': f'status: {seat.status}'})
            except Seat.DoesNotExist:
                failed_seats.append({'id': seat_id, 'reason': 'not found'})

        return Response({
            'locked_seats': locked_seats,
            'failed_seats': failed_seats
        }, status=status.HTTP_200_OK if not failed_seats else status.HTTP_207_MULTI_STATUS)

    @action(detail=False, methods=['post'], url_path='unlock')
    def unlock_seats(self, request):
        """
        批次解鎖多個座位
        """
        seat_ids = request.data.get('seat_ids', [])
        session_id = request.data.get('session_id', None)
        if not seat_ids or not session_id:
            return Response({'detail': 'seat_ids and session_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        unlocked_seats = []
        failed_seats = []

        for seat_id in seat_ids:
            try:
                seat = Seat.objects.get(id=seat_id)
                lock_key = f"seat_lock:{seat.id}"
                current_locker_session = redis_instance.get(lock_key)
                if seat.status == 'locked' and current_locker_session and current_locker_session.decode('utf-8') == session_id:
                    redis_instance.delete(lock_key)
                    seat.status = 'available'
                    seat.locked_until = None
                    seat.locked_by_session = None
                    seat.save()
                    unlocked_seats.append(seat.id)
                elif seat.status != 'locked':
                    failed_seats.append({'id': seat.id, 'reason': 'not locked'})
                else:
                    failed_seats.append({'id': seat.id, 'reason': 'locked by another session or lock expired'})
            except Seat.DoesNotExist:
                failed_seats.append({'id': seat_id, 'reason': 'not found'})

        return Response({
            'unlocked_seats': unlocked_seats,
            'failed_seats': failed_seats
        }, status=status.HTTP_200_OK if not failed_seats else status.HTTP_207_MULTI_STATUS)

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def create(self, request, *args, **kwargs):
        # 傳遞 request 和 redis_instance 到 serializer 的 context
        # 這是 DRF 的標準做法，讓 serializer 能訪問 request 資訊和外部依賴
        serializer = self.get_serializer(data=request.data, context={'request': request, 'redis_instance': redis_instance})
        
        # 執行驗證，如果驗證失敗會自動拋出 ValidationError，並由我們自定義的異常處理器捕獲
        serializer.is_valid(raise_exception=True) 

        # 從 serializer 中獲取驗證後並預處理的數據
        # 這些是我們在 serializer 的 validate 方法中添加到 self._xxx 的數據
        selected_seats = serializer._selected_seats
        total_amount = serializer._total_amount
        session_id = serializer._session_id

        seats_to_unlock_redis = [] # 追蹤成功 Redis 鎖定的座位
        lock_duration_seconds = 60 * 5 # 5分鐘

        try:
            with transaction.atomic():
                # 重新獲取座位並鎖定數據庫行，這是防止併發問題的關鍵步驟
                # 因為 serializer 的驗證階段無法保證原子性，且無法鎖定 DB 行
                # 這裡我們利用了 select_for_update 在事務中確保數據一致性
                for seat in selected_seats:
                    # 再次從 DB 獲取最新狀態並鎖定
                    # 這裡可以省略 get_object_or_404，因為座位 ID 在 serializer 中已經驗證過存在
                    seat_from_db = Seat.objects.select_for_update().get(id=seat.id) 

                    lock_key = f"seat_lock:{seat_from_db.id}"
                    current_locker_session = redis_instance.get(lock_key)

                    # 再次檢查座位狀態，防止在驗證和執行之間狀態改變
                    if seat_from_db.status not in ['available', 'cancelled']:
                        if seat_from_db.status == 'locked':
                            if not current_locker_session or current_locker_session.decode('utf-8') != session_id:
                                # 被其他人鎖定
                                raise serializers.ValidationError({'detail': f'Seat {seat_from_db.id} is locked by another user during final transaction.'})
                            else:
                                # 是自己的鎖定，續期 Redis 鎖
                                redis_instance.expire(lock_key, lock_duration_seconds)
                        elif seat_from_db.status == 'registered':
                            raise serializers.ValidationError({'detail': f'Seat {seat_from_db.id} is already registered during final transaction.'})
                        else:
                            raise serializers.ValidationError({'detail': f'Seat {seat_from_db.id} is in an invalid state during final transaction: {seat_from_db.get_status_display()}.'})
                    
                    # 確保在 Redis 中進行原子性鎖定，防止併發操作
                    if not redis_instance.set(lock_key, session_id, ex=lock_duration_seconds, nx=True):
                        # 如果鎖定失敗，且不是自己的鎖，則報錯
                        if current_locker_session and current_locker_session.decode('utf-8') != session_id:
                             raise serializers.ValidationError({'detail': f'Seat {seat_from_db.id} is already locked by another user in Redis during final transaction.'})
                        else:
                            # 是自己的鎖，續期
                            redis_instance.expire(lock_key, lock_duration_seconds)
                    
                    seats_to_unlock_redis.append(lock_key) # 成功鎖定或續期後加入列表


                    # 更新座位狀態為 'locked'，並保存到資料庫
                    seat_from_db.status = 'locked' 
                    seat_from_db.locked_until = timezone.now() + timedelta(seconds=lock_duration_seconds)
                    seat_from_db.locked_by_session = session_id
                    seat_from_db.save()
                
                # 準備訂單數據，使用 serializer.validated_data 確保數據已驗證
                order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"
                order_data = {
                    'order_number': order_number,
                    'event': serializer.validated_data['event'], # 從 serializer 獲取 Event 實例
                    'total_amount': total_amount, # 使用 serializer 計算的總金額
                    'status': 'registered',
                    'buyer_name': serializer.validated_data['buyer_name'],
                    # 'user': request.user if request.user.is_authenticated else None # 如果有用戶認證
                }
                
                # 創建 Order 實例
                order = Order.objects.create(**order_data)

                # 創建 OrderItem 並更新 Seat 狀態為 'registered'
                for seat in selected_seats: # 這裡的 seat 是從 serializer 獲取，需要用 ID 再次確保與 DB 狀態同步
                    # 再次從 DB 獲取最新狀態（已在 select_for_update 中處理）
                    current_seat = Seat.objects.select_for_update().get(id=seat.id)
                    OrderItem.objects.create(
                        order=order,
                        seat=current_seat, # 使用從 DB 獲取的最新座位實例
                        quantity=1,
                        price_at_purchase=current_seat.price
                    )
                    current_seat.status = 'registered'
                    current_seat.locked_until = None
                    current_seat.locked_by_session = None
                    current_seat.save()

            # 交易成功提交後，安全地從 Redis 刪除鎖定
            for lock_key in seats_to_unlock_redis:
                redis_instance.delete(lock_key)

            # 返回響應
            response_serializer = self.get_serializer(order)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except serializers.ValidationError as e:
            # 如果在 transaction 內拋出自定義的 ValidationError，重新拋出讓全局處理器捕獲
            raise e
        except Exception as e:
            # 任何在 transaction.atomic() 區塊內發生的錯誤都會觸發回滾
            # 手動處理 Redis 的解鎖 (對於那些在交易開始前就成功鎖定的)
            for lock_key in seats_to_unlock_redis:
                current_locker_session = redis_instance.get(lock_key)
                if current_locker_session and current_locker_session.decode('utf-8') == session_id:
                    redis_instance.delete(lock_key)
            
            # 重新拋出異常，讓 custom_exception_handler 處理
            raise e

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_order(self, request, pk=None):
        """
        取消訂單的 API 動作。
        將訂單狀態改為 'cancelled'，並釋放所有相關座位。
        """

        try:
            with transaction.atomic():
                # 獲取訂單並鎖定，防止併發取消，現在在交易內部
                order = get_object_or_404(Order.objects.select_for_update(), pk=pk)

                # 只有 'registered' 狀態的訂單才能被取消
                if order.status != 'registered':
                    return Response({'detail': f'Order cannot be cancelled. Current status: {order.get_status_display()}.'}, status=status.HTTP_400_BAD_REQUEST)
                
                order.status = 'cancelled'
                order.save()

                # 釋放訂單中的所有座位
                for order_item in list(order.items.all()): # <-- 注意這裡，使用 list() 避免在迭代時修改 QuerySet
                    seat = order_item.seat
                    if seat: # 確保座位存在
                        # 只有當座位是 'registered' 時才改為 'available'
                        # 如果座位是 'locked' 狀態，則確保解鎖並改為 'available'
                        if seat.status in ['registered', 'locked']:
                            seat.status = 'available'
                            seat.locked_until = None
                            seat.locked_by_session = None
                            seat.save()
                            # 確保 Redis 鎖定也清除 (以防萬一)
                            redis_instance.delete(f"seat_lock:{seat.id}")
                        # 如果座位已經是 'available' 或其他狀態，則不做改變
                        # 如果座位是 'cancelled' (表示已被取消過)，也可以讓它保持 'available'
                    order_item.delete() 

            response_serializer = self.get_serializer(order)
            return Response({'detail': 'Order successfully cancelled.', 'order': response_serializer.data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'detail': f'Failed to cancel order: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)