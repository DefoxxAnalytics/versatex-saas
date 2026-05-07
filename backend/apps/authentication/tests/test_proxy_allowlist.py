"""Finding A2: get_client_ip honors X-Real-IP / X-Forwarded-For only when
REMOTE_ADDR is in settings.TRUSTED_PROXIES."""

from unittest.mock import MagicMock

from django.test import TestCase, override_settings

from apps.authentication.utils import get_client_ip


def _request_with(remote_addr, x_real_ip=None, x_forwarded_for=None):
    request = MagicMock()
    meta = {"REMOTE_ADDR": remote_addr}
    if x_real_ip:
        meta["HTTP_X_REAL_IP"] = x_real_ip
    if x_forwarded_for:
        meta["HTTP_X_FORWARDED_FOR"] = x_forwarded_for
    request.META = meta
    return request


class TestProxyAllowlist(TestCase):
    @override_settings(TRUSTED_PROXIES=[])
    def test_untrusted_ignores_forwarded_headers(self):
        """Default empty allowlist — spoofed X-Real-IP must NOT be honored."""
        request = _request_with(
            remote_addr="1.2.3.4",
            x_real_ip="9.9.9.9",  # spoofed by attacker
        )
        assert (
            get_client_ip(request) == "1.2.3.4"
        ), "Untrusted source's X-Real-IP must not be honored"

    @override_settings(TRUSTED_PROXIES=["127.0.0.1"])
    def test_trusted_proxy_x_real_ip_honored(self):
        request = _request_with(
            remote_addr="127.0.0.1",
            x_real_ip="5.6.7.8",
        )
        assert get_client_ip(request) == "5.6.7.8"

    @override_settings(TRUSTED_PROXIES=["127.0.0.1"])
    def test_trusted_proxy_x_forwarded_for_honored(self):
        request = _request_with(
            remote_addr="127.0.0.1",
            x_forwarded_for="5.6.7.8, 10.0.0.1",
        )
        assert get_client_ip(request) == "5.6.7.8"

    @override_settings(TRUSTED_PROXIES=["127.0.0.1"])
    def test_untrusted_source_with_proxy_in_allowlist(self):
        """Even when allowlist exists, untrusted REMOTE_ADDR is ignored."""
        request = _request_with(
            remote_addr="8.8.8.8",  # not in allowlist
            x_real_ip="1.1.1.1",
        )
        assert (
            get_client_ip(request) == "8.8.8.8"
        ), "Non-allowlisted source's forwarded headers must not be honored"

    @override_settings(TRUSTED_PROXIES=["127.0.0.1"])
    def test_no_forwarded_headers_uses_remote_addr(self):
        request = _request_with(remote_addr="127.0.0.1")
        assert get_client_ip(request) == "127.0.0.1"
