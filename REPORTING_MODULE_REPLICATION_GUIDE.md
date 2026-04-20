# Django Reporting Module - Comprehensive Replication Guide

A complete guide for replicating the HTMX-powered reporting module with PDF/CSV exports, scheduling, sharing, and custom report builder functionality.

**Estimated Implementation Time**: 2-3 days for core features, 1 additional day for advanced features

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Step 1: Database Models](#step-1-database-models)
5. [Step 2: URL Patterns](#step-2-url-patterns)
6. [Step 3: Views](#step-3-views)
7. [Step 4: Templates](#step-4-templates)
8. [Step 5: Serializers (Optional - DRF)](#step-5-serializers)
9. [Step 6: Celery Tasks (Optional)](#step-6-celery-tasks)
10. [HTMX Patterns Reference](#htmx-patterns-reference)
11. [Customization Guide](#customization-guide)
12. [Troubleshooting](#troubleshooting)
13. [Replication Checklist](#replication-checklist)

---

## Overview

### Features

| Feature | Description |
|---------|-------------|
| **Report Generation** | On-demand report creation with date filtering |
| **Multiple Report Types** | 6+ configurable report types |
| **Export Formats** | CSV and PDF with styled tables |
| **Scheduling** | Daily, weekly, monthly, quarterly schedules |
| **Sharing** | Share reports with team members |
| **Preview** | Modal-based report preview |
| **Custom Builder** | User-defined reports with field selection |
| **HTMX-Powered UI** | No page reloads, smooth interactions |

### Technology Stack

- **Backend**: Django 4.2+
- **Frontend**: HTMX + Tailwind CSS + Font Awesome
- **PDF Generation**: ReportLab
- **Task Queue**: Celery (optional, for scheduled reports)
- **Database**: PostgreSQL (recommended) or SQLite

---

## Architecture

```
+-------------------------------------------------------------+
|                      USER INTERFACE                         |
|  +--------------+  +--------------+  +--------------------+ |
|  | Report Grid  |  | Recent List  |  | Scheduled Reports  | |
|  |  (6 cards)   |  |  (HTMX)      |  |     Section        | |
|  +--------------+  +--------------+  +--------------------+ |
+----------------------------+--------------------------------+
                             | HTMX Requests
                             v
+-------------------------------------------------------------+
|                        VIEWS LAYER                          |
|  +----------------+  +----------------+  +----------------+ |
|  | ReportGenerate |  | ReportPreview  |  | ReportDownload | |
|  |     View       |  |     View       |  |     View       | |
|  +----------------+  +----------------+  +----------------+ |
|  +----------------+  +----------------+  +----------------+ |
|  | ReportShare    |  | ReportSchedule |  | ReportBuilder  | |
|  |     View       |  |     View       |  |     View       | |
|  +----------------+  +----------------+  +----------------+ |
+----------------------------+--------------------------------+
                             |
                             v
+-------------------------------------------------------------+
|                      DATA LAYER                             |
|  +-----------------------------------------------------+   |
|  |                    Report Model                      |   |
|  |  - UUID PK        - Status Tracking                  |   |
|  |  - Report Type    - Summary Data (JSON)              |   |
|  |  - Scheduling     - Sharing (M2M)                    |   |
|  +-----------------------------------------------------+   |
|  +--------------+  +--------------+  +------------------+   |
|  | Your Model 1 |  | Your Model 2 |  |   Your Model N   |   |
|  | (e.g. Order) |  |(e.g.Product) |  |  (e.g. Customer) |   |
|  +--------------+  +--------------+  +------------------+   |
+-------------------------------------------------------------+
```

### Data Flow

```
1. User clicks "Generate Report"
   +-- HTMX POST to /reports/generate/

2. View creates Report with status='generating'
   +-- Queries database for report data
   +-- Stores summary in Report.summary_data (JSON)
   +-- Updates status to 'completed'

3. HTMX returns HTML fragment
   +-- Updates UI without page reload

4. User clicks "Download"
   +-- View retrieves Report.summary_data
   +-- Generates CSV or PDF
   +-- Returns file response
```

---

## Prerequisites

### Required Packages

Add to `requirements.txt`:

```
Django>=4.2
reportlab>=4.0  # PDF generation
```

### Optional Packages

```
celery>=5.3     # For scheduled reports
django-htmx>=1.17  # HTMX integration helpers
djangorestframework>=3.14  # API endpoints
```

### Frontend Dependencies

Include in your base template:

```html
<!-- HTMX -->
<script src="https://unpkg.com/htmx.org@1.9.10"></script>

<!-- Tailwind CSS -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- Font Awesome -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
```

---

## Step 1: Database Models

Create `models.py` in your analytics/reports app:

```python
import uuid
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone


class Report(models.Model):
    """
    Core report model for generation, storage, scheduling, and sharing.
    """

    # Report Types - Customize for your domain
    REPORT_TYPE_CHOICES = [
        ('spend_analysis', 'Spend Analysis'),
        ('supplier_performance', 'Supplier Performance'),
        ('savings_opportunities', 'Savings Opportunities'),
        ('price_trends', 'Price Trends'),
        ('contract_compliance', 'Contract Compliance'),
        ('executive_summary', 'Executive Summary'),
        ('custom', 'Custom Report'),
    ]

    # Export Formats
    REPORT_FORMAT_CHOICES = [
        ('pdf', 'PDF Document'),
        ('excel', 'Excel Spreadsheet'),
        ('csv', 'CSV File'),
        ('json', 'JSON Data'),
        ('dashboard', 'Dashboard View'),
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

    # Primary Key
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

    # Organization/Tenant (if multi-tenant)
    organization = models.ForeignKey(
        'core.Organization',  # Adjust to your org model
        on_delete=models.CASCADE,
        related_name='reports',
        null=True, blank=True
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
    summary_data = models.JSONField(default=dict, blank=True)  # Store report data

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
```

### Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Step 2: URL Patterns

Create `urls.py` in your reports app:

```python
from django.urls import path
from . import views

app_name = 'reports'  # Namespace for URL reversal

urlpatterns = [
    # === Main Views ===
    path('', views.ReportListView.as_view(), name='report_list'),
    path('<uuid:pk>/', views.ReportDetailView.as_view(), name='report_detail'),

    # === Report Generation ===
    path('generate/', views.ReportGenerateView.as_view(), name='report_generate'),
    path('<uuid:pk>/download/', views.ReportDownloadView.as_view(), name='report_download'),

    # === HTMX Endpoints (Partials & Modals) ===
    path('refresh/', views.ReportsRefreshView.as_view(), name='reports_refresh'),
    path('filter/', views.ReportsFilterView.as_view(), name='reports_filter'),
    path('more/', views.ReportsMoreView.as_view(), name='reports_more'),

    # === Report Actions ===
    path('<uuid:pk>/preview/', views.ReportPreviewView.as_view(), name='report_preview'),
    path('<uuid:pk>/delete/', views.ReportDeleteView.as_view(), name='report_delete'),
    path('<uuid:pk>/share/', views.ReportShareView.as_view(), name='report_share'),

    # === Scheduling ===
    path('<uuid:pk>/schedule/', views.ReportScheduleView.as_view(), name='report_schedule'),
    path('<uuid:pk>/schedule/delete/', views.ReportScheduleDeleteView.as_view(), name='report_schedule_delete'),
    path('schedule/new/', views.ReportScheduleNewView.as_view(), name='report_schedule_new'),

    # === Custom Report Builder ===
    path('builder/', views.ReportBuilderView.as_view(), name='report_builder'),
]
```

### Include in Main URLs

```python
# project/urls.py
from django.urls import path, include

urlpatterns = [
    # ... other urls
    path('reports/', include('apps.reports.urls')),
]
```

---

## Step 3: Views

Create `views.py` with all view classes:

```python
import csv
import io
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Avg, F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, DetailView, TemplateView

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from .models import Report

User = get_user_model()


# =============================================================================
# HELPER MIXIN - Customize for your authentication/organization needs
# =============================================================================

class OrganizationMixin:
    """
    Mixin to filter reports by user's organization.
    Customize this for your multi-tenant setup.
    """
    def get_organization(self):
        # Option 1: From user profile
        # return self.request.user.profile.organization

        # Option 2: From session
        # return self.request.session.get('organization_id')

        # Option 3: No multi-tenancy (return None)
        return getattr(self.request.user, 'organization', None)

    def get_queryset(self):
        qs = super().get_queryset()
        org = self.get_organization()
        if org:
            return qs.filter(organization=org)
        return qs.filter(created_by=self.request.user)


# =============================================================================
# MAIN VIEWS
# =============================================================================

class ReportListView(LoginRequiredMixin, OrganizationMixin, ListView):
    """List all reports for the organization."""
    model = Report
    template_name = 'reports/report_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    ordering = ['-created_at']


class ReportDetailView(LoginRequiredMixin, OrganizationMixin, DetailView):
    """View single report details."""
    model = Report
    template_name = 'reports/report_detail.html'
    context_object_name = 'report'


# =============================================================================
# REPORT GENERATION
# =============================================================================

class ReportGenerateView(LoginRequiredMixin, View):
    """
    Generate a report based on type and date range.
    Returns HTMX-compatible HTML response.
    """

    def post(self, request):
        report_type = request.POST.get('report_type', 'executive_summary')
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')

        # Default date range: last 30 days
        if not date_to:
            date_to = timezone.now().date()
        if not date_from:
            date_from = date_to - timedelta(days=30)

        try:
            # Create report record
            report = Report.objects.create(
                name=f"{report_type.replace('_', ' ').title()} Report",
                report_type=report_type,
                organization=self.get_organization(),
                created_by=request.user,
                period_start=date_from,
                period_end=date_to,
                status='generating'
            )

            # Generate report data
            summary_data = self._generate_report_data(report_type, date_from, date_to)

            # Mark as completed
            report.mark_completed(summary_data)

            # Return success HTML
            return render(request, 'reports/partials/generation_success.html', {
                'report': report
            })

        except Exception as e:
            return render(request, 'reports/partials/generation_error.html', {
                'error': str(e)
            }, status=400)

    def get_organization(self):
        return getattr(self.request.user, 'organization', None)

    def _generate_report_data(self, report_type, date_from, date_to):
        """
        Route to specific report generator based on type.
        CUSTOMIZE THESE METHODS for your domain models.
        """
        generators = {
            'spend_analysis': self._generate_spend_analysis,
            'supplier_performance': self._generate_supplier_performance,
            'savings_opportunities': self._generate_savings_opportunities,
            'price_trends': self._generate_price_trends,
            'contract_compliance': self._generate_contract_compliance,
            'executive_summary': self._generate_executive_summary,
        }

        generator = generators.get(report_type, self._generate_executive_summary)
        return generator(date_from, date_to)

    def _generate_spend_analysis(self, date_from, date_to):
        """
        Generate spend analysis data.
        CUSTOMIZE: Replace with your Order/PurchaseOrder model.
        """
        # Example with placeholder - replace with your models
        # from .models import PurchaseOrder, Supplier

        # Example data structure
        return {
            'total_spend': 125000.00,
            'period': f"{date_from} to {date_to}",
            'spend_by_category': [
                {'category': 'Category A', 'amount': 50000},
                {'category': 'Category B', 'amount': 45000},
                {'category': 'Category C', 'amount': 30000},
            ],
            'monthly_trend': [
                {'month': 'Jan', 'amount': 40000},
                {'month': 'Feb', 'amount': 42000},
                {'month': 'Mar', 'amount': 43000},
            ]
        }

    def _generate_supplier_performance(self, date_from, date_to):
        """Generate supplier performance metrics."""
        return {
            'total_suppliers': 45,
            'active_suppliers': 38,
            'avg_rating': 4.2,
            'on_time_delivery_rate': 94.5,
            'top_suppliers': [
                {'name': 'Supplier A', 'orders': 120, 'rating': 4.8},
                {'name': 'Supplier B', 'orders': 98, 'rating': 4.5},
                {'name': 'Supplier C', 'orders': 87, 'rating': 4.3},
            ]
        }

    def _generate_savings_opportunities(self, date_from, date_to):
        """Generate savings opportunity analysis."""
        return {
            'total_potential_savings': 15000,
            'opportunities': [
                {'item': 'Product A', 'current': 100, 'benchmark': 85, 'savings': 15},
                {'item': 'Product B', 'current': 200, 'benchmark': 180, 'savings': 20},
            ]
        }

    def _generate_price_trends(self, date_from, date_to):
        """Generate price trend analysis."""
        return {
            'avg_price_change': 2.5,
            'items_increased': 25,
            'items_decreased': 12,
            'items_stable': 63,
        }

    def _generate_contract_compliance(self, date_from, date_to):
        """Generate contract compliance metrics."""
        return {
            'compliance_rate': 92.3,
            'compliant_spend': 115000,
            'maverick_spend': 10000,
        }

    def _generate_executive_summary(self, date_from, date_to):
        """Generate executive summary with key KPIs."""
        return {
            'total_spend': 125000,
            'total_orders': 450,
            'active_suppliers': 38,
            'savings_achieved': 12500,
            'compliance_rate': 92.3,
        }


# =============================================================================
# REPORT DOWNLOAD (CSV/PDF)
# =============================================================================

class ReportDownloadView(LoginRequiredMixin, View):
    """
    Download report as CSV or PDF.
    Usage: /reports/<uuid>/download/?format=csv
           /reports/<uuid>/download/?format=pdf
    """

    def get(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        export_format = request.GET.get('format', 'csv')

        if export_format == 'pdf':
            return self._generate_pdf_response(report)
        else:
            return self._generate_csv_response(report)

    def _generate_csv_response(self, report):
        """Generate CSV file from report data."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report.name}.csv"'

        writer = csv.writer(response)

        # Header
        writer.writerow([report.name])
        writer.writerow([f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}"])
        writer.writerow([f"Period: {report.period_start} to {report.period_end}"])
        writer.writerow([])  # Empty row

        # Write summary data
        summary = report.summary_data or {}

        for key, value in summary.items():
            if isinstance(value, list):
                # Handle list data (tables)
                writer.writerow([key.replace('_', ' ').title()])
                if value and isinstance(value[0], dict):
                    # Write headers from first item's keys
                    headers = list(value[0].keys())
                    writer.writerow(headers)
                    for item in value:
                        writer.writerow([item.get(h, '') for h in headers])
                writer.writerow([])
            else:
                # Handle simple key-value
                writer.writerow([key.replace('_', ' ').title(), value])

        return response

    def _generate_pdf_response(self, report):
        """Generate styled PDF from report data."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch)

        elements = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1e3a5f'),  # Navy blue
            spaceAfter=12
        )

        # Title
        elements.append(Paragraph(report.name, title_style))
        elements.append(Paragraph(
            f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            styles['Normal']
        ))
        elements.append(Paragraph(
            f"Period: {report.period_start} to {report.period_end}",
            styles['Normal']
        ))
        elements.append(Spacer(1, 0.25*inch))

        # Summary data
        summary = report.summary_data or {}

        for key, value in summary.items():
            section_title = key.replace('_', ' ').title()
            elements.append(Paragraph(section_title, styles['Heading2']))

            if isinstance(value, list) and value and isinstance(value[0], dict):
                # Create table from list of dicts
                headers = list(value[0].keys())
                data = [headers]
                for item in value:
                    data.append([str(item.get(h, '')) for h in headers])

                table = self._create_styled_table(data)
                elements.append(table)
            else:
                # Simple value
                elements.append(Paragraph(f"{value}", styles['Normal']))

            elements.append(Spacer(1, 0.15*inch))

        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report.name}.pdf"'
        return response

    def _create_styled_table(self, data):
        """Create a styled ReportLab table."""
        table = Table(data)
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),

            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),

            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        return table


# =============================================================================
# HTMX PARTIAL VIEWS
# =============================================================================

class ReportsRefreshView(LoginRequiredMixin, View):
    """Refresh the recent reports list (HTMX)."""

    def get(self, request):
        reports = Report.objects.filter(
            created_by=request.user
        ).order_by('-created_at')[:10]

        return render(request, 'reports/partials/recent_reports_list.html', {
            'reports': reports
        })


class ReportsFilterView(LoginRequiredMixin, View):
    """Filter reports by type (HTMX)."""

    def get(self, request):
        report_type = request.GET.get('type', 'all')

        reports = Report.objects.filter(created_by=request.user)

        if report_type and report_type != 'all':
            reports = reports.filter(report_type=report_type)

        reports = reports.order_by('-created_at')[:10]

        return render(request, 'reports/partials/recent_reports_list.html', {
            'reports': reports
        })


class ReportsMoreView(LoginRequiredMixin, View):
    """Load more reports for pagination (HTMX)."""

    def get(self, request):
        offset = int(request.GET.get('offset', 0))
        limit = 10

        reports = Report.objects.filter(
            created_by=request.user
        ).order_by('-created_at')[offset:offset + limit]

        return render(request, 'reports/partials/recent_reports_list.html', {
            'reports': reports,
            'next_offset': offset + limit if reports.count() == limit else None
        })


# =============================================================================
# REPORT ACTIONS (Preview, Delete, Share)
# =============================================================================

class ReportPreviewView(LoginRequiredMixin, View):
    """Show report preview modal (HTMX)."""

    def get(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        return render(request, 'reports/partials/report_preview_modal.html', {
            'report': report
        })


class ReportDeleteView(LoginRequiredMixin, View):
    """Delete a report (HTMX)."""

    def delete(self, request, pk):
        report = get_object_or_404(Report, pk=pk, created_by=request.user)
        report.delete()

        return render(request, 'reports/partials/delete_success.html')

    # Support POST for browsers that don't support DELETE
    def post(self, request, pk):
        return self.delete(request, pk)


class ReportShareView(LoginRequiredMixin, View):
    """Share report with team members (HTMX)."""

    def get(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        users = User.objects.exclude(pk=request.user.pk)[:20]

        return render(request, 'reports/partials/report_share_modal.html', {
            'report': report,
            'users': users
        })

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        user_ids = request.POST.getlist('user_ids')

        if user_ids:
            users = User.objects.filter(pk__in=user_ids)
            report.shared_with.add(*users)

        return render(request, 'reports/partials/share_success.html')


# =============================================================================
# SCHEDULING
# =============================================================================

class ReportScheduleView(LoginRequiredMixin, View):
    """Configure report schedule (HTMX)."""

    def get(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        return render(request, 'reports/partials/report_schedule_modal.html', {
            'report': report,
            'frequencies': Report.SCHEDULE_FREQUENCY_CHOICES
        })

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)

        frequency = request.POST.get('frequency')

        if frequency:
            report.is_scheduled = True
            report.schedule_frequency = frequency
            report.calculate_next_run()
            report.save()

            return render(request, 'reports/partials/schedule_success.html', {
                'report': report
            })

        return render(request, 'reports/partials/schedule_error.html', {
            'error': 'Please select a frequency'
        }, status=400)


class ReportScheduleDeleteView(LoginRequiredMixin, View):
    """Remove schedule from report (HTMX)."""

    def delete(self, request, pk):
        report = get_object_or_404(Report, pk=pk)

        report.is_scheduled = False
        report.schedule_frequency = ''
        report.next_run = None
        report.save()

        return render(request, 'reports/partials/schedule_removed.html')

    def post(self, request, pk):
        return self.delete(request, pk)


class ReportScheduleNewView(LoginRequiredMixin, View):
    """Create new scheduled report (HTMX)."""

    def get(self, request):
        return render(request, 'reports/partials/schedule_new_modal.html', {
            'report_types': Report.REPORT_TYPE_CHOICES,
            'frequencies': Report.SCHEDULE_FREQUENCY_CHOICES
        })

    def post(self, request):
        name = request.POST.get('name')
        report_type = request.POST.get('report_type')
        frequency = request.POST.get('frequency')

        if not all([name, report_type, frequency]):
            return render(request, 'reports/partials/schedule_error.html', {
                'error': 'All fields are required'
            }, status=400)

        report = Report.objects.create(
            name=name,
            report_type=report_type,
            created_by=request.user,
            is_scheduled=True,
            schedule_frequency=frequency,
            status='scheduled'
        )
        report.calculate_next_run()
        report.save()

        return render(request, 'reports/partials/schedule_created.html', {
            'report': report
        })


# =============================================================================
# CUSTOM REPORT BUILDER
# =============================================================================

class ReportBuilderView(LoginRequiredMixin, View):
    """Custom report builder interface (HTMX)."""

    def get(self, request):
        # Define available data sources and their fields
        # CUSTOMIZE: Replace with your actual models
        data_sources = {
            'orders': {
                'label': 'Orders',
                'count': 0,  # Replace with actual count
                'fields': ['order_number', 'date', 'total', 'status', 'customer']
            },
            'products': {
                'label': 'Products',
                'count': 0,
                'fields': ['name', 'sku', 'price', 'category', 'stock']
            },
            'customers': {
                'label': 'Customers',
                'count': 0,
                'fields': ['name', 'email', 'company', 'total_orders']
            },
        }

        return render(request, 'reports/partials/report_builder_modal.html', {
            'data_sources': data_sources,
            'output_formats': ['csv', 'json', 'pdf']
        })

    def post(self, request):
        name = request.POST.get('name', 'Custom Report')
        data_source = request.POST.get('data_source')
        fields = request.POST.getlist('fields')
        output_format = request.POST.get('output_format', 'csv')

        # Create custom report
        report = Report.objects.create(
            name=name,
            report_type='custom',
            report_format=output_format,
            created_by=request.user,
            parameters={
                'data_source': data_source,
                'fields': fields
            },
            status='generating'
        )

        # Generate custom report data
        # CUSTOMIZE: Implement actual data retrieval
        summary_data = {
            'data_source': data_source,
            'fields': fields,
            'rows': []  # Add actual data here
        }

        report.mark_completed(summary_data)

        return render(request, 'reports/partials/builder_success.html', {
            'report': report,
            'output_format': output_format
        })
```

---

## Step 4: Templates

### Main Report Tab Template

Create `templates/reports/tabs/reports.html`:

```html
{% load static %}

<div class="space-y-6">
    <!-- Page Header -->
    <div class="flex justify-between items-center">
        <div>
            <h2 class="text-2xl font-bold text-gray-900">Reports</h2>
            <p class="text-gray-600 mt-1">Generate, schedule, and manage your reports</p>
        </div>
        <button hx-get="{% url 'reports:report_builder' %}"
                hx-target="#modal-container"
                hx-swap="innerHTML"
                class="btn btn-primary">
            <i class="fas fa-plus mr-2"></i> Custom Report
        </button>
    </div>

    <!-- Report Status Messages -->
    <div id="reports-generation-status"></div>

    <!-- Report Templates Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {% for template in report_templates %}
        <div class="bg-white rounded-lg shadow p-5 hover:shadow-md transition-shadow cursor-pointer"
             hx-post="{% url 'reports:report_generate' %}"
             hx-vals='{"report_type": "{{ template.type }}"}'
             hx-target="#reports-generation-status"
             hx-swap="innerHTML">
            <div class="flex items-center">
                <div class="p-3 {{ template.bg_color }} rounded-full mr-4">
                    <i class="fas {{ template.icon }} {{ template.text_color }} text-xl"></i>
                </div>
                <div>
                    <h3 class="font-semibold text-gray-900">{{ template.name }}</h3>
                    <p class="text-sm text-gray-500">{{ template.description }}</p>
                </div>
            </div>
            {% if template.last_generated %}
            <p class="text-xs text-gray-400 mt-3">
                <i class="fas fa-clock mr-1"></i> Last: {{ template.last_generated|timesince }} ago
            </p>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <!-- Recent Reports Section -->
    <div class="bg-white rounded-lg shadow">
        <div class="p-4 border-b border-gray-200 flex justify-between items-center">
            <h3 class="font-semibold text-gray-900">Recent Reports</h3>
            <div class="flex items-center space-x-2">
                <!-- Filter Dropdown -->
                <select hx-get="{% url 'reports:reports_filter' %}"
                        hx-target="#recent-reports-list"
                        hx-swap="innerHTML"
                        hx-include="this"
                        name="type"
                        class="form-select text-sm border-gray-300 rounded-md">
                    <option value="all">All Types</option>
                    {% for type_value, type_label in report_types %}
                    <option value="{{ type_value }}">{{ type_label }}</option>
                    {% endfor %}
                </select>

                <!-- Refresh Button -->
                <button hx-get="{% url 'reports:reports_refresh' %}"
                        hx-target="#recent-reports-list"
                        hx-swap="innerHTML"
                        class="p-2 text-gray-500 hover:text-gray-700">
                    <i class="fas fa-sync-alt"></i>
                </button>
            </div>
        </div>

        <div id="recent-reports-list" class="divide-y divide-gray-100">
            {% include 'reports/partials/recent_reports_list.html' %}
        </div>
    </div>

    <!-- Scheduled Reports Section -->
    <div class="bg-white rounded-lg shadow">
        <div class="p-4 border-b border-gray-200 flex justify-between items-center">
            <h3 class="font-semibold text-gray-900">Scheduled Reports</h3>
            <button hx-get="{% url 'reports:report_schedule_new' %}"
                    hx-target="#modal-container"
                    hx-swap="innerHTML"
                    class="text-sm text-blue-600 hover:text-blue-800">
                <i class="fas fa-plus mr-1"></i> Add Schedule
            </button>
        </div>
        <div class="p-4">
            {% if scheduled_reports %}
            <div class="space-y-3">
                {% for report in scheduled_reports %}
                <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <div>
                        <p class="font-medium text-gray-900">{{ report.name }}</p>
                        <p class="text-sm text-gray-500">
                            {{ report.get_schedule_frequency_display }} |
                            Next: {{ report.next_run|date:"M d, Y" }}
                        </p>
                    </div>
                    <button hx-get="{% url 'reports:report_schedule' report.pk %}"
                            hx-target="#modal-container"
                            hx-swap="innerHTML"
                            class="text-gray-400 hover:text-gray-600">
                        <i class="fas fa-cog"></i>
                    </button>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <p class="text-gray-500 text-center py-4">No scheduled reports</p>
            {% endif %}
        </div>
    </div>
</div>

<!-- Modal Container -->
<div id="modal-container"></div>
```

### Recent Reports List Partial

Create `templates/reports/partials/recent_reports_list.html`:

```html
{% if reports %}
    {% for report in reports %}
    <div class="flex justify-between items-center p-4 hover:bg-gray-50">
        <div class="flex items-center">
            <!-- Icon based on report type -->
            <div class="p-2 rounded-full mr-3
                {% if report.report_type == 'spend_analysis' %}bg-blue-100
                {% elif report.report_type == 'supplier_performance' %}bg-green-100
                {% elif report.report_type == 'savings_opportunities' %}bg-yellow-100
                {% elif report.report_type == 'price_trends' %}bg-purple-100
                {% elif report.report_type == 'contract_compliance' %}bg-indigo-100
                {% else %}bg-gray-100{% endif %}">
                <i class="fas
                    {% if report.report_type == 'spend_analysis' %}fa-chart-pie text-blue-600
                    {% elif report.report_type == 'supplier_performance' %}fa-users text-green-600
                    {% elif report.report_type == 'savings_opportunities' %}fa-piggy-bank text-yellow-600
                    {% elif report.report_type == 'price_trends' %}fa-chart-line text-purple-600
                    {% elif report.report_type == 'contract_compliance' %}fa-file-contract text-indigo-600
                    {% else %}fa-file-alt text-gray-600{% endif %}">
                </i>
            </div>
            <div>
                <p class="font-medium text-gray-900">{{ report.name }}</p>
                <p class="text-sm text-gray-500">
                    {{ report.created_at|date:"M d, Y H:i" }} |
                    {{ report.created_by.get_full_name|default:report.created_by.username }}
                </p>
            </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center space-x-2">
            <!-- Status Badge -->
            <span class="px-2 py-1 text-xs rounded-full
                {% if report.status == 'completed' %}bg-green-100 text-green-800
                {% elif report.status == 'generating' %}bg-blue-100 text-blue-800
                {% elif report.status == 'failed' %}bg-red-100 text-red-800
                {% else %}bg-gray-100 text-gray-800{% endif %}">
                {{ report.get_status_display }}
            </span>

            {% if report.status == 'completed' %}
            <!-- Preview -->
            <button hx-get="{% url 'reports:report_preview' report.pk %}"
                    hx-target="#modal-container"
                    hx-swap="innerHTML"
                    class="p-2 text-gray-400 hover:text-gray-600"
                    title="Preview">
                <i class="fas fa-eye"></i>
            </button>

            <!-- Download CSV -->
            <a href="{% url 'reports:report_download' report.pk %}?format=csv"
               class="p-2 text-gray-400 hover:text-gray-600"
               title="Download CSV">
                <i class="fas fa-file-csv"></i>
            </a>

            <!-- Download PDF -->
            <a href="{% url 'reports:report_download' report.pk %}?format=pdf"
               class="p-2 text-gray-400 hover:text-gray-600"
               title="Download PDF">
                <i class="fas fa-file-pdf"></i>
            </a>

            <!-- Share -->
            <button hx-get="{% url 'reports:report_share' report.pk %}"
                    hx-target="#modal-container"
                    hx-swap="innerHTML"
                    class="p-2 text-gray-400 hover:text-gray-600"
                    title="Share">
                <i class="fas fa-share-alt"></i>
            </button>

            <!-- Schedule -->
            <button hx-get="{% url 'reports:report_schedule' report.pk %}"
                    hx-target="#modal-container"
                    hx-swap="innerHTML"
                    class="p-2 text-gray-400 hover:text-gray-600"
                    title="Schedule">
                <i class="fas fa-clock"></i>
            </button>
            {% endif %}

            <!-- Delete -->
            <button hx-delete="{% url 'reports:report_delete' report.pk %}"
                    hx-confirm="Are you sure you want to delete this report?"
                    hx-target="closest div.flex.justify-between"
                    hx-swap="outerHTML"
                    class="p-2 text-gray-400 hover:text-red-600"
                    title="Delete">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    </div>
    {% endfor %}

    <!-- Load More Button -->
    {% if next_offset %}
    <div class="p-4 text-center">
        <button hx-get="{% url 'reports:reports_more' %}?offset={{ next_offset }}"
                hx-target="#recent-reports-list"
                hx-swap="beforeend"
                class="text-blue-600 hover:text-blue-800 text-sm">
            Load More
        </button>
    </div>
    {% endif %}
{% else %}
    <div class="p-8 text-center text-gray-500">
        <i class="fas fa-file-alt text-4xl mb-2 opacity-50"></i>
        <p>No reports yet. Click a report template above to generate one.</p>
    </div>
{% endif %}
```

### Small Response Partials

Create these small partial templates for HTMX responses:

**`templates/reports/partials/generation_success.html`**:
```html
<div class="bg-green-50 border border-green-200 rounded-lg p-4">
    <div class="flex items-center">
        <i class="fas fa-check-circle text-green-500 mr-2"></i>
        <span class="text-green-700">Report generated successfully!</span>
    </div>
    <div class="mt-2">
        <a href="{% url 'reports:report_detail' report.pk %}"
           class="text-green-600 hover:text-green-800 underline">
            View Report
        </a>
    </div>
</div>
```

**`templates/reports/partials/generation_error.html`**:
```html
<div class="bg-red-50 border border-red-200 rounded-lg p-4">
    <div class="flex items-center">
        <i class="fas fa-exclamation-circle text-red-500 mr-2"></i>
        <span class="text-red-700">Error: {{ error }}</span>
    </div>
</div>
```

**`templates/reports/partials/delete_success.html`**:
```html
<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm">
    <i class="fas fa-trash text-yellow-600 mr-2"></i>
    Report deleted successfully
</div>
```

**`templates/reports/partials/share_success.html`**:
```html
<div class="bg-green-50 border border-green-200 rounded-lg p-3 text-sm">
    <i class="fas fa-check text-green-600 mr-2"></i>
    Report shared successfully
</div>
```

**`templates/reports/partials/schedule_success.html`**:
```html
<div class="bg-green-50 border border-green-200 rounded-lg p-3 text-sm">
    <i class="fas fa-clock text-green-600 mr-2"></i>
    Scheduled to run {{ report.get_schedule_frequency_display }}.
    Next run: {{ report.next_run|date:"M d, Y H:i" }}
</div>
```

### Modal Templates

See the full modal templates in the Step 4 section of the original implementation. Key modals include:

1. **report_preview_modal.html** - Shows report data preview
2. **report_share_modal.html** - User selection for sharing
3. **report_schedule_modal.html** - Schedule configuration
4. **schedule_new_modal.html** - Create new scheduled report
5. **report_builder_modal.html** - Custom report builder

---

## Step 5: Serializers

For API access (optional), create `serializers.py`:

```python
from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    """Full report serializer for detail views."""

    class Meta:
        model = Report
        fields = [
            'id', 'name', 'description', 'report_type', 'report_format',
            'created_by', 'organization', 'period_start', 'period_end',
            'filters', 'parameters', 'status', 'error_message',
            'file_path', 'summary_data', 'is_public', 'shared_with',
            'is_scheduled', 'schedule_frequency', 'next_run',
            'created_at', 'updated_at', 'generated_at'
        ]
        read_only_fields = ['id', 'created_by', 'status', 'generated_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        validated_data['status'] = 'draft'
        return super().create(validated_data)


class ReportSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    class Meta:
        model = Report
        fields = ['id', 'name', 'report_type', 'status', 'created_at', 'generated_at']
```

---

## Step 6: Celery Tasks

For scheduled report execution, create `tasks.py`:

```python
from celery import shared_task
from django.utils import timezone
from .models import Report


@shared_task
def process_scheduled_reports():
    """
    Run scheduled reports that are due.
    Schedule this task to run every hour via Celery Beat.
    """
    now = timezone.now()
    due_reports = Report.objects.filter(
        is_scheduled=True,
        status='scheduled',
        next_run__lte=now
    )

    for report in due_reports:
        generate_report_async.delay(str(report.pk))


@shared_task
def generate_report_async(report_id):
    """
    Generate a single report asynchronously.
    """
    try:
        report = Report.objects.get(pk=report_id)
        report.status = 'generating'
        report.save()

        # Import view to reuse generation logic
        from .views import ReportGenerateView
        view = ReportGenerateView()

        # Generate data
        summary_data = view._generate_report_data(
            report.report_type,
            report.period_start or (timezone.now() - timezone.timedelta(days=30)).date(),
            report.period_end or timezone.now().date()
        )

        # Update report
        report.mark_completed(summary_data)

        # Calculate next run if scheduled
        if report.is_scheduled:
            report.last_run = timezone.now()
            report.calculate_next_run()
            report.status = 'scheduled'
            report.save()

        return f"Report {report.name} generated successfully"

    except Report.DoesNotExist:
        return f"Report {report_id} not found"
    except Exception as e:
        report.mark_failed(str(e))
        return f"Report {report_id} failed: {str(e)}"
```

### Celery Beat Schedule

Add to your Django settings:

```python
# settings.py
CELERY_BEAT_SCHEDULE = {
    'process-scheduled-reports': {
        'task': 'apps.reports.tasks.process_scheduled_reports',
        'schedule': 3600.0,  # Every hour
    },
}
```

---

## HTMX Patterns Reference

### Common Patterns Used

```html
<!-- 1. Generate Report (POST with JSON values) -->
<div hx-post="/reports/generate/"
     hx-vals='{"report_type": "spend_analysis"}'
     hx-target="#status-container"
     hx-swap="innerHTML">

<!-- 2. Open Modal (GET returning HTML) -->
<button hx-get="/reports/123/preview/"
        hx-target="#modal-container"
        hx-swap="innerHTML">

<!-- 3. Delete with Confirmation -->
<button hx-delete="/reports/123/delete/"
        hx-confirm="Are you sure?"
        hx-target="closest .report-item"
        hx-swap="outerHTML">

<!-- 4. Filter/Search -->
<select hx-get="/reports/filter/"
        hx-target="#reports-list"
        hx-swap="innerHTML"
        hx-include="this"
        name="type">

<!-- 5. Load More (Pagination) -->
<button hx-get="/reports/more/?offset=10"
        hx-target="#reports-list"
        hx-swap="beforeend">

<!-- 6. Form Submission in Modal -->
<form hx-post="/reports/123/share/"
      hx-target="#result-container"
      hx-swap="innerHTML">

<!-- 7. Auto-refresh after Action (via htmx trigger) -->
<script>
    setTimeout(function() {
        htmx.trigger(document.getElementById('reports-list'), 'refresh');
    }, 1500);
</script>
```

### CSRF Token Configuration

Ensure HTMX sends CSRF token with requests:

```html
<!-- In base template -->
<script>
    document.body.addEventListener('htmx:configRequest', function(event) {
        event.detail.headers['X-CSRFToken'] = '{{ csrf_token }}';
    });
</script>
```

---

## Customization Guide

### Adding New Report Types

1. **Add to REPORT_TYPE_CHOICES in model:**
```python
REPORT_TYPE_CHOICES = [
    # ... existing types
    ('inventory_status', 'Inventory Status'),
]
```

2. **Add generator method in view:**
```python
def _generate_inventory_status(self, date_from, date_to):
    return {
        'total_items': Inventory.objects.count(),
        'low_stock': Inventory.objects.filter(quantity__lt=F('reorder_point')).count(),
        # ... more data
    }
```

3. **Add to generators dict:**
```python
generators = {
    # ... existing
    'inventory_status': self._generate_inventory_status,
}
```

4. **Add template card:**
```html
<div hx-post="{% url 'reports:report_generate' %}"
     hx-vals='{"report_type": "inventory_status"}'>
    <i class="fas fa-boxes"></i>
    Inventory Status
</div>
```

### Customizing PDF Styling

Modify `_create_styled_table()` in views:

```python
# Change header color
('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#your-color')),

# Change font
('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),

# Add borders
('BOX', (0, 0), (-1, -1), 2, colors.black),
```

### Adding Email Notifications

```python
from django.core.mail import send_mail

def send_report_notification(report, recipients):
    send_mail(
        subject=f'Report Ready: {report.name}',
        message=f'Your report is ready for download.',
        from_email='reports@yourapp.com',
        recipient_list=recipients,
        html_message=f'''
            <h2>{report.name}</h2>
            <p>Your report has been generated.</p>
            <a href="{report.get_absolute_url()}">View Report</a>
        '''
    )
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| HTMX requests return 403 | Add CSRF token to HTMX config |
| Modal doesn't close | Check onclick handler on backdrop |
| Reports not generating | Check database queries in generators |
| PDF generation fails | Ensure reportlab is installed |
| Scheduled reports not running | Check Celery Beat is running |

### Debug Mode

Add to views for debugging:

```python
import logging
logger = logging.getLogger(__name__)

def post(self, request):
    logger.debug(f"Generating report: {request.POST}")
    # ... rest of code
```

---

## Replication Checklist

Use this checklist when implementing in a new project:

### Database
- [ ] Create Report model with all CHOICES
- [ ] Add indexes for organization, status, dates
- [ ] Run migrations
- [ ] (Optional) Add DashboardMetric, Alert models

### Views
- [ ] Create ReportGenerateView with domain-specific generators
- [ ] Create ReportDownloadView (CSV + PDF)
- [ ] Create ReportsRefreshView, ReportsFilterView, ReportsMoreView
- [ ] Create ReportPreviewView, ReportDeleteView, ReportShareView
- [ ] Create ReportScheduleView, ReportScheduleDeleteView, ReportScheduleNewView
- [ ] Create ReportBuilderView
- [ ] Customize OrganizationMixin for your auth setup

### URLs
- [ ] Add 15+ URL patterns with uuid:pk
- [ ] Include in main urls.py
- [ ] (Optional) Add DRF router for API

### Templates
- [ ] Create main reports.html tab template
- [ ] Create recent_reports_list.html partial
- [ ] Create report_preview_modal.html
- [ ] Create report_share_modal.html
- [ ] Create report_schedule_modal.html
- [ ] Create schedule_new_modal.html
- [ ] Create report_builder_modal.html
- [ ] Create small response partials (success/error messages)
- [ ] Add modal container div in base template

### Frontend
- [ ] Include HTMX library
- [ ] Include Tailwind CSS
- [ ] Include Font Awesome
- [ ] Configure CSRF token for HTMX
- [ ] Add custom btn classes (btn, btn-primary, btn-secondary)
- [ ] Add form-input, form-select classes

### Dependencies
- [ ] Add reportlab to requirements.txt
- [ ] (Optional) Add celery for scheduled reports
- [ ] (Optional) Add djangorestframework for API

### Testing
- [ ] Test report generation for each type
- [ ] Test CSV/PDF download
- [ ] Test modal open/close
- [ ] Test share functionality
- [ ] Test schedule create/update/delete
- [ ] Test custom report builder
- [ ] Test pagination (load more)

---

## Security Note

This module uses HTMX which updates the DOM via server-rendered HTML. Key security considerations:

1. **CSRF Protection**: Always include CSRF tokens in HTMX requests
2. **Server-side Validation**: All data is validated server-side before rendering
3. **User Authorization**: Views check user ownership before allowing actions
4. **Escaped Output**: Django templates auto-escape content by default

---

## File Summary

| File | Lines | Purpose |
|------|-------|---------|
| models.py | ~200 | Report model with all fields |
| views.py | ~500 | 15+ view classes |
| urls.py | ~30 | URL routing |
| serializers.py | ~40 | DRF serializers (optional) |
| tasks.py | ~60 | Celery tasks (optional) |
| reports.html | ~150 | Main template |
| recent_reports_list.html | ~100 | Reports list partial |
| Modal templates | ~400 | 5 modal templates |
| Response partials | ~50 | Small HTML responses |

**Total: ~1,500 lines of code**

---

## License

This documentation and associated code patterns are provided for replication and adaptation in your Django projects.

---

*Generated from Versatex Pricing Agent - January 2026*
