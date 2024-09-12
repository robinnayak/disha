from django.contrib import admin
from authentication.models import CustomUser, Profile,Location,Driver,Passenger,Organization,TemporaryUser
# Register your models here.

admin.site.register(CustomUser)
admin.site.register(Organization)
admin.site.register(Profile)
admin.site.register(Driver)
admin.site.register(Location)
admin.site.register(Passenger)
admin.site.register(TemporaryUser)

