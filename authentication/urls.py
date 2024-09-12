from django.urls import path, include
from . import views

urlpatterns = [
    path('register/',views.RegistrationView.as_view(),name='register'),
    path('verify-email/<uidb64>/<token>/',views.VerifyEmailView.as_view(),name='verify-email'),
    
    path('forget-password/', views.ForgetPasswordView.as_view(), name='forget-password'),
    path('reset-password/<str:uidb64>/<str:token>/', views.ResetPasswordView.as_view(), name='reset-password'), 
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),  # Add this line


    path('login/',views.LoginView.as_view(),name="login"),
    path('logout/',views.LogoutView.as_view(),name="logout"),
]

