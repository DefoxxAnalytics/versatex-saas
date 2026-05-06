"""Critical S-#2: CookieJWTAuthentication must NOT fall through to the
Authorization: Bearer header for browser clients in production. The
HTTP-only cookie XSS protection design requires that XSS-stolen tokens
cannot be replayed via the header.

Combined with the residual 'unsafe-inline' CSP (Phase 5 Task 5.2) that
keeps an XSS attack viable, this fallback would let a single XSS payload
exfiltrate an access token via fetch() with a Bearer header.
"""
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from apps.authentication.backends import CookieJWTAuthentication

User = get_user_model()


class TestCookieAuthNoHeaderFallback(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username="ch_u", password="pw")
        self.token = str(AccessToken.for_user(self.user))

    @override_settings(DEBUG=False)
    def test_header_only_request_rejected_in_production(self):
        """Production: bearer-header-only requests must NOT authenticate."""
        request = self.factory.get("/api/v1/whatever/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token}"
        # NO cookie set.
        result = CookieJWTAuthentication().authenticate(request)
        self.assertIsNone(
            result,
            "Bearer-header-only request authenticated despite no cookie. "
            "S-#2: this nullifies HTTP-only cookie XSS protection.",
        )

    @override_settings(DEBUG=False)
    def test_cookie_only_request_authenticates_in_production(self):
        """Production: cookie alone must still authenticate."""
        request = self.factory.get("/api/v1/whatever/")
        request.COOKIES["access_token"] = self.token
        result = CookieJWTAuthentication().authenticate(request)
        self.assertIsNotNone(
            result,
            "Cookie-based authentication broken — regression beyond the fix's intent.",
        )

    @override_settings(DEBUG=False)
    def test_cookie_with_bearer_header_uses_cookie(self):
        """Production: when both present, cookie wins (existing precedence)."""
        request = self.factory.get("/api/v1/whatever/")
        request.COOKIES["access_token"] = self.token
        request.META["HTTP_AUTHORIZATION"] = "Bearer some-other-token"
        result = CookieJWTAuthentication().authenticate(request)
        self.assertIsNotNone(
            result,
            "Cookie should take precedence over Bearer header.",
        )

    @override_settings(DEBUG=True)
    def test_header_fallback_allowed_in_debug(self):
        """DEBUG mode: header fallback preserved for local dev tooling
        (curl, Postman). This is the only intended use of the fallback."""
        request = self.factory.get("/api/v1/whatever/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token}"
        result = CookieJWTAuthentication().authenticate(request)
        self.assertIsNotNone(
            result,
            "DEBUG=True should preserve the header fallback for dev tooling. "
            "If this fails, the gate may have over-tightened.",
        )
