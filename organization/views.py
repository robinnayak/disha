from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError

from authentication.renderers import UserRenderer
from authentication.models import Driver
from authentication.serializers import DriverSerializer
from .models import Vehicle, Trip, TripPrice, Seat
from .serializers import VehicleSerializer, TripPriceSerializer, TripSerializer, SeatSerializer

class VehicleView(APIView):
    """
    API view to handle vehicle-related operations: 
    - Retrieve vehicles based on the user's role (organization, driver, or passenger)
    - Create a new vehicle and assign seats for organizations
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def get(self, request):
        """Retrieve vehicles based on the user role."""
        try:
            if request.user.is_organization:
                vehicles = Vehicle.objects.filter(organization__user=request.user).select_related('organization', 'driver')
            elif request.user.is_driver:
                vehicles = Vehicle.objects.filter(driver__user=request.user).select_related('organization', 'driver')
            else:  # Passengers retrieve all vehicles with associated trip prices
                vehicles = Vehicle.objects.select_related('organization', 'driver').all()
                trip_prices = TripPrice.objects.filter(trip__vehicle__in=vehicles).select_related('trip__vehicle')

                # Efficiently build the response data
                response_data = [
                    {
                        'vehicle': VehicleSerializer(vehicle).data,
                        'trip_price': TripPriceSerializer(
                            next((tp for tp in trip_prices if tp.trip.vehicle_id == vehicle.id), None)
                        ).data
                    }
                    for vehicle in vehicles
                ]
                return Response(response_data, status=status.HTTP_200_OK)

            serializer = VehicleSerializer(vehicles, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def post(self, request):
        """Create a new vehicle with seat assignments for an organization."""
        if not request.user.is_organization:
            return Response({"error": "Only organizations can create vehicles."}, status=status.HTTP_403_FORBIDDEN)

        dri_license = request.data.get('license_number')
        # if not dri_license:
        #     return Response({"error": "License number is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the driver exists and is not already assigned to another organization
        if dri_license:
            if not Driver.objects.filter(license_number=dri_license).exists():
                return Response({"error": "Driver not found"}, status=status.HTTP_404_NOT_FOUND)
            if Vehicle.objects.filter(driver__license_number=dri_license).exists():
                raise ValidationError("This driver is already assigned to another organization.")

        serializer = VehicleSerializer(data=request.data, context={'user': request.user, 'dri_license': dri_license})
        if serializer.is_valid():
            try:
                vehicle = serializer.save()
                self._create_seats_for_vehicle(vehicle)
                return Response({"message": "Vehicle created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _create_seats_for_vehicle(self, vehicle):
        """Create seats for a vehicle based on its seating capacity."""
        if vehicle.seats.exists():
            return
        seats = [Seat(vehicle=vehicle, seat_number=f"S{str(i).zfill(3)}") for i in range(1, vehicle.seating_capacity + 1)]
        Seat.objects.bulk_create(seats)


class VehicleDetailView(APIView):
    """
    API view to handle detailed operations on a single vehicle:
    - Retrieve vehicle details
    - Update vehicle information
    - Delete a vehicle
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]
    def get(self, request, RN=None):
        """Retrieve detailed information of a specific vehicle by registration number."""
        try:
            # Fetch vehicle based on registration number and user
            vehicle = self._get_vehicle_by_user(request.user, RN)

            # Fetch related trip details for the vehicle
            trip = Trip.objects.filter(vehicle=vehicle).select_related('vehicle').first()

            # Fetch all seats related to the vehicle
            seats = Seat.objects.filter(vehicle=vehicle)

            # Serialize vehicle, trip, and seat data
            vehicle_data = VehicleSerializer(vehicle).data
            trip_data = TripSerializer(trip).data if trip else {}
            seat_data = SeatSerializer(seats, many=True).data

            # Return the response including vehicle, trip, and seat details
            return Response({
                'vehicle': vehicle_data,
                'trip': trip_data,
                'seats': seat_data
            }, status=status.HTTP_200_OK)

        except Vehicle.DoesNotExist:
            return Response({"error": "Vehicle not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    def _get_vehicle_by_user(self, user, registration_number):
        # Helper method to fetch the vehicle based on the logged-in user and registration number
        if user.is_organization:
            return Vehicle.objects.get(registration_number=registration_number, organization__user=user)
        elif user.is_driver:
            return Vehicle.objects.get(registration_number=registration_number, driver__user=user)
        else:
            raise Vehicle.DoesNotExist("User does not have permission to access this vehicle.")
        
    def put(self, request, RN=None):
        """Update an existing vehicle by registration number."""
        
        dri_license = request.data.get('license_number')
        if dri_license:
            if not Driver.objects.filter(license_number=dri_license).exists():
                return Response({"error": "Driver not found"}, status=status.HTTP_404_NOT_FOUND)
            # if Vehicle.objects.filter(driver__license_number=dri_license).exists():
            #     raise ValidationError("This driver is already assigned to another organization.")

        try:
            vehicle = self._get_vehicle_by_user(request.user, RN)
            serializer = VehicleSerializer(vehicle, data=request.data, partial=True,context={'user': request.user, 'dri_license': dri_license})

            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Vehicle updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Vehicle.DoesNotExist:
            return Response({"error": "Vehicle not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, RN=None):
        """Delete an existing vehicle by registration number."""
        try:
            vehicle = self._get_vehicle_by_user(request.user, RN)
            # Check if the vehicle has an associated driver and clear the organization
            # Check if the vehicle has an associated driver and clear the organization
            if hasattr(vehicle, 'driver') and vehicle.driver:
                vehicle.driver.organization = None
                vehicle.driver.save()
                
            # Delete the vehicle instance
            vehicle.delete()
            return Response({"message": "Vehicle deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Vehicle.DoesNotExist:
            return Response({"error": "Vehicle not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _get_vehicle_by_user(self, user, RN):
        """Helper function to retrieve a vehicle based on user role."""
        filters = {'registration_number': RN}
        if user.is_organization:
            filters['organization__user'] = user
        elif user.is_driver:
            filters['driver__user'] = user
        return get_object_or_404(Vehicle, **filters)


class TripCreateAPIView(APIView):
    """
    API view to handle trip-related operations:
    - Retrieve trips based on the user role
    - Create a new trip with an associated trip price
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def get(self, request):
        """Retrieve trips based on user role."""
        try:
            if request.user.is_organization:
                trips = Trip.objects.filter(organization__user=request.user).select_related('organization', 'vehicle')
            else:
                trips = Trip.objects.all().select_related('organization', 'vehicle')

            # Calculate earnings for each trip
            for trip in trips:
                trip.calculate_earnings()

            serializer = TripSerializer(trips, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        """Create a new trip with associated trip price."""
        vehicle_registration_number = request.data.get('registration_number')
        trip_price = request.data.get('price', 0.00)

        if not vehicle_registration_number:
            return Response({"error": "Vehicle registration number is required."}, status=status.HTTP_400_BAD_REQUEST)

        vehicle = get_object_or_404(Vehicle, registration_number=vehicle_registration_number)

        serializer = TripSerializer(
            data=request.data,
            context={'user': request.user, 'registration_number': vehicle_registration_number, 'vehicle': vehicle}
        )

        if serializer.is_valid():
            try:
                trip = serializer.save()
                trip_price_instance = TripPrice.objects.create(trip=trip, price=trip_price)
                response_data = {
                    'trip': TripSerializer(trip).data,
                    'trip_price': TripPriceSerializer(trip_price_instance).data
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TripDetailView(APIView):
    """
    API view to handle detailed operations on a single trip:
    - Retrieve trip details
    - Update trip information
    - Delete a trip
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def get(self, request, trip_id=None):
        """Retrieve detailed information of a specific trip by trip ID."""
        trip = get_object_or_404(Trip, trip_id=trip_id, organization__user=request.user)
        trip.calculate_earnings()
        serializer = TripSerializer(trip)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @transaction.atomic
    def put(self, request, trip_id=None):
        """Update an existing trip by trip ID."""
        trip = get_object_or_404(Trip, trip_id=trip_id, organization__user=request.user)
        serializer = TripSerializer(trip, data=request.data, partial=True, context={'user': request.user, 'registration_number': trip.vehicle.registration_number})

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def delete(self, request, trip_id=None):
        """Delete an existing trip by trip ID."""
        trip = get_object_or_404(Trip, trip_id=trip_id, organization__user=request.user)
        trip.delete()
        return Response({"message": "Trip deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class TripResetView(APIView):
    """
    API view to handle the reset of a trip by updating its details.
    This view allows organizations or drivers to reset certain aspects of a trip.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    @transaction.atomic
    def put(self, request):
        """Reset an existing trip by updating its details."""
        trip_id = request.data.get('trip_id')
        user = request.user

        # Ensure the trip exists
        trip = get_object_or_404(Trip, trip_id=trip_id)

        # Ensure the user is either the organization or the driver associated with the trip
        if not (user == trip.organization.user or user == trip.vehicle.driver.user):
            return Response({"error": "You do not have permission to update this trip."}, status=status.HTTP_403_FORBIDDEN)

        serializer = TripSerializer(trip, data=request.data, partial=True, context={'user': user})

        if serializer.is_valid():
            serializer.save()
            
            trip.vehicle.reset_all_seats()
        
            return Response({"message": "Trip reset successfully", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DriverDetailsView(APIView):
    """
    API view to handle driver-related operations for organizations:
    - Retrieve drivers related to the organization
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def get(self, request):
        """Retrieve drivers related to the organization."""
        try:
            if not request.user.is_organization:
                return Response({"error": "Only organizations can retrieve drivers."}, status=status.HTTP_403_FORBIDDEN)

            drivers = Driver.objects.filter(organization__user=request.user).select_related('user')
            serializer = DriverSerializer(drivers, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)