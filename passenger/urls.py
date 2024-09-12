
from django.urls import path, include
from . import views
from authentication.views import ProfileAPIView
urlpatterns = [ 
    path('profile/', ProfileAPIView.as_view(), name='profile'),
    path('payment/',views.PaymentCreateView.as_view(),name='payment'),
    path('user-payment/',views.UserPaymentView.as_view(),name='user-payment'),   
    path("payment/status/<str:txn_id>/", views.PaymentDetailView.as_view(), name="payment-status"),
]


