"""
Custom JWT authentication backend that reads tokens from HTTP-only cookies.
This provides XSS protection by preventing JavaScript access to tokens.
"""
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads tokens from HTTP-only cookies.
    Falls back to Authorization header for backwards compatibility.
    """

    def authenticate(self, request):
        # First try to get token from cookie
        jwt_settings = settings.SIMPLE_JWT
        cookie_name = jwt_settings.get('AUTH_COOKIE', 'access_token')
        raw_token = request.COOKIES.get(cookie_name)

        if raw_token is None:
            # Fall back to Authorization header for backwards compatibility
            return super().authenticate(request)

        # Validate the token from cookie
        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except InvalidToken:
            # If cookie token is invalid, try header as fallback
            return super().authenticate(request)
