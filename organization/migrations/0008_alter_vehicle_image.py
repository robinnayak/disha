# Generated by Django 5.1 on 2024-09-16 14:04

import cloudinary.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0007_alter_vehicle_driver'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vehicle',
            name='image',
            field=cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True, verbose_name='vehicle_images'),
        ),
    ]
