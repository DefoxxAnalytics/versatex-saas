"""v3.0 Phase 1 Task 1.5 — post_save Redis I/O via ``transaction.on_commit``.

The procurement signals at ``apps/procurement/signals.py`` previously fired
``AIInsightsCache.invalidate_org_cache`` synchronously from within the database
transaction. If that transaction rolled back (FK violation, partial batch
failure, etc.) the cache had already been invalidated — leaving a cold cache
for unchanged data plus brief read-your-write inconsistency.

The fix wraps each side-effect call in ``transaction.on_commit`` so it only
fires after a successful commit. These tests assert:

1. **Rollback path:** when the surrounding transaction rolls back, the cache
   invalidation function is NEVER called.
2. **Commit path:** when the transaction commits, the cache invalidation
   function IS called exactly once per scheduled callback.
3. **Autocommit path:** outside an explicit transaction, the callback runs
   immediately (Django's documented behaviour for ``on_commit``).
"""

from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase

from apps.authentication.models import Organization
from apps.procurement.models import Transaction as TransactionModel
from apps.procurement.tests.factories import (
    CategoryFactory,
    SupplierFactory,
    TransactionFactory,
)

SIGNAL_TARGET = "apps.procurement.signals._invalidate_ai_cache"


class TransactionSaveOnCommitTests(TransactionTestCase):
    """End-to-end on_commit semantics for ``Transaction`` post_save.

    ``TransactionTestCase`` is required because the rollback assertion needs
    the explicit ``transaction.atomic()`` block to actually roll back at the
    DB layer — ``TestCase``'s outer atomic wrapper would swallow on_commit
    callbacks and never invoke them, which would make the commit-path
    assertion impossible to distinguish from a no-op.
    """

    def setUp(self):
        self.org = Organization.objects.create(
            name="Org OnCommit", slug="org-on-commit"
        )
        self.supplier = SupplierFactory(organization=self.org)
        self.category = CategoryFactory(organization=self.org)
        # Seed a row we can mutate to fire the post_save (created=False) path
        # without coupling to the create branch.
        self.existing_txn = TransactionFactory(
            organization=self.org,
            supplier=self.supplier,
            category=self.category,
        )

    def test_rollback_does_not_invalidate_cache(self):
        """A rolled-back transaction must NOT trigger cache invalidation."""
        with patch(SIGNAL_TARGET) as mock_invalidate:
            try:
                with transaction.atomic():
                    self.existing_txn.description = "edited inside doomed txn"
                    self.existing_txn.save()
                    # Force rollback. The signal already fired and scheduled an
                    # on_commit callback; raising aborts the transaction so the
                    # callback should be discarded.
                    raise IntegrityError("forced rollback")
            except IntegrityError:
                pass

            mock_invalidate.assert_not_called()

    def test_commit_invalidates_cache_after_save(self):
        """A successful commit must trigger exactly one cache invalidation."""
        with patch(SIGNAL_TARGET) as mock_invalidate:
            with transaction.atomic():
                self.existing_txn.description = "edited inside good txn"
                self.existing_txn.save()
                # Inside the atomic block, the callback has been scheduled but
                # not yet executed.
                mock_invalidate.assert_not_called()

            # After the block exits cleanly the on_commit hook fires.
            self.assertEqual(mock_invalidate.call_count, 1)
            args, _kwargs = mock_invalidate.call_args
            self.assertEqual(args[0], self.org.id)

    def test_autocommit_save_invalidates_cache_immediately(self):
        """Outside an explicit transaction, on_commit runs synchronously."""
        with patch(SIGNAL_TARGET) as mock_invalidate:
            self.existing_txn.description = "edited in autocommit"
            self.existing_txn.save()

            self.assertEqual(mock_invalidate.call_count, 1)


class TransactionDeleteOnCommitTests(TransactionTestCase):
    """post_delete on Transaction must also defer invalidation to on_commit."""

    def setUp(self):
        self.org = Organization.objects.create(name="Org Delete", slug="org-delete-oc")
        self.supplier = SupplierFactory(organization=self.org)
        self.category = CategoryFactory(organization=self.org)

    def test_rollback_of_delete_does_not_invalidate_cache(self):
        txn = TransactionFactory(
            organization=self.org,
            supplier=self.supplier,
            category=self.category,
        )
        # ``Model.delete()`` clears ``pk`` on the in-memory instance, so cache
        # the value before issuing the doomed delete.
        txn_pk = txn.pk

        with patch(SIGNAL_TARGET) as mock_invalidate:
            try:
                with transaction.atomic():
                    txn.delete()
                    raise IntegrityError("forced rollback")
            except IntegrityError:
                pass

            mock_invalidate.assert_not_called()

        # Row should still exist because the transaction rolled back.
        self.assertTrue(TransactionModel.objects.filter(pk=txn_pk).exists())

    def test_commit_of_delete_invalidates_cache(self):
        txn = TransactionFactory(
            organization=self.org,
            supplier=self.supplier,
            category=self.category,
        )

        with patch(SIGNAL_TARGET) as mock_invalidate:
            with transaction.atomic():
                txn.delete()
                mock_invalidate.assert_not_called()

            self.assertEqual(mock_invalidate.call_count, 1)


class DataUploadOnCommitTests(TestCase):
    """``DataUpload`` post_save uses on_commit; verify via captured callbacks.

    Uses ``captureOnCommitCallbacks`` (Django 4.0+) which collects callbacks
    that would have fired on commit. This works inside ``TestCase`` where the
    outer atomic wrapper would otherwise discard them.
    """

    def setUp(self):
        from apps.procurement.models import DataUpload

        self.DataUpload = DataUpload
        self.org = Organization.objects.create(name="Org DU", slug="org-du-oc")

    def test_completed_upload_schedules_on_commit_callback(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            self.DataUpload.objects.create(
                organization=self.org,
                file_name="x.csv",
                original_file_name="x.csv",
                file_size=1,
                batch_id="batch-oc-1",
                total_rows=0,
                successful_rows=0,
                failed_rows=0,
                duplicate_rows=0,
                status="completed",
            )

        # Exactly one callback (the cache invalidation) should be queued.
        self.assertEqual(len(callbacks), 1)

    def test_non_completed_upload_does_not_schedule_callback(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            self.DataUpload.objects.create(
                organization=self.org,
                file_name="y.csv",
                original_file_name="y.csv",
                file_size=1,
                batch_id="batch-oc-2",
                total_rows=0,
                successful_rows=0,
                failed_rows=0,
                duplicate_rows=0,
                status="processing",
            )

        self.assertEqual(len(callbacks), 0)

    def test_executed_callback_invokes_invalidate(self):
        with patch(SIGNAL_TARGET) as mock_invalidate:
            with self.captureOnCommitCallbacks(execute=True):
                self.DataUpload.objects.create(
                    organization=self.org,
                    file_name="z.csv",
                    original_file_name="z.csv",
                    file_size=1,
                    batch_id="batch-oc-3",
                    total_rows=0,
                    successful_rows=0,
                    failed_rows=0,
                    duplicate_rows=0,
                    status="completed",
                )

            self.assertEqual(mock_invalidate.call_count, 1)
            args, _kwargs = mock_invalidate.call_args
            self.assertEqual(args[0], self.org.id)
