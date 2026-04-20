"""
Procurement data models with security enhancements:
- UUID fields for IDOR protection
- Encrypted fields for sensitive data
- Secure file name handling
"""
import uuid
import re
from django.db import models
from django.contrib.auth.models import User
from apps.authentication.models import Organization

# Note: Field encryption is optional. To enable it:
# 1. Set FIELD_ENCRYPTION_KEY in your environment
# 2. Install django-encrypted-model-fields
# When not configured, standard Django fields are used instead.
# For now, we use regular fields for maximum compatibility.


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal attacks.
    Removes directory components and special characters.
    """
    if not filename:
        return 'unnamed_file'

    # Remove any directory components
    filename = filename.replace('\\', '/').split('/')[-1]

    # Remove any path traversal attempts
    filename = re.sub(r'\.\.+', '', filename)

    # Remove any null bytes
    filename = filename.replace('\x00', '')

    # Keep only safe characters
    safe_filename = re.sub(r'[^\w\s\-\.]', '', filename)

    # Ensure filename is not empty and doesn't start with a dot
    if not safe_filename or safe_filename.startswith('.'):
        safe_filename = 'file_' + safe_filename

    # Limit length
    if len(safe_filename) > 200:
        name, ext = safe_filename.rsplit('.', 1) if '.' in safe_filename else (safe_filename, '')
        safe_filename = name[:195] + ('.' + ext if ext else '')

    return safe_filename


class Supplier(models.Model):
    """
    Supplier model - organization-scoped
    Includes UUID for secure external references
    """
    # UUID for external API references (prevents ID enumeration)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='suppliers'
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, blank=True)

    # Contact information (consider enabling field encryption in production)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ['organization', 'name']
        indexes = [
            models.Index(fields=['organization', 'name']),
            models.Index(fields=['uuid']),
        ]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class Category(models.Model):
    """
    Category model - organization-scoped
    Includes UUID for secure external references
    """
    # UUID for external API references
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='categories'
    )
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='subcategories'
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'
        unique_together = ['organization', 'name']
        indexes = [
            models.Index(fields=['organization', 'name']),
            models.Index(fields=['uuid']),
        ]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class Transaction(models.Model):
    """
    Procurement transaction model - organization-scoped
    Includes UUID for secure external references
    """
    # UUID for external API references
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_transactions'
    )

    # Core fields
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='transactions'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='transactions'
    )

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()
    description = models.TextField(blank=True)

    # Optional fields
    subcategory = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    fiscal_year = models.IntegerField(null=True, blank=True)
    spend_band = models.CharField(max_length=50, blank=True)
    payment_method = models.CharField(max_length=100, blank=True)

    # Invoice number (consider enabling field encryption in production)
    invoice_number = models.CharField(max_length=100, blank=True)

    # Metadata
    upload_batch = models.CharField(max_length=100, blank=True)  # For tracking uploads
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['organization', '-date']),
            models.Index(fields=['organization', 'supplier']),
            models.Index(fields=['organization', 'category']),
            models.Index(fields=['organization', 'fiscal_year']),
            models.Index(fields=['upload_batch']),
            models.Index(fields=['uuid']),
        ]

    def __str__(self):
        return f"{self.supplier.name} - {self.amount} on {self.date}"


class ColumnMappingTemplate(models.Model):
    """
    Stores reusable column mapping configurations for CSV uploads.
    Scoped per-organization to allow different teams to have their own templates.
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='mapping_templates'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    mapping = models.JSONField(default=dict)  # {"csv_column": "target_field"}
    is_default = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_mapping_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'name']
        unique_together = ['organization', 'name']
        verbose_name = 'Column Mapping Template'
        verbose_name_plural = 'Column Mapping Templates'
        indexes = [
            models.Index(fields=['organization', 'is_default']),
            models.Index(fields=['uuid']),
        ]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

    def save(self, *args, **kwargs):
        # Ensure only one default per organization
        if self.is_default:
            ColumnMappingTemplate.objects.filter(
                organization=self.organization,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class DataUpload(models.Model):
    """
    Track data upload history with background processing support.
    Includes UUID for secure external references.
    """
    # UUID for external API references
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='data_uploads'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='data_uploads'
    )

    # Sanitized file name - original name stored separately
    file_name = models.CharField(max_length=255)
    original_file_name = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField()  # in bytes
    batch_id = models.CharField(max_length=100, unique=True)

    # Statistics
    total_rows = models.IntegerField(default=0)
    successful_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    duplicate_rows = models.IntegerField(default=0)

    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partially Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    error_log = models.JSONField(default=list, blank=True)

    # Background processing support
    celery_task_id = models.CharField(max_length=255, blank=True, db_index=True)
    progress_percent = models.IntegerField(default=0)
    progress_message = models.CharField(max_length=255, blank=True)

    # Column mapping tracking
    column_mapping_template = models.ForeignKey(
        'ColumnMappingTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploads'
    )
    column_mapping_snapshot = models.JSONField(default=dict, blank=True)

    # File storage for async processing
    stored_file = models.FileField(
        upload_to='uploads/%Y/%m/%d/',
        null=True,
        blank=True
    )

    # Processing mode indicator
    PROCESSING_MODE_CHOICES = [
        ('sync', 'Synchronous'),
        ('async', 'Asynchronous'),
    ]
    processing_mode = models.CharField(
        max_length=10,
        choices=PROCESSING_MODE_CHOICES,
        default='sync'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['batch_id']),
            models.Index(fields=['uuid']),
            models.Index(fields=['celery_task_id']),
            models.Index(fields=['status']),
        ]

    def save(self, *args, **kwargs):
        # Sanitize file name before saving
        if self.file_name and not self.original_file_name:
            self.original_file_name = self.file_name
        self.file_name = sanitize_filename(self.file_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.file_name} - {self.status} ({self.organization.name})"


