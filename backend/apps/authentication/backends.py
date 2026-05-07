"""
Custom JWT authentication backend that reads tokens from HTTP-only cookies.
This provides XSS protection by preventing JavaScript access to tokens.
"""

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads tokens from HTTP-only cookies.

    The Authorization: Bearer header fallback is gated on DEBUG=True so
    local dev tooling (curl, Postman, REST client extensions) keeps working
    without breaking the cookie-XSS protection design in production.

    Browser clients in production must use the cookie path exclusively —
    an XSS-stolen token cannot be replayed via the header. Programmatic
    API clients needing header auth should use a separate authentication
    class with explicit opt-in.
    """

    def authenticate(self, request):
        jwt_settings = settings.SIMPLE_JWT
        cookie_name = jwt_settings.get("AUTH_COOKIE", "access_token")
        raw_token = request.COOKIES.get(cookie_name)

        if raw_token is None:
            # S-#2 (v3 Phase 0 Task 0.5): only honor the Authorization
            # header in DEBUG. In production, returning None forces a 401
            # for header-only browser requests, closing the cookie-XSS
            # bypass that the residual 'unsafe-inline' CSP keeps viable.
            if getattr(settings, "DEBUG", False):
                return super().authenticate(request)
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except InvalidToken:
            if getattr(settings, "DEBUG", False):
                return super().authenticate(request)
            return None
