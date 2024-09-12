from django.contrib import admin
from . import models
# Register your models here.

admin.site.register(models.Review)
admin.site.register(models.Vehicle)
admin.site.register(models.Seat)
admin.site.register(models.TripPrice)


class AdminTrip(admin.ModelAdmin):
    # Fields to display in the list view
    list_display = ('trip_id', 'organization', 'vehicle', 'from_location', 'to_location', 'start_datetime', 'end_datetime', 'is_completed', 'passenger_count', 'total_earnings')

    # Fields to filter the list view
    list_filter = ('is_completed', 'from_location', 'to_location', 'organization', 'start_datetime')

    # Fields to search within the admin panel
    search_fields = ('trip_id', 'vehicle__registration_number', 'from_location', 'to_location', 'organization__name')

    # Fields to display in the detailed edit view
    fields = ('trip_id', 'organization', 'vehicle', 'from_location', 'to_location', 'is_reverese_trip', 'duration', 'distance', 'start_datetime', 'end_datetime', 'is_completed', 'total_earnings', 'passenger_count', 'last_updated_by')

    # Automatically populate the trip_id field
    readonly_fields = ('trip_id',)

    # Order by start datetime in descending order
    ordering = ('-start_datetime',)

# Registering the Trip model and AdminTrip class in the admin panel
admin.site.register(models.Trip, AdminTrip)