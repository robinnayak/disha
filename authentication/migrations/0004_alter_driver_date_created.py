# Generated by Django 5.1 on 2024-08-29 15:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_driver_date_created'),
    ]

    operations = [
        migrations.AlterField(
            model_name='driver',
            name='date_created',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
