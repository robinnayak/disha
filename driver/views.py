from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError

from authentication.renderers import UserRenderer
from authentication.models import Driver,Organization
from authentication.serializers import DriverSerializer,OrganizationSerializer
from organization.serializers import TripSerializer
from organization.models import Trip
# Create your views here.
class OrganizationDetailView(APIView):
    """
    API view to retrieve the organization related to the authenticated driver.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]
    
    def get(self, request):
        if request.user.is_driver:
            driver = get_object_or_404(Driver, user=request.user)
            organization = driver.organization
            
            if not organization:
                return Response({"message": "No organization associated with this driver."}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = OrganizationSerializer(organization)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"message": "You are not a driver or authorized to view this."}, status=status.HTTP_400_BAD_REQUEST)
        
        
class SetTripComplete(APIView):
    """
    API view to set a trip as complete.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]
    
    def get(self,request):
        return Response({"test":"test message"},status=status.HTTP_200_OK)
    
    def post(self, request):
        # request.data.get('license_number')
        trip_id = request.data.get('trip_id')
        if request.user.is_driver:
            
            driver = get_object_or_404(Driver, user=request.user)
            trip = get_object_or_404(Trip, trip_id=trip_id, vehicle__driver=driver)
            with transaction.atomic():
                trip.is_completed = True
                trip.save()
                
                # Update the vehicle availability
                # trip.vehicle.available_seat += trip.bookings.filter(is_confirmed=True).count()
                # trip.vehicle.save()
                
                return Response({"message": "Trip marked as complete."}, status=status.HTTP_200_OK)
        
        elif request.user.is_organization:
            organization = get_object_or_404(Organization, user=request.user)
            trip = get_object_or_404(Trip, trip_id=trip_id, vehicle__organization=organization)
            
            with transaction.atomic():
                trip.is_completed = True
                trip.save()
                
                # # Update the vehicle availability
                # trip.vehicle.available_seat += trip.bookings.filter(is_confirmed=True).count()
                # trip.vehicle.save()
                
                return Response({"message": "Trip marked as complete."}, status=status.HTTP_200_OK)
        
        else:
            return Response({"message": "You are not a driver or organization or authorized to view this."}, status=status.HTTP_400_BAD_REQUEST)