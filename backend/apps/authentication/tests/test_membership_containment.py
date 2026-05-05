"""
Phase 0 interim containment for Finding #2 — cross-org admin escalation.

Verifies that the membership creation endpoint is gated behind the
MEMBERSHIP_CREATE_ENABLED feature flag. When the flag is False (default),
all POST /api/v1/auth/memberships/ calls return 503. When True, the
endpoint operates as before (request reaches serializer/queryset layers).

Permanent fix lands in Phase 1 task 1.2 (proper requester-is-admin-of-target-org
check); this test pins the interim behavior.
"""
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.authentication.models import Organization, UserProfile

User = get_user_model()


class TestMembershipCreateContainment(APITestCase):
    """
    Note on test setup: a `post_save` signal on UserProfile auto-creates a
    UserOrganizationMembership for (user, profile.organization). To avoid
    colliding with the unique-together (user, organization) constraint, the
    target user's profile is anchored to a different org (`other_org`) than
    the org we POST against (`self.org`) — this is also the realistic shape
    of the cross-org admin escalation that Finding #2 describes.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="Test Org", slug="test")
        self.other_org = Organization.objects.create(name="Other Org", slug="other")
        self.admin = User.objects.create_user(username="admin", password="pw")
        UserProfile.objects.create(user=self.admin, organization=self.org, role="admin")
        self.client.force_authenticate(self.admin)

    @override_settings(MEMBERSHIP_CREATE_ENABLED=False)
    def test_create_blocked_when_flag_disabled(self):
        target_user = User.objects.create_user(username="target", password="pw")
        UserProfile.objects.create(user=target_user, organization=self.other_org, role="viewer")
        response = self.client.post("/api/v1/auth/memberships/", {
            "user": target_user.id,
            "organization": self.org.id,
            "role": "admin",
        })
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @override_settings(MEMBERSHIP_CREATE_ENABLED=True)
    def test_create_passes_through_when_flag_enabled(self):
        target_user = User.objects.create_user(username="target2", password="pw")
        UserProfile.objects.create(user=target_user, organization=self.other_org, role="viewer")
        response = self.client.post("/api/v1/auth/memberships/", {
            "user": target_user.id,
            "organization": self.org.id,
            "role": "admin",
        })
        # Either 201 (creation worked) or 400 (validation error) is acceptable; just NOT 503.
        self.assertNotEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
