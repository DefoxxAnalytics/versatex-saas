"""Finding C3 - DB-level enforcement of supplier ``organization_id`` match.

The application-level checks in serializers cannot defend against direct ORM
writes (admin shell, raw SQL, bulk imports, ``.update()``). Migration
``0009_cross_org_fk_check_constraints`` installs Postgres triggers that raise
on any ``INSERT``/``UPDATE`` where ``model.organization_id`` differs from the
referenced ``supplier.organization_id``.

These tests exercise the trigger by attempting writes that bypass the
serializer entirely (``.objects.create`` / ``.save``) and asserting the DB
raises ``IntegrityError``.
"""
from datetime import date, timedelta
from decimal import Decimal
import unittest

import pytest
from django.db import IntegrityError, connection, transaction as db_transaction
from django.test import TestCase, TransactionTestCase

from apps.authentication.models import Organization
from apps.procurement.models import (
    Contract,
    Invoice,
    PurchaseOrder,
    Supplier,
    Transaction,
)
from apps.procurement.tests.factories import CategoryFactory


# Triggers are PL/pgSQL; on SQLite (used by settings_test) the migration is a
# no-op, so the enforcement tests would all fail. Skip the whole module unless
# the connected DB is Postgres.
postgres_only = unittest.skipUnless(
    connection.vendor == "postgresql",
    "Cross-org FK trigger enforcement is Postgres-only "
    "(migration 0009 is a no-op on other backends).",
)


@pytest.mark.postgres
@postgres_only
class CrossOrgFKCheckBase(TransactionTestCase):
    """Shared org/supplier setup.

    ``TransactionTestCase`` is required because each ``IntegrityError`` from
    the trigger aborts the surrounding transaction; ``TestCase`` would mark
    subsequent assertions as broken since the outer atomic wrapper is dirty.
    """

    def setUp(self):
        self.org_a = Organization.objects.create(
            name="Org A", slug="org-a-c3"
        )
        self.org_b = Organization.objects.create(
            name="Org B", slug="org-b-c3"
        )
        # Supplier belongs to org_b; we will try to attach it to rows in org_a.
        self.supplier_b = Supplier.objects.create(
            organization=self.org_b,
            name="Cross-Org Supplier",
            code="CROSS-001",
            is_active=True,
        )
        self.supplier_a = Supplier.objects.create(
            organization=self.org_a,
            name="Same-Org Supplier",
            code="SAME-001",
            is_active=True,
        )


@pytest.mark.postgres
@postgres_only
class TransactionCrossOrgFKTests(CrossOrgFKCheckBase):
    def setUp(self):
        super().setUp()
        self.category_a = CategoryFactory(organization=self.org_a)

    def test_create_with_cross_org_supplier_raises(self):
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                Transaction.objects.create(
                    organization=self.org_a,
                    supplier=self.supplier_b,  # belongs to org_b
                    category=self.category_a,
                    amount=Decimal("100.00"),
                    date=date.today(),
                )

    def test_create_with_same_org_supplier_succeeds(self):
        tx = Transaction.objects.create(
            organization=self.org_a,
            supplier=self.supplier_a,
            category=self.category_a,
            amount=Decimal("100.00"),
            date=date.today(),
        )
        self.assertIsNotNone(tx.pk)

    def test_update_to_cross_org_supplier_raises(self):
        tx = Transaction.objects.create(
            organization=self.org_a,
            supplier=self.supplier_a,
            category=self.category_a,
            amount=Decimal("100.00"),
            date=date.today(),
        )
        tx.supplier = self.supplier_b
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                tx.save()


@pytest.mark.postgres
@postgres_only
class ContractCrossOrgFKTests(CrossOrgFKCheckBase):
    def _contract_kwargs(self, organization, supplier):
        return dict(
            organization=organization,
            supplier=supplier,
            contract_number="C-0001",
            title="Test Contract",
            total_value=Decimal("10000.00"),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
        )

    def test_create_with_cross_org_supplier_raises(self):
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                Contract.objects.create(
                    **self._contract_kwargs(self.org_a, self.supplier_b)
                )

    def test_create_with_same_org_supplier_succeeds(self):
        contract = Contract.objects.create(
            **self._contract_kwargs(self.org_a, self.supplier_a)
        )
        self.assertIsNotNone(contract.pk)

    def test_update_to_cross_org_supplier_raises(self):
        contract = Contract.objects.create(
            **self._contract_kwargs(self.org_a, self.supplier_a)
        )
        contract.supplier = self.supplier_b
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                contract.save()


@pytest.mark.postgres
@postgres_only
class PurchaseOrderCrossOrgFKTests(CrossOrgFKCheckBase):
    def _po_kwargs(self, organization, supplier, po_number="PO-0001"):
        return dict(
            organization=organization,
            po_number=po_number,
            supplier=supplier,
            total_amount=Decimal("5000.00"),
            created_date=date.today(),
        )

    def test_create_with_cross_org_supplier_raises(self):
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                PurchaseOrder.objects.create(
                    **self._po_kwargs(self.org_a, self.supplier_b)
                )

    def test_create_with_same_org_supplier_succeeds(self):
        po = PurchaseOrder.objects.create(
            **self._po_kwargs(self.org_a, self.supplier_a)
        )
        self.assertIsNotNone(po.pk)

    def test_update_to_cross_org_supplier_raises(self):
        po = PurchaseOrder.objects.create(
            **self._po_kwargs(self.org_a, self.supplier_a, po_number="PO-0002")
        )
        po.supplier = self.supplier_b
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                po.save()


@pytest.mark.postgres
@postgres_only
class InvoiceCrossOrgFKTests(CrossOrgFKCheckBase):
    def _invoice_kwargs(self, organization, supplier, invoice_number="INV-0001"):
        return dict(
            organization=organization,
            invoice_number=invoice_number,
            supplier=supplier,
            invoice_amount=Decimal("250.00"),
            net_amount=Decimal("250.00"),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )

    def test_create_with_cross_org_supplier_raises(self):
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                Invoice.objects.create(
                    **self._invoice_kwargs(self.org_a, self.supplier_b)
                )

    def test_create_with_same_org_supplier_succeeds(self):
        invoice = Invoice.objects.create(
            **self._invoice_kwargs(self.org_a, self.supplier_a)
        )
        self.assertIsNotNone(invoice.pk)

    def test_update_to_cross_org_supplier_raises(self):
        invoice = Invoice.objects.create(
            **self._invoice_kwargs(
                self.org_a, self.supplier_a, invoice_number="INV-0002"
            )
        )
        invoice.supplier = self.supplier_b
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                invoice.save()


@pytest.mark.postgres
@postgres_only
class TriggerInstallationTests(TestCase):
    """Sanity check that the migration installed all four triggers."""

    EXPECTED_TRIGGERS = {
        ("procurement_transaction", "procurement_transaction_check_supplier_org_trg"),
        ("procurement_contract", "procurement_contract_check_supplier_org_trg"),
        ("procurement_purchaseorder", "procurement_purchaseorder_check_supplier_org_trg"),
        ("procurement_invoice", "procurement_invoice_check_supplier_org_trg"),
    }

    def test_all_four_triggers_present(self):
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT event_object_table, trigger_name
                FROM information_schema.triggers
                WHERE trigger_name LIKE %s
                """,
                ["procurement_%_check_supplier_org_trg"],
            )
            rows = {(r[0], r[1]) for r in cur.fetchall()}

        missing = self.EXPECTED_TRIGGERS - rows
        self.assertFalse(
            missing,
            f"Missing cross-org FK triggers: {missing}. Found: {rows}",
        )
