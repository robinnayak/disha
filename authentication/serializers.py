from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import CustomUser, Profile, Location, Driver, Organization, Passenger,TemporaryUser
from django.urls import reverse
from django.core.mail import send_mail
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.hashers import check_password, make_password

# CustomUser Serializer

class CustomUserSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'password', 'password2', 'email', 'is_organization', 'is_driver', 'is_passenger']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        # Validate phone number length if provided
        if 'profile' in data:
            phone_number = data['profile'].get('phone_number')
            if phone_number and len(phone_number) != 10:
                raise serializers.ValidationError("Phone number must be 10 digits")

        # Check if username already exists
        if CustomUser.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError("Username already exists")
        
        # Ensure password and password2 match
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Passwords must match")
        
        return data

    def create(self, validated_data):
        # Remove password2 from validated data since it's not needed for user creation
        validated_data.pop('password2', None)
        
        # Create the CustomUser instance
        user = CustomUser.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        # Update the CustomUser instance
        instance = super().update(instance, validated_data)
        return instance


class TemporaryUserSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = TemporaryUser
        fields = ['username', 'email', 'password', 'password2', 'is_organization', 'is_driver', 'is_passenger', 'license_number']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        # Ensure password and password2 match
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Passwords must match")
        
        # # Check if email already exists in the TemporaryUser model
        # if TemporaryUser.objects.filter(email=data['email']).exists():
        #     raise serializers.ValidationError("A temporary user with this email already exists.")
        
        # # Check if username already exists in the TemporaryUser model
        # if TemporaryUser.objects.filter(username=data['username']).exists():
        #     raise serializers.ValidationError("A temporary user with this username already exists.")
        
        return data

    def create(self, validated_data):
        # Remove password2 from validated data since it's not needed for saving the TemporaryUser
        validated_data.pop('password2', None)
        
        # Create TemporaryUser instance
        temporary_user = TemporaryUser.objects.create(**validated_data)
        return temporary_user


# CustomUser Login Serializer
class CustomUserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        # Fetch user by username
        user = CustomUser.objects.filter(username=data['username']).first()

        # Validate user existence and password correctness
        if not user or not user.check_password(data['password']):
            raise serializers.ValidationError("Invalid username or password")
        
        return data

# Serializer for Forget Password
class ForgetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, data):
        # Check if a user with the given email exists
        if not CustomUser.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return data

    def save(self, request):
        user = CustomUser.objects.get(email=self.validated_data['email'])
        token = PasswordResetTokenGenerator().make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Build the password reset URL using Django's reverse function
        reset_url = request.build_absolute_uri(
            reverse('reset-password', kwargs={'uidb64': uid, 'token': token})
        )

        # Send the reset password email
        subject = 'Reset Your Password'
        message = f'Hi {user.username},\n\nPlease click the link below to reset your password:\n{reset_url}\n\nThank you!'
        send_mail(subject, message, 'no-reply@example.com', [user.email])
        return reset_url


# Serializer for Reset Password
class ResetPasswordSerializer(serializers.Serializer):
    # Password validation
    password = serializers.RegexField(
        regex=r'^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
        write_only=True,
        error_messages={'invalid': 'Password must be at least 8 characters long, with at least one capital letter, one number, and one special symbol'}
    )
    password2 = serializers.CharField(write_only=True, style={'input_type': 'password'}, required=True)

    def validate(self, data):
        # Ensure the two passwords match
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Passwords must match.")
        return data

    def save(self):
        uidb64 = self.context.get('uidb64')
        token = self.context.get('token')

        try:
            # Decode the user ID and retrieve the user
            uid = urlsafe_base64_decode(uidb64).decode()
            print("decoded uid",uid)
            user = CustomUser.objects.get(pk=uid)
            print("user",user)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            raise serializers.ValidationError("Invalid UID or user does not exist.")

        # Check if the token is valid
        if not PasswordResetTokenGenerator().check_token(user, token):
            raise serializers.ValidationError("Token is invalid or expired.")

        # Set the new password
        user.set_password(self.validated_data['password'])
        user.save()

        return user

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password2 = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        user = self.context.get('user')
        print(f"User: {user}")
        print(f"Current password hash: {user.password}")  # Debugging: print current password hash

        # Check if the old password is correct
        if not check_password(data['old_password'], user.password):
            raise serializers.ValidationError({"old_password": "Old password is incorrect."})

        # Check if the new passwords match
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError({"new_password": "Password1 and Password2 Doesn't Match."})

        # Debugging: hash the new password to see how it looks before saving
        print(f"New password hash before saving: {make_password(data['new_password'])}")

        # Optional: Add additional password validation (like minimum length)
        if len(data['new_password']) < 8:
            raise serializers.ValidationError({"new_password": "Password must be at least 8 characters long."})

        return data

    def save(self):
        user = self.context.get('user')

        # Debugging: print current password hash before changing
        print(f"Current password hash before saving: {user.password}")
        password = make_password(self.validated_data['new_password'])
        print("new password", password)
        # Set the new password and save the user
        user.set_password(self.validated_data['new_password'])

        # Debugging: print new password hash after saving
        print(f"New password hash after saving: {user.password}")

        user.save()

        # Verify by checking if the new password matches the new hashed password
        if check_password(self.validated_data['new_password'], user.password):
            print("Password change successful.")
        else:
            print("Password hash mismatch after saving.")

        return user
    
# Location Serializer
class LocationSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)

    class Meta:
        model = Location
        fields = '__all__'

    def create(self, validated_data):
        # Retrieve user from the context
        username = self.context['username']
        user = CustomUser.objects.get(username=username)

        # Create or update the Location instance
        location, created = Location.objects.update_or_create(
            user=user,
            defaults=validated_data
        )
        return location


# Organization Serializer
class OrganizationSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    email = serializers.ReadOnlyField(source='user.email')
    # user = CustomUserSerializer(read_only=True)

    class Meta:
        model = Organization
        fields = '__all__'

    def create(self, validated_data):
        # Retrieve user from the context
        username = self.context['username']
        user = CustomUser.objects.get(username=username)
        validated_data['user'] = user

        # Create the Organization instance
        organization = Organization.objects.create(**validated_data)
        return organization
    
    def update(self, instance, validated_data):
        # Extract and update user data if provided
        user_data = validated_data.pop('user', None)
        if user_data:
            CustomUser.objects.filter(pk=instance.user.pk).update(**user_data)
        
        # Update the Organization instance with the remaining data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance

# Driver Serializer
class DriverSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    email = serializers.ReadOnlyField(source='user.email')
    
    class Meta:
        model = Driver
        fields = '__all__'

    def create(self, validated_data):
        # Retrieve user from the context
        username = self.context['username']
        user = CustomUser.objects.get(username=username)
        validated_data['user'] = user

        # Create the Driver instance
        driver = Driver.objects.create(**validated_data)
        return driver

    def update(self, instance, validated_data):
        # Handle specific context for organization assignment if applicable
        check_organization = self.context.get('check_organization')
        org_email = self.context.get('org_email')
        if check_organization and org_email:
            organization = Organization.objects.get(user__email=org_email)
            instance.organization = organization
        
        # Update the Driver instance with the remaining data
        return super().update(instance, validated_data)


# Passenger Serializer
class PassengerSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    email = serializers.ReadOnlyField(source='user.email')
    
    class Meta:
        model = Passenger
        fields = '__all__'

    def validate_loyalty_points(self, value):
        # Validate that loyalty points are not negative
        if value < 0:
            raise serializers.ValidationError("Loyalty points cannot be negative.")
        return value

    def create(self, validated_data):
        # Retrieve user from the context
        username = self.context['username']
        user = CustomUser.objects.get(username=username)
        validated_data['user'] = user

        # Create the Passenger instance
        passenger = Passenger.objects.create(**validated_data)
        return passenger
    
    def update(self, instance, validated_data):
        # Validate loyalty points logic during update
        loyalty_points = validated_data.get('loyalty_points', instance.loyalty_points)
        if loyalty_points < 0 or ('redeem_points' in self.initial_data and loyalty_points > instance.loyalty_points):
            raise serializers.ValidationError("Invalid loyalty points operation.")
        
        # Update the Passenger instance with the remaining data
        return super().update(instance, validated_data)
