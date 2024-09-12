from rest_framework import serializers
from authentication.models import CustomUser, Driver, Organization, Passenger
from authentication.serializers import CustomUserSerializer, OrganizationSerializer, DriverSerializer, PassengerSerializer
from .models import Vehicle, Review, Seat, Trip, TripPrice
import random
import string
from django.utils import timezone
from datetime import timedelta


class VehicleSerializer(serializers.ModelSerializer):
    organization = serializers.ReadOnlyField(source='organization.user.username')
    driver = serializers.ReadOnlyField(source='driver.user.username')
    license_number = serializers.ReadOnlyField(source='driver.license_number')
    
    class Meta:
        model = Vehicle
        fields = '__all__'
        extra_kwargs = {
            'registration_number': {'read_only': True,'required':False}
        }
        

    def create(self, validated_data):
        user = self.context.get('user')
        dri_license = self.context.get('dri_license')
        print("dri license",dri_license) 

        # Assign organization and driver to the vehicle
        validated_data = self._assign_organization_and_driver(validated_data, user, dri_license)
        
        # Generate registration number
        veh_id = self._generate_random_string()
        reg_id = self._generate_registration_number(veh_id, validated_data['organization'].user.username)
        validated_data['registration_number'] = reg_id

        # Create the vehicle and reset its available seats
        vehicle = Vehicle.objects.create(**validated_data)
        vehicle.reset_all_seats()
        self._assign_organization_to_driver(vehicle)

        return vehicle
    
    
    def update(self, instance, validated_data):
        """
        Update a vehicle, ensuring that certain fields cannot be modified.
        """
        user = self.context.get('user')
        dri_license = self.context.get('dri_license')
        
        # These fields should not be updated
        validated_data.pop('registration_number', None)
        validated_data.pop('license_plate_number', None)
        validated_data.pop('organization', None)
        validated_data.pop('driver', None)

        # Assign organization and driver to the vehicle
        validated_data = self._assign_organization_and_driver(validated_data, user, dri_license)
        # Update allowed fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        instance.save()
        self._assign_organization_to_driver(instance)
        return instance
        
    
    def _assign_organization_to_driver(self,vehicle):
        """
        Assign organization to the driver of the vehicle.
        """
        if vehicle.driver:
            vehicle.driver.organization = vehicle.organization
            vehicle.driver.save()
    
    
    def reset_all_seats(self):
        """
        Resets all seats in this vehicle to unoccupied status.
        """
        # Reset each seat to unoccupied for this specific vehicle
        self.seats.update(is_occupied=False)

        # Update vehicle's available seat count
        self.available_seat = self.seating_capacity
        self.save()
            
    def _assign_organization_and_driver(self, validated_data, user, dri_license):
        """
        Assign organization and driver to the vehicle based on the current user and driver license number.
        """
        if dri_license:
            try:
                driver = Driver.objects.get(license_number=dri_license)
                validated_data['driver'] = driver
            except Driver.DoesNotExist:
                raise serializers.ValidationError("Driver with the provided license number does not exist.")
        else:
            validated_data['driver'] = None

        # Assign organization based on the current user
        try:
            organization = Organization.objects.get(user=user)
            validated_data['organization'] = organization
        except Organization.DoesNotExist:
            raise serializers.ValidationError("Organization for the provided user does not exist.")

        return validated_data

    @staticmethod
    def _generate_random_string(length=4):
        """Generate a random string of digits for vehicle ID."""
        return ''.join(random.choices(string.digits, k=length))

    @staticmethod
    def _generate_registration_number(id, username):
        """Generate a vehicle registration number."""
        org_initials = username[:2].upper()
        return f"VEH-{org_initials}-{id}"


class ReviewSerializer(serializers.ModelSerializer):
    reviewer = serializers.SerializerMethodField(read_only=True)
    reviewee = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Review
        fields = '__all__'

    def get_reviewer(self, obj):
        """Return the serialized reviewer object based on its type."""
        reviewer = obj.reviewer
        if isinstance(reviewer, Passenger):
            return PassengerSerializer(reviewer).data
        elif isinstance(reviewer, Driver):
            return DriverSerializer(reviewer).data
        elif isinstance(reviewer, Organization):
            return OrganizationSerializer(reviewer).data
        return None

    def get_reviewee(self, obj):
        """Return the serialized reviewee object based on its type."""
        reviewee = obj.reviewee
        if isinstance(reviewee, Passenger):
            return PassengerSerializer(reviewee).data
        elif isinstance(reviewee, Driver):
            return DriverSerializer(reviewee).data
        elif isinstance(reviewee, Organization):
            return OrganizationSerializer(reviewee).data
        return None

    def validate(self, data):
        """
        Ensure that reviewer and reviewee are not the same entity.
        """
        if data['reviewer_content_type'] == data['reviewee_content_type'] and data['reviewer_object_id'] == data['reviewee_object_id']:
            raise serializers.ValidationError("Reviewer and reviewee cannot be the same.")
        
        return data

