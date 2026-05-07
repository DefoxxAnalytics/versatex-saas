"""
Business logic for procurement data processing with security enhancements:
- CSV formula injection prevention
- File type validation
- Sanitized error messages
- Cryptographically secure batch IDs
- Multi-organization support for super admins
"""

import logging
import secrets
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
from django.db import IntegrityError, models, transaction
from django.db.models import Q
from django.utils import timezone

from apps.authentication.models import Organization

from .models import Category, DataUpload, Supplier, Transaction

logger = logging.getLogger(__name__)

# Characters that can trigger formula execution in spreadsheets
FORMULA_CHARS = ("=", "+", "-", "@", "\t", "\r", "\n")

# Maximum rows to process in a single upload
MAX_ROWS_PER_UPLOAD = 50000


def normalize_name(name: str) -> str:
    """
    Canonicalize a Supplier / Category name for storage and lookup.

    Returns lowercase, whitespace-normalized form. Used to eliminate the
    case-collision race in concurrent CSV uploads where two writers with the
    same name in different cases (e.g. "ACME Corp" and "acme corp") both
    miss a case-insensitive lookup, both INSERT, and produce duplicate rows
    that the (organization, name) unique constraint cannot prevent because
    the constraint is case-sensitive at the DB level.

    The unique_together (organization, name) on Supplier and Category enforces
    canonical equality after this function is applied on every read AND write,
    serializing concurrent writers via IntegrityError.

    Args:
        name: Raw name from CSV / form input.

    Returns:
        Canonical form: stripped, internal whitespace collapsed, lowercased.
        Empty string if input is empty / None / whitespace-only.
    """
    if not name:
        return ""
    return " ".join(str(name).split()).lower()


def get_or_create_supplier(organization, name, defaults=None):
    """
    Race-safe Supplier lookup-or-create using canonical name normalization.

    Pattern:
    1. Normalize the name once via `normalize_name`.
    2. Inside `transaction.atomic()`, attempt `get_or_create` with the
       canonical name. The atomic block ensures the SELECT and the INSERT
       run in the same transaction so the unique constraint actually
       protects us.
    3. On `IntegrityError` (concurrent writer beat us to the INSERT),
       retry once with `.get(name=canonical)` — the canonical form means
       the second writer's exact-match lookup finds the first writer's
       row instead of duplicating.

    Returns:
        Tuple (supplier, created) matching `get_or_create`'s contract.

    Raises:
        ValueError: If `name` is empty after normalization.
    """
    canonical = normalize_name(name)
    if not canonical:
        raise ValueError("Supplier name is required")

    create_defaults = dict(defaults or {})
    try:
        with transaction.atomic():
            return Supplier.objects.get_or_create(
                organization=organization,
                name=canonical,
                defaults=create_defaults,
            )
    except IntegrityError:
        return Supplier.objects.get(organization=organization, name=canonical), False


def get_or_create_category(organization, name, defaults=None):
    """
    Race-safe Category lookup-or-create. See `get_or_create_supplier` for
    the full rationale — this is the same pattern applied to Category.
    """
    canonical = normalize_name(name)
    if not canonical:
        raise ValueError("Category name is required")

    create_defaults = dict(defaults or {})
    try:
        with transaction.atomic():
            return Category.objects.get_or_create(
                organization=organization,
                name=canonical,
                defaults=create_defaults,
            )
    except IntegrityError:
        return Category.objects.get(organization=organization, name=canonical), False


def sanitize_csv_value(value: str) -> str:
    """
    Sanitize a CSV value to prevent formula injection.
    Prefixes dangerous characters with a single quote.
    """
    if not value or not isinstance(value, str):
        return value

    value = value.strip()

    # Check if the value starts with a formula character
    if value and value[0] in FORMULA_CHARS:
        # Prefix with single quote to prevent formula execution
        return "'" + value

    return value


