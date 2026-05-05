"""Finding #1 permanent fix: RegisterSerializer must not accept caller-controlled role.

Bug background: anonymous POST to /api/v1/auth/register/ with
{"role": "admin", "organization": <id>, ...} previously minted a fully-privileged
admin in any active organization. This test enforces that the role field is no
longer a writable input on RegisterSerializer; new users always start as 'viewer'.

See docs/codebase-review-2026-05-04-v2.md Finding #1.
"""
import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status

from apps.authentication.models import UserProfile
from apps.authentication.serializers import RegisterSerializer


@pytest.mark.django_db
class TestRegisterRoleHardening:
    """Drift-guard suite for Finding #1 permanent fix."""

    def test_anonymous_register_with_role_admin_creates_viewer(self, api_client, organization):
        """Even when 'role': 'admin' is in the body, the new profile must be viewer."""
        url = reverse('register')
        response = api_client.post(url, {
            'username': 'attacker',
            'email': 'attacker@example.com',
            'password': 'S0meStrongPass!',
            'password_confirm': 'S0meStrongPass!',
            'first_name': 'A',
            'last_name': 'B',
            'organization': organization.id,
            'role': 'admin',  # malicious input - must be ignored
        })

        # Registration may succeed (201) or be rejected for some other reason
        # (rate-limit, etc.). If it succeeds, the profile MUST be viewer.
        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(username='attacker')
            profile = UserProfile.objects.get(user=user)
            assert profile.role == 'viewer', (
                f"BUG: caller-controlled role accepted. Profile.role = {profile.role!r}. "
                f"See Finding #1 - tenant takeover via self-registration."
            )

    def test_anonymous_register_without_role_creates_viewer(self, api_client, organization):
        """Default behavior unchanged: a normal registration creates a viewer."""
        url = reverse('register')
        response = api_client.post(url, {
            'username': 'normal',
            'email': 'normal@example.com',
            'password': 'S0meStrongPass!',
            'password_confirm': 'S0meStrongPass!',
            'first_name': 'N',
            'last_name': 'U',
            'organization': organization.id,
        })

        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(username='normal')
            profile = UserProfile.objects.get(user=user)
            assert profile.role == 'viewer'

    def test_drift_guard_role_not_in_serializer_input_fields(self):
        """Drift-guard: 'role' must not be a writable input field on RegisterSerializer."""
        serializer = RegisterSerializer()
        writable_fields = {
            name for name, field in serializer.fields.items()
            if not field.read_only
        }
        assert 'role' not in writable_fields, (
            "RegisterSerializer must not accept 'role' as a writable input field. "
            "See Finding #1 - caller-controlled role enables tenant takeover."
        )
