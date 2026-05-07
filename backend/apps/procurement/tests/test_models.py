"""
Tests for procurement models.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.authentication.tests.factories import OrganizationFactory, UserFactory
from apps.procurement.models import (
    Category,
    DataUpload,
    Supplier,
    Transaction,
    sanitize_filename,
)

from .factories import (
    CategoryFactory,
    DataUploadFactory,
    SupplierFactory,
    TransactionFactory,
)


class TestSanitizeFilename:
    """Tests for filename sanitization function."""

    def test_basic_filename(self):
        """Test sanitization of basic filename."""
        assert sanitize_filename("test.csv") == "test.csv"

    def test_removes_directory_path(self):
        """Test that directory paths are removed."""
        assert sanitize_filename("/path/to/file.csv") == "file.csv"
        assert sanitize_filename("C:\\Users\\test\\file.csv") == "file.csv"

    def test_removes_path_traversal(self):
        """Test that path traversal attempts are removed."""
        # Takes last path component, then removes .. sequences
        assert sanitize_filename("../../../etc/passwd") == "passwd"
        assert sanitize_filename("..\\..\\windows\\system32") == "system32"

    def test_removes_null_bytes(self):
        """Test that null bytes are removed."""
        assert sanitize_filename("file\x00.csv") == "file.csv"

    def test_removes_special_characters(self):
        """Test that special characters are removed."""
        assert sanitize_filename('file<>:"|?*.csv') == "file.csv"

    def test_handles_empty_string(self):
        """Test handling of empty filename."""
        assert sanitize_filename("") == "unnamed_file"
        assert sanitize_filename(None) == "unnamed_file"

    def test_handles_dot_file(self):
        """Test handling of files starting with dot."""
        assert sanitize_filename(".hidden") == "file_.hidden"

    def test_truncates_long_filename(self):
        """Test that long filenames are truncated."""
        long_name = "a" * 250 + ".csv"
        result = sanitize_filename(long_name)
        assert len(result) <= 200
        assert result.endswith(".csv")

    def test_preserves_valid_characters(self):
        """Test that valid characters are preserved."""
        assert sanitize_filename("my-file_2024.csv") == "my-file_2024.csv"
        assert sanitize_filename("Report 2024 Q1.xlsx") == "Report 2024 Q1.xlsx"


@pytest.mark.django_db
class TestSupplier:
    """Tests for Supplier model."""

    def test_create_supplier(self, organization):
        """Test creating a supplier."""
        supplier = Supplier.objects.create(
            organization=organization, name="Test Supplier", code="SUP001"
        )
        assert supplier.id is not None
        assert supplier.uuid is not None
        assert supplier.name == "Test Supplier"
        assert supplier.is_active is True

    def test_supplier_str(self, organization):
        """Test supplier string representation."""
        supplier = Supplier.objects.create(organization=organization, name="Acme Corp")
        assert "Acme Corp" in str(supplier)
        assert organization.name in str(supplier)

    def test_supplier_unique_per_org(self, organization):
        """Test that supplier name must be unique within organization."""
        Supplier.objects.create(organization=organization, name="Unique Supplier")
        with pytest.raises(IntegrityError):
            Supplier.objects.create(organization=organization, name="Unique Supplier")

    def test_same_name_different_orgs(self, organization, other_organization):
        """Test that same supplier name is allowed in different orgs."""
        Supplier.objects.create(organization=organization, name="Shared Name")
        supplier2 = Supplier.objects.create(
            organization=other_organization, name="Shared Name"
        )
        assert supplier2.id is not None

    def test_supplier_uuid_unique(self, organization):
        """Test that supplier UUIDs are unique."""
        supplier1 = SupplierFactory(organization=organization)
        supplier2 = SupplierFactory(organization=organization)
        assert supplier1.uuid != supplier2.uuid

    def test_supplier_ordering(self, organization):
        """Test that suppliers are ordered by name."""
        SupplierFactory(organization=organization, name="Zebra Corp")
        SupplierFactory(organization=organization, name="Alpha Inc")
        SupplierFactory(organization=organization, name="Middle LLC")

        suppliers = list(Supplier.objects.filter(organization=organization))
        assert suppliers[0].name == "Alpha Inc"
        assert suppliers[1].name == "Middle LLC"
        assert suppliers[2].name == "Zebra Corp"


@pytest.mark.django_db
class TestCategory:
    """Tests for Category model."""

    def test_create_category(self, organization):
        """Test creating a category."""
        category = Category.objects.create(
            organization=organization,
            name="Test Category",
            description="A test category",
        )
        assert category.id is not None
        assert category.uuid is not None
        assert category.is_active is True

    def test_category_with_parent(self, organization):
        """Test creating a category with parent."""
        parent = CategoryFactory(organization=organization, name="Parent")
        child = Category.objects.create(
            organization=organization, name="Child", parent=parent
        )
        assert child.parent == parent
        assert child in parent.subcategories.all()

    def test_category_str(self, organization):
        """Test category string representation."""
        category = Category.objects.create(
            organization=organization, name="Office Supplies"
        )
        assert "Office Supplies" in str(category)
        assert organization.name in str(category)

    def test_category_unique_per_org(self, organization):
        """Test that category name must be unique within organization."""
        Category.objects.create(organization=organization, name="Unique Category")
        with pytest.raises(IntegrityError):
            Category.objects.create(organization=organization, name="Unique Category")


@pytest.mark.django_db
class TestTransaction:
    """Tests for Transaction model."""

    def test_create_transaction(self, organization, supplier, category, admin_user):
        """Test creating a transaction."""
        transaction = Transaction.objects.create(
            organization=organization,
            supplier=supplier,
            category=category,
            amount=Decimal("1500.00"),
            date=date.today(),
            uploaded_by=admin_user,
            upload_batch="test-batch",
        )
        assert transaction.id is not None
        assert transaction.uuid is not None
        assert transaction.amount == Decimal("1500.00")

    def test_transaction_str(self, transaction):
        """Test transaction string representation."""
        str_repr = str(transaction)
        assert transaction.supplier.name in str_repr
        assert str(transaction.amount) in str_repr

    def test_transaction_ordering(self, organization, supplier, category, admin_user):
        """Test that transactions are ordered by date descending."""
        tx1 = Transaction.objects.create(
            organization=organization,
            supplier=supplier,
            category=category,
            amount=Decimal("100"),
            date=date(2024, 1, 1),
            uploaded_by=admin_user,
            invoice_number="INV-001",
        )
        tx2 = Transaction.objects.create(
            organization=organization,
            supplier=supplier,
            category=category,
            amount=Decimal("200"),
            date=date(2024, 6, 15),
            uploaded_by=admin_user,
            invoice_number="INV-002",
        )
        tx3 = Transaction.objects.create(
            organization=organization,
            supplier=supplier,
            category=category,
            amount=Decimal("300"),
            date=date(2024, 3, 10),
            uploaded_by=admin_user,
            invoice_number="INV-003",
        )

        transactions = list(Transaction.objects.filter(organization=organization))
        assert transactions[0].date >= transactions[1].date
        assert transactions[1].date >= transactions[2].date

    def test_transaction_duplicates_allowed(
        self, organization, supplier, category, admin_user
    ):
        """Duplicate transactions (same org/supplier/date/invoice) are allowed.

        The legacy unique constraint was removed in migration 0008 to support
        the flexible-duplicate-detection CSV upload flow (commit 0b32f14);
        deduplication is now handled in the import service, not the schema.
        """
        Transaction.objects.create(
            organization=organization,
            supplier=supplier,
            category=category,
            amount=Decimal("1000"),
            date=date(2024, 1, 15),
            uploaded_by=admin_user,
            invoice_number="INV-UNIQUE",
        )
        # Should NOT raise: same-key duplicates are legal at the DB layer.
        Transaction.objects.create(
            organization=organization,
            supplier=supplier,
            category=category,
            amount=Decimal("1000"),
            date=date(2024, 1, 15),
            uploaded_by=admin_user,
            invoice_number="INV-UNIQUE",
        )
        assert (
            Transaction.objects.filter(
                organization=organization, invoice_number="INV-UNIQUE"
            ).count()
            == 2
        )

    def test_transaction_supplier_protected(self, transaction, supplier):
        """Test that deleting supplier is protected."""
        from django.db.models import ProtectedError

        with pytest.raises(ProtectedError):
            supplier.delete()

    def test_transaction_category_protected(self, transaction, category):
        """Test that deleting category is protected."""
        from django.db.models import ProtectedError

        with pytest.raises(ProtectedError):
            category.delete()


@pytest.mark.django_db
class TestDataUpload:
    """Tests for DataUpload model."""

    def test_create_data_upload(self, organization, admin_user):
        """Test creating a data upload record."""
        upload = DataUpload.objects.create(
            organization=organization,
            uploaded_by=admin_user,
            file_name="test.csv",
            file_size=1024,
            batch_id="batch-001",
        )
        assert upload.id is not None
        assert upload.uuid is not None
        assert upload.status == "processing"

    def test_data_upload_sanitizes_filename(self, organization, admin_user):
        """Test that filename is sanitized on save."""
        upload = DataUpload.objects.create(
            organization=organization,
            uploaded_by=admin_user,
            file_name="../../../etc/passwd",
            file_size=100,
            batch_id="batch-002",
        )
        assert "../" not in upload.file_name
        assert "etc" not in upload.file_name or "passwd" not in upload.file_name

    def test_data_upload_preserves_original_filename(self, organization, admin_user):
        """Test that original filename is preserved."""
        upload = DataUpload.objects.create(
            organization=organization,
            uploaded_by=admin_user,
            file_name="data/../report.csv",
            file_size=100,
            batch_id="batch-003",
        )
        assert upload.original_file_name == "data/../report.csv"

    def test_data_upload_status_choices(self, organization, admin_user):
        """Test valid status choices."""
        for status_code, _ in DataUpload.STATUS_CHOICES:
            upload = DataUpload.objects.create(
                organization=organization,
                uploaded_by=admin_user,
                file_name="test.csv",
                file_size=100,
                batch_id=f"batch-{status_code}",
                status=status_code,
            )
            assert upload.status == status_code

    def test_data_upload_str(self, organization, admin_user):
        """Test data upload string representation."""
        upload = DataUpload.objects.create(
            organization=organization,
            uploaded_by=admin_user,
            file_name="report.csv",
            file_size=2048,
            batch_id="batch-str-test",
        )
        str_repr = str(upload)
        assert "report.csv" in str_repr
        assert organization.name in str_repr

    def test_batch_id_unique(self, organization, admin_user):
        """Test that batch_id must be unique."""
        DataUpload.objects.create(
            organization=organization,
            uploaded_by=admin_user,
            file_name="file1.csv",
            file_size=100,
            batch_id="unique-batch",
        )

        with pytest.raises(IntegrityError):
            DataUpload.objects.create(
                organization=organization,
                uploaded_by=admin_user,
                file_name="file2.csv",
                file_size=200,
                batch_id="unique-batch",
            )

    def test_data_upload_ordering(self, organization, admin_user):
        """Test that uploads are ordered by created_at descending."""
        upload1 = DataUploadFactory(organization=organization, uploaded_by=admin_user)
        upload2 = DataUploadFactory(organization=organization, uploaded_by=admin_user)
        upload3 = DataUploadFactory(organization=organization, uploaded_by=admin_user)

        uploads = list(DataUpload.objects.filter(organization=organization))
        # Most recent first
        assert uploads[0].created_at >= uploads[1].created_at
        assert uploads[1].created_at >= uploads[2].created_at
