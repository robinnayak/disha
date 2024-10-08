# Generated by Django 5.1 on 2024-09-16 14:04

import cloudinary.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0009_temporaryuser_last_login'),
    ]

    operations = [
        migrations.AlterField(
            model_name='driver',
            name='profile_image',
            field=cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True, verbose_name='profile_images'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='profile_image',
            field=cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True, verbose_name='profile_images'),
        ),
    ]
