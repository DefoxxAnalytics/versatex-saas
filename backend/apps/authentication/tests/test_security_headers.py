"""Drift-guard for v2.12 HSTS security headers (Finding #15).

Django's SecurityMiddleware emits Strict-Transport-Security only when:
  - SECURE_HSTS_SECONDS > 0
  - the request is HTTPS (or trusted via SECURE_PROXY_SSL_HEADER)

Production gates these on `not DEBUG` in `config/settings.py:430-459`. In dev
DEBUG=True so the header is intentionally absent. This test forces the prod
config via override_settings + a `secure=True` test client request to confirm
the middleware actually emits the header — catching regressions where someone
disables HSTS, drops SECURE_HSTS_SECONDS to 0, or removes SecurityMiddleware
from MIDDLEWARE entirely.

See docs/codebase-review-2026-05-06-second-pass.md for the v2.12 second-pass
review requesting this drift-guard.
"""

import pytest
from django.test import Client, override_settings


@pytest.mark.django_db
class TestHSTSHeader:
    """Drift-guard suite for HSTS emission (Finding #15)."""

    @override_settings(
        DEBUG=False,
        SECURE_HSTS_SECONDS=31536000,
        SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
        SECURE_HSTS_PRELOAD=False,
        # Production also redirects HTTP -> HTTPS; a `secure=True` client request
        # bypasses that redirect so the response actually carries the HSTS header.
        SECURE_SSL_REDIRECT=False,
        ALLOWED_HOSTS=["testserver", "*"],
    )
    def test_hsts_header_emitted_on_https_request(self) -> None:
        # given a production-like config with HSTS enabled
        client = Client()

        # when a secure (HTTPS) request hits the public health endpoint
        response = client.get("/api/health/", secure=True)

        # then the response carries the Strict-Transport-Security header with
        # both max-age and includeSubDomains directives
        hsts = response.headers.get("Strict-Transport-Security", "")
        assert hsts, (
            "Strict-Transport-Security header missing on HTTPS response. "
            "Either SecurityMiddleware was removed from MIDDLEWARE, or "
            "SECURE_HSTS_SECONDS dropped to 0. Finding #15 regression."
        )
        assert "max-age=" in hsts, f"HSTS header lacks max-age directive: {hsts!r}"
        assert "includeSubDomains" in hsts, (
            f"HSTS header lacks includeSubDomains directive: {hsts!r}. "
            "Without it, *.versatexanalytics.com subdomains can be SSL-stripped "
            "even after the apex is HTTPS-pinned."
        )

    @override_settings(
        DEBUG=True,
        SECURE_HSTS_SECONDS=0,
        ALLOWED_HOSTS=["testserver", "*"],
    )
    def test_hsts_header_absent_in_dev(self) -> None:
        # given dev settings (DEBUG=True, no HSTS configured)
        client = Client()

        # when an HTTPS request hits the same endpoint
        response = client.get("/api/health/", secure=True)

        # then the HSTS header is absent — confirming the prod-gating works
        # and we're not accidentally emitting it in dev (which would brick
        # local self-signed-cert workflows for a year).
        assert (
            "Strict-Transport-Security" not in response.headers
        ), "HSTS emitted in dev — SECURE_HSTS_SECONDS gating is broken."
