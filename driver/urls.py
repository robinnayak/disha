
from django.urls import path, include
from authentication.views import ProfileAPIView
from .views import OrganizationDetailView, SetTripComplete
urlpatterns = [ 
 path('profile/',ProfileAPIView.as_view(),name='driver-profile'),
 path('organization/',OrganizationDetailView.as_view(),name='driver-org'),
 path('trip/completed/',SetTripComplete.as_view(),name='trip-completed'),
]


