# Generated by Django 5.1 on 2024-08-27 13:07

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0009_alter_booking_trip_datetime'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='trip_datetime',
            field=models.DateField(default=django.utils.timezone.now),
        ),
    ]
