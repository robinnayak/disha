from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from itsdangerous import URLSafeTimedSerializer
from django.conf import settings
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
def get_tokens_for_user(user):
    refersh = RefreshToken.for_user(user)
    return{
        'refresh':str(refersh),
        'access':str(refersh.access_token)
    }


def generate_verification_token(user):
    """Generates a token for email verification using itsdangerous."""
    
    print("user generate verification token",user)
    serializer = URLSafeTimedSerializer(settings.SECRET_KEY)
    token = serializer.dumps(user.email, salt='email-confirmation-salt')
    print("token",token)
    return token


def verify_token(token, max_age=3600):
    """Verifies the token, returns the email if successful."""
    serializer = URLSafeTimedSerializer(settings.SECRET_KEY)
    try:
        email = serializer.loads(token, salt='email-confirmation-salt', max_age=max_age)
        print("verify token email",email)
        return email
    except SignatureExpired:
        raise SignatureExpired("Verification link has expired.")
    except BadTimeSignature:
        raise BadTimeSignature("Invalid verification link.")
    