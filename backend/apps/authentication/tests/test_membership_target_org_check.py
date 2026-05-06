"""Finding #2 permanent fix: perform_create must validate target-org admin role.

Bug background: UserOrganizationMembershipViewSet.perform_create called
serializer.save(invited_by=request.user) without verifying that request.user
is admin OF the target organization. The class-level IsAdmin permission gates
*who* can call but not *which* org they target. As a result, an admin of Org A
could POST {"user": X, "organization": <B_id>, "role": "admin"} and grant
admin in Org B — full lateral escalation across tenants.

See docs/codebase-review-2026-05-04-v2.md Finding #2.
"""
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import (
    Organization,
    UserOrganizationMembership,
    UserProfile,
)

User = get_user_model()


class TestMembershipTargetOrgCheck(APITestCase):
    """Drift-guard suite for Finding #2 permanent fix."""

    def setUp(self):
        self.org_a = Organization.objects.create(name="Org A", slug="org-a-mtoc")
        self.org_b = Organization.objects.create(name="Org B", slug="org-b-mtoc")

        # Admin of org A only.
        self.admin_a = User.objects.create_user(username="admin_a_mtoc", password="pw")
        UserProfile.objects.create(user=self.admin_a, organization=self.org_a, role="admin")

        # Admin of both orgs (multi-org case).
        self.admin_ab = User.objects.create_user(username="admin_ab_mtoc", password="pw")
        UserProfile.objects.create(user=self.admin_ab, organization=self.org_a, role="admin")
        # The post_save signal on UserProfile auto-creates a membership for
        # (admin_ab, org_a). Add an explicit admin membership in org_b.
        UserOrganizationMembership.objects.create(
            user=self.admin_ab, organization=self.org_b, role="admin", is_active=True
        )

        # Target user — profile in org_a, so signal does NOT mirror them into
        # org_b. Without a target-org check, admin_a could grant them admin in
        # org_b (the cross-org escalation we're guarding against).
        self.target = User.objects.create_user(username="target_mtoc", password="pw")
        UserProfile.objects.create(user=self.target, organization=self.org_a, role="viewer")

    def test_admin_a_cannot_create_membership_in_org_b(self):
        """The Finding #2 attack: admin of A grants admin in B → 403."""
        self.client.force_authenticate(self.admin_a)
        response = self.client.post("/api/v1/auth/memberships/", {
            "user": self.target.id,
            "organization": self.org_b.id,
            "role": "admin",
        })
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            f"Expected 403, got {response.status_code}: {response.data!r}",
        )

    def test_admin_a_can_create_membership_in_own_org_a(self):
        """Sanity: admin_a CAN create memberships in their own org."""
        # Create a fresh user whose profile org is B, so they are NOT yet a
        # member of org A (the post_save signal only auto-mirrors profile.org).
        new_user = User.objects.create_user(username="newbie_mtoc", password="pw")
        UserProfile.objects.create(user=new_user, organization=self.org_b, role="viewer")

        self.client.force_authenticate(self.admin_a)
        response = self.client.post("/api/v1/auth/memberships/", {
            "user": new_user.id,
            "organization": self.org_a.id,
            "role": "viewer",
        })
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"Expected 201, got {response.status_code}: {response.data!r}",
        )

    def test_admin_ab_can_create_membership_in_either_org(self):
        """Multi-org admin can POST for both orgs they admin."""
        # u1's profile is in org_a, so signal gives them org_a membership but
        # NOT org_b. We POST a membership for u1 in org_b — admin_ab is admin
        # of org_b and the user is not yet a member there.
        u1 = User.objects.create_user(username="u1_mtoc", password="pw")
        UserProfile.objects.create(user=u1, organization=self.org_a, role="viewer")

        self.client.force_authenticate(self.admin_ab)
        response_b = self.client.post("/api/v1/auth/memberships/", {
            "user": u1.id,
            "organization": self.org_b.id,
            "role": "viewer",
        })
        self.assertEqual(
            response_b.status_code,
            status.HTTP_201_CREATED,
            f"Expected 201 for admin_ab → org_b, got {response_b.status_code}: {response_b.data!r}",
        )
