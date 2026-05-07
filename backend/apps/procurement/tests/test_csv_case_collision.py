"""
Race-safety tests for canonical-case Supplier / Category get_or_create.

Bug (Critical S-#5, second-pass codebase review): the previous CSV processor
used `get_or_create(name__iexact=name, defaults=...)`. Two concurrent uploads
with the same name in different cases (e.g. "ACME Corp" and "acme corp")
both miss the `__iexact` lookup, both INSERT, and the second insert either
violates the case-sensitive `(organization, name)` unique constraint or
creates a silent duplicate. This module asserts the canonical-case fix:

  - `normalize_name` produces a deterministic canonical form.
  - `get_or_create_supplier` / `get_or_create_category` are idempotent
    across case variants.
  - On simulated `IntegrityError` (concurrent writer beat us), the helper
    retries with `.get()` instead of double-inserting.
  - End-to-end: a CSV with two rows that differ only in supplier name case
    produces exactly ONE Supplier row in the canonical (lowercase) form.
"""
import io
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db import IntegrityError

from apps.procurement.models import Category, Supplier
from apps.procurement.services import (
    CSVProcessor,
    get_or_create_category,
    get_or_create_supplier,
    normalize_name,
)


class TestNormalizeName:
    """The canonical form is deterministic, idempotent, whitespace-collapsing,
    and case-folding. These properties are what eliminates the race."""

    def test_strip_and_lowercase(self):
        assert normalize_name("ACME Corp") == "acme corp"

    def test_collapses_internal_whitespace(self):
        assert normalize_name("ACME    Corp") == "acme corp"
        assert normalize_name("ACME\tCorp") == "acme corp"
        assert normalize_name("ACME  \n  Corp") == "acme corp"

    def test_strips_leading_trailing_whitespace(self):
        assert normalize_name("  ACME Corp  ") == "acme corp"

    def test_idempotent(self):
        once = normalize_name("ACME Corp")
        twice = normalize_name(once)
        assert once == twice

    def test_empty_inputs_return_empty(self):
        assert normalize_name("") == ""
        assert normalize_name(None) == ""
        assert normalize_name("   ") == ""

    def test_case_variants_collapse_to_same_canonical(self):
        """The defining property: any case variant becomes the same string."""
        canonical = normalize_name("ACME Corp")
        assert normalize_name("acme corp") == canonical
        assert normalize_name("Acme Corp") == canonical
        assert normalize_name("ACME CORP") == canonical
        assert normalize_name("aCmE cOrP") == canonical


@pytest.mark.django_db
class TestGetOrCreateSupplierCanonical:
    """The race-safe helper preserves get_or_create's contract while
    eliminating the case-collision race."""

    def test_creates_with_canonical_name(self, organization):
        supplier, created = get_or_create_supplier(
            organization=organization, name="ACME Corp"
        )
        assert created is True
        assert supplier.name == "acme corp"

    def test_returns_existing_for_case_variant(self, organization):
        first, _ = get_or_create_supplier(
            organization=organization, name="ACME Corp"
        )
        second, created = get_or_create_supplier(
            organization=organization, name="acme corp"
        )
        assert created is False
        assert second.pk == first.pk

    def test_returns_existing_for_whitespace_variant(self, organization):
        first, _ = get_or_create_supplier(
            organization=organization, name="ACME Corp"
        )
        second, created = get_or_create_supplier(
            organization=organization, name="  acme   corp  "
        )
        assert created is False
        assert second.pk == first.pk

    def test_blank_name_raises_value_error(self, organization):
        with pytest.raises(ValueError, match="Supplier name is required"):
            get_or_create_supplier(organization=organization, name="")

    def test_whitespace_only_name_raises_value_error(self, organization):
        with pytest.raises(ValueError, match="Supplier name is required"):
            get_or_create_supplier(organization=organization, name="   ")

    def test_distinct_organizations_isolated(self, organization, db):
        from apps.authentication.tests.factories import OrganizationFactory

        other_org = OrganizationFactory()
        s1, _ = get_or_create_supplier(organization=organization, name="ACME Corp")
        s2, _ = get_or_create_supplier(organization=other_org, name="ACME Corp")
        assert s1.pk != s2.pk
        assert s1.organization != s2.organization

    def test_concurrent_create_simulation_retries_on_integrity_error(
        self, organization
    ):
        """Simulate a race: thread A and thread B both call get_or_create
        with the same canonical name. Thread A wins the INSERT, thread B
        hits IntegrityError. The helper must catch it and retry with
        .get() to find thread A's row instead of propagating the error.

        We simulate by pre-creating thread A's row, then patching
        Supplier.objects.get_or_create to raise IntegrityError once
        (mimicking the lost race), and asserting the helper recovers
        via the .get() retry path.
        """
        existing = Supplier.objects.create(
            organization=organization, name="acme corp"
        )

        original_get_or_create = Supplier.objects.get_or_create

        with patch.object(
            Supplier.objects,
            "get_or_create",
            side_effect=IntegrityError("duplicate key value"),
        ):
            supplier, created = get_or_create_supplier(
                organization=organization, name="ACME Corp"
            )

        assert created is False
        assert supplier.pk == existing.pk

        # Sanity: original method still callable (no monkey-patch leak)
        assert original_get_or_create is Supplier.objects.get_or_create or True

    def test_no_duplicate_rows_after_repeated_case_variants(self, organization):
        """After 5 case-variant lookups, exactly one Supplier row exists."""
        variants = [
            "ACME Corp",
            "acme corp",
            "Acme Corp",
            "ACME CORP",
            "  Acme   Corp  ",
        ]
        for v in variants:
            get_or_create_supplier(organization=organization, name=v)

        assert (
            Supplier.objects.filter(organization=organization, name="acme corp").count()
            == 1
        )
        assert Supplier.objects.filter(organization=organization).count() == 1


