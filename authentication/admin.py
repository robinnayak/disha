from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from authentication.models import CustomUser, Profile,Location,Driver,Passenger,Organization,TemporaryUser
# Register your models here.

# admin.site.register(CustomUser)

admin.site.register(Location)
admin.site.register(TemporaryUser)

class CustomUserAdmin(UserAdmin):
    # Define the fields to be displayed in the admin panel
    list_display = ('id','username', 'email', 'is_organization', 'is_driver', 'is_passenger', 'is_staff', 'is_active')
    
    # Fields to filter users in the admin panel
    list_filter = ('is_organization', 'is_driver', 'is_passenger', 'is_staff', 'is_active')
    
    # Fields to be used when creating or editing a user in the admin panel
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'is_active', 'is_organization', 'is_driver', 'is_passenger')}),
        ('Email Verification', {'fields': ('is_email_verified', 'email_verification_token')}),
        ('Important dates', {'fields': ('last_login',)}),
    )
    
    # Fields for adding a user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_staff', 'is_superuser', 'is_active'),
        }),
    )
    
    search_fields = ('username', 'email')
    ordering = ('username',)
    filter_horizontal = ()

# Register the CustomUser model with the admin site
admin.site.register(CustomUser, CustomUserAdmin)

# Profile Admin
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'phone_number', 'address', 'date_of_birth')
    search_fields = ('user__username', 'phone_number', 'address')

# Organization Admin
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'registration_number', 'total_earnings', 'no_of_trips', 'date_created')
    search_fields = ('name', 'registration_number')
    list_filter = ('date_created',)
    ordering = ('-date_created',)

# Driver Admin
@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'organization', 'license_number', 'experience', 'availability_status', 'total_earnings', 'date_created', 'no_of_trips')
    search_fields = ('user__username', 'license_number', 'organization__name')
    list_filter = ('availability_status', 'date_created', 'organization')

# Passenger Admin
@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'phone_number', 'emergency_contact_name', 'emergency_contact_number', 'loyalty_points', 'preferred_language')
    search_fields = ('user__username', 'phone_number', 'emergency_contact_name')
    list_filter = ('preferred_language',)
