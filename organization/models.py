from django.db import models
from authentication.models import Organization, Driver
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from rest_framework import serializers
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
from cloudinary.models import CloudinaryField
# Review Model
class Review(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Star'),
        (3, '3 Star'),
        (4, '4 Star'),
        (5, '5 Star'),
    ]
    rating = models.IntegerField(choices=RATING_CHOICES, help_text="Rating out of 5")
    comment = models.TextField(blank=True, null=True, help_text="Optional comment for the review")
    created_at = models.DateTimeField(auto_now_add=True)

    reviewer_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='reviewer_reviews')
    reviewer_object_id = models.PositiveIntegerField()
    reviewer = GenericForeignKey('reviewer_content_type', 'reviewer_object_id')

    reviewee_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='reviewee_reviews')
    reviewee_object_id = models.PositiveIntegerField()
    reviewee = GenericForeignKey('reviewee_content_type', 'reviewee_object_id')

    def __str__(self):
        reviewer_name = getattr(self.reviewer, 'username', 'unknown')
        reviewee_name = getattr(self.reviewee, 'username', 'unknown')
        return f"Review by {reviewer_name} for {reviewee_name} - {self.rating} Stars"

# Vehicle Model
class Vehicle(models.Model):
    VEHICLE_TYPE_CHOICES = (
        ('jeep', 'Jeep'),
        ('hilux', 'Hilux'),
        ('bike', 'Bike'),
        ('bus', 'Bus'),
        ('car', 'Car'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_query_name="vehicle_organization")
    driver = models.OneToOneField(Driver, on_delete=models.SET_NULL, blank=True, null=True, related_query_name="vehicle_driver")
    registration_number = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_TYPE_CHOICES, db_index=True)
    company_made = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=30, default="black")
    seating_capacity = models.PositiveIntegerField(default=0)
    license_plate_number = models.CharField(max_length=10, unique=True)
    insurance_expiry_date = models.DateField()
    fitness_certificate_expiry_date = models.DateField()
    # image = models.ImageField(upload_to='vehicle_images', blank=True, null=True)
    image = CloudinaryField('vehicle_images', blank=True, null=True)
    
    available_seat = models.PositiveIntegerField(default=0)

    def reset_all_seats(self):
        """
        Resets all seats in this vehicle to unoccupied status and updates the available seat count.
        """
        self.seats.update(is_occupied=False)
        self.available_seat = self.seating_capacity
        self.save()

    def save(self, *args, **kwargs):
        """Ensure available seats are properly set before saving."""
        if self.available_seat < 0:
            raise serializers.ValidationError("Available seats cannot be less than zero.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.registration_number} - {self.company_made} {self.model}"
    

# Seat Model
class Seat(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=5)
    is_occupied = models.BooleanField(default=False)
    reserved_for_driver = models.BooleanField(default=False)
    reserved_for_conductor = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        """Set seat as occupied and reserved for the driver if it's the first seat in the vehicle."""
        if not self.pk and not self.vehicle.seats.exists():
            self.is_occupied = True
            self.reserved_for_driver = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Seat {self.seat_number} in {self.vehicle.registration_number}"

    def reserve_for_conductor(self):
        """Reserve the seat for the conductor if it's not occupied or reserved for the driver."""
        if not self.reserved_for_driver and not self.is_occupied:
            self.reserved_for_conductor = True
            self.save()
            return True
        return False


trip_choices = [
    ('kathmandu', 'Kathmandu'),
    ('pokhara', 'Pokhara'),
    ('chitwan', 'Chitwan'),
    ('lumbini', 'Lumbini'),
    ('janakpur', 'Janakpur'),
    ('biratnagar', 'Biratnagar'),
    ('birgunj', 'Birgunj'),
    ('dharan', 'Dharan'),
    ('butwal', 'Butwal'),
    ('hetauda', 'Hetauda'),
    ('nepalgunj', 'Nepalgunj'),
    ('dhangadhi', 'Dhangadhi'),
    ('bharatpur', 'Bharatpur'),
    ('itahari', 'Itahari'),
    ('gaur', 'Gaur'),
    ('tansen', 'Tansen'),
    ('jomsom', 'Jomsom'),
    ('namche_bazaar', 'Namche Bazaar'),
    ('manang', 'Manang'),
    ('lukla', 'Lukla'),
    ('jaleswor', 'Jaleswor'),
    ('mathayani', 'Mathayani'),
]

# Trip Model
class Trip(models.Model):
    trip_id = models.CharField(max_length=100, unique=True, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='organization')
    vehicle = models.OneToOneField(Vehicle, on_delete=models.CASCADE, related_name='vehicle')
    from_location = models.CharField(max_length=100, choices= trip_choices, db_index=True)
    to_location = models.CharField(max_length=100, choices=trip_choices, db_index=True)
    is_reverese_trip = models.BooleanField(default=False)
    duration = models.DurationField(blank=True, null=True)
    distance = models.FloatField(help_text="Distance in kilometers", blank=True, null=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    is_completed = models.BooleanField(default=False)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    passenger_count = models.PositiveIntegerField(default=0)
    last_updated_by = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        """Generate trip ID, calculate duration, and reset vehicle seats if trip is completed."""
        if not self.trip_id:
            self.trip_id = self.generate_trip_id()

        if not self.duration and self.distance:
            self.duration = self.calculate_duration_based_on_distance()

        # Ensure end_datetime is set to 7 hours after start_datetime
        if self.start_datetime and not self.end_datetime:
            self.end_datetime = self.start_datetime + timedelta(hours=7)

        if self.start_datetime:
            self.end_datetime = self.start_datetime + timedelta(hours=7)
        
        # if self.is_completed:
        #     self.vehicle.reset_all_seats()

        super().save(*args, **kwargs)

    def generate_trip_id(self):
        """Generate a unique trip ID based on locations and timestamp."""
        prefix = f"{self.from_location[:3]}{self.to_location[:3]}"
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        return f"{prefix}{timestamp}".upper()

    def calculate_duration_based_on_distance(self):
        """Estimate trip duration based on distance, assuming an average speed of 60 km/h."""
        return timezone.timedelta(hours=self.distance / 60)

    def calculate_earnings(self):
        """Calculate total earnings and passenger count from confirmed bookings."""
        confirmed_paid_bookings = self.booking_set.filter(is_confirmed=True, is_paid=True)
        confirmed_bookings = self.booking_set.filter(is_confirmed=True)
        self.total_earnings = confirmed_paid_bookings.aggregate(Sum('price'))['price__sum'] or 0
        self.passenger_count = confirmed_bookings.aggregate(Sum('num_passengers'))['num_passengers__sum'] or 0
        self.save()
        return self.total_earnings, self.passenger_count

    def __str__(self) -> str:
        return self.trip_id

# TripPrice Model
class TripPrice(models.Model):
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name='price')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Trip from {self.trip.from_location} to {self.trip.to_location} - Price: {self.price}"



    