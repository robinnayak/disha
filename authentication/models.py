from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.db import models, transaction
from django.core.exceptions import ValidationError
import random
import string
from django.utils import timezone
from django.db.models import Sum
from django.apps import apps
from django.contrib.auth.hashers import make_password
from cloudinary.models import CloudinaryField

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username must be set")
        if not email:
            raise ValueError("The Email must be set")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, email, password, **extra_fields)

    def get_by_natural_key(self, username):
        return self.get(username=username)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=64,blank=True,null=True)
    

    is_organization = models.BooleanField(default=False)
    is_driver = models.BooleanField(default=False)
    is_passenger = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'password']

    def __str__(self):
        return self.username

#To store temporary custom user data 
class TemporaryUser(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    is_driver = models.BooleanField(default=False)
    is_organization = models.BooleanField(default=False)
    is_passenger = models.BooleanField(default=True)
    license_number = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(auto_now=True)
    
    
        

class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True)
    # profile_image = models.ImageField(upload_to='profile_images', blank=True, null=True)
    profile_image =  CloudinaryField('profile_images', blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.user.username} - profile"

class Organization(Profile):
    name = models.CharField(max_length=150, blank=True, null=True)
    registration_number = models.CharField(max_length=150, unique=True, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='organization_logos', blank=True, null=True)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    remaining_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    date_created = models.DateTimeField(auto_now_add=True)
    no_of_trips = models.IntegerField(default=0)

    def __str__(self) -> str:
        return self.user.username

    def get_total_reviews(self):
        return self.organization_reviews.count()
    
    def update_total_earnings(self, date=None):
        """
        Calculate and update the total daily earnings for the organization.
        :param date: Optional date for which to calculate the earnings (defaults to today).
        """
        DailyEarnings = apps.get_model('booking.DailyEarnings')
        
        # Fetch earnings related to the organization
        earnings = DailyEarnings.objects.filter(
            trip__organization=self,
        )
        
        # Corrected the method to use 'aggregate' instead of 'aaggregate'
        total_earnings = earnings.aggregate(total_earnings=Sum('total_earnings'))['total_earnings'] or 0.0
        no_of_trips = earnings.count()
        
        # Update the organization's fields
        self.total_earnings = total_earnings
        self.no_of_trips = no_of_trips
        self.save()
        return self.total_earnings, self.no_of_trips


    def update_earnings(self, amount):
        self.total_earnings += amount
        self.remaining_earnings += amount
        self.save()

    def withdraw_earnings(self, amount):
        if amount > self.remaining_earnings:
            raise ValidationError('Insufficient funds to withdraw')
        self.remaining_earnings -= amount
        self.save()

    def _generate_registration_number(self):
        random_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        random_number = ''.join(random.choices(string.digits, k=14))
        return f"ORG-{random_number}"

    def save(self, *args, **kwargs):
        if not self.registration_number:
            self.registration_number = self._generate_registration_number()
        super().save(*args, **kwargs)

class Driver(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='driver_profile')
    phone_number = models.CharField(max_length=15, blank=True)
    # profile_image = models.ImageField(upload_to='profile_images', blank=True, null=True)
    profile_image =  CloudinaryField('profile_images', blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, blank=True, null=True, related_name='drivers')
    license_number = models.CharField(max_length=16, blank=True, unique=True)
    experience = models.IntegerField(default=1)
    availability_status = models.BooleanField(default=True)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    remaining_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    date_created = models.DateTimeField(auto_now=True)
    no_of_trips = models.IntegerField(default=0)
    def __str__(self):
        return self.user.username
    
    def update_total_earnings(self, date=None):
        """
        Calculate and update the total daily earnings for the driver.
        :param date: Optional date for which to calculate the earnings (defaults to today).
        """
        DailyEarnings = apps.get_model('booking.DailyEarnings')
        
        # Fetch earnings related to the driver through the vehicle
        earnings = DailyEarnings.objects.filter(
            trip__vehicle__driver=self,
        )
        
        # Corrected the method to use 'aggregate' instead of 'aaggregate'
        total_earnings = earnings.aggregate(total_earnings=Sum('total_earnings'))['total_earnings'] or 0.0
        no_of_trips = earnings.count()
        
        # Update the driver's fields
        self.total_earnings = total_earnings
        self.no_of_trips = no_of_trips
        self.save()
        return self.total_earnings, self.no_of_trips


    # def update_earnings(self, amount):
    #     self.total_earnings += amount
    #     self.remaining_earnings += amount
    #     self.save()

    def withdraw_earnings(self, amount):
        if amount > self.remaining_earnings:
            raise ValidationError("Insufficient earnings to withdraw the requested amount.")
        try:
            with transaction.atomic():
                self.remaining_earnings -= amount
                self.save()
        except Exception as e:
            raise ValidationError(f"An error occurred while withdrawing earnings: {str(e)}")

class Location(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='location')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    heading = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Location of {self.user.username} as {self.timestamp}"

class Passenger(Profile):
    emergency_contact_name = models.CharField(max_length=50, blank=True)
    emergency_contact_number = models.CharField(max_length=15, blank=True)
    preferred_language = models.CharField(max_length=20, choices=[('en', 'English'), ('ne', 'Nepali')], blank=True)
    loyalty_points = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} - profile"

    def add_loyalty_points(self, points):
        self.loyalty_points += points
        self.save()

    def redeem_loyalty_points(self, points):
        if points > self.loyalty_points:
            raise ValidationError("Insufficient loyalty points.")
        try:
            with transaction.atomic():
                self.loyalty_points -= points
                self.save()
        except Exception as e:
            raise ValidationError(f"An error occurred while redeeming loyalty points: {str(e)}")
