"""
Tests for the admin 'Export seeded dataset as ZIP' action.

Critical test: `test_column_constants_match_importers` pins the exporter column
constants to the procurement importer source-of-truth. If anyone edits
P2PImportMixin.p2p_import_fields or CSVProcessor.REQUIRED_COLUMNS /
OPTIONAL_COLUMNS without following through here, this test fails loudly in CI
before round-trip breaks in production.
"""

import csv
import io
import zipfile
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.contrib.auth.models import User

from apps.authentication.admin import OrganizationAdmin, export_demo_datasets
from apps.authentication.admin_export import (
    CATEGORY_COLUMNS,
    CONTRACT_COLUMNS,
    GR_COLUMNS,
    INVOICE_COLUMNS,
    PO_COLUMNS,
    POLICY_COLUMNS,
    PR_COLUMNS,
    SUPPLIER_COLUMNS,
    TRANSACTION_COLUMNS,
    VIOLATION_COLUMNS,
    build_org_zip,
)
from apps.authentication.models import AuditLog, Organization, UserProfile


def _csv_header(zf, name):
    with zf.open(name) as f:
        reader = csv.reader(io.TextIOWrapper(f, encoding="utf-8"))
        return next(reader)


@pytest.fixture
def demo_org(db):
    return Organization.objects.create(
        name="Demo Co",
        slug="demo-co",
        is_active=True,
        is_demo=True,
    )


@pytest.fixture
def non_demo_org(db):
    return Organization.objects.create(
        name="Real Customer",
        slug="real-customer",
        is_active=True,
        is_demo=False,
    )


@pytest.fixture
def seeded_demo_org(demo_org, admin_user):
    """A demo org with one row of each model so build_org_zip has real data to emit."""
    from apps.procurement.models import (
        Category,
        Contract,
        GoodsReceipt,
        Invoice,
        PolicyViolation,
        PurchaseOrder,
        PurchaseRequisition,
        SpendingPolicy,
        Supplier,
        Transaction,
    )

    sup = Supplier.objects.create(
        organization=demo_org,
        name="Acme Widgets",
        code="ACME",
        contact_email="ops@acme.test",
        is_active=True,
    )
    cat = Category.objects.create(
        organization=demo_org,
        name="Industrial Supplies",
        is_active=True,
    )
    txn = Transaction.objects.create(
        organization=demo_org,
        supplier=sup,
        category=cat,
        amount=Decimal("1234.56"),
        date=date(2025, 6, 1),
        description="Test spend",
        uploaded_by=admin_user,
    )
    pr = PurchaseRequisition.objects.create(
        organization=demo_org,
        pr_number="PR-001",
        department="Maintenance",
        cost_center="CC-1001",
        description="Bolt stock refill",
        estimated_amount=Decimal("5000.00"),
        currency="USD",
        status="approved",
        priority="medium",
        created_date=date(2025, 5, 1),
        submitted_date=date(2025, 5, 2),
        approval_date=date(2025, 5, 3),
        supplier_suggested=sup,
        category=cat,
    )
    po = PurchaseOrder.objects.create(
        organization=demo_org,
        po_number="PO-001",
        supplier=sup,
        category=cat,
        total_amount=Decimal("5000.00"),
        currency="USD",
        tax_amount=Decimal("400.00"),
        freight_amount=Decimal("50.00"),
        status="approved",
        created_date=date(2025, 5, 10),
        approval_date=date(2025, 5, 11),
        sent_date=date(2025, 5, 12),
        required_date=date(2025, 6, 1),
        promised_date=date(2025, 5, 28),
        requisition=pr,
        is_contract_backed=False,
    )
    gr = GoodsReceipt.objects.create(
        organization=demo_org,
        gr_number="GR-001",
        purchase_order=po,
        received_date=date(2025, 5, 28),
        quantity_ordered=Decimal("100"),
        quantity_received=Decimal("98"),
        quantity_accepted=Decimal("98"),
        amount_received=Decimal("4900.00"),
        status="received",
        inspection_notes="Minor scuff on one box",
    )
    Invoice.objects.create(
        organization=demo_org,
        invoice_number="INV-001",
        supplier=sup,
        purchase_order=po,
        goods_receipt=gr,
        invoice_amount=Decimal("4900.00"),
        invoice_date=date(2025, 6, 2),
        due_date=date(2025, 7, 2),
        currency="USD",
        tax_amount=Decimal("400.00"),
        net_amount=Decimal("4500.00"),
        payment_terms="Net 30",
        payment_terms_days=30,
        status="received",
        match_status="3way_matched",
        has_exception=False,
    )
    contract = Contract.objects.create(
        organization=demo_org,
        supplier=sup,
        contract_number="C-001",
        title="Annual Widget Supply",
        total_value=Decimal("120000.00"),
        annual_value=Decimal("120000.00"),
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        renewal_notice_days=90,
        status="active",
        auto_renew=False,
    )
    contract.categories.add(cat)
    policy = SpendingPolicy.objects.create(
        organization=demo_org,
        name="Capital Authorization",
        description="Purchases over $100k need VP approval",
        rules={"threshold_usd": 100000, "approver_role": "vp"},
        is_active=True,
    )
    PolicyViolation.objects.create(
        organization=demo_org,
        transaction=txn,
        policy=policy,
        violation_type="threshold_exceeded",
        severity="medium",
        details={"actual": "1234.56", "limit": "1000.00"},
        is_resolved=False,
    )
    return demo_org