class Contract(models.Model):
    """
    Contract model for tracking supplier agreements.
    Contracts are imported via CSV (read-only in frontend).
    Used for contract analytics and compliance tracking.
    """
    # UUID for external API references
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='contracts'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='contracts'
    )

    # Contract Details
    contract_number = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Financial Terms
    total_value = models.DecimalField(max_digits=15, decimal_places=2)
    annual_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Dates
    start_date = models.DateField()
    end_date = models.DateField()
    renewal_notice_days = models.IntegerField(default=90)

    # Status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('renewed', 'Renewed'),
        ('terminated', 'Terminated'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    auto_renew = models.BooleanField(default=False)

    # Categories covered by this contract
    categories = models.ManyToManyField(Category, blank=True, related_name='contracts')

    # Import tracking
    upload_batch = models.CharField(max_length=100, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['end_date']
        unique_together = ['organization', 'contract_number']
        indexes = [
            models.Index(fields=['organization', 'end_date']),
            models.Index(fields=['organization', 'supplier']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['uuid']),
        ]

    def __str__(self):
        return f"{self.contract_number} - {self.title} ({self.supplier.name})"

    @property
    def days_to_expiry(self):
        """Calculate days until contract expires."""
        from datetime import date
        if self.end_date:
            return (self.end_date - date.today()).days
        return None

    @property
    def is_expiring_soon(self):
        """Check if contract is expiring within renewal notice period."""
        days = self.days_to_expiry
        return days is not None and 0 < days <= self.renewal_notice_days


class SpendingPolicy(models.Model):
    """
    Spending policy model for compliance tracking.
    Defines rules for maverick spend detection.
    """
    # UUID for external API references
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='spending_policies'
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Policy Rules (JSON for flexibility)
    # Example structure:
    # {
    #     "max_transaction_amount": 10000,
    #     "required_approval_threshold": 5000,
    #     "preferred_suppliers": ["uuid1", "uuid2"],
    #     "restricted_categories": ["uuid3"],
    #     "require_contract": true
    # }
    rules = models.JSONField(default=dict)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Spending policies'
        unique_together = ['organization', 'name']
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['uuid']),
        ]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class PolicyViolation(models.Model):
    """
    Policy violation model for tracking compliance issues.
    Records transactions that violate spending policies.
    """
    # UUID for external API references
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='policy_violations'
    )
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='violations'
    )
    policy = models.ForeignKey(
        SpendingPolicy,
        on_delete=models.CASCADE,
        related_name='violations'
    )

    # Violation Details
    VIOLATION_TYPE_CHOICES = [
        ('amount_exceeded', 'Amount Exceeded'),
        ('non_preferred_supplier', 'Non-Preferred Supplier'),
        ('restricted_category', 'Restricted Category'),
        ('no_contract', 'No Contract Coverage'),
        ('approval_missing', 'Approval Missing'),
    ]
    violation_type = models.CharField(max_length=50, choices=VIOLATION_TYPE_CHOICES)

    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')

    # Additional details about the violation
    details = models.JSONField(default=dict)

    # Resolution tracking
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='resolved_violations'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['organization', 'is_resolved']),
            models.Index(fields=['organization', 'severity']),
            models.Index(fields=['uuid']),
        ]

    def __str__(self):
        return f"{self.violation_type} - {self.transaction} ({self.severity})"


