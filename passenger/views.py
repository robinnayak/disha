from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from booking.models import Booking
from booking.serializers import BookingSerializer
from .models import Payment
from .serializers import PaymentSerializer,OngoingTripSerializer
from authentication.models import Passenger
from authentication.renderers import UserRenderer
from django.utils import timezone
# class PassengerHomePageView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, *args, **kwargs):
#         try:
#             passenger = Passenger.objects.get(user=request.user)
            
#             # Get the trip the passenger is associated with
#             trip = passenger.trip
#             if not trip:
#                 return Response({"message": "No trip associated with the passenger"}, status=404)

#             # Serialize trip data (vehicle data will also be serialized via the TripSerializer)
#             trip_serializer = TripSerializer(trip)

#             data = {
#                 'trip': trip_serializer.data,
#                 'seat_number': passenger.seat_number
#             }

#             return Response(data, status=200)
#         except Passenger.DoesNotExist:
#             return Response({"error": "Passenger not found"}, status=404)


class PaymentCreateView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]
    
    def post(self,request):
        booking_id = request.data.get('booking_id')
        payment_method = request.data.get('payment_method')
        
        if not booking_id or not payment_method:
            return Response({'message':'Please provide both booking_id and payment_method'},status=status.HTTP_400_BAD_REQUEST)
        
        context = {
            'username' : request.user.username,
            'booking_id' : booking_id
        }
        
        serializer = PaymentSerializer(data=request.data,context=context)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    serializer.save()
                return Response({"message":"Payment successful.","data":serializer.data},status=status.HTTP_201_CREATED)
            
            except Exception as e:
                return Response({'error':str(e)},status=status.HTTP_400_BAD_REQUEST)
            
        else:
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
class UserPaymentView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]
    def get(self, request):
        user = request.user
        payments = Payment.objects.none()

        if user.is_organization:
            payments = Payment.objects.filter(booking__trip__organization=user.organization)
        elif user.is_driver:
            payments = Payment.objects.filter(booking__trip__vehicle__driver=user.driver)
        elif user.is_passenger:
            payments = Payment.objects.filter(passenger__user=user)
        else:
            return Response({"detail": "Invalid user role."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]
    
    def get(self,request,*args,**kwargs):
        transaction_id = kwargs.get('txn_id')
        
        
        if not transaction_id:
            return Response({'message':'Please provide transaction_id'},status=status.HTTP_400_BAD_REQUEST)
        
        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
            serializer = PaymentSerializer(payment)
            return Response(serializer.data,status=status.HTTP_200_OK)
        
        except Payment.DoesNotExist:
            return Response({'message':'Payment not found'},status=status.HTTP_404_NOT_FOUND)
        

class BookingListView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]
    
    def get(self,request,*args,**kwargs):
        user = request.user
        bookings = Booking.objects.none()
        
        if user.is_organization:
            bookings = Booking.objects.filter(trip__organization=user.organization)
        elif user.is_driver:
            bookings = Booking.objects.filter(trip__vehicle__driver=user.driver)
        elif user.is_passenger:
            bookings = Booking.objects.filter(passenger__user=user)
        else:
            return Response({"detail": "Invalid user role."}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = BookingSerializer(bookings,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    

class OngoingTripView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]
    
    def get(self,request):
        user = request.user
        
        if user.is_passenger:
            passenger = Passenger.objects.get(user=user)
            print("passenger",passenger)
            ongoing_trips = Booking.objects.filter(
                passenger=passenger,
                trip__is_completed = False,
                trip_datetime__gte=timezone.now()
            ).order_by('trip_datetime')
            print(ongoing_trips)

            serializer = OngoingTripSerializer(ongoing_trips,many=True)
            
            return Response(serializer.data,status=status.HTTP_200_OK)
        
        else:
            return Response({"detail": "Invalid user role."}, status=status.HTTP_400_BAD_REQUEST)