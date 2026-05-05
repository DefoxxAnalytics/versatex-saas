"""Finding #11 permanent fix: switch_organization must be atomic.

Bug background: switch_organization made two sequential .update() calls
(unset old primary, set new primary) without transaction.atomic() or
select_for_update. The model's save() correctly uses both, but .update()
bypasses save(), so concurrent calls can break the
'exactly one is_primary=True per user' invariant. If the second update
also fails after the first succeeds, the user is left with ZERO primaries.

See docs/codebase-review-2026-05-04-v2.md Finding #11.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import (
    Organization,
    UserOrganizationMembership,
    UserProfile,
)

User = get_user_model()


class TestSwitchOrgAtomicity(APITestCase):
    """Drift-guard suite for Finding #11 permanent fix."""

    def setUp(self):
        self.org_a = Organization.objects.create(name="Org A", slug="org-a-soa")
        self.org_b = Organization.objects.create(name="Org B", slug="org-b-soa")

        self.user = User.objects.create_user(username="multiuser_soa", password="pw")
        # post_save signal on UserProfile auto-creates a primary membership in org_a.
        UserProfile.objects.create(user=self.user, organization=self.org_a, role="admin")

        # Add a second active (non-primary) membership in org_b.
        UserOrganizationMembership.objects.create(
            user=self.user,
            organization=self.org_b,
            role="admin",
            is_active=True,
            is_primary=False,
        )

        self.client.force_authenticate(self.user)
        self.switch_url = f"/api/v1/auth/user/organizations/{self.org_b.id}/switch/"

    def _primary_org_ids(self):
        return list(
            UserOrganizationMembership.objects.filter(
                user=self.user, is_primary=True
            ).values_list("organization_id", flat=True)
        )

    def test_switch_to_org_b_succeeds(self):
        """Sanity: a normal switch sets B primary and unsets A primary."""
        response = self.client.post(self.switch_url)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"Got {response.status_code}: {response.data!r}",
        )
        primaries = self._primary_org_ids()
        self.assertEqual(
            primaries,
            [self.org_b.id],
            f"Expected only org_b as primary, got {primaries}",
        )

    def test_switch_holds_invariant_after_internal_error(self):
        """If the second update raises mid-flight, the first must roll back too.

        We patch the second .update() call (the SET-primary on org_b) to raise.
        Without atomicity, the first .update() (UNSET-primary on org_a)
        persists, leaving the user with ZERO primaries — invariant violated.
        With atomicity, both updates roll back and org_a remains primary.
        """
        original_primaries = self._primary_org_ids()
        self.assertEqual(
            original_primaries,
            [self.org_a.id],
            f"Setup precondition: expected org_a primary, got {original_primaries}",
        )

        original_filter = UserOrganizationMembership.objects.filter
        call_count = {"n": 0}

        def filter_with_failing_second_update(*args, **kwargs):
            qs = original_filter(*args, **kwargs)
            real_update = qs.update

            def update_wrapper(*a, **k):
                call_count["n"] += 1
                if call_count["n"] == 2:
                    raise IntegrityError("simulated mid-flight failure")
                return real_update(*a, **k)

            qs.update = update_wrapper
            return qs

        with patch.object(
            UserOrganizationMembership.objects,
            "filter",
            side_effect=filter_with_failing_second_update,
        ):
            try:
                self.client.post(self.switch_url)
            except IntegrityError:
                # Without atomicity OR if the view doesn't catch the error,
                # the request raises. That's fine — what matters is the DB state.
                pass

        # After the simulated failure, the invariant must hold:
        # exactly one primary, still org_a (rolled back).
        primaries = self._primary_org_ids()
        self.assertEqual(
            len(primaries),
            1,
            f"Invariant broken: expected exactly 1 primary, got {primaries}.",
        )
        self.assertEqual(
            primaries,
            [self.org_a.id],
            f"Rollback failed: expected org_a primary preserved, got {primaries}",
        )