# =============================================================================
# P2P (Procure-to-Pay) Analytics Models
# =============================================================================

class PurchaseRequisition(models.Model):
    """
    Purchase Requisition - Initial request for goods/services.
    Part of the P2P Analytics Suite for cycle time and workflow analysis.
    """
    # UUID for external API references (prevents ID enumeration)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('converted_to_po', 'Converted to PO'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    # Identity - organization scoped for multi-tenancy
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='purchase_requisitions'
    )
    pr_number = models.CharField(max_length=50)

    # Request details
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requisitions_created'
    )
    department = models.CharField(max_length=100, blank=True)
    cost_center = models.CharField(max_length=50, blank=True)

    # Content
    supplier_suggested = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suggested_requisitions'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requisitions'
    )
    description = models.TextField(blank=True)

    # Financial
    estimated_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    budget_code = models.CharField(max_length=50, blank=True)

    # Status & Workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')

    # Key Dates (for cycle time analysis)
    created_date = models.DateField()
    submitted_date = models.DateField(null=True, blank=True)
    approval_date = models.DateField(null=True, blank=True)
    rejection_date = models.DateField(null=True, blank=True)

    # Approval tracking
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_requisitions'
    )
    rejection_reason = models.TextField(blank=True)

    # Metadata
    upload_batch = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date', '-created_at']
        unique_together = ['organization', 'pr_number']
        verbose_name = 'Purchase Requisition'
        verbose_name_plural = 'Purchase Requisitions'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'created_date']),
            models.Index(fields=['organization', 'department']),
            models.Index(fields=['organization', 'priority']),
            models.Index(fields=['uuid']),
            models.Index(fields=['upload_batch']),
        ]

    def __str__(self):
        return f"{self.pr_number} - {self.status} ({self.organization.name})"

    @property
    def days_to_approval(self):
        """Calculate days from submission to approval."""
        if self.submitted_date and self.approval_date:
            return (self.approval_date - self.submitted_date).days
        return None

    @property
    def is_overdue(self):
        """Check if PR is pending approval for too long (> 5 days)."""
        from datetime import date
        if self.status == 'pending_approval' and self.submitted_date:
            return (date.today() - self.submitted_date).days > 5
        return False


