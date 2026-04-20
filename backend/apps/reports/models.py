"""
Report models for the reporting module.
Adapted from REPORTING_MODULE_REPLICATION_GUIDE.md
"""
import uuid
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.authentication.models import Organization


class Report(models.Model):
    """
    Core report model for generation, storage, scheduling, and sharing.
    Stores report configuration and generated data in summary_data JSONField.
    """

    # Report Types
    REPORT_TYPE_CHOICES = [
        ('spend_analysis', 'Spend Analysis'),
        ('supplier_performance', 'Supplier Performance'),
        ('savings_opportunities', 'Savings Opportunities'),
        ('price_trends', 'Price Trends'),
        ('contract_compliance', 'Contract Compliance'),
        ('executive_summary', 'Executive Summary'),
        ('pareto_analysis', 'Pareto Analysis'),
        ('stratification', 'Spend Stratification'),
        ('seasonality', 'Seasonality & Trends'),
        ('year_over_year', 'Year-over-Year Analysis'),
        ('tail_spend', 'Tail Spend Analysis'),
        ('custom', 'Custom Report'),
        # P2P Report Types
        ('p2p_pr_status', 'PR Status Report'),
        ('p2p_po_compliance', 'PO Compliance Report'),
        ('p2p_ap_aging', 'AP Aging Report'),
    ]

    # Export Formats
    REPORT_FORMAT_CHOICES = [
        ('pdf', 'PDF Document'),
        ('xlsx', 'Excel Spreadsheet'),
        ('csv', 'CSV File'),
    ]

    # Status Tracking
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('scheduled', 'Scheduled'),
    ]

    # Schedule Frequencies
    SCHEDULE_FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]

    # Primary Key - UUID for security
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic Information
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPE_CHOICES)
    report_format = models.CharField(
        max_length=20,
        choices=REPORT_FORMAT_CHOICES,
        default='pdf'
    )

    # Organization (multi-tenant)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='reports'
    )

    # Ownership
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_reports'
    )

    # Date Range for Report Data
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    # Filters and Parameters (JSON for flexibility)
    filters = models.JSONField(default=dict, blank=True)
    parameters = models.JSONField(default=dict, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    error_message = models.TextField(blank=True)

    # Generated Output
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    summary_data = models.JSONField(default=dict, blank=True)

    # Sharing
    is_public = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='shared_reports',
        blank=True
    )

    # Scheduling
    is_scheduled = models.BooleanField(default=False)
    schedule_frequency = models.CharField(
        max_length=20,
        choices=SCHEDULE_FREQUENCY_CHOICES,
        blank=True
    )
    next_run = models.DateTimeField(null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'report_type']),
            models.Index(fields=['created_by']),
            models.Index(fields=['status']),
            models.Index(fields=['is_scheduled', 'next_run']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"

    def save(self, *args, **kwargs):
        # Auto-generate name if not provided
        if not self.name:
            self.name = f"{self.get_report_type_display()} - {timezone.now().strftime('%Y-%m-%d')}"
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if report is older than 30 days."""
        if self.generated_at:
            return timezone.now() - self.generated_at > timedelta(days=30)
        return False

    def calculate_next_run(self):
        """Calculate next scheduled run time based on frequency."""
        now = timezone.now()
        frequency_deltas = {
            'daily': timedelta(days=1),
            'weekly': timedelta(weeks=1),
            'bi_weekly': timedelta(weeks=2),
            'monthly': timedelta(days=30),
            'quarterly': timedelta(days=90),
        }
        delta = frequency_deltas.get(self.schedule_frequency, timedelta(days=1))
        self.next_run = now + delta
        return self.next_run

    def mark_completed(self, summary_data=None):
        """Mark report as completed with optional summary data."""
        self.status = 'completed'
        self.generated_at = timezone.now()
        if summary_data:
            self.summary_data = summary_data
        self.save()

    def mark_failed(self, error_message):
        """Mark report as failed with error message."""
        self.status = 'failed'
        self.error_message = error_message
        self.save()

    def can_access(self, user):
        """Check if user can access this report."""
        from apps.authentication.organization_utils import user_can_access_org

        if user.is_superuser:
            return True
        if self.created_by == user:
            return True
        if self.is_public:
            return True
        if self.shared_with.filter(id=user.id).exists():
            return True
        # Check organization membership using multi-org aware utility
        # This supports users with multiple organization memberships
        if user_can_access_org(user, self.organization):
            return True
        return False
