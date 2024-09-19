from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from authentication.models import CustomUser, Profile,Location,Driver,Passenger,Organization,TemporaryUser
# Register your models here.

# admin.site.register(CustomUser)
admin.site.register(Organization)
admin.site.register(Profile)
admin.site.register(Driver)
admin.site.register(Location)
admin.site.register(Passenger)
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