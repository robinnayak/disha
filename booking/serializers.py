from rest_framework import serializers
from authentication.models import Passenger, Driver
from authentication.serializers import PassengerSerializer
from organization.models import Trip, Seat
from organization.serializers import TripSerializer, SeatSerializer
from .models import Booking, Ticket, DailyEarnings
from datetime import timedelta

class BookingSerializer(serializers.ModelSerializer):
    
    """Serializer for handling Booking data, including validation and creation logic."""
    
    # Read-only fields from related models
    passenger_username = serializers.ReadOnlyField(source='passenger.user.username')
    trip_from_location = serializers.ReadOnlyField(source='trip.from_location')
    trip_to_location = serializers.ReadOnlyField(source='trip.to_location')
    is_completed = serializers.ReadOnlyField(source='trip.is_completed')
    price_per_person = serializers.DecimalField(source='trip.price.price', max_digits=10, decimal_places=2, read_only=True)

    # Related serializer for seats
    seats = SeatSerializer(many=True)
    class Meta:
        model = Booking
        fields = '__all__'
        extra_kwargs = {
            'num_passengers': {'required': False},
            'vehicle':{'required':False},
            'passenger':{'required':False},
            'trip':{'required':False},
        }

    def validate(self, data):
        """Custom validation logic for Booking instances."""
        seats_data = data.get('seats', [])
        trip_id = data.get('trip_id')

        # Prevent updating if the booking is already confirmed or paid
        if self.instance:
            if self.instance.is_confirmed:
                raise serializers.ValidationError({"message": "Booking is already confirmed and cannot be updated."})
            if self.instance.is_paid:
                raise serializers.ValidationError({"message": "Booking is already paid and cannot be updated."})

        # Ensure at least one seat is selected
        if not seats_data:
            raise serializers.ValidationError({"seats": "At least one seat must be selected."})

        # Set the number of passengers based on the number of selected seats
        data['num_passengers'] = len(seats_data)

        return data

    def create(self, validated_data):
        """Create a new Booking instance with the selected seats."""
        user = self.context.get('user')
        trip_id = self.context.get('trip_id')
        seats_data = validated_data.pop('seats', [])

        # Assign passenger to the booking
        try:
            passenger = Passenger.objects.get(user=user)
            validated_data['passenger'] = passenger
        except Passenger.DoesNotExist:
            raise serializers.ValidationError({"message": "Passenger not found"})

        # Assign trip to the booking and validate seat availability
        try:
            trip = Trip.objects.select_related('vehicle').get(trip_id=trip_id)
            available_seats = trip.vehicle.available_seat
            if len(seats_data) > available_seats:
                raise serializers.ValidationError({"seats": f"Not enough seats available. Only {available_seats} seats are left."})
            validated_data['trip'] = trip
        except Trip.DoesNotExist:
            raise serializers.ValidationError({"message": "Trip not found"})

        # Check if selected seats are occupied and validate seat selection
        seat_numbers = [seat['seat_number'] for seat in seats_data]
        seats = trip.vehicle.seats.filter(seat_number__in=seat_numbers, is_occupied=False)
        
        if seats.count() != len(seat_numbers):
            raise serializers.ValidationError({"seats": "One or more seats are already occupied or invalid."})

        # Create the booking and assign the seats
        booking = Booking.objects.create(**validated_data)
        booking.seats.set(seats)
        booking.save()

        # Update seat occupation and vehicle availability
        self.update_seat_occupation_and_vehicle_availability(booking)

        return booking

    def update_seat_occupation_and_vehicle_availability(self, booking):
        """Update the status of selected seats and the vehicle's available seat count."""
        if booking.seats.exists():
            num_passengers = booking.seats.count()
            booking.seats.update(is_occupied=True)
            booking.trip.vehicle.available_seat -= num_passengers
            booking.trip.vehicle.save()

    def update(self, instance, validated_data):
        """Update a Booking instance with partial data, excluding seats."""
        validated_data.pop('seats', None)
        instance.is_confirmed = validated_data.get('is_confirmed', instance.is_confirmed)
        instance.is_paid = validated_data.get('is_paid', instance.is_paid)
        instance.save()
        return instance


