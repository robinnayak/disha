from django.core.mail import send_mail
from django.urls import reverse
from authentication.tokens import generate_verification_token
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from django.conf import settings

def send_verification_email(user, request):
    """Sends a verification email with a token to the user's email."""
    token = generate_verification_token(user)
    verification_url = request.build_absolute_uri(reverse('verify-email', kwargs={'uidb64': user.pk, 'token': token}))
    
    subject = 'Verify Your Email'
    message = f'Hi {user.username},\n\nPlease verify your email by clicking the link below:\n{verification_url}\n\nThank you!'
    send_mail(subject, message, 'disha@example.com', [user.email])


