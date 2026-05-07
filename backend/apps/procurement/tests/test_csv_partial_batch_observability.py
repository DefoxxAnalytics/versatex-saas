"""Finding C2: per-batch observability on async CSV upload.

`process_csv_upload` commits each ``transaction.atomic()`` block independently.
If batch 5 raises after batches 1-4 commit, those four batches are kept and the
upload is marked ``status='partial'`` -- but historically the user had no way
to tell *which* batches survived. These tests assert that:

  - Per-batch outcome is recorded in ``DataUpload.error_log`` (both successes
    and failures), with row ranges, exception class, exception message and
    ``first_failed_row_number`` for failed batches.
  - ``progress_message`` carries a concise human-readable summary naming the
    first failed batch and its row range.
  - When a batch rolls back under ``skip_invalid=False``, prior batches stay
    committed, the failing batch is recorded as failed (with rolled_back=True),
    and remaining batches are left unprocessed.
  - Status reflects partial success when at least one batch committed.
"""

import json
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase

from apps.authentication.models import Organization, UserProfile
from apps.procurement.models import DataUpload, Transaction
from apps.procurement.tasks import process_csv_upload

User = get_user_model()


CSV_MAPPING = {
    "supplier": "supplier",
    "category": "category",
    "amount": "amount",
    "date": "date",
    "description": "description",
}


def _row(idx, *, bad_date=False):
    """Build one CSV data row. Optionally emit an invalid date string."""
    date = "not-a-date" if bad_date else "2026-01-15"
    return f"Acme Co,Office,{100 + idx}.00,{date},desc-{idx}\n"


def _build_csv(
    rows_per_batch, *, batch_count, fail_in_batch=None, fail_at_row_in_batch=None
):
    """Build a CSV with ``batch_count`` batches of ``rows_per_batch`` rows.

    If ``fail_in_batch`` is supplied (0-indexed), the row at
    ``fail_at_row_in_batch`` (0-indexed within that batch) emits an
    unparseable date, which validation will reject.
    """
    header = "supplier,category,amount,date,description\n"
    body_parts = []
    for batch_idx in range(batch_count):
        for row_idx in range(rows_per_batch):
            global_idx = batch_idx * rows_per_batch + row_idx
            is_bad = (
                fail_in_batch is not None
                and batch_idx == fail_in_batch
                and row_idx == fail_at_row_in_batch
            )
            body_parts.append(_row(global_idx, bad_date=is_bad))
    return header + "".join(body_parts)


class _BasePartialBatchTest(TestCase):
    """Shared org/user/upload fixtures. Patches CSV_BATCH_SIZE to a small
    value so we don't need 4000-row fixtures.
    """

    BATCH_SIZE = 5

    def setUp(self):
        # Shrink batch size so 3-batch fixtures stay tiny.
        self._batch_size_patcher = patch(
            "apps.procurement.tasks.CSV_BATCH_SIZE", self.BATCH_SIZE
        )
        self._batch_size_patcher.start()
        self.addCleanup(self._batch_size_patcher.stop)

        self.organization = Organization.objects.create(name="C2 Org", slug="c2-org")
        self.user = User.objects.create_user(
            username="c2_uploader",
            email="c2@example.com",
            password="UploadPass123!",
        )
        UserProfile.objects.create(
            user=self.user,
            organization=self.organization,
            role="manager",
            is_active=True,
        )

    def _create_upload(self, csv_payload):
        upload = DataUpload.objects.create(
            organization=self.organization,
            uploaded_by=self.user,
            file_name="partial.csv",
            original_file_name="partial.csv",
            file_size=len(csv_payload),
            batch_id=f"batch-{uuid.uuid4().hex[:12]}",
            status="pending",
        )
        upload.stored_file.save("partial.csv", ContentFile(csv_payload.encode("utf-8")))
        return upload

    @staticmethod
    def _decoded_log(upload):
        """error_log is stored as a JSON string; decode to a list of dicts."""
        raw = upload.error_log
        if not raw:
            return []
        if isinstance(raw, list):
            return raw
        return json.loads(raw)

    @staticmethod
    def _batch_entries(log):
        return [e for e in log if e.get("kind") == "batch"]

    @staticmethod
    def _row_entries(log):
        return [e for e in log if e.get("kind") == "row"]


