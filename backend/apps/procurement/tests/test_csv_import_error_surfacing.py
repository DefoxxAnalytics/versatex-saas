"""Finding #12: P2P CSV importers must surface per-row error details.

Each of the four P2P CSV importers (PR/PO/GR/Invoice) historically caught
``Exception`` and silently incremented ``stats['failed']``, discarding the
exception cause. Admin reported "Imported X, Y failed" with zero diagnostic
detail. These tests assert that:

  - Every failing row contributes a structured entry to ``stats['errors']``
    with ``row``, ``error_class``, and ``message`` keys.
  - Row numbers reflect the CSV row (1-indexed, with row 1 = header), so
    the first data row that fails is row 2.
  - The exception message is preserved on the entry.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.authentication.models import Organization, UserProfile
from apps.procurement.admin import (
    GoodsReceiptAdmin,
    InvoiceAdmin,
    PurchaseOrderAdmin,
    PurchaseRequisitionAdmin,
)
from apps.procurement.models import (
    GoodsReceipt,
    Invoice,
    PurchaseOrder,
    PurchaseRequisition,
    Supplier,
)

User = get_user_model()


class _BaseImporterErrorSurfacingTest(TestCase):
    """Shared setup for the four importer-specific test cases."""

    def setUp(self):
        self.org = Organization.objects.create(name="Org C12", slug="org-c12")
        self.admin_user = User.objects.create_user(
            username="adm_c12", password="pw", is_staff=True
        )
        UserProfile.objects.create(
            user=self.admin_user, organization=self.org, role="admin"
        )

    def _assert_error_entry_shape(self, err, expected_row):
        """Each error entry must record row, exception class, and message."""
        self.assertIn("row", err, f"missing 'row' key: {err}")
        self.assertEqual(
            err["row"],
            expected_row,
            f"Expected row={expected_row}, got {err}",
        )
        self.assertIn("error_class", err, f"missing 'error_class' key: {err}")
        self.assertIn("message", err, f"missing 'message' key: {err}")
        self.assertTrue(err["message"], f"empty message in error entry: {err}")


class TestPurchaseRequisitionImporterErrorSurfacing(_BaseImporterErrorSurfacingTest):
    def test_pr_importer_captures_row_failure(self):
        """When a PR row raises during create(), errors list must capture it."""
        admin_instance = PurchaseRequisitionAdmin(
            PurchaseRequisition, django_admin.site
        )

        # Valid-looking row that will pass all explicit guards (pr_number,
        # estimated_amount) and reach the model create() call. We force the
        # create() to raise so the bare except branch is exercised.
        rows = [
            {
                "pr_number": "PR-FAIL-001",
                "department": "Eng",
                "cost_center": "CC-1",
                "description": "test",
                "estimated_amount": "100.00",
                "currency": "USD",
                "budget_code": "B1",
                "status": "draft",
                "priority": "medium",
                "created_date": "2026-01-01",
                "submitted_date": "",
                "approval_date": "",
                "supplier_suggested": "",
                "category": "",
            }
        ]

        with patch.object(
            PurchaseRequisition.objects,
            "create",
            side_effect=ValueError("boom-pr"),
        ):
            stats = admin_instance._process_p2p_import(
                rows, self.org, "batch-pr", self.admin_user
            )

        self.assertGreaterEqual(stats["failed"], 1)
        self.assertIn("errors", stats)
        self.assertGreaterEqual(len(stats["errors"]), 1)
        self._assert_error_entry_shape(stats["errors"][0], expected_row=2)
        self.assertEqual(stats["errors"][0]["error_class"], "ValueError")
        self.assertIn("boom-pr", stats["errors"][0]["message"])


class TestPurchaseOrderImporterErrorSurfacing(_BaseImporterErrorSurfacingTest):
    def test_po_importer_captures_row_failure(self):
        admin_instance = PurchaseOrderAdmin(PurchaseOrder, django_admin.site)

        rows = [
            {
                "po_number": "PO-FAIL-001",
                "supplier_name": "Acme",
                "total_amount": "5000.00",
                "currency": "USD",
                "tax_amount": "0",
                "freight_amount": "0",
                "status": "draft",
                "category": "Office",
                "created_date": "2026-01-01",
                "approval_date": "",
                "sent_date": "",
                "required_date": "",
                "promised_date": "",
                "pr_number": "",
                "is_contract_backed": "false",
            }
        ]

        with patch.object(
            PurchaseOrder.objects,
            "create",
            side_effect=ValueError("boom-po"),
        ):
            stats = admin_instance._process_p2p_import(
                rows, self.org, "batch-po", self.admin_user
            )

        self.assertGreaterEqual(stats["failed"], 1)
        self.assertGreaterEqual(len(stats["errors"]), 1)
        self._assert_error_entry_shape(stats["errors"][0], expected_row=2)
        self.assertEqual(stats["errors"][0]["error_class"], "ValueError")
        self.assertIn("boom-po", stats["errors"][0]["message"])


class TestGoodsReceiptImporterErrorSurfacing(_BaseImporterErrorSurfacingTest):
    def test_gr_importer_captures_row_failure(self):
        admin_instance = GoodsReceiptAdmin(GoodsReceipt, django_admin.site)

        # GR import requires an existing PO; create one (with required FKs)
        # so the row reaches the create() call site.
        supplier = Supplier.objects.create(
            organization=self.org, name="Acme GR-Test Supplier"
        )
        po = PurchaseOrder.objects.create(
            organization=self.org,
            po_number="PO-FOR-GR-001",
            supplier=supplier,
            total_amount=Decimal("1000.00"),
            currency="USD",
            tax_amount=Decimal("0"),
            freight_amount=Decimal("0"),
            status="approved",
            created_date=date(2026, 1, 1),
            original_amount=Decimal("1000.00"),
        )

        rows = [
            {
                "gr_number": "GR-FAIL-001",
                "po_number": po.po_number,
                "received_date": "2026-01-15",
                "quantity_ordered": "10",
                "quantity_received": "10",
                "quantity_accepted": "10",
                "amount_received": "1000.00",
                "status": "received",
                "inspection_notes": "",
            }
        ]

        with patch.object(
            GoodsReceipt.objects, "create", side_effect=ValueError("boom-gr")
        ):
            stats = admin_instance._process_p2p_import(
                rows, self.org, "batch-gr", self.admin_user
            )

        self.assertGreaterEqual(stats["failed"], 1)
        self.assertGreaterEqual(len(stats["errors"]), 1)
        self._assert_error_entry_shape(stats["errors"][0], expected_row=2)
        self.assertEqual(stats["errors"][0]["error_class"], "ValueError")
        self.assertIn("boom-gr", stats["errors"][0]["message"])


class TestInvoiceImporterErrorSurfacing(_BaseImporterErrorSurfacingTest):
    def test_invoice_importer_captures_row_failure(self):
        admin_instance = InvoiceAdmin(Invoice, django_admin.site)

        rows = [
            {
                "invoice_number": "INV-FAIL-001",
                "supplier_name": "Acme",
                "invoice_amount": "2500.00",
                "invoice_date": "2026-02-15",
                "due_date": "2026-03-15",
                "currency": "USD",
                "tax_amount": "0",
                "net_amount": "2500.00",
                "payment_terms": "Net 30",
                "payment_terms_days": "30",
                "status": "received",
                "match_status": "unmatched",
                "po_number": "",
                "gr_number": "",
                "received_date": "",
                "approved_date": "",
                "paid_date": "",
                "has_exception": "false",
                "exception_type": "",
                "exception_amount": "",
                "exception_notes": "",
            }
        ]

        with patch.object(
            Invoice.objects, "create", side_effect=ValueError("boom-inv")
        ):
            stats = admin_instance._process_p2p_import(
                rows, self.org, "batch-inv", self.admin_user
            )

        self.assertGreaterEqual(stats["failed"], 1)
        self.assertGreaterEqual(len(stats["errors"]), 1)
        self._assert_error_entry_shape(stats["errors"][0], expected_row=2)
        self.assertEqual(stats["errors"][0]["error_class"], "ValueError")
        self.assertIn("boom-inv", stats["errors"][0]["message"])


class TestImporterErrorTruncation(_BaseImporterErrorSurfacingTest):
    """Pathological exception messages must be truncated to keep logs sane."""

    def test_message_is_truncated(self):
        admin_instance = PurchaseRequisitionAdmin(
            PurchaseRequisition, django_admin.site
        )
        long_msg = "x" * 2000
        rows = [
            {
                "pr_number": "PR-LONG-001",
                "department": "Eng",
                "cost_center": "",
                "description": "",
                "estimated_amount": "100.00",
                "currency": "USD",
                "budget_code": "",
                "status": "draft",
                "priority": "medium",
                "created_date": "2026-01-01",
                "submitted_date": "",
                "approval_date": "",
                "supplier_suggested": "",
                "category": "",
            }
        ]
        with patch.object(
            PurchaseRequisition.objects,
            "create",
            side_effect=RuntimeError(long_msg),
        ):
            stats = admin_instance._process_p2p_import(
                rows, self.org, "batch-long", self.admin_user
            )
        self.assertEqual(len(stats["errors"]), 1)
        self.assertLessEqual(len(stats["errors"][0]["message"]), 500)