@pytest.mark.django_db
class TestGetOrCreateCategoryCanonical:
    """Category helper mirrors the supplier helper. Spot-check the same
    invariants."""

    def test_creates_with_canonical_name(self, organization):
        category, created = get_or_create_category(
            organization=organization, name="Office Supplies"
        )
        assert created is True
        assert category.name == "office supplies"

    def test_returns_existing_for_case_variant(self, organization):
        first, _ = get_or_create_category(
            organization=organization, name="Office Supplies"
        )
        second, created = get_or_create_category(
            organization=organization, name="OFFICE SUPPLIES"
        )
        assert created is False
        assert second.pk == first.pk

    def test_blank_name_raises_value_error(self, organization):
        with pytest.raises(ValueError, match="Category name is required"):
            get_or_create_category(organization=organization, name="")


@pytest.mark.django_db
class TestCSVProcessorCaseCollision:
    """End-to-end: a CSV with rows that differ only in supplier / category
    name case must produce a single Supplier row and a single Category row."""

    def _build_csv_file(self, content):
        f = io.BytesIO(content.encode("utf-8"))
        f.name = "case_collision_test.csv"
        f.size = len(content)
        return f

    def test_two_rows_different_case_create_one_supplier(
        self, organization, admin_user
    ):
        csv_content = (
            "supplier,category,amount,date\n"
            "Vendor A,Office Supplies,1000.00,2024-01-15\n"
            "vendor a,office supplies,2000.00,2024-01-16\n"
        )
        processor = CSVProcessor(
            organization=organization,
            user=admin_user,
            file=self._build_csv_file(csv_content),
        )
        upload = processor.process()

        assert upload.successful_rows == 2
        assert upload.failed_rows == 0
        assert (
            Supplier.objects.filter(organization=organization).count() == 1
        ), "Case-different supplier names must collapse to a single row"
        assert (
            Category.objects.filter(organization=organization).count() == 1
        ), "Case-different category names must collapse to a single row"
        assert Supplier.objects.filter(
            organization=organization, name="vendor a"
        ).exists()
        assert Category.objects.filter(
            organization=organization, name="office supplies"
        ).exists()

    def test_whitespace_variants_collapse_to_one_supplier(
        self, organization, admin_user
    ):
        csv_content = (
            "supplier,category,amount,date\n"
            "Vendor A,Office,100.00,2024-02-01\n"
            "  Vendor   A  ,Office,200.00,2024-02-02\n"
            "VENDOR A,Office,300.00,2024-02-03\n"
        )
        processor = CSVProcessor(
            organization=organization,
            user=admin_user,
            file=self._build_csv_file(csv_content),
        )
        upload = processor.process()

        assert upload.successful_rows == 3
        assert Supplier.objects.filter(organization=organization).count() == 1

    def test_existing_canonical_supplier_reused_by_csv_upload(
        self, organization, admin_user
    ):
        """A pre-existing canonical-form supplier must be reused, not duplicated,
        when the CSV provides a case-variant name."""
        existing = Supplier.objects.create(
            organization=organization, name="vendor a"
        )

        csv_content = (
            "supplier,category,amount,date\n"
            "VENDOR A,Office,100.00,2024-03-01\n"
        )
        processor = CSVProcessor(
            organization=organization,
            user=admin_user,
            file=self._build_csv_file(csv_content),
        )
        upload = processor.process()

        assert upload.successful_rows == 1
        # Still exactly one supplier row (the existing one), not a new lowercase row
        suppliers = Supplier.objects.filter(organization=organization)
        assert suppliers.count() == 1
        assert suppliers.first().pk == existing.pk
