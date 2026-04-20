"""
OpenAPI schema extensions for drf-spectacular.
Registers custom authentication classes with the API schema generator.
"""
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CookieJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    OpenAPI schema extension for CookieJWTAuthentication.

    This tells drf-spectacular how to document our custom JWT authentication
    that supports both HTTP-only cookies and Authorization header.
    """
    target_class = 'apps.authentication.backends.CookieJWTAuthentication'
    name = 'CookieJWTAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': (
                'JWT authentication via HTTP-only cookie or Authorization header.\n\n'
                '**Cookie Auth (Recommended):**\n'
                'Tokens are automatically sent via HTTP-only cookies after login.\n\n'
                '**Header Auth:**\n'
                'Include token in Authorization header: `Bearer <access_token>`'
            ),
        }
