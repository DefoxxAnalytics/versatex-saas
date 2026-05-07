"""Finding B9 (Phase 1 task 1.5b): delete_insight_feedback must use
membership-aware admin check, not legacy profile.role.

Multi-org user is admin in Org A and viewer in Org B. The view targets
Org B (via ?organization_id=<org_b>). The feedback is owned by another
user in Org B. Under the legacy profile.role check, delete would be
incorrectly granted (profile.role == 'admin'). Under membership-aware
check (user_is_admin_in_org with feedback.organization), delete is
correctly denied (user is only viewer in Org B).
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.analytics.models import InsightFeedback
from apps.authentication.models import (
    Organization,
    UserOrganizationMembership,
    UserProfile,
)

User = get_user_model()


class TestDeleteFeedbackMembershipAware(APITestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="Org A", slug="dim-a")
        self.org_b = Organization.objects.create(name="Org B", slug="dim-b")

        # Multi-org user: admin in A, viewer in B.
        self.user = User.objects.create_user(username="dimuser", password="pw")
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

        # Feedback owned by a different user in Org B.
        self.other = User.objects.create_user(username="other_dim", password="pw")
        UserProfile.objects.create(
            user=self.other, organization=self.org_b, role="viewer"
        )
        self.feedback_in_org_b = InsightFeedback.objects.create(
            organization=self.org_b,
            insight_id="insight-001",
            insight_type="maverick_spend",
            insight_title="Test insight",
            insight_severity="medium",
            action_taken="implemented",
            action_by=self.other,
        )

        self.client.force_authenticate(self.user)

    def _delete_url(self, feedback_id, org_id):
        # Target org B explicitly so get_target_organization scopes to Org B
        # (otherwise feedback lookup 404s before reaching the admin check).
        return (
            f"/api/v1/analytics/ai-insights/feedback/{feedback_id}/delete/"
            f"?organization_id={org_id}"
        )

    def test_admin_in_org_a_cannot_delete_feedback_in_org_b(self):
        """User is admin in A but viewer in B; the feedback is in B; not the
        owner. The legacy profile.role == 'admin' check would incorrectly
        grant deletion. Membership-aware check must DENY (403).
        """
        url = self._delete_url(self.feedback_in_org_b.id, self.org_b.id)
        response = self.client.delete(url)
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            f"Expected 403 (membership-aware admin check denies non-admin in Org B); "
            f"got {response.status_code}. Feedback should still exist.",
        )
        # Sanity: feedback was NOT deleted.
        self.assertTrue(
            InsightFeedback.objects.filter(id=self.feedback_in_org_b.id).exists(),
            "Feedback must still exist after denied delete.",
        )

    def test_admin_in_org_a_can_delete_feedback_in_org_a(self):
        """Sanity: user is admin in Org A; admin-in-org grants deletion of
        another user's feedback in Org A.
        """
        other_in_a = User.objects.create_user(username="other_in_a", password="pw")
        UserProfile.objects.create(
            user=other_in_a, organization=self.org_a, role="viewer"
        )
        feedback_in_a = InsightFeedback.objects.create(
            organization=self.org_a,
            insight_id="insight-002",
            insight_type="maverick_spend",
            insight_title="Test insight A",
            insight_severity="medium",
            action_taken="implemented",
            action_by=other_in_a,
        )
        url = self._delete_url(feedback_in_a.id, self.org_a.id)
        response = self.client.delete(url)
        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            f"Expected 204 (admin in Org A); got {response.status_code}.",
        )

    def test_owner_can_always_delete_their_own_feedback(self):
        """Sanity: the feedback owner can always delete, regardless of role."""
        viewer_in_b = self.other  # already viewer in Org B and owner of feedback
        self.client.force_authenticate(viewer_in_b)
        url = self._delete_url(self.feedback_in_org_b.id, self.org_b.id)
        response = self.client.delete(url)
        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            f"Owner must be able to delete their own feedback; got {response.status_code}.",
        )
