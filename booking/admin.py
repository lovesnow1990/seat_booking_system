# booking/admin.py

from django.contrib import admin
from .models import Venue, Event, Seat, Order, OrderItem

# 註冊您的模型
admin.site.register(Venue)
admin.site.register(Event)
admin.site.register(Seat)
admin.site.register(Order)
admin.site.register(OrderItem)

# 如果想在後台看到更詳細的列表和搜尋功能，可以這樣定義：
# @admin.register(Venue)
# class VenueAdmin(admin.ModelAdmin):
#     list_display = ('name', 'capacity')
#     search_fields = ('name',)

# @admin.register(Event)
# class EventAdmin(admin.ModelAdmin):
#     list_display = ('name', 'venue', 'event_date', 'event_time', 'base_price', 'is_active')
#     list_filter = ('is_active', 'venue', 'event_date')
#     search_fields = ('name', 'description')
#     raw_id_fields = ('venue',) # 讓 ForeignKey 選擇更方便

# @admin.register(Seat)
# class SeatAdmin(admin.ModelAdmin):
#     list_display = ('event', 'row', 'column', 'status', 'price', 'locked_until')
#     list_filter = ('status', 'event')
#     search_fields = ('event__name', 'row', 'column')
#     raw_id_fields = ('event',)

# @admin.register(Order)
# class OrderAdmin(admin.ModelAdmin):
#     list_display = ('order_number', 'user', 'event', 'total_amount', 'status', 'created_at')
#     list_filter = ('status', 'created_at', 'event')
#     search_fields = ('order_number', 'buyer_name', 'buyer_email', 'user__username')
#     raw_id_fields = ('user', 'event')

# @admin.register(OrderItem)
# class OrderItemAdmin(admin.ModelAdmin):
#     list_display = ('order', 'seat', 'quantity', 'price_at_purchase')
#     raw_id_fields = ('order', 'seat')