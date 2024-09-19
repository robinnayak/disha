from django.urls import path, include
from . import views

urlpatterns = [
    path('create/',views.BookingCreateView.as_view(),name='booking-create'),
    path('filter/',views.BookingFilterView.as_view(),name='booking-filter'),
    path('detail/<str:booking_id>/',views.BookingDetailView.as_view(),name='booking-detail'),   
    path('tickets/',views.TicketFilterView.as_view(),name='tickets'),   
      
    path('daily-earnings/create/', views.DailyEarningsCreateView.as_view(), name='daily-earnings-create'),
    path('daily-earnings/filter/', views.DailyEarningsFilterView.as_view(), name='daily-earnings-filter'),
    path('reset-trip/',views.ResetTripView.as_view(),name='reset-trip')    
]

