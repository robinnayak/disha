from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import Group
from django.contrib.auth import login, logout, authenticate
from authentication.models import CustomUser, Driver, Organization, Passenger,TemporaryUser
from django.db.models import Q
from authentication.serializers import CustomUserSerializer, CustomUserLoginSerializer, DriverSerializer, OrganizationSerializer, PassengerSerializer,TemporaryUserSerializer,ForgetPasswordSerializer,ResetPasswordSerializer,ChangePasswordSerializer
from authentication.tokens import get_tokens_for_user
from .renderers import UserRenderer
from django.shortcuts import get_object_or_404
from django.db import transaction
from functools import lru_cache
from authentication.emailverification import send_verification_email
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from authentication.tokens import verify_token
# Cache frequently accessed data using LRU caching
@lru_cache(maxsize=100)
def get_cached_user(username):
    """Helper function to cache user data to reduce database load."""
    return CustomUser.objects.select_related('profile', 'driver_profile', 'location').filter(username=username).first()

def get_profile_by_role(user):
    """Helper function to retrieve user profile based on their role."""
    if user.is_organization:
        return get_object_or_404(Organization, user=user)
    elif user.is_driver:
        return get_object_or_404(Driver, user=user)
    elif user.is_passenger:
        return get_object_or_404(Passenger, user=user)
    return None

def get_serializer_by_profile(profile, *args, **kwargs):
    """Helper function to get the appropriate serializer for the profile."""
    profile_serializer_map = {
        Organization: OrganizationSerializer,
        Driver: DriverSerializer,
        Passenger: PassengerSerializer
    }
    return profile_serializer_map[type(profile)](profile, *args, **kwargs)

class RegistrationView(APIView):
    def get(self, request):
        try:
            users = CustomUser.objects.only('id', 'username', 'email')
            serializer = CustomUserSerializer(users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def post(self, request):
        data = request.data
        is_driver = data.get('is_driver', False)
        license_number = data.get('license_number', None)

        # Driver-specific validation
        if is_driver and not license_number:
            return Response({"error": "License field is required for driver registration"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if email already exists in TemporaryUser
        if TemporaryUser.objects.filter(email=data['email']).exists():
            return Response({"error": "User with this email already exists"}, status=status.HTTP_400_BAD_REQUEST)

        # Use serializer to validate and save temporary user
        serializer = TemporaryUserSerializer(data=data)
        if serializer.is_valid():
            temporary_user = serializer.save()

            # Send verification email
            send_verification_email(temporary_user, request)

            return Response({
                'message': 'Verification email sent. Please check your inbox.',
                'user': serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):

    def get(self, request, uidb64, token):
        try:
            # Decode uidb64 to retrieve the TemporaryUser
            # uid = urlsafe_base64_decode(uidb64).decode()

            # print(f"Decoded UID: {uid}")
            temp_user = TemporaryUser.objects.get(pk=uidb64)
            # Verify the token
            email = verify_token(token)  # Custom function

            if email != temp_user.email:
                return Response({'error': 'Token email does not match user email.'}, status=status.HTTP_400_BAD_REQUEST)

            # Transaction block to create the actual user
            with transaction.atomic():
                user = CustomUser.objects.create_user(
                    username=temp_user.username,
                    email=temp_user.email,
                    password=temp_user.password,  # Already hashed in TemporaryUser
                    is_organization=temp_user.is_organization,
                    is_driver=temp_user.is_driver,
                    is_passenger=temp_user.is_passenger,
                    is_email_verified=True
                )

                # Handle group assignment and profile creation (Driver, Organization, or Passenger)
                if user.is_driver:
                    print("Assigning user to 'driver' group and creating driver profile.")
                    self._assign_group(user, 'driver')
                    Driver.objects.create(user=user, license_number=temp_user.license_number)
                elif user.is_organization:
                    print("Assigning user to 'organization' group and creating organization profile.")
                    self._assign_group(user, 'organization')
                    Organization.objects.create(user=user)
                elif user.is_passenger:
                    print("Assigning user to 'passenger' group and creating passenger profile.")
                    self._assign_group(user, 'passenger')
                    Passenger.objects.create(user=user)

                # Generate JWT token for the user
                jwt_token = self._generate_token_for_user(user)

                # Delete the temporary user record after successful verification
                temp_user.delete()

            return Response({
                'message': 'User created and email verified successfully.',
                'token': jwt_token
            }, status=status.HTTP_201_CREATED)

        # Error Handling
        except TemporaryUser.DoesNotExist as e:
            return Response({'error': 'Invalid verification link.'}, status=status.HTTP_400_BAD_REQUEST)
        except SignatureExpired:
            return Response({'error': 'Verification link has expired.'}, status=status.HTTP_400_BAD_REQUEST)
        except BadTimeSignature:
            return Response({'error': 'Invalid verification link.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _assign_group(self, user, group_name):
        """Assign the user to the specified group."""
        print(f"Assigning user {user.username} to group {group_name}")
        group = get_object_or_404(Group, name=group_name)
        user.groups.add(group)

    def _generate_token_for_user(self, user):
        """Generate JWT token for the authenticated user."""
        return get_tokens_for_user(user)


class LoginView(APIView):
    @transaction.atomic
    def post(self, request):
        serializer = CustomUserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']

            # Using the cached user retrieval function
            user = get_cached_user(username)
            if user and user.check_password(password):
                login(request, user)
                token = get_tokens_for_user(user)
                return Response({
                    'message': 'User logged in successfully',
                    'user': CustomUserSerializer(user).data,
                    'token': token
                }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# View for Forget Password
class ForgetPasswordView(APIView):
    renderer_classes = [UserRenderer]

    @transaction.atomic
    def post(self, request):
        serializer = ForgetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            reset_url = serializer.save(request)
            message = {
                'message': 'Password reset link sent. Please check your email.',
                'reset_url': reset_url
            }
            return Response(data=message, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# View for Reset Password
class ResetPasswordView(APIView):

    @transaction.atomic
    def post(self, request, uidb64, token):
        data = request.data
        context = {
            'uidb64': uidb64,
            'token': token
        }
        serializer = ResetPasswordSerializer(data=data, context=context)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    @transaction.atomic
    def post(self, request):
        context = {
            'user':request.user
        }
        serializer = ChangePasswordSerializer(data=request.data, context=context)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Password has been changed successfully.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            logout(request)
            return Response({
                'message': 'User logged out successfully',
                'user': user.username
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [UserRenderer]

    def get(self, request):
        user = request.user
        profile = get_profile_by_role(user)
        if not profile:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = get_serializer_by_profile(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @transaction.atomic
    def put(self, request):
        user = request.user
        profile = get_profile_by_role(user)
        if not profile:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = get_serializer_by_profile(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        user = request.user
        # profile = get_profile_by_role(user)
        if not user:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        with transaction.atomic():
            # Delete the profile first
            # Delete the associated CustomUser instance
            user.delete()
            print("succesfuly deleted",user.username)
        return Response({"message": f"Profile of {user.username} deleted successfully."}, status=status.HTTP_200_OK)