class TestPartialBatchAbort(_BasePartialBatchTest):
    """skip_invalid=False: a bad row in batch 1 (0-indexed) must roll back
    that batch, leave batch 0 committed, and skip batch 2 entirely.
    """

    def test_batch_failure_recorded_with_row_range_and_first_failed_row(self):
        # 3 batches of 5 rows = 15 data rows. Row 7 (CSV row 9, batch index 1
        # row index 1) emits an invalid date.
        csv_payload = _build_csv(
            rows_per_batch=self.BATCH_SIZE,
            batch_count=3,
            fail_in_batch=1,
            fail_at_row_in_batch=1,
        )
        upload = self._create_upload(csv_payload)

        process_csv_upload.apply(
            args=[upload.id, CSV_MAPPING],
            kwargs={"skip_invalid": False},
        ).get()

        upload.refresh_from_db()

        # Status: prior batch committed, so this is partial (not failed).
        self.assertEqual(
            upload.status,
            "partial",
            f"Expected partial status, got {upload.status!r}",
        )

        # Counts: batch 0 committed 5 rows; batches 1 & 2 left no rows.
        self.assertEqual(upload.successful_rows, self.BATCH_SIZE)
        self.assertEqual(
            Transaction.objects.filter(organization=self.organization).count(),
            self.BATCH_SIZE,
            "Only batch 0's rows must be visible in the database after a "
            "batch-1 abort",
        )

        log = self._decoded_log(upload)
        batches = self._batch_entries(log)

        # Batches 0 (succeeded) and 1 (failed) must be present. Batch 2
        # never ran -- we should NOT see an entry for it.
        self.assertEqual(
            len(batches),
            2,
            f"Expected exactly 2 batch entries (succeeded + failed), got "
            f"{len(batches)}: {batches}",
        )
        succeeded = [b for b in batches if b["status"] == "succeeded"]
        failed = [b for b in batches if b["status"] == "failed"]
        self.assertEqual(len(succeeded), 1, f"batches: {batches}")
        self.assertEqual(len(failed), 1, f"batches: {batches}")

        # Succeeded batch is batch 0, rows 2-6 (1-indexed CSV row numbers,
        # row 1 is the header).
        b0 = succeeded[0]
        self.assertEqual(b0["batch_index"], 0)
        self.assertEqual(b0["first_row_number"], 2)
        self.assertEqual(b0["rows_in_batch"], self.BATCH_SIZE)
        self.assertEqual(b0["rows_ingested"], self.BATCH_SIZE)
        self.assertFalse(b0["rolled_back"])

        # Failed batch is batch 1. The bad row was row index 1 within the
        # batch -> CSV row 8 (header=1, batch starts at row 7, second row
        # is row 8). first_row_number for batch 1 = 7.
        b1 = failed[0]
        self.assertEqual(b1["batch_index"], 1)
        self.assertEqual(b1["first_row_number"], 7)
        self.assertTrue(b1["rolled_back"])
        self.assertIn("error_class", b1)
        self.assertIn("message", b1)
        self.assertEqual(
            b1["first_failed_row_number"],
            8,
            f"first_failed_row_number should pinpoint the bad row, got {b1}",
        )

        # progress_message must surface the partial outcome.
        self.assertIn("1 of 3 batches succeeded", upload.progress_message)
        self.assertIn("first failed batch: 1", upload.progress_message)
        self.assertIn("rows 7-", upload.progress_message)


class TestAllBatchesSucceed(_BasePartialBatchTest):
    """When every batch commits cleanly, status='completed', every batch is
    logged with status='succeeded', and the summary names total batches."""

    def test_all_batches_logged_as_succeeded(self):
        csv_payload = _build_csv(rows_per_batch=self.BATCH_SIZE, batch_count=2)
        upload = self._create_upload(csv_payload)

        process_csv_upload.apply(
            args=[upload.id, CSV_MAPPING],
            kwargs={"skip_invalid": True},
        ).get()

        upload.refresh_from_db()
        self.assertEqual(upload.status, "completed")
        self.assertEqual(upload.successful_rows, 2 * self.BATCH_SIZE)

        log = self._decoded_log(upload)
        batches = self._batch_entries(log)
        self.assertEqual(len(batches), 2)
        for b in batches:
            self.assertEqual(b["status"], "succeeded")
            self.assertFalse(b["rolled_back"])
            self.assertEqual(b["rows_ingested"], self.BATCH_SIZE)

        self.assertIn("2 of 2 batches succeeded", upload.progress_message)


class TestPerRowErrorsAlsoLogged(_BasePartialBatchTest):
    """skip_invalid=True with a bad row: per-row errors and per-batch
    summaries must coexist in the same error_log."""

    def test_row_error_logged_alongside_batch_summary(self):
        # 2 batches of 5 rows. Row index 2 in batch 1 has a bad date. With
        # skip_invalid=True, that row is recorded as a per-row error and
        # batch 1 still commits 4 rows.
        csv_payload = _build_csv(
            rows_per_batch=self.BATCH_SIZE,
            batch_count=2,
            fail_in_batch=1,
            fail_at_row_in_batch=2,
        )
        upload = self._create_upload(csv_payload)

        process_csv_upload.apply(
            args=[upload.id, CSV_MAPPING],
            kwargs={"skip_invalid": True},
        ).get()

        upload.refresh_from_db()

        # Both batches commit; one row is invalid.
        self.assertEqual(upload.status, "partial")
        self.assertEqual(upload.successful_rows, 2 * self.BATCH_SIZE - 1)
        self.assertEqual(upload.failed_rows, 1)

        log = self._decoded_log(upload)
        batches = self._batch_entries(log)
        rows = self._row_entries(log)

        # Both batches should be marked succeeded (no rollback).
        self.assertEqual(len(batches), 2)
        for b in batches:
            self.assertEqual(b["status"], "succeeded")
            self.assertFalse(b["rolled_back"])
        self.assertEqual(batches[1]["rows_skipped_invalid"], 1)
        self.assertEqual(batches[1]["rows_ingested"], self.BATCH_SIZE - 1)

        # Per-row error: bad row is batch 1 row index 2 -> CSV row 9.
        self.assertGreaterEqual(len(rows), 1)
        bad_row_entries = [r for r in rows if r["row"] == 9]
        self.assertTrue(
            bad_row_entries,
            f"Expected per-row error for CSV row 9, got rows: {rows}",
        )
