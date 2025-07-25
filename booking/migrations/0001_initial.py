# Generated by Django 5.2.4 on 2025-07-06 08:22

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='場次名稱')),
                ('description', models.TextField(blank=True, null=True, verbose_name='場次描述')),
                ('event_date', models.DateField(verbose_name='活動日期')),
                ('event_time', models.TimeField(verbose_name='活動時間')),
                ('base_price', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='基本票價')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否啟用')),
            ],
            options={
                'verbose_name': '場次',
                'verbose_name_plural': '場次',
            },
        ),
        migrations.CreateModel(
            name='Venue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True, verbose_name='場地名稱')),
                ('layout_data', models.JSONField(blank=True, default=dict, null=True, verbose_name='座位佈局資料（JSON）')),
                ('capacity', models.IntegerField(verbose_name='總座位數')),
            ],
            options={
                'verbose_name': '場地',
                'verbose_name_plural': '場地',
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_number', models.CharField(max_length=100, unique=True, verbose_name='訂單號')),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='總金額')),
                ('status', models.CharField(choices=[('pending', '待支付'), ('paid', '已支付'), ('cancelled', '已取消'), ('refunded', '已退款')], default='pending', max_length=20, verbose_name='訂單狀態')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='創建時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                ('payment_id', models.CharField(blank=True, max_length=255, null=True, verbose_name='支付交易ID')),
                ('buyer_name', models.CharField(max_length=100, verbose_name='購買者姓名')),
                ('buyer_email', models.EmailField(max_length=254, verbose_name='購買者Email')),
                ('buyer_phone', models.CharField(blank=True, max_length=20, null=True, verbose_name='購買者電話')),
                ('event', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='booking.event', verbose_name='所屬場次')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='訂購者')),
            ],
            options={
                'verbose_name': '訂單',
                'verbose_name_plural': '訂單',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Seat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('row', models.CharField(max_length=10, verbose_name='行號')),
                ('column', models.IntegerField(verbose_name='座位號')),
                ('status', models.CharField(choices=[('available', '可選'), ('locked', '已鎖定'), ('sold', '已售出')], default='available', max_length=20, verbose_name='座位狀態')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='座位價格')),
                ('locked_until', models.DateTimeField(blank=True, null=True, verbose_name='鎖定到期時間')),
                ('locked_by_session', models.CharField(blank=True, max_length=255, null=True, verbose_name='鎖定會話ID/使用者ID（可選）')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.event', verbose_name='所屬場次')),
            ],
            options={
                'verbose_name': '座位',
                'verbose_name_plural': '座位',
                'unique_together': {('event', 'row', 'column')},
            },
        ),
        migrations.AddField(
            model_name='event',
            name='venue',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.venue', verbose_name='所屬場地'),
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)], verbose_name='數量')),
                ('price_at_purchase', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='購買時價格')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='booking.order', verbose_name='所屬訂單')),
                ('seat', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='booking.seat', verbose_name='購買的座位')),
            ],
            options={
                'verbose_name': '訂單項',
                'verbose_name_plural': '訂單項',
                'unique_together': {('order', 'seat')},
            },
        ),
        migrations.AlterUniqueTogether(
            name='event',
            unique_together={('venue', 'event_date', 'event_time', 'name')},
        ),
    ]
