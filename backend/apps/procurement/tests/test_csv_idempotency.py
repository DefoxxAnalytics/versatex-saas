"""v3.0 Phase 1 task 1.7 -- `process_csv_upload` idempotency across retries.

Bug (Concurrency H, second-pass codebase review): the Celery task processes
CSV rows in batches but is not idempotent across retries. If the worker
crashes mid-batch (OOM kill, db connection drop, signal trap), Celery's
default retry re-runs the task from row 0. Rows already inserted are
duplicated -- now caught by the canonical-case unique constraint, but:
  - row counts diverge from reality
  - audit-log entries duplicate
  - status fields thrash on intermediate writes

Fix: `DataUpload.last_processed_batch_index` checkpoint advances after each
batch via `.update()` (signal-free). On task entry, the checkpoint indicates
where to resume; on terminal completion, it resets to 0.

These tests assert:
  - mid-batch crash leaves `last_processed_batch_index` at the count of
    fully-handled batches (the next batch to attempt)
  - re-invoking the task with the same `data_upload_id` skips the prior
    batches (no double-insert)
  - successful run resets the checkpoint to 0 so the same upload_id can be
    safely re-processed if needed
  - in-memory accumulators (counts, error_log, batch_log) are seeded from
    persisted state so the resumed run's final tallies are correct
"""
import json
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import models as django_models
from django.test import TestCase, TransactionTestCase

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


def _row(idx):
    """Build one valid CSV data row with a unique amount for traceability."""
    return f"Acme Co,Office,{1000 + idx}.00,2026-01-15,desc-{idx}\n"


def _build_csv(*, rows_per_batch, batch_count):
    """Build a CSV with `batch_count` batches of `rows_per_batch` valid rows.

    Total rows = rows_per_batch * batch_count. Every row is well-formed so
    failures must originate from the explicit monkeypatch in the test, not
    from validation or duplicate checks.
    """
    header = "supplier,category,amount,date,description\n"
    body_parts = []
    for batch_idx in range(batch_count):
        for row_idx in range(rows_per_batch):
            global_idx = batch_idx * rows_per_batch + row_idx
            body_parts.append(_row(global_idx))
    return header + "".join(body_parts)


class _IdempotencyFixturesMixin:
    """Shared org/user/upload fixtures. Patches CSV_BATCH_SIZE small so we
    can simulate multi-batch crashes with a few hundred rows of fixture
    data instead of thousands."""

    BATCH_SIZE = 5

    def setUp(self):
        super().setUp()
        self._batch_size_patcher = patch(
            "apps.procurement.tasks.CSV_BATCH_SIZE", self.BATCH_SIZE
        )
        self._batch_size_patcher.start()
        self.addCleanup(self._batch_size_patcher.stop)

        # Org slug is unique-per-class to avoid collisions across the
        # mix of TestCase (rolled-back) and TransactionTestCase (truncate)
        # subclasses in this module.
        slug_suffix = uuid.uuid4().hex[:8]
        self.organization = Organization.objects.create(
            name=f"Idempotency Org {slug_suffix}",
            slug=f"idempotency-org-{slug_suffix}",
        )
        self.user = User.objects.create_user(
            username=f"idem_uploader_{slug_suffix}",
            email=f"idem-{slug_suffix}@example.com",
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
            file_name="idempotency.csv",
            original_file_name="idempotency.csv",
            file_size=len(csv_payload),
            batch_id=f"batch-{uuid.uuid4().hex[:12]}",
            status="pending",
        )
        upload.stored_file.save(
            "idempotency.csv", ContentFile(csv_payload.encode("utf-8"))
        )
        return upload


class _BaseIdempotencyTest(_IdempotencyFixturesMixin, TestCase):
    """Default base: TestCase rollback isolation. Use this for tests that
    don't depend on observing partially-committed state from inside the
    task (e.g., happy-path success-completion checks)."""


class TestCheckpointAdvancesPerBatch(_BaseIdempotencyTest):
    """A clean run advances the checkpoint after every batch and resets it
    to 0 at terminal completion. Tests the happy-path contract.
    """

    def test_successful_run_resets_checkpoint_to_zero(self):
        csv_payload = _build_csv(rows_per_batch=self.BATCH_SIZE, batch_count=3)
        upload = self._create_upload(csv_payload)

        process_csv_upload.apply(
            args=[upload.id, CSV_MAPPING],
            kwargs={"skip_invalid": True},
        ).get()

        upload.refresh_from_db()
        self.assertEqual(upload.status, "completed")
        self.assertEqual(upload.successful_rows, 3 * self.BATCH_SIZE)
        self.assertEqual(
            upload.last_processed_batch_index,
            0,
            "Successful completion must reset the idempotency checkpoint "
            "to 0 so the upload_id is safe to re-process if needed.",
        )