class TicketSerializer(serializers.ModelSerializer):
    """Serializer for handling Ticket data."""
    booking_id = serializers.ReadOnlyField(source='booking.booking_id')
    class Meta:
        model = Ticket
        fields = '__all__'

    def create(self, validated_data):
        """Create a new Ticket instance associated with a booking."""
        booking_id = self.context.get('booking_id')
        try:
            booking = Booking.objects.get(id=booking_id)
            validated_data['booking'] = booking
        except Booking.DoesNotExist:
            raise serializers.ValidationError({"message": "Booking not found"})

        return Ticket.objects.create(**validated_data)


class DailyEarningSerializer(serializers.ModelSerializer):
    """Serializer for handling DailyEarnings data, including calculation logic."""

    trip = TripSerializer(read_only=True)
    bookings = BookingSerializer(many=True, read_only=True)

    class Meta:
        model = DailyEarnings
        fields = '__all__'
        extra_kwargs = {
            'num_passengers_on_that_day': {'required': False},
            'total_earnings': {'required': False},
        }

    def create(self, validated_data):
        """Create a DailyEarnings entry with the related trip and bookings."""
        trip_id = self.context.get('trip_id')
        user = self.context.get('user')
        
        if user.is_organization:
            organization = user.profile.organization
        elif user.is_driver:
            driver = user.driver_profile
        else:
            raise serializers.ValidationError("User must be associated with an organization or a driver.")
        
        try:
            if user.is_organization:
                trip = Trip.objects.select_related('organization', 'vehicle').get(
                    trip_id=trip_id,
                    organization=organization
                )
            elif user.is_driver:
                trip = Trip.objects.select_related('organization', 'vehicle').get(
                    trip_id=trip_id,
                    vehicle__driver=driver
                )
            else:
                raise serializers.ValidationError("User must be associated with an organization or a driver.")
            
            # Check if the trip is completed
            if not trip.is_completed:
                raise serializers.ValidationError({"message": "Trip Need to be completed." })
            
            validated_data['trip'] = trip
        except Trip.DoesNotExist:
            raise serializers.ValidationError({"message": "Trip not found."})     
        
        
        bookings = Booking.objects.filter(trip=trip, is_confirmed=True, is_paid=True)
        if not bookings.exists():
            raise serializers.ValidationError({"message": "No bookings found for the trip."})

        # Set trip date and ensure no duplicate DailyEarnings entries for the same trip date
        latest_trip_datetime = bookings.latest('trip_datetime').trip_datetime
        validated_data['trip_date'] = latest_trip_datetime
        
        # Ensure no duplicate DailyEarnings entries for the same trip date
        if DailyEarnings.objects.filter(trip=trip, trip_date=latest_trip_datetime).exists():
            raise serializers.ValidationError({"message": "DailyEarnings entry already exists or no Bookings are available for this date."})

        # Check if trip_date matches trip start_datetime
        if latest_trip_datetime != trip.start_datetime.date():
            raise serializers.ValidationError({"message": "Trip date does not match the trip's start date."})


        # Create DailyEarnings entry and assign bookings
        daily_earning = DailyEarnings.objects.create(**validated_data)
        daily_earning.bookings.set(bookings.filter(trip_datetime=latest_trip_datetime))
        
        # Calculate total earnings and number of passengers
        daily_earning.calculate_total_earnings_and_passengers()
        
        # Reset vehicle seats
        vehicle = trip.vehicle
        vehicle.reset_all_seats()
        
        #Total earnings added to the organization from the total no of trips
        organization = trip.organization
        organization.update_total_earnings()
        
        #Total earnings added to the Driver 
        driver = vehicle.driver
        driver.update_total_earnings()
        
        # Update the trip's start date to the next day from the total no of trips
        trip.start_datetime = trip.start_datetime + timedelta(days=1)
        trip.is_completed = False
        trip.total_earnings = 0.0
        trip.passenger_count = 0
        trip.last_updated_by = user.username
        trip.save()
    
        return daily_earning