@pytest.mark.django_db
class TestBuildOrgZip:
    def test_zip_contains_all_expected_files(self, seeded_demo_org):
        # #given a seeded demo org
        # #when the zip is built
        payload, counts = build_org_zip(seeded_demo_org)

        # #then the archive contains every CSV and the README
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            expected = {
                f"{seeded_demo_org.slug}/{name}"
                for name in [
                    "suppliers.csv",
                    "categories.csv",
                    "transactions.csv",
                    "purchase_requisitions.csv",
                    "purchase_orders.csv",
                    "goods_receipts.csv",
                    "invoices.csv",
                    "contracts.csv",
                    "spending_policies.csv",
                    "policy_violations.csv",
                    "README.txt",
                ]
            }
            assert expected == set(zf.namelist())

    def test_csv_headers_match_column_constants(self, seeded_demo_org):
        # #given a built zip
        payload, _ = build_org_zip(seeded_demo_org)
        slug = seeded_demo_org.slug

        # #then every CSV's first row equals its declared columns constant
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            assert _csv_header(zf, f"{slug}/suppliers.csv") == SUPPLIER_COLUMNS
            assert _csv_header(zf, f"{slug}/categories.csv") == CATEGORY_COLUMNS
            assert _csv_header(zf, f"{slug}/transactions.csv") == TRANSACTION_COLUMNS
            assert _csv_header(zf, f"{slug}/purchase_requisitions.csv") == PR_COLUMNS
            assert _csv_header(zf, f"{slug}/purchase_orders.csv") == PO_COLUMNS
            assert _csv_header(zf, f"{slug}/goods_receipts.csv") == GR_COLUMNS
            assert _csv_header(zf, f"{slug}/invoices.csv") == INVOICE_COLUMNS
            assert _csv_header(zf, f"{slug}/contracts.csv") == CONTRACT_COLUMNS
            assert _csv_header(zf, f"{slug}/spending_policies.csv") == POLICY_COLUMNS
            assert _csv_header(zf, f"{slug}/policy_violations.csv") == VIOLATION_COLUMNS

    def test_row_counts_reflect_seed(self, seeded_demo_org):
        # #when the zip is built with exactly one row per model
        _, counts = build_org_zip(seeded_demo_org)

        # #then every count is exactly 1
        assert counts == {
            "suppliers": 1,
            "categories": 1,
            "transactions": 1,
            "prs": 1,
            "pos": 1,
            "grs": 1,
            "invoices": 1,
            "contracts": 1,
            "policies": 1,
            "violations": 1,
        }