class _SimulatedWorkerCrash(BaseException):
    """BaseException subclass that bypasses `except Exception` handlers.

    A real Celery worker SIGKILL/OOM-kill leaves no in-process opportunity
    for cleanup -- the kernel terminates the process and Celery re-dispatches
    the task on a fresh worker. We can't simulate that within a single
    Python process, but we can simulate the in-task state at the moment
    of crash by raising a `BaseException` subclass: it propagates through
    every `except Exception` block in the task (the per-row, per-batch,
    and outer-try handlers), exits the task function, and leaves the
    DataUpload row in whatever state the last `.update()` call wrote.
    That is exactly the state a fresh worker would observe on retry.
    """


class TestMidBatchCrashLeavesCheckpoint(
    _IdempotencyFixturesMixin, TransactionTestCase
):
    """Simulate a worker crash mid-run: the 3rd batch (batch_index=2) raises
    a BaseException that bypasses the task's `except Exception` handlers,
    mimicking a real SIGKILL that leaves no in-process cleanup.

    Uses ``TransactionTestCase`` (not ``TestCase``) because the task's
    ``transaction.atomic()`` per-batch acts as a real BEGIN/COMMIT in
    production; under ``TestCase``'s outer-atomic wrapping it would behave
    as a savepoint and post-batch ``.update()`` calls wouldn't survive a
    BaseException unwinding. ``TransactionTestCase`` truncates between
    tests instead of rolling back, matching production semantics.
    """

    def test_crash_at_third_batch_checkpoints_at_two(self):
        # 5 batches of 5 rows. We'll fail Transaction.objects.create on the
        # first row of batch_index=2 (rows 11-15 in 0-indexed terms).
        rows_per_batch = self.BATCH_SIZE
        batch_count = 5
        csv_payload = _build_csv(
            rows_per_batch=rows_per_batch, batch_count=batch_count
        )
        upload = self._create_upload(csv_payload)

        original_create = Transaction.objects.create
        call_counter = {"n": 0}

        def crashing_create(*args, **kwargs):
            call_counter["n"] += 1
            # Batch 0 has 5 creates (calls 1-5). Batch 1 has 5 creates
            # (calls 6-10). Batch 2's first create is call 11; raise then.
            if call_counter["n"] == 11:
                raise _SimulatedWorkerCrash("simulated worker SIGKILL")
            return original_create(*args, **kwargs)

        # Call the task's underlying function directly (bypassing Celery's
        # eager tracer, which wraps the call in handlers that interfere
        # with BaseException propagation in unhelpful ways for this test).
        # The task body is what we want to exercise; .apply() vs direct
        # call is irrelevant to the idempotency invariant.
        with patch.object(
            Transaction.objects, "create", side_effect=crashing_create
        ):
            with self.assertRaises(_SimulatedWorkerCrash):
                process_csv_upload.run(
                    upload.id, CSV_MAPPING, skip_invalid=True
                )

        upload.refresh_from_db()

        # Checkpoint records the next batch to attempt. Batches 0 and 1
        # committed and advanced the checkpoint to 2; the crash hit
        # before batch 2's checkpoint update could fire, so the
        # persisted value is exactly 2 -- "next batch to attempt".
        self.assertEqual(
            upload.last_processed_batch_index,
            2,
            f"Expected checkpoint at 2 (next batch to retry), got "
            f"{upload.last_processed_batch_index}. Status was "
            f"{upload.status!r}.",
        )

        # Batches 0 and 1 committed; batch 2's transaction.atomic() rolled
        # back when the BaseException unwound the with-block. Batches 3-4
        # never ran. Exactly 2 * BATCH_SIZE = 10 rows in the database.
        self.assertEqual(
            Transaction.objects.filter(organization=self.organization).count(),
            2 * self.BATCH_SIZE,
            "Only batches 0 and 1 should have committed rows before the "
            "simulated crash.",
        )

        # Persisted running counts reflect the two committed batches.
        self.assertEqual(upload.successful_rows, 2 * self.BATCH_SIZE)