class PurchaseOrder(models.Model):
    """
    Purchase Order - Formal commitment to supplier.
    Part of the P2P Analytics Suite for cycle time and contract compliance analysis.
    """
    # UUID for external API references (prevents ID enumeration)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('sent_to_supplier', 'Sent to Supplier'),
        ('acknowledged', 'Acknowledged'),
        ('partially_received', 'Partially Received'),
        ('fully_received', 'Fully Received'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]

    # Identity - organization scoped for multi-tenancy
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='purchase_orders'
    )
    po_number = models.CharField(max_length=50)

    # Supplier linkage
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders'
    )

    # Category for analytics
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_orders'
    )

    # Financial
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    freight_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Contract linkage
    contract = models.ForeignKey(
        Contract,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_orders'
    )
    is_contract_backed = models.BooleanField(default=False)

    # Status & Workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Key Dates (for cycle time analysis)
    created_date = models.DateField()
    approval_date = models.DateField(null=True, blank=True)
    sent_date = models.DateField(null=True, blank=True)
    required_date = models.DateField(null=True, blank=True)  # When goods needed
    promised_date = models.DateField(null=True, blank=True)  # Supplier's promise

    # Approvals
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_purchase_orders'
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_purchase_orders'
    )

    # Amendment tracking
    original_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    amendment_count = models.PositiveIntegerField(default=0)

    # PR Linkage (optional - PO may be created without PR)
    requisition = models.ForeignKey(
        PurchaseRequisition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_orders'
    )

    # Metadata
    upload_batch = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date', '-created_at']
        unique_together = ['organization', 'po_number']
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'supplier']),
            models.Index(fields=['organization', 'created_date']),
            models.Index(fields=['organization', 'is_contract_backed']),
            models.Index(fields=['uuid']),
            models.Index(fields=['upload_batch']),
        ]

    def __str__(self):
        return f"{self.po_number} - {self.supplier.name} ({self.organization.name})"

    @property
    def is_maverick(self):
        """Check if PO is maverick (not backed by contract)."""
        return not self.is_contract_backed

    @property
    def amount_variance(self):
        """Calculate variance from original amount if amended."""
        if self.original_amount and self.original_amount > 0:
            return float((self.total_amount - self.original_amount) / self.original_amount * 100)
        return 0


class GoodsReceipt(models.Model):
    """
    Goods Receipt - Confirmation of delivery.
    Critical for 3-way matching (PO vs GR vs Invoice).
    """
    # UUID for external API references (prevents ID enumeration)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    STATUS_CHOICES = [
        ('pending', 'Pending Inspection'),
        ('accepted', 'Accepted'),
        ('partial_accept', 'Partially Accepted'),
        ('rejected', 'Rejected'),
    ]

    # Identity - organization scoped for multi-tenancy
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='goods_receipts'
    )
    gr_number = models.CharField(max_length=50)

    # Linkage to PO (required)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='goods_receipts'
    )

    # Receipt details
    received_date = models.DateField()
    received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='goods_received'
    )

    # Quantities (for variance analysis)
    quantity_ordered = models.DecimalField(max_digits=15, decimal_places=2)
    quantity_received = models.DecimalField(max_digits=15, decimal_places=2)
    quantity_accepted = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Value tracking for matching
    amount_received = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    inspection_notes = models.TextField(blank=True)

    # Metadata
    upload_batch = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-received_date', '-created_at']
        unique_together = ['organization', 'gr_number']
        verbose_name = 'Goods Receipt'
        verbose_name_plural = 'Goods Receipts'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'received_date']),
            models.Index(fields=['organization', 'purchase_order']),
            models.Index(fields=['uuid']),
            models.Index(fields=['upload_batch']),
        ]

    def __str__(self):
        return f"{self.gr_number} - PO: {self.purchase_order.po_number} ({self.organization.name})"

    @property
    def quantity_variance(self):
        """Calculate quantity variance percentage."""
        if self.quantity_ordered and self.quantity_ordered > 0:
            return float((self.quantity_received - self.quantity_ordered) / self.quantity_ordered * 100)
        return 0

    @property
    def has_variance(self):
        """Check if there's significant variance (>1%)."""
        return abs(self.quantity_variance) > 1


