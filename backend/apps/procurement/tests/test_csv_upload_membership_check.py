"""Finding C4: Celery CSV upload task must re-check membership at execution time.

`process_csv_upload` runs asynchronously after `delay()` returns. Between enqueue
and execution, the uploading user could be removed or deactivated from the
organization. The task must re-verify an active `UserOrganizationMembership`
before writing any rows; otherwise a removed user can still ingest data.
"""

import io
import json
import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase

from apps.authentication.models import (
    Organization,
    UserOrganizationMembership,
    UserProfile,
)
from apps.procurement.models import DataUpload, Transaction
from apps.procurement.tasks import process_csv_upload

User = get_user_model()


CSV_PAYLOAD = (
    "supplier,category,amount,date,description\n"
    "Acme Co,Office,1000.00,2026-01-15,Pens\n"
    "Acme Co,Office,2500.00,2026-01-16,Paper\n"
)

CSV_MAPPING = {
    "supplier": "supplier",
    "category": "category",
    "amount": "amount",
    "date": "date",
    "description": "description",
}

EXPECTED_ERROR_MESSAGE = (
    "User no longer an active member of organization at execution time"
)


class CeleryCSVUploadMembershipCheckTests(TestCase):
    """Finding C4: re-verify membership at task execution, not at enqueue."""

    def setUp(self):
        self.organization = Organization.objects.create(
            name="Membership-Check Org",
            slug="membership-check-org",
        )
        self.user = User.objects.create_user(
            username="csv_uploader_c4",
            email="csv_uploader_c4@example.com",
            password="UploadPass123!",
        )
        # Creating a UserProfile auto-syncs an active membership via signal.
        UserProfile.objects.create(
            user=self.user,
            organization=self.organization,
            role="manager",
            is_active=True,
        )

        self.upload = DataUpload.objects.create(
            organization=self.organization,
            uploaded_by=self.user,
            file_name="member_check.csv",
            original_file_name="member_check.csv",
            file_size=len(CSV_PAYLOAD),
            batch_id=f"batch-{uuid.uuid4().hex[:12]}",
            status="pending",
        )
        self.upload.stored_file.save(
            "member_check.csv", ContentFile(CSV_PAYLOAD.encode("utf-8"))
        )

    def _deactivate_membership(self):
        membership = UserOrganizationMembership.objects.get(
            user=self.user, organization=self.organization
        )
        membership.is_active = False
        membership.save()

    def test_task_aborts_when_membership_no_longer_active(self):
        """Task must mark upload failed and ingest zero rows when user is no
        longer an active member at execution time.
        """
        self._deactivate_membership()

        # Sanity check: arranged state matches the bug scenario.
        self.assertFalse(
            UserOrganizationMembership.objects.filter(
                user=self.user,
                organization=self.organization,
                is_active=True,
            ).exists(),
            "Test setup invariant: membership must be inactive before task runs",
        )
        transactions_before = Transaction.objects.filter(
            organization=self.organization
        ).count()

        result = process_csv_upload.apply(
            args=[self.upload.id, CSV_MAPPING],
            kwargs={"skip_invalid": True},
        ).get()

        self.upload.refresh_from_db()
        self.assertEqual(
            self.upload.status,
            "failed",
            f"upload.status should be 'failed', got {self.upload.status!r}",
        )

        # The exact error message must be surfaced through the upload's error
        # surface so admins can see why the ingest aborted.
        error_log_text = (
            self.upload.error_log
            if isinstance(self.upload.error_log, str)
            else json.dumps(self.upload.error_log)
        )
        self.assertIn(
            EXPECTED_ERROR_MESSAGE,
            error_log_text,
            f"error_log must contain {EXPECTED_ERROR_MESSAGE!r}, got {error_log_text!r}",
        )

        transactions_after = Transaction.objects.filter(
            organization=self.organization
        ).count()
        self.assertEqual(
            transactions_after,
            transactions_before,
            "No transactions may be ingested when membership check fails",
        )
        self.assertEqual(
            self.upload.successful_rows,
            0,
            "successful_rows must remain 0 when membership check fails",
        )

        # Structured early-return result so callers can distinguish this from
        # ordinary processing failures.
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("status"), "failed")
        self.assertIn(EXPECTED_ERROR_MESSAGE, result.get("error", ""))

    def test_task_proceeds_when_membership_remains_active(self):
        """Regression guard: an active membership must not be blocked."""
        self.assertTrue(
            UserOrganizationMembership.objects.filter(
                user=self.user,
                organization=self.organization,
                is_active=True,
            ).exists()
        )

        process_csv_upload.apply(
            args=[self.upload.id, CSV_MAPPING],
            kwargs={"skip_invalid": True},
        ).get()

        self.upload.refresh_from_db()
        self.assertIn(self.upload.status, {"completed", "partial"})
        self.assertEqual(self.upload.successful_rows, 2)
