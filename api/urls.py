from django.urls import path, include
from authentication.views import ProfileAPIView
from .views import ReviewCreateAPIView,ReviewListAPIView,PassengerHomeView
from booking.views import TicketFilterView,TicketDetailView
urlpatterns = [
    # path('profile/',ProfileAPIView.as_view(),name="profile"),
    path('',PassengerHomeView.as_view(),name='home'),
    path('reviews/create/',ReviewCreateAPIView.as_view(),name='review-create'),
    path('review/',ReviewListAPIView.as_view(),name='review'),
    path('ticket/filter/',TicketFilterView.as_view(),name='ticket-filter'),
    path('ticket/detail/<str:ticket_id>/',TicketDetailView.as_view(),name='ticket-detail'),
    path('auth/',include('authentication.urls')),
    path('organization/',include('organization.urls')),
    path('booking/',include('booking.urls')),
    path('passenger/',include('passenger.urls')),
    path('driver/',include('driver.urls')),
]