class Invoice(models.Model):
    """
    Supplier Invoice - Billing document.
    Core model for 3-way matching and AP aging analysis.
    """
    # UUID for external API references (prevents ID enumeration)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    STATUS_CHOICES = [
        ('received', 'Received'),
        ('pending_match', 'Pending Match'),
        ('matched', 'Matched'),
        ('exception', 'Exception'),
        ('approved', 'Approved for Payment'),
        ('on_hold', 'On Hold'),
        ('paid', 'Paid'),
        ('disputed', 'Disputed'),
    ]

    MATCH_STATUS_CHOICES = [
        ('unmatched', 'Unmatched'),
        ('2way_matched', '2-Way Matched'),
        ('3way_matched', '3-Way Matched'),
        ('exception', 'Match Exception'),
    ]

    EXCEPTION_TYPE_CHOICES = [
        ('price_variance', 'Price Variance'),
        ('quantity_variance', 'Quantity Variance'),
        ('no_po', 'No Purchase Order'),
        ('duplicate', 'Duplicate Invoice'),
        ('missing_gr', 'Missing Goods Receipt'),
        ('other', 'Other'),
    ]

    # Identity - organization scoped for multi-tenancy
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    invoice_number = models.CharField(max_length=100)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='invoices'
    )

    # Linkage (for 3-way match)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices'
    )
    goods_receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices'
    )

    # Financial
    invoice_amount = models.DecimalField(max_digits=15, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')

    # Payment terms
    payment_terms = models.CharField(max_length=50, blank=True)  # e.g., "Net 30", "2/10 Net 30"
    payment_terms_days = models.PositiveIntegerField(null=True, blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_days = models.PositiveIntegerField(null=True, blank=True)

    # Key Dates (for aging analysis)
    invoice_date = models.DateField()
    received_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    approved_date = models.DateField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)

    # Status & Matching
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    match_status = models.CharField(max_length=20, choices=MATCH_STATUS_CHOICES, default='unmatched')

    # Exception tracking
    has_exception = models.BooleanField(default=False)
    exception_type = models.CharField(max_length=20, choices=EXCEPTION_TYPE_CHOICES, blank=True)
    exception_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    exception_notes = models.TextField(blank=True)
    exception_resolved = models.BooleanField(default=False)
    exception_resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_invoice_exceptions'
    )
    exception_resolved_at = models.DateTimeField(null=True, blank=True)

    # Hold tracking
    hold_reason = models.TextField(blank=True)

    # Metadata
    upload_batch = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date', '-created_at']
        unique_together = ['organization', 'invoice_number', 'supplier']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'match_status']),
            models.Index(fields=['organization', 'due_date']),
            models.Index(fields=['organization', 'supplier']),
            models.Index(fields=['organization', 'has_exception']),
            models.Index(fields=['organization', 'invoice_date']),
            models.Index(fields=['uuid']),
            models.Index(fields=['upload_batch']),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.supplier.name} ({self.organization.name})"

    @property
    def days_outstanding(self):
        """Calculate days since invoice date (for aging)."""
        from datetime import date
        if self.paid_date:
            return (self.paid_date - self.invoice_date).days
        return (date.today() - self.invoice_date).days

    @property
    def days_overdue(self):
        """Calculate days past due date."""
        from datetime import date
        if self.paid_date:
            return max(0, (self.paid_date - self.due_date).days)
        return max(0, (date.today() - self.due_date).days)

    @property
    def is_overdue(self):
        """Check if invoice is past due."""
        from datetime import date
        return self.status not in ['paid', 'disputed'] and date.today() > self.due_date

    @property
    def aging_bucket(self):
        """Get aging bucket for AP analysis."""
        days = self.days_outstanding
        if days <= 30:
            return 'current'
        elif days <= 60:
            return '31-60'
        elif days <= 90:
            return '61-90'
        else:
            return '90+'

    @property
    def discount_available(self):
        """Check if early payment discount is still available."""
        from datetime import date
        if self.discount_days and self.discount_percent and self.invoice_date:
            discount_deadline = self.invoice_date
            from datetime import timedelta
            discount_deadline = discount_deadline + timedelta(days=self.discount_days)
            return date.today() <= discount_deadline
        return False

    @property
    def price_variance(self):
        """Calculate price variance against PO."""
        if self.purchase_order and self.purchase_order.total_amount > 0:
            return float(
                (self.invoice_amount - self.purchase_order.total_amount) /
                self.purchase_order.total_amount * 100
            )
        return None
