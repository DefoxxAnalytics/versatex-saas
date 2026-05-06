"""Finding #4: cross-org reads of is_public=True reports must be blocked.

`Report.can_access` short-circuits to `True` whenever `is_public=True`, with
no organization check. Combined with the four endpoints
(`detail`, `status`, `delete`, `download`) doing
`Report.objects.get(id=report_id)` (no org filter), any authenticated user
who knows or guesses a UUID can read any public report from any tenant.

Phase 0 containment: add an org filter at the queryset level on all four
sites so the get raises DoesNotExist for cross-org access.
Phase 1 task 1.3 will resolve `is_public` semantics with product and refactor
`can_access` properly.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import Organization, UserProfile
from apps.reports.models import Report

User = get_user_model()


class TestReportCrossOrgIsolation(APITestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="OrgA", slug="orga")
        self.org_b = Organization.objects.create(name="OrgB", slug="orgb")

        self.user_b = User.objects.create_user(username="ub", password="pw")
        UserProfile.objects.create(
            user=self.user_b,
            organization=self.org_b,
            role="viewer",
            is_active=True,
        )

        owner_a = User.objects.create_user(username="oa", password="pw")
        UserProfile.objects.create(
            user=owner_a,
            organization=self.org_a,
            role="admin",
            is_active=True,
        )

        self.public_report = Report.objects.create(
            organization=self.org_a,
            created_by=owner_a,
            name="OrgA public report",
            report_type="spend_analysis",
            report_format="pdf",
            is_public=True,
            status="completed",
        )

        refresh = RefreshToken.for_user(self.user_b)
        # Cookie-based auth (header fallback is DEBUG-only since S-#2).
        self.client.cookies["access_token"] = str(refresh.access_token)

    def test_user_in_org_b_cannot_read_org_a_public_report_detail(self):
        url = reverse("reports:detail", kwargs={"report_id": self.public_report.id})
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )

    def test_user_in_org_b_cannot_read_org_a_public_report_status(self):
        url = reverse("reports:status", kwargs={"report_id": self.public_report.id})
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )

    def test_user_in_org_b_cannot_download_org_a_public_report(self):
        url = reverse("reports:download", kwargs={"report_id": self.public_report.id})
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )

    def test_user_in_org_b_cannot_delete_org_a_public_report(self):
        url = reverse("reports:delete", kwargs={"report_id": self.public_report.id})
        response = self.client.delete(url)
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )
