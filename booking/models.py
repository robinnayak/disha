# booking/models.py

from django.db import models
from django.utils import timezone
from organization.models import Trip,TripPrice, Seat
from authentication.models import Passenger
from django.conf import settings
import os
from rest_framework.serializers import ValidationError
import random
from django.db.models.signals import post_save
from django.dispatch import receiver

class Booking(models.Model):
    booking_id = models.CharField(max_length=200, unique=True, editable=False)
    passenger = models.ForeignKey(Passenger, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    trip_datetime = models.DateField(default=timezone.now)
    num_passengers = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    booking_datetime = models.DateTimeField(auto_now_add=True)
    seats = models.ManyToManyField(Seat, related_name="bookings", blank=True)
    is_confirmed = models.BooleanField(default=False, db_index=True)
    is_paid = models.BooleanField(default=False, db_index=True)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._seats_updated = False  # Add this line to initialize the attribute

    def save(self, *args, **kwargs):
        print("Running save method...")

        if not self.booking_id:
            
            from_location = self.trip.from_location[:3].upper()
            to_location = self.trip.to_location[:3].upper()
            random_number = random.randint(100000, 999999)
            self.booking_id = f"BOK-{from_location}{to_location}-{random_number}"
            print(f"Generated booking ID: {self.booking_id}")

        self.trip_datetime = self.trip.start_datetime.date()
        self.price = self.trip.price.price * self.num_passengers
        print(f"Calculated price: {self.price}")

        super().save(*args, **kwargs)
        print("Booking saved successfully.")

        self.generate_or_update_ticket()

    def update_seat_occupation_and_vehicle_availability(self):
        print("Running update_seat_occupation_and_vehicle_availability method...")
        
        # Check if the instance is being created (id is None)
        if self.pk is None:
            if self.seats.exists():
                print(f"Updating {self.seats.count()} seat(s) to occupied status.")
                self.num_passengers = self.seats.count()
                self.seats.update(is_occupied=True)
                self.trip.vehicle.available_seat -= self.num_passengers
                self.trip.vehicle.save()
                print(f"Updated vehicle available seats: {self.trip.vehicle.available_seat}")
            else:
                print("No seats selected for booking.")
        else:
            print("Instance is being updated, not running seat occupation and vehicle availability update.")
        
    def __str__(self) -> str:
        return f"{self.booking_id} - {self.passenger.user.username}"

    def delete(self, *args, **kwargs):
        self.reset_seat_occupation_and_vehicle_availability()
        super().delete(*args, **kwargs)

    def reset_seat_occupation_and_vehicle_availability(self):
        print("Running reset_seat_occupation_and_vehicle_availability method...")
        if self.seats.exists():
            print(f"Updating {self.seats.count()} seat(s) to available status.")
            self.seats.update(is_occupied=False)
            self.trip.vehicle.available_seat += self.seats.count()
            self.trip.vehicle.save()
            print(f"Updated vehicle available seats: {self.trip.vehicle.available_seat}")

    def generate_or_update_ticket(self):
        ticket_content = self.generate_ticket_content()
        filename = f"{self.booking_id}.txt"
        ticket_dir = os.path.join(settings.MEDIA_ROOT, 'tickets')
        ticket_file_path = os.path.join(ticket_dir, filename)

        if not os.path.exists(ticket_dir):
            os.makedirs(ticket_dir)

        # Create or update the ticket record
        ticket, created = Ticket.objects.get_or_create(booking=self)
        try:
            with open(ticket_file_path, 'w') as ticket_file:
                ticket_file.write(ticket_content)
            ticket.ticket_file = ticket_file_path
            ticket.save()
        except Exception as e:
            raise ValidationError(f"Error creating or updating ticket file: {str(e)}")

    def generate_ticket_content(self):
        """Generate the content for the ticket file."""
        seats_list = ', '.join(seat.seat_number for seat in self.seats.all())
        vehicle_details = f"Vehicle: {self.trip.vehicle.company_made} {self.trip.vehicle.model} {self.trip.vehicle.color}, Plate: {self.trip.vehicle.license_plate_number}"
        return f"""
        -------------------------------------
        Organization: {self.trip.organization.user.username}
        Booking ID: {self.booking_id}
        Booking Date and Time: {self.booking_datetime.strftime("%Y-%m-%d %H:%M:%S")}
        Passenger: {self.passenger.user.username}
        Trip: {self.trip.from_location} to {self.trip.to_location}
        No. of Passengers: {self.num_passengers}
        Seats: {seats_list}
        Price per Person: {self.trip.price.price}
        Total Price: {self.price}
        Trip Date: {self.trip.start_datetime.strftime("%Y-%m-%d %H:%M:%S")}
        Ticket Booked Time: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}
        Driver: {self.trip.vehicle.driver.user.username}
        {vehicle_details}
        Status: {'Confirmed' if self.is_confirmed else 'Not Confirmed'}, {'Paid' if self.is_paid else 'Not Paid'}
        -------------------------------------
        """

class Ticket(models.Model):
    ticket_id = models.CharField(max_length=200, unique=True, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    ticket_file = models.FileField(upload_to='tickets/', max_length=200)

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            from_location = self.booking.trip.from_location[:2].upper()
            to_location = self.booking.trip.to_location[:2].upper()
            random_digits = ''.join(random.choices('0123456789', k=9))
            self.ticket_id = f"TK-{from_location}-{to_location}-{random_digits}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ticket for {self.booking.trip.vehicle.registration_number} - {self.booking.trip.from_location} to {self.booking.trip.to_location}"

class DailyEarnings(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='daily_earnings')
    trip_date = models.DateField(default=timezone.now)  # Default to today's date
    num_passengers_on_that_day = models.PositiveIntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    bookings = models.ManyToManyField(Booking, related_name='daily_earnings', blank=True)
    is_completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Earnings for {self.trip_date} - Trip ID: {self.trip.trip_id}"
        

    def calculate_total_earnings_and_passengers(self):
        self.is_completed = True
        bookings = self.bookings.filter(trip_datetime=self.trip_date)
        self.num_passengers_on_that_day = sum(booking.num_passengers for booking in bookings)
        self.total_earnings = sum(booking.price for booking in bookings)
        self.save()