from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from .serializers import BookingSerializer, TicketSerializer, DailyEarningSerializer
from .models import Booking, Ticket, DailyEarnings
from organization.models import TripPrice, Trip
from authentication.models import Passenger,Organization,Driver
from authentication.renderers import UserRenderer


class BookingCreateView(APIView):
    """
    API view for creating a booking. 
    Only authenticated users can create a booking.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def post(self, request):
        user = request.user
        trip_id = request.data.get('trip_id', '')
        seats = request.data.get('seats', [])
        print("seats",seats)
        print("trip_id",trip_id)
        
        if not isinstance(seats, list):
            return Response({"error": "Seats must be provided as a list."}, status=status.HTTP_400_BAD_REQUEST)

        trip = Trip.objects.filter(trip_id=trip_id).select_related('vehicle').first()
        print("trip",trip)
        if not trip:
            return Response({"error": "Trip not found."}, status=status.HTTP_400_BAD_REQUEST)

        context = {
            'user': user,
            'trip_id': trip_id,
            'seats': seats
        }

        serializer = BookingSerializer(data=request.data, context=context)
        try:
            if serializer.is_valid():
                with transaction.atomic():
                    booking = serializer.save()
                message = {
                    "message": "Booking created successfully",
                    "data": serializer.data
                }
                return Response(message, status=status.HTTP_201_CREATED)
            else:
                return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"status": "error", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BookingFilterView(APIView):
    """
    API view for filtering bookings based on the user's role.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def get(self, request):
        try:
            queryset = Booking.objects.select_related('trip', 'trip__vehicle').prefetch_related('seats')

            if request.user.is_organization:
                queryset = queryset.filter(trip__organization__user=request.user)
            elif request.user.is_driver:
                queryset = queryset.filter(trip__vehicle__driver__user=request.user)
            elif request.user.is_passenger:
                queryset = queryset.filter(passenger__user=request.user)
            else:
                return Response({"error": "User is not a driver, organization, or passenger"}, status=status.HTTP_400_BAD_REQUEST)

            serializer = BookingSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BookingDetailView(APIView):
    """
    API view for retrieving, updating, and deleting a specific booking.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def get(self, request, booking_id):
        try:
            booking = get_object_or_404(
                Booking.objects.select_related('trip', 'trip__vehicle').prefetch_related('seats'),
                booking_id=booking_id
            )

            # Ensure the user is authorized to view the booking
            if (request.user.is_driver and booking.trip.vehicle.driver.user != request.user) or \
               (request.user.is_organization and booking.trip.organization.user != request.user) or \
               (request.user.is_passenger and booking.passenger.user != request.user):
                return Response({"message": "Not authorized to view this booking."}, status=status.HTTP_403_FORBIDDEN)

            serializer = BookingSerializer(booking)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, booking_id):
        try:
            booking = get_object_or_404(Booking, booking_id=booking_id)

            # Ensure the user is authorized to update the booking
            if (request.user.is_driver and booking.trip.vehicle.driver.user != request.user) or \
               (request.user.is_organization and booking.trip.organization.user != request.user) or \
               (request.user.is_passenger and booking.passenger.user != request.user):
                return Response({"message": "Not authorized to update this booking."}, status=status.HTTP_403_FORBIDDEN)

            serializer = BookingSerializer(booking, data=request.data, partial=True)
            if serializer.is_valid():
                with transaction.atomic():
                    serializer.save()
                return Response({"message": "Booking updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, booking_id):
        try:
            booking = get_object_or_404(Booking, booking_id=booking_id)

            # Ensure the user is authorized to delete the booking
            if (request.user.is_driver and booking.trip.vehicle.driver.user != request.user) or \
               (request.user.is_organization and booking.trip.organization.user != request.user) or \
               (request.user.is_passenger and booking.passenger.user != request.user):
                return Response({"message": "Not authorized to delete this booking."}, status=status.HTTP_403_FORBIDDEN)

            with transaction.atomic():
                booking.delete()
            return Response({"message": "Booking deleted successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TicketCreateView(APIView):
    """
    API view for creating a ticket. 
    Only authenticated users can create a ticket.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TicketSerializer(data=request.data)
        try:
            if serializer.is_valid():
                with transaction.atomic():
                    serializer.save()
                message = {
                    "message": "Ticket created successfully",
                    "data": serializer.data
                }
                return Response(message, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TicketFilterView(APIView):
    """
    API view for filtering tickets based on the user's role.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def get(self, request):
        try:
            queryset = Ticket.objects.select_related('booking__trip', 'booking__trip__vehicle').prefetch_related('booking__seats')

            if request.user.is_driver:
                queryset = queryset.filter(booking__trip__vehicle__driver__user=request.user)
            elif request.user.is_organization:
                queryset = queryset.filter(booking__trip__organization__user=request.user)
            else:
                queryset = queryset.filter(booking__passenger__user=request.user)

            serializer = TicketSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TicketDetailView(APIView):
    """
    API view for retrieving, updating, and deleting a specific ticket.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id):
        try:
            ticket = get_object_or_404(
                Ticket.objects.select_related('booking__trip', 'booking__trip__vehicle').prefetch_related('booking__seats'),
                ticket_id=ticket_id
            )

            # Ensure the user is authorized to view the ticket
            if (request.user.is_driver and ticket.booking.trip.vehicle.driver.user != request.user) or \
               (request.user.is_organization and ticket.booking.trip.organization.user != request.user) or \
               (request.user.is_passenger and ticket.booking.passenger.user != request.user):
                return Response({"message": "Not authorized to view this ticket."}, status=status.HTTP_403_FORBIDDEN)

            serializer = TicketSerializer(ticket)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, ticket_id):
        try:
            ticket = get_object_or_404(
                Ticket.objects.select_related('booking__trip', 'booking__trip__vehicle').prefetch_related('booking__seats'),
                ticket_id=ticket_id
            )

            # Ensure the user is authorized to update the ticket
            if (request.user.is_driver and ticket.booking.trip.vehicle.driver.user != request.user) or \
               (request.user.is_organization and ticket.booking.trip.organization.user != request.user) or \
               (request.user.is_passenger and ticket.booking.passenger.user != request.user):
                return Response({"message": "Not authorized to update this ticket."}, status=status.HTTP_403_FORBIDDEN)

            serializer = TicketSerializer(ticket, data=request.data, partial=True)
            if serializer.is_valid():
                with transaction.atomic():
                    serializer.save()
                return Response({"message": "Ticket updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    def delete(self, request, ticket_id):
        try:
            ticket = get_object_or_404(
                Ticket.objects.select_related('booking__trip', 'booking__trip__vehicle').prefetch_related('booking__seats'),
                ticket_id=ticket_id
            )

            # Ensure the user is authorized to delete the ticket
            if (request.user.is_driver and ticket.booking.trip.vehicle.driver.user != request.user) or \
               (request.user.is_organization and ticket.booking.trip.organization.user != request.user) or \
               (request.user.is_passenger and ticket.booking.passenger.user != request.user):
                return Response({"message": "Not authorized to delete this ticket."}, status=status.HTTP_403_FORBIDDEN)

            with transaction.atomic():
                ticket.delete()
            return Response({"message": "Ticket deleted successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DailyEarningsCreateView(APIView):
    """
    API view for creating daily earnings.
    Only authenticated users (likely drivers or organizations) can create daily earnings.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]
    
    def post(self, request):
        trip_id = request.data.get('trip_id')
        user = request.user
        context = {
            'trip_id': trip_id,
            'user': user
        }
        
        serializer = DailyEarningSerializer(data=request.data, context=context)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # Save DailyEarnings and get the instance
                    serializer.save()
                
                # Prepare a success response
                message = {
                    "message": "Daily earnings created successfully",
                    "data": serializer.data
                }
                return Response(message, status=status.HTTP_201_CREATED)
            
            except Organization.DoesNotExist:
                return Response({"error": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)
            
            except Driver.DoesNotExist:
                return Response({"error": "Driver not found."}, status=status.HTTP_404_NOT_FOUND)
            
            except Exception as e:
                # Log or print the exception for debugging purposes
                print(f"Error during daily earnings creation: {e}")
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        # Return serializer errors if invalid
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    

class DailyEarningsFilterView(APIView):
    """
    API view for filtering daily earnings based on the user's role.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def get(self, request):
        try:
            queryset = DailyEarnings.objects.select_related('trip', 'trip__vehicle')

            if request.user.is_driver:
                queryset = queryset.filter(trip__vehicle__driver__user=request.user)
            elif request.user.is_organization:
                queryset = queryset.filter(trip__organization__user=request.user)
            else:
                return Response({"error": "User is not a driver or organization"}, status=status.HTTP_400_BAD_REQUEST)

            serializer = DailyEarningSerializer(queryset, many=True)
            
            
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DailyEarningsDetailView(APIView):
    """
    API view for retrieving, updating, and deleting specific daily earnings.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, earnings_id):
        try:
            daily_earnings = get_object_or_404(
                DailyEarnings.objects.select_related('trip', 'trip__vehicle'),
                earnings_id=earnings_id
            )

            # Ensure the user is authorized to view the daily earnings
            if (request.user.is_driver and daily_earnings.trip.vehicle.driver.user != request.user) or \
               (request.user.is_organization and daily_earnings.trip.organization.user != request.user):
                return Response({"message": "Not authorized to view these earnings."}, status=status.HTTP_403_FORBIDDEN)

            serializer = DailyEarningSerializer(daily_earnings)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, earnings_id):
        try:
            daily_earnings = get_object_or_404(
                DailyEarnings.objects.select_related('trip', 'trip__vehicle'),
                earnings_id=earnings_id
            )

            # Ensure the user is authorized to update the daily earnings
            if (request.user.is_driver and daily_earnings.trip.vehicle.driver.user != request.user) or \
               (request.user.is_organization and daily_earnings.trip.organization.user != request.user):
                return Response({"message": "Not authorized to update these earnings."}, status=status.HTTP_403_FORBIDDEN)

            serializer = DailyEarningSerializer(daily_earnings, data=request.data, partial=True)
            if serializer.is_valid():
                with transaction.atomic():
                    serializer.save()
                return Response({"message": "Daily earnings updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, earnings_id):
        try:
            daily_earnings = get_object_or_404(
                DailyEarnings.objects.select_related('trip', 'trip__vehicle'),
                earnings_id=earnings_id
            )

            # Ensure the user is authorized to delete the daily earnings
            if (request.user.is_driver and daily_earnings.trip.vehicle.driver.user != request.user) or \
               (request.user.is_organization and daily_earnings.trip.organization.user != request.user):
                return Response({"message": "Not authorized to delete these earnings."}, status=status.HTTP_403_FORBIDDEN)

            with transaction.atomic():
                daily_earnings.delete()
            return Response({"message": "Daily earnings deleted successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

   
