"""Findings A1 + B9 (1.5b): P2P permission classes must use membership-aware role.

Multi-org user is admin in Org A and viewer in Org B. Permission classes
that require admin/manager must grant for Org A targets and deny for Org B.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.authentication.models import (
    Organization,
    UserOrganizationMembership,
    UserProfile,
)
from apps.authentication.permissions import (
    CanApprovePO,
    CanApprovePR,
    CanResolveExceptions,
    CanViewPaymentData,
)

User = get_user_model()


class _StubView:
    def __init__(self, kwargs=None):
        self.kwargs = kwargs or {}


class TestP2PPermissionsMembershipAware(TestCase):
    """Each P2P permission class requiring admin/manager must resolve role
    against the request's target org, not the user's legacy profile.organization.
    """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.org_a = Organization.objects.create(name="Org A", slug="p2p-a")
        self.org_b = Organization.objects.create(name="Org B", slug="p2p-b")

        # Multi-org user: admin in A, viewer in B.
        self.user = User.objects.create_user(username="p2puser", password="pw")
        UserProfile.objects.create(
            user=self.user, organization=self.org_a, role="admin"
        )
        # post_save signal creates membership (user, org_a, admin).
        UserOrganizationMembership.objects.create(
            user=self.user,
            organization=self.org_b,
            role="viewer",
            is_active=True,
            is_primary=False,
        )

    def _request_for_org(self, org):
        request = self.factory.post(
            "/whatever/", {"organization": org.id}, format="json"
        )
        request.user = self.user
        request.data = {"organization": org.id}
        return request

    def _check(self, perm_class, org, expected):
        request = self._request_for_org(org)
        view = _StubView()
        actual = perm_class().has_permission(request, view)
        self.assertEqual(
            actual,
            expected,
            f"{perm_class.__name__} for {org.slug}: expected {expected}, got {actual}",
        )

    # --- CanResolveExceptions: admin OR manager ---
    def test_can_resolve_exceptions_grants_for_org_a(self):
        self._check(CanResolveExceptions, self.org_a, True)

    def test_can_resolve_exceptions_denies_for_org_b(self):
        self._check(CanResolveExceptions, self.org_b, False)

    # --- CanViewPaymentData: admin OR manager ---
    def test_can_view_payment_data_grants_for_org_a(self):
        self._check(CanViewPaymentData, self.org_a, True)

    def test_can_view_payment_data_denies_for_org_b(self):
        self._check(CanViewPaymentData, self.org_b, False)

    # --- CanApprovePO: admin OR manager ---
    def test_can_approve_po_grants_for_org_a(self):
        self._check(CanApprovePO, self.org_a, True)

    def test_can_approve_po_denies_for_org_b(self):
        self._check(CanApprovePO, self.org_b, False)

    # --- CanApprovePR: admin OR manager ---
    def test_can_approve_pr_grants_for_org_a(self):
        self._check(CanApprovePR, self.org_a, True)

    def test_can_approve_pr_denies_for_org_b(self):
        self._check(CanApprovePR, self.org_b, False)
