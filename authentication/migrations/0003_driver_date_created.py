# Generated by Django 5.1 on 2024-08-29 15:18

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_passenger'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='date_created',
            field=models.DateTimeField(default=datetime.datetime(2024, 8, 29, 15, 18, 8, 497832, tzinfo=datetime.timezone.utc)),
        ),
    ]