class TestResumeSkipsCompletedBatches(
    _IdempotencyFixturesMixin, TransactionTestCase
):
    """End-to-end retry simulation: invoke the task, force a mid-batch
    crash, then re-invoke with the same upload_id. Assert the resumed run
    skips completed batches (no double-insert), processes only the
    remaining batches, and ends with the correct row count.

    See ``TestMidBatchCrashLeavesCheckpoint`` for why ``TransactionTestCase``
    is required here.
    """

    def test_retry_resumes_from_checkpoint_no_double_insert(self):
        rows_per_batch = self.BATCH_SIZE
        batch_count = 4
        csv_payload = _build_csv(
            rows_per_batch=rows_per_batch, batch_count=batch_count
        )
        upload = self._create_upload(csv_payload)

        original_create = Transaction.objects.create
        first_run_calls = {"n": 0}

        def crashing_create(*args, **kwargs):
            first_run_calls["n"] += 1
            # Crash on first row of batch 2 (call 11 = 2*5 + 1).
            if first_run_calls["n"] == 11:
                raise _SimulatedWorkerCrash("simulated worker SIGKILL")
            return original_create(*args, **kwargs)

        # First invocation: BaseException bypasses every `except Exception`
        # in the task and propagates out, leaving the DataUpload row in
        # the same state a fresh-worker retry would observe. Call the
        # task body directly to bypass Celery's eager-mode tracer.
        with patch.object(
            Transaction.objects, "create", side_effect=crashing_create
        ):
            with self.assertRaises(_SimulatedWorkerCrash):
                process_csv_upload.run(
                    upload.id, CSV_MAPPING, skip_invalid=True
                )

        upload.refresh_from_db()
        self.assertEqual(upload.last_processed_batch_index, 2)
        rows_after_crash = Transaction.objects.filter(
            organization=self.organization
        ).count()
        self.assertEqual(rows_after_crash, 2 * self.BATCH_SIZE)

        # The crashed run never reached the success-path stored_file
        # cleanup, so the file is still present for the retry to read.
        self.assertTrue(
            bool(upload.stored_file),
            "stored_file must still be present for the resume invocation",
        )

        # Second invocation: no crash; should resume from batch 2 and
        # complete cleanly. Celery would re-dispatch with the same args.
        process_csv_upload.apply(
            args=[upload.id, CSV_MAPPING],
            kwargs={"skip_invalid": True},
        ).get()

        upload.refresh_from_db()

        # End state: all 4 batches processed cleanly across the two runs.
        # No row was double-inserted -- the canonical unique constraint
        # would have raised, but we assert by count for clarity.
        self.assertEqual(upload.status, "completed")
        self.assertEqual(upload.successful_rows, batch_count * self.BATCH_SIZE)
        self.assertEqual(
            Transaction.objects.filter(organization=self.organization).count(),
            batch_count * self.BATCH_SIZE,
            "Resumed run must not double-insert prior batches' rows.",
        )
        self.assertEqual(
            upload.last_processed_batch_index,
            0,
            "Successful completion (after resume) resets the checkpoint.",
        )

        # batch_log: the first run committed batches 0-1 and crashed
        # before batch 2's outcome was recorded. The resumed run
        # processed batches 2-3 successfully. Final log should record
        # all four batch indices as succeeded.
        log = json.loads(upload.error_log) if upload.error_log else []
        batch_entries = [e for e in log if e.get("kind") == "batch"]
        succeeded_indices = sorted(
            e["batch_index"] for e in batch_entries
            if e["status"] == "succeeded"
        )
        self.assertEqual(
            succeeded_indices,
            [0, 1, 2, 3],
            f"All 4 batch indices must appear as succeeded across the "
            f"two runs. Got: {batch_entries}",
        )


class TestFreshUploadStartsAtZero(_BaseIdempotencyTest):
    """Defensive: a brand-new DataUpload has `last_processed_batch_index=0`
    by default and the task treats it as a fresh run, not a resume.
    """

    def test_default_field_value_is_zero(self):
        csv_payload = _build_csv(rows_per_batch=self.BATCH_SIZE, batch_count=1)
        upload = self._create_upload(csv_payload)
        self.assertEqual(upload.last_processed_batch_index, 0)

        process_csv_upload.apply(
            args=[upload.id, CSV_MAPPING],
            kwargs={"skip_invalid": True},
        ).get()

        upload.refresh_from_db()
        self.assertEqual(upload.status, "completed")
        self.assertEqual(upload.last_processed_batch_index, 0)


class TestFieldExistsOnModel(TestCase):
    """The new field is wired into the Django model with the expected
    type and default. Catches future schema-change mistakes (e.g.,
    accidentally renaming or dropping the column).
    """

    def test_field_is_positive_integer_default_zero(self):
        field = DataUpload._meta.get_field("last_processed_batch_index")
        self.assertIsInstance(field, django_models.PositiveIntegerField)
        self.assertEqual(field.default, 0)
