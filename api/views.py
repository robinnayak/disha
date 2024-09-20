from django.shortcuts import render
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from authentication.renderers import UserRenderer
from organization.models import Review
from organization.serializers import ReviewSerializer,TripSerializer,TripPriceSerializer
from django.contrib.contenttypes.models import ContentType
from authentication.models import Passenger,Driver,Organization,CustomUser
from organization.models import Trip,Vehicle
from django.db.models import Q
from datetime import datetime
from .models import SupportRequest,Feedback
from .serializers import SupportRequestSerializer,FeedbackSerializer
from django.core.mail import send_mail
from django.conf import settings
# Create your views here.

class PassengerHomeView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def get_filtered_trips(self, filters):
        """
        This method applies filters to the Trip queryset based on provided parameters.
        """
        # Base query for trips
        trips_query = Trip.objects.all()

        # Apply filters if parameters are provided
        if filters.get('date'):
            filter_date = datetime.strptime(filters['date'], '%Y-%m-%d').date()
            trips_query = trips_query.filter(start_datetime__date=filter_date)

        if filters.get('origin'):
            trips_query = trips_query.filter(from_location__icontains=filters['origin'])

        if filters.get('destination'):
            trips_query = trips_query.filter(to_location__icontains=filters['destination'])

        if filters.get('available_seats'):
            trips_query = trips_query.filter(vehicle__available_seat__gte=int(filters['available_seats']))

        if filters.get('organization'):
            trips_query = trips_query.filter(organization__user__username__icontains=filters['organization'])

        if filters.get('driver'):
            trips_query = trips_query.filter(vehicle__driver__user__username__icontains=filters['driver'])

        return trips_query

    def get_vehicle_trip_data(self, trips_query):
        """
        This method fetches vehicle data and related trips based on the filtered trips query.
        """
        # Fetch vehicles that are related to trips and have a driver assigned
        vehicles = Vehicle.objects.select_related('driver').filter(driver__isnull=False)

        vehicle_trip_data = []

        for vehicle in vehicles:
            # Fetch the related trip for the vehicle if it exists and matches filters
            trip = getattr(vehicle, 'vehicle', None)  # 'vehicle' is the related name for Trip model

            if trip and trip in trips_query:
                # Serialize the trip data
                trip_serializer = TripSerializer(trip)
                
                # Append the serialized data to the list
                vehicle_trip_data.append(trip_serializer.data)

        return vehicle_trip_data

    def get(self, request, *args, **kwargs):
        """
        GET method for fetching home data without filters.
        """
        try:
            # Fetch all trips without filters
            trips_query = Trip.objects.all()
            vehicle_trip_data = self.get_vehicle_trip_data(trips_query)

            # Return the list as a response
            return Response({"vehicle_trip_data": vehicle_trip_data}, status=status.HTTP_200_OK)

        except Exception as e:
            # Return an error response if any exception occurs
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        """
        POST method for searching trips based on filters.
        """
        try:
            # Retrieve filter parameters from the request data
            filters = request.data

            # Get filtered trips using the helper method
            trips_query = self.get_filtered_trips(filters)

            # Fetch and serialize vehicle and trip data
            vehicle_trip_data = self.get_vehicle_trip_data(trips_query)

            # Return the filtered list as a response
            return Response({"vehicle_trip_data": vehicle_trip_data}, status=status.HTTP_200_OK)

        except Exception as e:
            # Return an error response if any exception occurs
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
       
class ReviewCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]
    def post(self, request, *args, **kwargs):
        data = request.data
        user = request.user

        # Determine the reviewer type
        if user.is_organization:
            reviewer_instance = Organization.objects.get(user=user)
            reviewer_content_type = ContentType.objects.get_for_model(Organization)
        elif user.is_passenger:
            reviewer_instance = Passenger.objects.get(user=user)
            reviewer_content_type = ContentType.objects.get_for_model(Passenger)
        elif user.is_driver:
            reviewer_instance = Driver.objects.get(user=user)
            reviewer_content_type = ContentType.objects.get_for_model(Driver)
        else:
            raise ValidationError("Reviewer type is not recognized.")

        # Set the reviewer info in the request data
        data['reviewer_content_type'] = reviewer_content_type.id
        data['reviewer_object_id'] = reviewer_instance.id

        # Determine the reviewee type based on input data
        reviewee_id = data.get('reviewee_object_id')
        reviewee_type = data.get('reviewee_content_type')

        if not reviewee_id or not reviewee_type:
            raise ValidationError("Reviewee content type and object ID must be provided.")

        if reviewee_type == "driver":
            reviewee_instance = Driver.objects.get(id=reviewee_id)
            reviewee_content_type = ContentType.objects.get_for_model(Driver)
        elif reviewee_type == "organization":
            reviewee_instance = Organization.objects.get(id=reviewee_id)
            reviewee_content_type = ContentType.objects.get_for_model(Organization)
        elif reviewee_type == "passenger":
            reviewee_instance = Passenger.objects.get(id=reviewee_id)
            reviewee_content_type = ContentType.objects.get_for_model(Passenger)
        else:
            raise ValidationError("Reviewee type is not recognized.")

        # Set the reviewee info in the request data
        data['reviewee_content_type'] = reviewee_content_type.id
        data['reviewee_object_id'] = reviewee_instance.id

        # Validate and create the review
        serializer = ReviewSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)        
       
class ReviewListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]
    def get(self, request, *args, **kwargs):
        user = request.user

        # Filter reviews based on the current user type
        if hasattr(user, 'passenger_profile'):
            reviews = Review.objects.filter(
                reviewer_content_type=ContentType.objects.get_for_model(Passenger),
                reviewer_object_id=user.passenger_profile.id
            ) | Review.objects.filter(
                reviewee_content_type=ContentType.objects.get_for_model(Passenger),
                reviewee_object_id=user.passenger_profile.id
            )
        elif hasattr(user, 'driver_profile'):
            reviews = Review.objects.filter(
                reviewer_content_type=ContentType.objects.get_for_model(Driver),
                reviewer_object_id=user.driver_profile.id
            ) | Review.objects.filter(
                reviewee_content_type=ContentType.objects.get_for_model(Driver),
                reviewee_object_id=user.driver_profile.id
            )
        elif hasattr(user, 'organization_profile'):
            reviews = Review.objects.filter(
                reviewer_content_type=ContentType.objects.get_for_model(Organization),
                reviewer_object_id=user.organization_profile.id
            ) | Review.objects.filter(
                reviewee_content_type=ContentType.objects.get_for_model(Organization),
                reviewee_object_id=user.organization_profile.id
            )
        else:
            reviews = Review.objects.none()

        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class SupportRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]
    
    def get(self,request):
        user = request.user
        if user.is_superuser:
            support_requests = SupportRequest.objects.all()
        else:
            support_requests = SupportRequest.objects.filter(user=user)
        
        serializer = SupportRequestSerializer(support_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user

        # Pass user in the context for the serializer
        serializer = SupportRequestSerializer(data=request.data, context={'user': user})
        
        if serializer.is_valid():
            # Save the SupportRequest instance
            support_request = serializer.save()

            # Send an email to the app owner
            subject = f"New Support Request: {support_request.subject}"
            message = f"""
                Support Request from: {request.user.email}
                Subject: {support_request.subject}

                Message:
                {support_request.message}
            """
            app_owner_email = "robinnayak86@gmail.com"
            print("user email to send message",user.email)
            send_mail(subject, message, user.email, [app_owner_email])

            # Return a success response
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

class FeedbackView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]
    def get(self, request):
        # Return only feedback from the authenticated user
        feedback = Feedback.objects.filter(user=request.user)
        serializer = FeedbackSerializer(feedback, many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)

    def post(self, request):
        # Create new feedback
        serializer = FeedbackSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(user=request.user)  # Associate feedback with the authenticated user
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)