class SeatSerializer(serializers.ModelSerializer):
    organization = serializers.ReadOnlyField(source='vehicle.organization.user.username')
    driver = serializers.ReadOnlyField(source='vehicle.driver.user.username')
    vehicle_registration_number = serializers.ReadOnlyField(source='vehicle.registration_number')
    
    class Meta:
        model = Seat
        fields = '__all__'
        extra_kwargs = {
            'vehicle': {'read_only': True, 'required': False},
            
        }
    def update(self, instance, validated_data):
        """
        Update seat information, including seat number and occupancy status.
        """
        seat_number = validated_data.get('seat_number', instance.seat_number)
        is_occupied = validated_data.get('is_occupied', instance.is_occupied)

        if seat_number != instance.seat_number:
            instance.seat_number = seat_number
        
        if is_occupied != instance.is_occupied:
            instance.is_occupied = is_occupied
            # Adjust vehicle's available seating capacity accordingly
            vehicle = instance.vehicle
            if vehicle:
                vehicle.seating_capacity += -1 if is_occupied else 1
                vehicle.save()

        instance.save()
        return instance

    @staticmethod
    def reset_all_seats():
        """
        Resets all seats to unoccupied status at the end of the day.
        """
        vehicles = Vehicle.objects.prefetch_related('seats').all()

        for vehicle in vehicles:
            # Reset each seat to unoccupied
            vehicle.seats.update(is_occupied=False)

            # Update vehicle's available seat count
            vehicle.available_seat = vehicle.seating_capacity
            vehicle.save()


class TripPriceSerializer(serializers.ModelSerializer):
    trip_id  = serializers.ReadOnlyField(source='trip.trip_price')
    vehicle_id = serializers.ReadOnlyField(source='vehicle.registration_number')

    class Meta:
        model = TripPrice
        fields = '__all__'

    def create(self, validated_data):
        """
        Create a trip price instance, ensuring correct trip and vehicle assignment.
        """
        trip_id = self.context.get('trip_id')
        vehicle_registration_number = self.context.get('vehicle_registration_number')
        org_email = self.context.get('org_email')

        try:
            trip = Trip.objects.get(id=trip_id, organization__user__email=org_email)
        except Trip.DoesNotExist:
            raise serializers.ValidationError("Trip with the provided ID and organization email does not exist.")

        try:
            vehicle = Vehicle.objects.get(registration_number=vehicle_registration_number)
        except Vehicle.DoesNotExist:
            raise serializers.ValidationError("Vehicle with the provided registration number does not exist.")

        validated_data['trip'] = trip
        validated_data['vehicle'] = vehicle

        return TripPrice.objects.create(**validated_data)

class TripSerializer(serializers.ModelSerializer):
    organization = serializers.ReadOnlyField(source='vehicle.organization.user.username')
    driver = serializers.ReadOnlyField(source='vehicle.driver.user.username')
    vehicle_registration_number = serializers.ReadOnlyField(source='vehicle.registration_number')
    license_plate_number = serializers.ReadOnlyField(source='vehicle.license_plate_number')
    vehicle_type = serializers.ReadOnlyField(source='vehicle.vehicle_type')
    color = serializers.ReadOnlyField(source='vehicle.color')
    vehicle_image = serializers.SerializerMethodField()  # Changed to SerializerMethodField
    trip_price = TripPriceSerializer(source='price', read_only=True)
    available_seat = serializers.ReadOnlyField(source='vehicle.available_seat')
    seats = SeatSerializer(source='vehicle.seats', many=True, read_only=True)

    class Meta:
        model = Trip
        fields = '__all__'
        extra_kwargs = {
            'vehicle': {'required': False},
        }

    def get_vehicle_image(self, obj):
        """Return the URL of the vehicle image if it exists, otherwise return None."""
        vehicle = obj.vehicle
        if vehicle and vehicle.image:
            return vehicle.image.url
        return None  # Return None or an empty string if there is no image associated

    def create(self, validated_data):
        """
        Create a trip instance, ensuring that the organization and vehicle are correctly assigned.
        """
        user = self.context.get('user')
        vehicle_registration = self.context.get('registration_number')

        if vehicle_registration:
            try:
                vehicle = Vehicle.objects.get(registration_number=vehicle_registration)
                validated_data['vehicle'] = vehicle
            except Vehicle.DoesNotExist:
                raise serializers.ValidationError("Vehicle with the provided registration number does not exist.")
        else:
            raise serializers.ValidationError("Vehicle registration number is required to create a trip.")

        if user:
            try:
                organization = Organization.objects.get(user=user)
                validated_data['organization'] = organization
            except Organization.DoesNotExist:
                raise serializers.ValidationError("Organization with the provided email does not exist.")

        return Trip.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update a trip, with restrictions on certain fields and automatic end time adjustment.
        """
        # Restricted fields
        restricted_fields = ['organization', 'trip_id', 'vehicle', 'from_location', 'to_location']
        for field in restricted_fields:
            validated_data.pop(field, None)
        
        # Check permission for updating
        user = self.context.get('user')
        if not (user == instance.organization.user or user == instance.vehicle.driver.user):
            raise serializers.ValidationError("You do not have permission to update this trip.")
        
        # Update allowed fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.last_updated_by = user.username
        instance.save()
        return instance
