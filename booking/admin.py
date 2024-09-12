from django.contrib import admin
from .models import Booking,Ticket,DailyEarnings

# Register your models here.

admin.site.register(Ticket)
# admin.site.register(DailyEarnings)

class BookingAdmin(admin.ModelAdmin):
    
    list_display = ['id','booking_id','trip','trip_datetime','passenger','num_passengers','price','booking_datetime','is_confirmed','is_paid']
    list_filter = ['trip','passenger','is_confirmed','is_paid']
    search_fields = ['trip','passenger','is_confirmed','is_paid']
    list_per_page = 10
    
admin.site.register(Booking, BookingAdmin)

from django.contrib import admin
from .models import DailyEarnings  # Import the DailyEarnings model

class DailyEarningsAdmin(admin.ModelAdmin):
    list_display = (
        'id',  # Display the ID of the DailyEarnings instance
        'trip',  # Display the related trip
        'trip_date',  # Display the trip date
        'num_passengers_on_that_day',  # Display the number of passengers on that day
        'total_earnings',  # Display the total earnings
        'is_completed',  # Display whether the trip is completed
    )
    list_filter = (
        'trip_date',  # Filter by trip date
        'is_completed',  # Filter by completion status
    )
    search_fields = (
        'trip__from_location',  # Allow searching by trip's from location
        'trip__to_location',  # Allow searching by trip's to location
        'trip__organization__name',  # Allow searching by organization's name
        'trip__driver__name',  # Allow searching by driver's name
    )
    filter_horizontal = ('bookings',)  # Enable a horizontal filter for the bookings many-to-many field
    ordering = ('-trip_date',)  # Order by trip date in descending order (most recent first)

# Register the DailyEarnings model with the customized admin class
admin.site.register(DailyEarnings, DailyEarningsAdmin)
