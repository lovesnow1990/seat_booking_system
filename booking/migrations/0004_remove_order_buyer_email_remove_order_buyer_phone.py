# Generated by Django 5.2.4 on 2025-07-06 14:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0003_alter_event_base_price_alter_seat_price'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='buyer_email',
        ),
        migrations.RemoveField(
            model_name='order',
            name='buyer_phone',
        ),
    ]
