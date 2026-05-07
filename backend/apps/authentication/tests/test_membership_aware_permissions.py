"""Findings A1 + B9: IsAdmin and IsManager must use membership-aware role.

A user who is admin of Org A and viewer of Org B should be granted admin
permissions on Org-A-targeted requests and denied on Org-B-targeted requests.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.authentication.models import (
    Organization,
    UserOrganizationMembership,
    UserProfile,
)
from apps.authentication.permissions import IsAdmin, IsManager

User = get_user_model()


class _StubView:
    def __init__(self, kwargs=None):
        self.kwargs = kwargs or {}


class TestMembershipAwarePermissions(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.org_a = Organization.objects.create(name="Org A", slug="map-a")
        self.org_b = Organization.objects.create(name="Org B", slug="map-b")

        # Multi-org user: admin in A, viewer in B.
        self.user = User.objects.create_user(username="multiuser_map", password="pw")
        UserProfile.objects.create(
            user=self.user, organization=self.org_a, role="admin"
        )
        # post_save signal creates membership in org_a (admin role from profile).
        # Add explicit viewer membership in org_b.
        UserOrganizationMembership.objects.create(
            user=self.user,
            organization=self.org_b,
            role="viewer",
            is_active=True,
            is_primary=False,
        )

    # --- has_permission via request.data['organization'] ---
    def test_isadmin_grants_when_request_targets_org_a(self):
        request = self.factory.post(
            "/whatever/", {"organization": self.org_a.id}, format="json"
        )
        request.user = self.user
        # DRF parses request.data on access; mimic that path:
        request.data = {"organization": self.org_a.id}
        view = _StubView()
        self.assertTrue(IsAdmin().has_permission(request, view))

    def test_isadmin_denies_when_request_targets_org_b(self):
        request = self.factory.post(
            "/whatever/", {"organization": self.org_b.id}, format="json"
        )
        request.user = self.user
        request.data = {"organization": self.org_b.id}
        view = _StubView()
        self.assertFalse(
            IsAdmin().has_permission(request, view),
            "User is viewer in Org B; IsAdmin must deny.",
        )

    # --- has_permission via view.kwargs['org_id'] ---
    def test_isadmin_grants_via_view_kwargs_for_org_a(self):
        request = self.factory.get("/whatever/")
        request.user = self.user
        request.data = {}
        view = _StubView(kwargs={"org_id": self.org_a.id})
        self.assertTrue(IsAdmin().has_permission(request, view))

    def test_isadmin_denies_via_view_kwargs_for_org_b(self):
        request = self.factory.get("/whatever/")
        request.user = self.user
        request.data = {}
        view = _StubView(kwargs={"org_id": self.org_b.id})
        self.assertFalse(IsAdmin().has_permission(request, view))

    # --- has_object_permission via obj.organization ---
    def test_isadmin_object_perm_uses_obj_org_a(self):
        class Obj:
            pass

        obj = Obj()
        obj.organization = self.org_a
        request = self.factory.get("/whatever/")
        request.user = self.user
        request.data = {}
        view = _StubView()
        self.assertTrue(IsAdmin().has_object_permission(request, view, obj))

    def test_isadmin_object_perm_uses_obj_org_b(self):
        class Obj:
            pass

        obj = Obj()
        obj.organization = self.org_b
        request = self.factory.get("/whatever/")
        request.user = self.user
        request.data = {}
        view = _StubView()
        self.assertFalse(IsAdmin().has_object_permission(request, view, obj))

    # --- IsManager parallel sanity ---
    def test_ismanager_grants_for_org_a(self):
        # Add manager-or-admin role in org_a — admin counts as manager.
        request = self.factory.post(
            "/whatever/", {"organization": self.org_a.id}, format="json"
        )
        request.user = self.user
        request.data = {"organization": self.org_a.id}
        view = _StubView()
        self.assertTrue(IsManager().has_permission(request, view))

    def test_ismanager_denies_for_org_b(self):
        request = self.factory.post(
            "/whatever/", {"organization": self.org_b.id}, format="json"
        )
        request.user = self.user
        request.data = {"organization": self.org_b.id}
        view = _StubView()
        self.assertFalse(
            IsManager().has_permission(request, view),
            "User is viewer in Org B; IsManager must deny.",
        )

    # --- Fallback to profile.organization when no other context ---
    def test_isadmin_falls_back_to_profile_org_when_no_target(self):
        request = self.factory.get("/whatever/")
        request.user = self.user
        request.data = {}
        view = _StubView()
        # User's profile.organization is org_a (admin) — should grant.
        self.assertTrue(
            IsAdmin().has_permission(request, view),
            "Without explicit target, fall back to profile.organization (org_a, admin -> True).",
        )

    # --- query_params resolution (Findings A1 + B9 follow-up) ---
    # Production views like resolve_exception read ?organization_id=B via
    # get_target_organization. Without query_params resolution in the helper,
    # a manager-in-A / viewer-in-B user could escalate by spoofing
    # ?organization_id=B while the permission falls back to profile.org.
    def test_isadmin_grants_via_query_param_for_org_a(self):
        request = self.factory.get(f"/whatever/?organization_id={self.org_a.id}")
        request.user = self.user
        request.data = {}
        view = _StubView()
        self.assertTrue(IsAdmin().has_permission(request, view))

    def test_isadmin_denies_via_query_param_for_org_b(self):
        """Multi-org user spoofs ?organization_id=B; permission must deny."""
        request = self.factory.get(f"/whatever/?organization_id={self.org_b.id}")
        request.user = self.user
        request.data = {}
        view = _StubView()
        self.assertFalse(
            IsAdmin().has_permission(request, view),
            "User is viewer in Org B; ?organization_id=B must NOT escalate.",
        )

    def test_query_param_org_id_alias_also_resolves(self):
        request = self.factory.get(f"/whatever/?org_id={self.org_b.id}")
        request.user = self.user
        request.data = {}
        view = _StubView()
        self.assertFalse(IsAdmin().has_permission(request, view))