def validate_csv_file(file) -> tuple[bool, str]:
    """
    Validate that a file is actually a CSV file.
    Returns (is_valid, error_message).
    """
    # Check file extension
    if not file.name.lower().endswith(".csv"):
        return False, "File must have .csv extension"

    # Check file size (50MB max)
    if file.size > 50 * 1024 * 1024:
        return False, "File size must be less than 50MB"

    # Try to read first few bytes to check if it's text
    try:
        file.seek(0)
        first_bytes = file.read(1024)
        file.seek(0)

        # Check for binary content (null bytes, etc.)
        if b"\x00" in first_bytes:
            return False, "File appears to be binary, not CSV"

        # Try to decode as UTF-8
        try:
            first_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Try common encodings
            try:
                first_bytes.decode("latin-1")
            except UnicodeDecodeError:
                return False, "File encoding not recognized"

    except Exception as e:
        logger.warning(f"CSV validation error: {e}")
        return False, "Could not validate file format"

    return True, ""


class CSVProcessor:
    """
    Process CSV files and import procurement data
    With security enhancements for formula injection prevention
    """

    REQUIRED_COLUMNS = ["supplier", "category", "amount", "date"]
    OPTIONAL_COLUMNS = [
        "description",
        "subcategory",
        "location",
        "fiscal_year",
        "spend_band",
        "payment_method",
        "invoice_number",
        "organization",
    ]

    def __init__(
        self, organization, user, file, skip_duplicates=True, allow_multi_org=False
    ):
        """
        Initialize CSV processor.

        Args:
            organization: Default organization to use for records without organization column
            user: User performing the upload
            file: CSV file object
            skip_duplicates: Whether to skip duplicate records
            allow_multi_org: If True, allows organization column to specify different orgs
                             (only for super admins)
        """
        self.default_organization = organization
        self.user = user
        self.file = file
        self.skip_duplicates = skip_duplicates
        self.allow_multi_org = allow_multi_org
        # Use cryptographically secure token instead of UUID
        # This prevents batch ID guessing/enumeration attacks
        self.batch_id = secrets.token_urlsafe(32)
        self.errors = []
        self.stats = {"total": 0, "successful": 0, "failed": 0, "duplicates": 0}
        # Track which organizations were affected (for audit logging)
        self.orgs_affected = set()
        # Cache for organization lookups (name/slug -> Organization)
        self._org_cache = {}

    def process(self):
        """
        Main processing method
        Returns: DataUpload instance
        """
        # Validate file first
        is_valid, error_msg = validate_csv_file(self.file)
        if not is_valid:
            raise ValueError(f"Invalid file: {error_msg}")

        # Create upload record (uses default org for the record itself)
        upload = DataUpload.objects.create(
            organization=self.default_organization,
            uploaded_by=self.user,
            file_name=self.file.name,
            file_size=self.file.size,
            batch_id=self.batch_id,
            status="processing",
        )

        try:
            # Read CSV
            df = pd.read_csv(self.file)
            # Strip whitespace from column names to handle columns like " amount "
            df.columns = df.columns.str.strip()
            self.stats["total"] = len(df)

            # Check row limit
            if len(df) > MAX_ROWS_PER_UPLOAD:
                raise ValueError(
                    f"File contains {len(df)} rows, maximum allowed is {MAX_ROWS_PER_UPLOAD}"
                )

            # Validate columns
            self._validate_columns(df)

            # Process rows
            self._process_rows(df)

            # Update upload record
            upload.total_rows = self.stats["total"]
            upload.successful_rows = self.stats["successful"]
            upload.failed_rows = self.stats["failed"]
            upload.duplicate_rows = self.stats["duplicates"]
            upload.error_log = self._sanitize_error_log()
            upload.completed_at = timezone.now()

            if self.stats["failed"] == 0:
                upload.status = "completed"
            elif self.stats["successful"] > 0:
                upload.status = "partial"
            else:
                upload.status = "failed"

            upload.save()

        except Exception as e:
            logger.error(f"CSV processing error: {e}")
            upload.status = "failed"
            upload.error_log = [{"error": self._sanitize_error_message(str(e))}]
            upload.completed_at = timezone.now()
            upload.save()
            raise ValueError(self._sanitize_error_message(str(e)))

        return upload

    def _sanitize_error_log(self) -> list:
        """Sanitize error log to remove sensitive data"""
        sanitized = []
        for error in self.errors[:100]:  # Limit to 100 errors
            sanitized.append(
                {
                    "row": error.get("row", 0),
                    "error": self._sanitize_error_message(
                        error.get("error", "Unknown error")
                    ),
                    # Don't include raw data in error log
                }
            )
        return sanitized

    def _sanitize_error_message(self, message: str) -> str:
        """Remove potentially sensitive information from error messages"""
        sensitive_patterns = [
            "DETAIL:",
            "SQL",
            "psycopg2",
            "postgresql",
            "/app/",
            "/home/",
            "Traceback",
            'File "',
        ]

        message_lower = message.lower()
        for pattern in sensitive_patterns:
            if pattern.lower() in message_lower:
                return "An error occurred while processing this row."

        # Truncate long messages
        if len(message) > 200:
            return message[:200] + "..."

        return message

    def _validate_columns(self, df):
        """Validate required columns exist"""
        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

    def _resolve_organization(
        self, org_identifier: str, row_index: int
    ) -> Organization:
        """
        Resolve organization by name or slug.

        Args:
            org_identifier: Organization name or slug from CSV
            row_index: Current row index (for error messages)

        Returns:
            Organization instance

        Raises:
            ValueError: If organization not found (fail fast)
        """
        if not org_identifier:
            return self.default_organization

        org_identifier = org_identifier.strip()

        # Check cache first
        if org_identifier in self._org_cache:
            return self._org_cache[org_identifier]

        # Try to find by name (case-insensitive) or slug
        org = (
            Organization.objects.filter(is_active=True)
            .filter(Q(name__iexact=org_identifier) | Q(slug__iexact=org_identifier))
            .first()
        )

        if not org:
            # Get list of valid organizations for helpful error message
            valid_orgs = list(
                Organization.objects.filter(is_active=True).values_list(
                    "name", flat=True
                )[:10]
            )
            valid_list = ", ".join(valid_orgs)
            if len(valid_orgs) == 10:
                valid_list += ", ..."

            raise ValueError(
                f"Row {row_index + 2}: Organization '{org_identifier}' not found. "
                f"Valid organizations: {valid_list}"
            )

        # Cache the result
        self._org_cache[org_identifier] = org
        return org

    def _process_rows(self, df):
        """Process each row in the dataframe"""
        for index, row in df.iterrows():
            try:
                self._process_row(row, index)
                self.stats["successful"] += 1
            except Exception as e:
                self.stats["failed"] += 1
                self.errors.append(
                    {
                        "row": index + 2,  # +2 for header and 0-indexing
                        "error": str(e),
                        # Don't store raw data for security
                    }
                )

    def _process_row(self, row, index):
        """Process a single row with formula injection prevention.

        v3.1 Phase 1 (P-C1): @transaction.atomic decorator removed. The
        decorator wrapped each row in a savepoint, but combined with the
        IntegrityError catch below it could abort the outer connection's
        transaction state on duplicate-FK violations and cascade to a
        TransactionAborted on subsequent ORM calls — collapsing a partial-
        success upload to a full failure with miscounted stats. The race-
        safe `get_or_create_supplier`/`get_or_create_category` helpers
        already manage their own savepoints internally, so per-row atomic
        wrapping was redundant.
        """
        # Resolve organization for this row
        if (
            self.allow_multi_org
            and "organization" in row
            and pd.notna(row["organization"])
        ):
            organization = self._resolve_organization(str(row["organization"]), index)
        else:
            organization = self.default_organization

        # Track affected organizations for audit logging
        self.orgs_affected.add(organization.name)

        # Get or create supplier (sanitize name, canonical-case race-safe)
        supplier_name = sanitize_csv_value(str(row["supplier"]).strip())
        if not supplier_name or supplier_name == "'":
            raise ValueError("Supplier name is required")

        supplier, _ = get_or_create_supplier(
            organization=organization, name=supplier_name, defaults={"is_active": True}
        )

        # Get or create category (sanitize name, canonical-case race-safe)
        category_name = sanitize_csv_value(str(row["category"]).strip())
        if not category_name or category_name == "'":
            raise ValueError("Category name is required")

        category, _ = get_or_create_category(
            organization=organization, name=category_name, defaults={"is_active": True}
        )

        # Parse date
        try:
            date = pd.to_datetime(row["date"]).date()
        except Exception:
            raise ValueError(f"Invalid date format: {row['date']}")

        # Parse and validate amount
        try:
            amount_str = str(row["amount"]).replace(",", "").replace("$", "").strip()
            amount = Decimal(amount_str)
            if amount < 0:
                raise ValueError("Amount cannot be negative")
            if amount > Decimal("999999999999.99"):
                raise ValueError("Amount exceeds maximum allowed value")
        except (InvalidOperation, ValueError) as e:
            raise ValueError(f"Invalid amount value: {row['amount']}")

        # Build optional fields with sanitization (exclude 'organization' - handled separately)
        optional_data = {}
        excluded_optional = {"invoice_number", "organization"}
        for col in self.OPTIONAL_COLUMNS:
            if col in excluded_optional:
                continue
            if col in row and pd.notna(row[col]):
                # Sanitize all string values to prevent formula injection
                value = str(row[col]).strip()
                optional_data[col] = sanitize_csv_value(value)

        # Get invoice number for uniqueness check
        invoice_number = ""
        if "invoice_number" in row and pd.notna(row["invoice_number"]):
            invoice_number = sanitize_csv_value(str(row["invoice_number"]).strip())

        # Application-level duplicate detection on (org, supplier, date, invoice_number).
        # The DB-level unique constraint was removed in migration 0008 to support the
        # skip-duplicates upload flow; detection now lives here. The IntegrityError
        # catch below is kept as a belt-and-suspenders guard for any constraint that
        # may be re-added in future migrations.
        if self.skip_duplicates and invoice_number:
            if Transaction.objects.filter(
                organization=organization,
                supplier=supplier,
                date=date,
                invoice_number=invoice_number,
            ).exists():
                self.stats["duplicates"] += 1
                self.stats[
                    "successful"
                ] -= 1  # Will be incremented in caller, so offset
                return

        try:
            Transaction.objects.create(
                organization=organization,
                uploaded_by=self.user,
                supplier=supplier,
                category=category,
                amount=amount,
                date=date,
                upload_batch=self.batch_id,
                invoice_number=invoice_number,
                **optional_data,
            )
        except IntegrityError:
            if self.skip_duplicates:
                self.stats["duplicates"] += 1
                self.stats["successful"] -= 1
                return
            raise ValueError("Duplicate transaction detected")


