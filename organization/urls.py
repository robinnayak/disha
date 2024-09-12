from django.urls import path, include
from . import views
from authentication.views import ProfileAPIView

urlpatterns = [
    path('profile/',ProfileAPIView.as_view(),name='org-profile'),
    path('vehicles/',views.VehicleView.as_view(),name='vehicles'),
    path('vehicles/<str:RN>/',views.VehicleDetailView.as_view(),name='vehicle-detail'),
    path('trips/',views.TripCreateAPIView.as_view(),name='trip-create'),
    path('trips/<str:trip_id>/',views.TripDetailView.as_view(),name='trip-detail'),
    path('trip-reset/',views.TripResetView.as_view(),name='trip-reset'),
    path('drivers/',views.DriverDetailsView.as_view(),name='org-drivers'),
]