@pytest.mark.django_db
class TestColumnDriftGuard:
    """
    Pins our exporter column constants to the importer source-of-truth.
    If any of these assertions fail, it means someone changed an importer
    schema without updating admin_export.py — fix the drift before merging.
    """

    def test_p2p_columns_match_p2pimportmixin(self):
        # #given the four P2P admins
        from apps.procurement.admin import (
            GoodsReceiptAdmin,
            InvoiceAdmin,
            PurchaseOrderAdmin,
            PurchaseRequisitionAdmin,
        )

        # #then our constants match their p2p_import_fields exactly
        assert PR_COLUMNS == list(PurchaseRequisitionAdmin.p2p_import_fields)
        assert PO_COLUMNS == list(PurchaseOrderAdmin.p2p_import_fields)
        assert GR_COLUMNS == list(GoodsReceiptAdmin.p2p_import_fields)
        assert INVOICE_COLUMNS == list(InvoiceAdmin.p2p_import_fields)

    def test_transaction_columns_align_with_csvprocessor(self):
        # #given the CSV processor column contract
        from apps.procurement.services import CSVProcessor

        required = set(CSVProcessor.REQUIRED_COLUMNS)
        optional = set(CSVProcessor.OPTIONAL_COLUMNS)
        ours = set(TRANSACTION_COLUMNS)

        # #then every required column is present
        assert required.issubset(ours), f"missing required columns: {required - ours}"
        # #and no column is unrecognized by the importer
        assert ours.issubset(
            required | optional
        ), f"unknown columns: {ours - (required | optional)}"


@pytest.mark.django_db
class TestExportAction:
    def test_rejects_non_demo_org_in_selection(
        self, admin_user, demo_org, non_demo_org
    ):
        # #given a queryset mixing a demo and non-demo org
        admin_user.is_superuser = True
        admin_user.save()
        queryset = Organization.objects.filter(pk__in=[demo_org.pk, non_demo_org.pk])

        request = MagicMock()
        request.user = admin_user
        request._messages = MagicMock()  # silence the messages framework

        # #when the action runs
        response = export_demo_datasets(MagicMock(), request, queryset)

        # #then no response is returned (action aborts with messages.error)
        assert response is None

    def test_rejects_non_superuser(self, admin_user, seeded_demo_org):
        # #given a non-superuser admin
        admin_user.is_superuser = False
        admin_user.save()
        queryset = Organization.objects.filter(pk=seeded_demo_org.pk)

        request = MagicMock()
        request.user = admin_user
        request._messages = MagicMock()

        # #when the action runs
        response = export_demo_datasets(MagicMock(), request, queryset)

        # #then no response is returned
        assert response is None

    def test_successful_export_returns_zip_and_writes_auditlog(
        self, admin_user, seeded_demo_org
    ):
        # #given a superuser and a seeded demo org
        admin_user.is_superuser = True
        admin_user.save()
        queryset = Organization.objects.filter(pk=seeded_demo_org.pk)

        request = MagicMock()
        request.user = admin_user
        request.META = {"REMOTE_ADDR": "127.0.0.1", "HTTP_USER_AGENT": "pytest"}

        # #when the action runs
        response = export_demo_datasets(MagicMock(), request, queryset)

        # #then a ZIP response is returned
        assert response is not None
        assert response["Content-Type"] == "application/zip"
        assert "attachment" in response["Content-Disposition"]

        # #and the outer zip contains the per-slug inner zip
        with zipfile.ZipFile(io.BytesIO(response.content)) as outer:
            assert f"{seeded_demo_org.slug}-dataset.zip" in outer.namelist()

        # #and an audit log row was written
        import json as _json

        log = AuditLog.objects.filter(
            action="export",
            resource="organization_dataset",
            resource_id=seeded_demo_org.slug,
        ).latest("timestamp")
        assert log.user_id == admin_user.pk
        assert log.details["organization_name"] == seeded_demo_org.name
        assert log.details["is_demo"] is True
        counts = _json.loads(log.details["row_counts"])
        assert counts["prs"] == 1


@pytest.mark.django_db
class TestGetActionsVisibility:
    def test_non_superuser_does_not_see_export_action(self, rf, admin_user):
        # #given an admin-role user who is not a Django superuser
        admin_user.is_superuser = False
        admin_user.save()
        request = rf.get("/admin/authentication/organization/")
        request.user = admin_user

        # #when get_actions runs
        model_admin = OrganizationAdmin(Organization, admin_site=MagicMock())
        actions = model_admin.get_actions(request)

        # #then export_demo_datasets is filtered out
        assert "export_demo_datasets" not in actions

    def test_superuser_sees_export_action(self, rf, admin_user):
        # #given a Django superuser
        admin_user.is_superuser = True
        admin_user.save()
        request = rf.get("/admin/authentication/organization/")
        request.user = admin_user

        # #when get_actions runs
        model_admin = OrganizationAdmin(Organization, admin_site=MagicMock())
        actions = model_admin.get_actions(request)

        # #then export_demo_datasets is present
        assert "export_demo_datasets" in actions