def get_duplicate_transactions(organization, days=30):
    """
    Find potential duplicate transactions
    """
    from datetime import timedelta

    from django.db.models import Count

    cutoff_date = timezone.now().date() - timedelta(days=days)

    duplicates = (
        Transaction.objects.filter(organization=organization, date__gte=cutoff_date)
        .values("supplier", "category", "amount", "date")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
    )

    return duplicates


def bulk_delete_transactions(organization, transaction_ids):
    """
    Bulk delete transactions for an organization
    """
    return Transaction.objects.filter(
        organization=organization, id__in=transaction_ids
    ).delete()


def export_transactions_to_csv(organization, filters=None):
    """
    Export transactions to CSV format with formula injection prevention
    """
    queryset = Transaction.objects.filter(organization=organization)

    if filters:
        if "start_date" in filters and filters["start_date"]:
            queryset = queryset.filter(date__gte=filters["start_date"])
        if "end_date" in filters and filters["end_date"]:
            queryset = queryset.filter(date__lte=filters["end_date"])
        if "supplier" in filters and filters["supplier"]:
            queryset = queryset.filter(supplier_id=filters["supplier"])
        if "category" in filters and filters["category"]:
            queryset = queryset.filter(category_id=filters["category"])

    # Convert to dataframe
    data = queryset.values(
        "supplier__name",
        "category__name",
        "amount",
        "date",
        "description",
        "subcategory",
        "location",
        "fiscal_year",
        "spend_band",
        "payment_method",
        "invoice_number",
    )

    df = pd.DataFrame(data)

    # Rename columns
    df.columns = [
        "Supplier",
        "Category",
        "Amount",
        "Date",
        "Description",
        "Subcategory",
        "Location",
        "Fiscal Year",
        "Spend Band",
        "Payment Method",
        "Invoice Number",
    ]

    # Sanitize all string columns to prevent formula injection in exported CSV
    string_columns = [
        "Supplier",
        "Category",
        "Description",
        "Subcategory",
        "Location",
        "Spend Band",
        "Payment Method",
        "Invoice Number",
    ]
    for col in string_columns:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: sanitize_csv_value(str(x)) if pd.notna(x) else ""
            )

    return df
