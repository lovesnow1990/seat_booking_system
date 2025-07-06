# booking/models.py

from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User # 引入 User 模型，如果未來需要用戶關聯
import uuid # 導入 uuid 模組用於生成訂單號

class Venue(models.Model):
    """
    場地模型，例如音樂廳、體育館。
    """
    name = models.CharField(max_length=200, unique=True, verbose_name="場地名稱")
    capacity = models.IntegerField(verbose_name="總座位數", validators=[MinValueValidator(1)])
    layout_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="座位佈局資料",
        help_text="JSON格式的座位佈局信息，例如區域劃分、排數、座位數等。"
    )

    class Meta:
        verbose_name = "場地"
        verbose_name_plural = "場地"
        ordering = ['name']

    def __str__(self):
        return self.name

class Event(models.Model):
    """
    場次模型，例如一場演唱會或球賽。
    """
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, verbose_name="所屬場地")
    name = models.CharField(max_length=200, verbose_name="場次名稱")
    description = models.TextField(blank=True, verbose_name="場次描述")
    event_date = models.DateField(verbose_name="活動日期")
    event_time = models.TimeField(verbose_name="活動時間")
    base_price = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="基本票價"
    )
    is_active = models.BooleanField(default=True, verbose_name="是否啟用")

    class Meta:
        verbose_name = "場次"
        verbose_name_plural = "場次"
        # 確保在同一場地和日期時間只有一個相同名稱的場次
        unique_together = ('venue', 'event_date', 'event_time', 'name')
        ordering = ['event_date', 'event_time', 'venue__name']

    def __str__(self):
        return f"{self.name} - {self.event_date} {self.event_time} ({self.venue.name})"

class Seat(models.Model):
    """
    座位模型，屬於特定場次。
    """
    # 座位狀態選項
    SEAT_STATUS_CHOICES = [
        ('available', '可選'),
        ('locked', '鎖定中'), # 通常用於暫時鎖定（例如選座後支付前）
        ('registered', '已登記'), # 新增：替代 sold 狀態
        ('cancelled', '已取消'), # 新增：用於訂單取消後座位釋放
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, verbose_name="所屬場次")
    row = models.CharField(max_length=10, verbose_name="行號")
    column = models.CharField(max_length=10, verbose_name="座位號")
    status = models.CharField(
        max_length=20,
        choices=SEAT_STATUS_CHOICES,
        default='available',
        verbose_name="座位狀態"
    )
    price = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0, # 增加預設值，避免 null 錯誤
        verbose_name="座位價格"
    )
    # 用於鎖定追蹤 (在取消支付整合後，這些欄位可以根據需求決定保留或移除)
    locked_until = models.DateTimeField(null=True, blank=True, verbose_name="鎖定至")
    locked_by_session = models.CharField(max_length=255, null=True, blank=True, verbose_name="由會話鎖定")

    class Meta:
        verbose_name = "座位"
        verbose_name_plural = "座位"
        # 確保在同一場次下，行號和座位號是唯一的
        unique_together = ('event', 'row', 'column')
        ordering = ['event', 'row', 'column']

    def __str__(self):
        return f"{self.event.name} - {self.row}{self.column} ({self.get_status_display()})"

class Order(models.Model):
    """
    訂單模型。
    """
    # 簡化訂單狀態選項
    ORDER_STATUS_CHOICES = [
        ('registered', '已登記'), # 替代 pending/paid 狀態
        ('cancelled', '已取消'),
    ]

    order_number = models.CharField(max_length=50, unique=True, blank=True, verbose_name="訂單號")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, verbose_name="所屬場次")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="訂購者") # 可選，如果後續有用戶系統
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="總金額",
        default=0.00 # 增加預設值，確保不會為空
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='registered', # 預設為已登記
        verbose_name="訂單狀態"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    # 由於沒有支付，payment_id 可移除或保留，如果未來可能重新引入支付
    # payment_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="支付交易ID")

    buyer_name = models.CharField(max_length=100, verbose_name="購買者姓名")

    class Meta:
        verbose_name = "訂單"
        verbose_name_plural = "訂單"
        ordering = ['-created_at']

    def __str__(self):
        return f"訂單號: {self.order_number} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    """
    訂單項模型，記錄訂單中的具體座位。
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="所屬訂單")
    seat = models.OneToOneField(Seat, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="購買的座位") # OneToOneField 確保一個座位只屬於一個訂單項
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="數量")
    price_at_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="購買時價格"
    )

    class Meta:
        verbose_name = "訂單項"
        verbose_name_plural = "訂單項"
        # 確保一個座位不會被重複加入到同一個訂單項中
        unique_together = ('order', 'seat')
        ordering = ['order', 'seat__row', 'seat__column']

    def __str__(self):
        seat_info = f"{self.seat.row}{self.seat.column}" if self.seat else "未知座位"
        return f"訂單 {self.order.order_number} - 座位 {seat_info}"