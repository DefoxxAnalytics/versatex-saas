# Procure-to-Pay (P2P) Analytics Suite - Implementation Plan

## Overview

Extend Versatex Analytics with comprehensive PO, PR, and Invoice analysis pages to support full Procure-to-Pay (P2P) cycle analytics when the new comprehensive dataset arrives.

**Priority Focus Areas** (per user):
1. P2P Cycle Times - End-to-end process duration analysis
2. 3-Way Matching - PO vs Receipt vs Invoice discrepancy detection
3. Invoice Aging/AP - Payment terms compliance, cash flow optimization

**Scope**: Full P2P Suite with 6+ new analysis pages

---

## Table of Contents

1. [Phase 1: Data Model Extensions](#phase-1-data-model-extensions)
2. [Phase 2: Backend Analytics Services](#phase-2-backend-analytics-services)
3. [Phase 3: Frontend Pages](#phase-3-new-frontend-pages-6-pages)
4. [Phase 4: API Endpoints](#phase-4-api-endpoints)
5. [Phase 5: Frontend Hooks & Types](#phase-5-frontend-hooks--types)
6. [Phase 6: Data Import Support](#phase-6-data-import-support)
7. [Phase 7: Reports Integration](#phase-7-reports-integration)
8. [Phase 8: Access Control](#phase-8-access-control)
9. [Implementation Sequence](#implementation-sequence)
10. [Files to Create/Modify](#files-to-createmodify)
11. [Success Metrics](#success-metrics)

---

## Phase 1: Data Model Extensions

### New Models Required

#### 1. PurchaseRequisition Model

```python
# backend/apps/procurement/models.py

class PurchaseRequisition(models.Model):
    """Purchase Requisition - initial request for goods/services"""

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

    # Identity
    organization = models.ForeignKey('authentication.Organization', on_delete=models.CASCADE)
    pr_number = models.CharField(max_length=50)

    # Request details
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='requisitions')
    department = models.CharField(max_length=100, blank=True)
    cost_center = models.CharField(max_length=50, blank=True)

    # Content
    supplier_suggested = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True)
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
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_requisitions')
    rejection_reason = models.TextField(blank=True)

    # Linkage
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.SET_NULL, null=True, blank=True, related_name='requisitions')

    # Metadata
    upload_batch = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['organization', 'pr_number']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'created_date']),
            models.Index(fields=['organization', 'department']),
        ]
```

#### 2. PurchaseOrder Model

```python
class PurchaseOrder(models.Model):
    """Purchase Order - formal commitment to supplier"""

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

    # Identity
    organization = models.ForeignKey('authentication.Organization', on_delete=models.CASCADE)
    po_number = models.CharField(max_length=50)

    # Supplier
    supplier = models.ForeignKey('Supplier', on_delete=models.CASCADE)

    # Financial
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    freight_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Contract linkage
    contract = models.ForeignKey('Contract', on_delete=models.SET_NULL, null=True, blank=True)
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
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_pos')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_pos')

    # Amendment tracking
    original_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    amendment_count = models.PositiveIntegerField(default=0)

    # Metadata
    upload_batch = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['organization', 'po_number']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'supplier']),
            models.Index(fields=['organization', 'created_date']),
        ]
```

#### 3. GoodsReceipt Model (for 3-Way Matching)

```python
class GoodsReceipt(models.Model):
    """Goods Receipt - confirmation of delivery"""

    STATUS_CHOICES = [
        ('pending', 'Pending Inspection'),
        ('accepted', 'Accepted'),
        ('partial_accept', 'Partially Accepted'),
        ('rejected', 'Rejected'),
    ]

    # Identity
    organization = models.ForeignKey('authentication.Organization', on_delete=models.CASCADE)
    gr_number = models.CharField(max_length=50)

    # Linkage
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='goods_receipts')

    # Receipt details
    received_date = models.DateField()
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # Quantities (for variance analysis)
    quantity_ordered = models.DecimalField(max_digits=15, decimal_places=2)
    quantity_received = models.DecimalField(max_digits=15, decimal_places=2)
    quantity_accepted = models.DecimalField(max_digits=15, decimal_places=2, null=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    inspection_notes = models.TextField(blank=True)

    # Metadata
    upload_batch = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['organization', 'gr_number']
```

#### 4. Invoice Model (Enhanced)

```python
class Invoice(models.Model):
    """Supplier Invoice - billing document"""

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

    # Identity
    organization = models.ForeignKey('authentication.Organization', on_delete=models.CASCADE)
    invoice_number = models.CharField(max_length=100)
    supplier = models.ForeignKey('Supplier', on_delete=models.CASCADE)

    # Linkage (for 3-way match)
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.SET_NULL, null=True, blank=True)
    goods_receipt = models.ForeignKey('GoodsReceipt', on_delete=models.SET_NULL, null=True, blank=True)

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

    # Hold tracking
    hold_reason = models.TextField(blank=True)

    # Metadata
    upload_batch = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['organization', 'invoice_number', 'supplier']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'match_status']),
            models.Index(fields=['organization', 'due_date']),
            models.Index(fields=['organization', 'supplier']),
        ]
```

---

## Phase 2: Backend Analytics Services

### New Service: P2PAnalyticsService

**File**: `backend/apps/analytics/p2p_services.py`

```python
class P2PAnalyticsService:
    """
    Analytics service for Procure-to-Pay process metrics.
    Handles PR, PO, GR, and Invoice analysis.
    """

    def __init__(self, organization, filters=None):
        self.organization = organization
        self.filters = filters or {}

    # ============ P2P CYCLE TIME ANALYSIS ============

    def get_p2p_cycle_overview(self):
        """
        Get end-to-end P2P cycle time metrics.
        Returns average days for each stage.
        """
        # PR to PO conversion time
        # PO to GR receipt time
        # GR to Invoice time
        # Invoice to Payment time
        # Total P2P cycle time

    def get_cycle_time_by_category(self):
        """Cycle times broken down by spend category."""

    def get_cycle_time_by_supplier(self):
        """Cycle times broken down by supplier."""

    def get_cycle_time_trends(self, months=12):
        """Monthly trend of cycle times."""

    def get_bottleneck_analysis(self):
        """Identify where delays occur in the P2P process."""

    # ============ 3-WAY MATCHING ANALYSIS ============

    def get_matching_overview(self):
        """
        Get 3-way match rates and exception metrics.
        """
        # Total invoices
        # 3-way matched %
        # 2-way matched %
        # Exception rate
        # Exception amount

    def get_exceptions_by_type(self):
        """Breakdown of exceptions by type."""

    def get_exceptions_by_supplier(self):
        """Which suppliers have most exceptions."""

    def get_price_variance_analysis(self):
        """PO price vs Invoice price variances."""

    def get_quantity_variance_analysis(self):
        """PO qty vs GR qty vs Invoice qty variances."""

    # ============ INVOICE AGING / AP ANALYSIS ============

    def get_aging_overview(self):
        """
        Invoice aging buckets: Current, 1-30, 31-60, 61-90, 90+
        """

    def get_aging_by_supplier(self):
        """Aging breakdown by supplier."""

    def get_payment_terms_compliance(self):
        """
        On-time vs late payment rates.
        Early payment discount capture rate.
        """

    def get_days_payable_outstanding(self):
        """Average DPO calculation."""

    def get_cash_flow_forecast(self):
        """Projected payments by week/month."""

    # ============ PR ANALYSIS ============

    def get_pr_overview(self):
        """PR metrics: volume, conversion rate, rejection rate."""

    def get_pr_approval_analysis(self):
        """Approval bottlenecks, average approval time."""

    def get_pr_by_department(self):
        """Requisition patterns by department."""

    # ============ PO ANALYSIS ============

    def get_po_overview(self):
        """PO metrics: volume, value, contract coverage."""

    def get_po_leakage_analysis(self):
        """Off-contract PO identification."""

    def get_po_amendment_analysis(self):
        """PO change order patterns."""
```

---

## Phase 3: New Frontend Pages (6 Pages)

### Page 1: P2P Cycle Dashboard (`/p2p-cycle`)

**Purpose**: End-to-end process visibility and cycle time analysis

**Layout**:
```
┌──────────────────────────────────────────────────────────────────┐
│ 🔄 Procure-to-Pay Cycle Analysis                                 │
├──────────────────────────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │
│ │ PR→PO   │ │ PO→GR   │ │ GR→INV  │ │ INV→PAY │ │ TOTAL   │     │
│ │ 3.2 days│ │ 8.1 days│ │ 2.4 days│ │ 12.5 days│ │ 26.2 days│    │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘     │
├──────────────────────────────────────────────────────────────────┤
│ [PROCESS FUNNEL CHART - Sankey Diagram]                          │
│                                                                  │
│ PRs Created → Approved → Converted to PO → Received → Paid       │
│     1,250   →   1,180  →      1,050     →    980    →  920       │
├──────────────────────────────────────────────────────────────────┤
│ [CYCLE TIME TREND - Line Chart]                                  │
│ Monthly average cycle times over past 12 months                  │
├──────────────────────────────────────────────────────────────────┤
│ [BOTTLENECK TABLE]                                               │
│ Stage           │ Avg Days │ Target │ Variance │ Status          │
│ PR Approval     │   2.1    │  1.0   │  +110%   │ 🔴 Critical     │
│ PO Processing   │   1.1    │  1.0   │   +10%   │ 🟢 On Track     │
└──────────────────────────────────────────────────────────────────┘
```

**Key Features**:
- Process stage KPI cards with targets
- Sankey diagram showing document flow
- Cycle time trend analysis
- Bottleneck identification with drill-downs
- Category/Supplier cycle time comparison

**Drill-downs**:
- Click stage → Show top 10 slowest items in that stage
- Click supplier → Show supplier-specific cycle times

---

### Page 2: 3-Way Match Center (`/matching`)

**Purpose**: Invoice matching analysis and exception management

**Layout**:
```
┌──────────────────────────────────────────────────────────────────┐
│ ⚖️ 3-Way Match Analysis                                          │
├──────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ MATCH RATE  │ │ EXCEPTIONS  │ │ EXCEPTION $ │ │ AVG RESOLVE │ │
│ │   78.5%     │ │    215      │ │   $847K     │ │   4.2 days  │ │
│ │ 3-way match │ │ open items  │ │ at risk     │ │ resolution  │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│ [MATCH STATUS DONUT]          │ [EXCEPTION BY TYPE BAR]          │
│                               │                                  │
│   ■ 3-Way: 78.5%              │   Price Variance:     85 ($320K) │
│   ■ 2-Way: 12.3%              │   Quantity Variance:  62 ($180K) │
│   ■ Exception: 9.2%           │   No PO:              38 ($220K) │
│                               │   Duplicate:          18 ($95K)  │
│                               │   Missing GR:         12 ($32K)  │
├──────────────────────────────────────────────────────────────────┤
│ [EXCEPTION TABLE - Sortable, Filterable]                         │
│ Invoice #  │ Supplier      │ Type      │ Amount  │ Age  │ Action │
│ INV-2024-1 │ Acme Corp     │ Price Var │ $2,450  │ 5d   │ [View] │
│ INV-2024-2 │ Beta Inc      │ No PO     │ $8,900  │ 3d   │ [View] │
└──────────────────────────────────────────────────────────────────┘
```

**Key Features**:
- Match rate metrics by volume and value
- Exception breakdown by type
- Supplier exception scorecards
- Exception resolution workflow
- Price/Quantity variance drill-downs

**Drill-downs**:
- Click exception type → Show all invoices with that exception
- Click supplier → Show supplier matching performance

---

### Page 3: Invoice Aging & AP Dashboard (`/invoice-aging`)

**Purpose**: Accounts Payable aging and payment analysis

**Layout**:
```
┌──────────────────────────────────────────────────────────────────┐
│ 💰 Invoice Aging & Accounts Payable                              │
├──────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ TOTAL AP    │ │ OVERDUE     │ │ DPO         │ │ ON-TIME %   │ │
│ │   $2.4M     │ │   $485K     │ │  42 days    │ │   72.5%     │ │
│ │ outstanding │ │ past due    │ │ avg payable │ │ payments    │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│ [AGING BUCKETS - Stacked Bar]                                    │
│                                                                  │
│   Current (0-30):  $1.2M  ████████████████                       │
│   31-60 days:      $420K  ███████                                │
│   61-90 days:      $295K  █████                                  │
│   90+ days:        $485K  ████████ (!)                           │
├──────────────────────────────────────────────────────────────────┤
│ [TOP AGED SUPPLIERS]          │ [PAYMENT FORECAST]               │
│                               │                                  │
│ 1. Acme Corp     $180K (95d)  │ This Week:   $420K               │
│ 2. Beta Inc      $145K (72d)  │ Next Week:   $380K               │
│ 3. Gamma LLC     $98K  (65d)  │ Week 3:      $290K               │
│ 4. Delta Co      $62K  (48d)  │ Week 4:      $510K               │
├──────────────────────────────────────────────────────────────────┤
│ [PAYMENT TERMS COMPLIANCE]                                       │
│ Net 30:  85% on-time │ Net 45:  78% on-time │ Net 60:  92%      │
└──────────────────────────────────────────────────────────────────┘
```

**Key Features**:
- AP balance by aging bucket
- Days Payable Outstanding (DPO) trends
- Payment terms compliance rates
- Early payment discount capture analysis
- Cash flow forecast
- Top aged invoices with action buttons

**Drill-downs**:
- Click aging bucket → Show all invoices in that bucket
- Click supplier → Show supplier payment history

---

### Page 4: Purchase Requisition Analysis (`/requisitions`)

**Purpose**: Requisition patterns, approval efficiency, and conversion rates

**Layout**:
```
┌──────────────────────────────────────────────────────────────────┐
│ 📋 Purchase Requisition Analysis                                 │
├──────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ TOTAL PRs   │ │ CONVERSION  │ │ AVG APPROVAL│ │ REJECTION   │ │
│ │    1,250    │ │   84.0%     │ │   2.1 days  │ │   5.6%      │ │
│ │ this period │ │ PR → PO     │ │ time        │ │ rate        │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│ [PR STATUS FUNNEL]              │ [PR BY DEPARTMENT PIE]         │
│                                 │                                │
│ Created:    1,250 ████████████  │   Operations:  45%             │
│ Submitted:  1,220 ███████████   │   IT:          25%             │
│ Approved:   1,180 ██████████    │   Marketing:   15%             │
│ Converted:  1,050 █████████     │   HR:          10%             │
│ Rejected:      70 █             │   Other:        5%             │
├──────────────────────────────────────────────────────────────────┤
│ [APPROVAL TIME DISTRIBUTION]                                     │
│ <1 day: 35% │ 1-2 days: 40% │ 2-5 days: 18% │ >5 days: 7%       │
├──────────────────────────────────────────────────────────────────┤
│ [PENDING APPROVAL TABLE]                                         │
│ PR #     │ Requestor  │ Amount   │ Days Pending │ Approver       │
│ PR-1234  │ John Smith │ $15,000  │ 5 days       │ Jane Doe       │
└──────────────────────────────────────────────────────────────────┘
```

**Key Features**:
- PR volume and conversion metrics
- Approval time analysis with targets
- Department-level requisition patterns
- Rejection analysis with reasons
- Pending approvals (aged items)
- Requestor compliance scoring

---

### Page 5: Purchase Order Analysis (`/purchase-orders`)

**Purpose**: PO management, contract coverage, and amendment tracking

**Layout**:
```
┌──────────────────────────────────────────────────────────────────┐
│ 📦 Purchase Order Analysis                                       │
├──────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ TOTAL POs   │ │ PO VALUE    │ │ CONTRACT %  │ │ AMENDMENTS  │ │
│ │    850      │ │   $12.5M    │ │   72.3%     │ │   12.5%     │ │
│ │ this period │ │ committed   │ │ on-contract │ │ changed POs │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│ [PO STATUS BREAKDOWN]           │ [CONTRACT vs MAVERICK PIE]     │
│                                 │                                │
│ Approved:      425  █████████   │   On Contract:   72.3%         │
│ Sent:          280  ██████      │   Preferred:     15.2%         │
│ Received:      95   ██          │   Maverick:      12.5%         │
│ Closed:        50   █           │                                │
├──────────────────────────────────────────────────────────────────┤
│ [PO LEAKAGE BY CATEGORY]                                         │
│ IT Services:      $420K maverick (25% of category)               │
│ Office Supplies:  $180K maverick (35% of category) ⚠️            │
│ Professional Svc: $95K  maverick (8% of category)                │
├──────────────────────────────────────────────────────────────────┤
│ [AMENDMENT ANALYSIS]                                             │
│ Avg amendments per PO: 0.3 │ Avg value change: +8.5%             │
│ Top reasons: Scope change (45%), Price adjustment (30%)          │
└──────────────────────────────────────────────────────────────────┘
```

**Key Features**:
- PO volume and value metrics
- Contract coverage analysis
- Maverick PO identification (PO Leakage)
- Amendment/change order tracking
- Supplier PO concentration
- Open PO aging

---

### Page 6: Supplier Payment Performance (`/supplier-payments`)

**Purpose**: Supplier-centric view of payment and P2P metrics

**Layout**:
```
┌──────────────────────────────────────────────────────────────────┐
│ 🏢 Supplier Payment Performance                                  │
├──────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ SUPPLIERS   │ │ ON-TIME %   │ │ AVG DPO     │ │ EXCEPTIONS  │ │
│ │    145      │ │   76.2%     │ │  38 days    │ │   8.5%      │ │
│ │ with AP     │ │ payment     │ │ by supplier │ │ rate        │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│ [SUPPLIER PERFORMANCE TABLE - Click for Drill-down]              │
│ Supplier      │ AP Balance │ DPO  │ On-Time │ Exceptions │ Score │
│ Acme Corp     │ $245K      │ 52d  │ 65%     │ 15%        │ 62/100│
│ Beta Inc      │ $180K      │ 35d  │ 88%     │ 5%         │ 85/100│
│ Gamma LLC     │ $156K      │ 41d  │ 72%     │ 12%        │ 71/100│
├──────────────────────────────────────────────────────────────────┤
│ [SUPPLIER DRILL-DOWN MODAL]                                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Acme Corp - Payment History                                 │ │
│ │                                                             │ │
│ │ Total Invoices: 45  │  Avg Payment: $5,444  │  DPO: 52d    │ │
│ │                                                             │ │
│ │ [Payment Timeline Chart]                                    │ │
│ │ [Exception Breakdown]                                       │ │
│ │ [Recent Invoices Table]                                     │ │
│ └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

**Key Features**:
- Supplier payment scorecard
- DPO by supplier comparison
- Exception rates by supplier
- Payment history visualization
- Supplier risk indicators
- Strategic supplier prioritization

---

## Phase 4: API Endpoints

### New Endpoints

```
# P2P Cycle Analysis
GET /api/v1/analytics/p2p/cycle-overview/
GET /api/v1/analytics/p2p/cycle-by-category/
GET /api/v1/analytics/p2p/cycle-by-supplier/
GET /api/v1/analytics/p2p/cycle-trends/?months=12
GET /api/v1/analytics/p2p/bottlenecks/
GET /api/v1/analytics/p2p/stage-drilldown/<stage>/

# 3-Way Matching
GET /api/v1/analytics/matching/overview/
GET /api/v1/analytics/matching/exceptions/
GET /api/v1/analytics/matching/exceptions-by-type/
GET /api/v1/analytics/matching/exceptions-by-supplier/
GET /api/v1/analytics/matching/price-variance/
GET /api/v1/analytics/matching/quantity-variance/
GET /api/v1/analytics/matching/invoice/<int:invoice_id>/

# Invoice Aging
GET /api/v1/analytics/aging/overview/
GET /api/v1/analytics/aging/buckets/
GET /api/v1/analytics/aging/by-supplier/
GET /api/v1/analytics/aging/payment-terms-compliance/
GET /api/v1/analytics/aging/dpo-trends/?months=12
GET /api/v1/analytics/aging/cash-forecast/?weeks=4

# Purchase Requisitions
GET /api/v1/analytics/requisitions/overview/
GET /api/v1/analytics/requisitions/approval-analysis/
GET /api/v1/analytics/requisitions/by-department/
GET /api/v1/analytics/requisitions/pending/
GET /api/v1/analytics/requisitions/<int:pr_id>/

# Purchase Orders
GET /api/v1/analytics/purchase-orders/overview/
GET /api/v1/analytics/purchase-orders/leakage/
GET /api/v1/analytics/purchase-orders/amendments/
GET /api/v1/analytics/purchase-orders/by-supplier/
GET /api/v1/analytics/purchase-orders/<int:po_id>/

# Supplier Payments
GET /api/v1/analytics/supplier-payments/overview/
GET /api/v1/analytics/supplier-payments/scorecard/
GET /api/v1/analytics/supplier-payments/<int:supplier_id>/
GET /api/v1/analytics/supplier-payments/<int:supplier_id>/history/
```

---

## Phase 5: Frontend Hooks & Types

### New Hooks (`frontend/src/hooks/useP2PAnalytics.ts`)

```typescript
// P2P Cycle
export function useP2PCycleOverview()
export function useP2PCycleByCategory()
export function useP2PCycleBySupplier()
export function useP2PCycleTrends(months: number)
export function useP2PBottlenecks()
export function useP2PStageDrilldown(stage: string | null)

// 3-Way Matching
export function useMatchingOverview()
export function useMatchingExceptions(params: ExceptionFilters)
export function useMatchingExceptionsByType()
export function useMatchingExceptionsBySupplier()
export function usePriceVarianceAnalysis()
export function useQuantityVarianceAnalysis()
export function useInvoiceMatchDetail(invoiceId: number | null)

// Invoice Aging
export function useAgingOverview()
export function useAgingBuckets()
export function useAgingBySupplier()
export function usePaymentTermsCompliance()
export function useDPOTrends(months: number)
export function useCashForecast(weeks: number)

// Requisitions
export function usePROverview()
export function usePRApprovalAnalysis()
export function usePRByDepartment()
export function usePRPending()
export function usePRDetail(prId: number | null)

// Purchase Orders
export function usePOOverview()
export function usePOLeakage()
export function usePOAmendments()
export function usePOBySupplier()
export function usePODetail(poId: number | null)

// Supplier Payments
export function useSupplierPaymentsOverview()
export function useSupplierPaymentsScorecard()
export function useSupplierPaymentDetail(supplierId: number | null)
export function useSupplierPaymentHistory(supplierId: number | null)
```

---

## Phase 6: Data Import Support

### CSV Import Templates

Create CSV templates for each new document type:

1. **purchase_requisitions.csv**
   - Required: pr_number, created_date, estimated_amount
   - Optional: supplier, category, department, status, approval_date

2. **purchase_orders.csv**
   - Required: po_number, supplier, created_date, total_amount
   - Optional: contract, status, approval_date, required_date

3. **goods_receipts.csv**
   - Required: gr_number, po_number, received_date, quantity_received
   - Optional: quantity_ordered, status

4. **invoices.csv**
   - Required: invoice_number, supplier, invoice_date, due_date, invoice_amount
   - Optional: po_number, paid_date, payment_terms, status

### Import Service Extensions

Extend existing `DataUploadService` to handle:
- PR/PO/GR/Invoice file detection
- Cross-reference validation (PR→PO→GR→Invoice linkage)
- Auto-matching where PO numbers match
- Exception flagging during import

---

## Phase 7: Reports Integration

### New Report Types

Add to existing Reports module:

1. **P2P Cycle Report** - End-to-end process metrics
2. **Invoice Exception Report** - All open exceptions
3. **AP Aging Report** - Detailed aging analysis
4. **PO Leakage Report** - Off-contract spending
5. **Supplier Payment Scorecard** - Supplier performance summary

---

## Phase 8: Access Control

The P2P Analytics Suite integrates with the existing role-based access control (RBAC) system.

### Existing Roles

```python
# backend/apps/authentication/models.py
ROLE_CHOICES = [
    ('admin', 'Administrator'),
    ('manager', 'Manager'),
    ('viewer', 'Viewer'),
]
```

### Page-Level Access Matrix

| Page | Viewer | Manager | Admin |
|------|--------|---------|-------|
| P2P Cycle Dashboard | View | View | Full |
| 3-Way Match Center | View | Resolve Exceptions | Full |
| Invoice Aging | View | View | Full + Forecasts |
| Requisitions | View Own | View All | Full |
| Purchase Orders | View | Approve | Full |
| Supplier Payments | Hidden | View | Full |

### Backend Permission Classes

Create custom permission classes for P2P endpoints:

```python
# backend/apps/analytics/permissions.py

from rest_framework.permissions import BasePermission

class HasP2PAccess(BasePermission):
    """Check if organization has P2P module enabled."""
    def has_permission(self, request, view):
        org = request.user.profile.organization
        return getattr(org, 'p2p_module_enabled', True)

class CanResolveExceptions(BasePermission):
    """Only managers+ can resolve invoice exceptions."""
    def has_permission(self, request, view):
        return request.user.profile.role in ['admin', 'manager']

class CanViewPaymentData(BasePermission):
    """Only admins can view sensitive payment data."""
    def has_permission(self, request, view):
        return request.user.profile.role == 'admin'

class CanApprovePO(BasePermission):
    """Only managers+ can approve purchase orders."""
    def has_permission(self, request, view):
        return request.user.profile.role in ['admin', 'manager']
```

### API Endpoint Permissions

```python
# backend/apps/analytics/p2p_views.py

class P2PCycleOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasP2PAccess]

class MatchingExceptionsView(APIView):
    permission_classes = [IsAuthenticated, HasP2PAccess]

class ResolveExceptionView(APIView):
    permission_classes = [IsAuthenticated, HasP2PAccess, CanResolveExceptions]

class InvoiceAgingView(APIView):
    permission_classes = [IsAuthenticated, HasP2PAccess]

class PaymentForecastView(APIView):
    permission_classes = [IsAuthenticated, HasP2PAccess, CanViewPaymentData]

class SupplierPaymentsView(APIView):
    permission_classes = [IsAuthenticated, HasP2PAccess, CanViewPaymentData]

class ApprovePOView(APIView):
    permission_classes = [IsAuthenticated, HasP2PAccess, CanApprovePO]
```

### Frontend Route Protection

```typescript
// frontend/src/App.tsx

// P2P Routes with role-based access
<Route path="/p2p-cycle">
  <ProtectedRoute>
    <P2PCyclePage />
  </ProtectedRoute>
</Route>

<Route path="/matching">
  <ProtectedRoute>
    <MatchCenterPage />
  </ProtectedRoute>
</Route>

<Route path="/supplier-payments">
  <ProtectedRoute requiredRole="admin">
    <SupplierPaymentsPage />
  </ProtectedRoute>
</Route>
```

### Component-Level Permissions

```typescript
// frontend/src/pages/MatchCenter.tsx

import { PermissionGate } from '@/components/PermissionGate';

// Only managers+ can see the resolve button
<PermissionGate requiredRole="manager">
  <Button onClick={handleResolveException}>
    Resolve Exception
  </Button>
</PermissionGate>

// Only admins can see payment amounts
<PermissionGate requiredRole="admin">
  <PaymentAmountColumn />
</PermissionGate>
```

### Navigation Visibility

```typescript
// frontend/src/components/DashboardLayout.tsx

const P2P_NAV_ITEMS = [
  { path: '/p2p-cycle', label: 'P2P Cycle', icon: RefreshCw, minRole: 'viewer' },
  { path: '/matching', label: '3-Way Matching', icon: Scale, minRole: 'viewer' },
  { path: '/invoice-aging', label: 'Invoice Aging', icon: Clock, minRole: 'viewer' },
  { path: '/requisitions', label: 'Requisitions', icon: ClipboardList, minRole: 'viewer' },
  { path: '/purchase-orders', label: 'Purchase Orders', icon: Package, minRole: 'viewer' },
  { path: '/supplier-payments', label: 'Supplier Payments', icon: Building2, minRole: 'admin' },
];

// Filter nav items based on user role
const visibleNavItems = P2P_NAV_ITEMS.filter(item =>
  hasMinimumRole(user.profile.role, item.minRole)
);
```

### Organization Feature Flag (Optional)

Add P2P module toggle to Organization model:

```python
# backend/apps/authentication/models.py

class Organization(models.Model):
    # ... existing fields ...

    # Feature flags
    p2p_module_enabled = models.BooleanField(
        default=False,
        help_text='Enable Procure-to-Pay analytics module'
    )
```

### Audit Logging

All P2P actions are logged via the existing `AuditLog` model:

```python
# Add to ALLOWED_DETAIL_KEYS in AuditLog model
ALLOWED_DETAIL_KEYS = {
    # ... existing keys ...
    # P2P Analytics keys
    'pr_id', 'po_id', 'invoice_id', 'gr_id',
    'exception_type', 'resolution_notes',
    'approval_action', 'amount_approved',
}
```

---

## Implementation Sequence

### Milestone 1: Data Foundation
- [ ] Create new Django models (PR, PO, GR, Invoice)
- [ ] Create and run migrations
- [ ] Update admin.py for new models
- [ ] Create CSV import templates and update DataUploadService
- [ ] Add serializers for new models

### Milestone 2: P2P Analytics Service
- [ ] Create P2PAnalyticsService class
- [ ] Implement cycle time calculations
- [ ] Implement 3-way matching logic
- [ ] Implement aging calculations
- [ ] Add API endpoints for new analytics
- [ ] Add to urls.py

### Milestone 3: Frontend - Page 1 & 2
- [ ] Create TypeScript types in api.ts
- [ ] Create useP2PAnalytics.ts hooks
- [ ] Build P2P Cycle Dashboard page
- [ ] Build 3-Way Match Center page
- [ ] Add pages to navigation

### Milestone 4: Frontend - Page 3 & 4
- [ ] Build Invoice Aging Dashboard page
- [ ] Build Purchase Requisition Analysis page
- [ ] Implement drill-down modals
- [ ] Add filtering capabilities

### Milestone 5: Frontend - Page 5 & 6
- [ ] Build Purchase Order Analysis page
- [ ] Build Supplier Payment Performance page
- [ ] Implement all drill-down modals
- [ ] Polish UI and dark mode

### Milestone 6: Reports & Testing
- [ ] Add new report generators
- [ ] Update report templates
- [ ] Write backend tests
- [ ] Write frontend tests
- [ ] Documentation updates

---

## Files to Create/Modify

### Backend (New Files)
| File | Description |
|------|-------------|
| `backend/apps/procurement/models.py` | Add PR, PO, GR, Invoice models |
| `backend/apps/analytics/p2p_services.py` | New P2P analytics service |
| `backend/apps/analytics/p2p_views.py` | New API views |
| `backend/apps/analytics/p2p_urls.py` | New URL patterns |
| `backend/apps/procurement/serializers.py` | Update for new models |
| `backend/apps/reports/generators/p2p_*.py` | New report generators |

### Backend (Modify)
| File | Changes |
|------|---------|
| `backend/apps/analytics/urls.py` | Include p2p_urls |
| `backend/apps/procurement/admin.py` | Register new models |
| `backend/apps/procurement/services.py` | Extend import service |

### Frontend (New Files)
| File | Description |
|------|-------------|
| `frontend/src/hooks/useP2PAnalytics.ts` | New hooks |
| `frontend/src/pages/P2PCycle.tsx` | Page 1 |
| `frontend/src/pages/MatchCenter.tsx` | Page 2 |
| `frontend/src/pages/InvoiceAging.tsx` | Page 3 |
| `frontend/src/pages/Requisitions.tsx` | Page 4 |
| `frontend/src/pages/PurchaseOrders.tsx` | Page 5 |
| `frontend/src/pages/SupplierPayments.tsx` | Page 6 |

### Frontend (Modify)
| File | Changes |
|------|---------|
| `frontend/src/lib/api.ts` | Add types and API methods |
| `frontend/src/components/DashboardLayout.tsx` | Add nav items |
| `frontend/src/App.tsx` | Add routes |

---

## Success Metrics

After implementation, the platform should enable:

| Metric | Target |
|--------|--------|
| **P2P Visibility** | Track any document from requisition to payment |
| **Cycle Time Reduction** | Identify and resolve bottlenecks |
| **Exception Reduction** | Target <10% invoice exception rate |
| **Payment Optimization** | Maintain healthy DPO while capturing discounts |
| **Compliance** | >80% on-contract purchasing |
| **Cash Management** | Accurate payment forecasting |

---

## Notes

- All new models follow the existing multi-tenancy pattern with `organization` FK
- Reuse existing UI patterns (KPI cards, data tables, drill-down modals)
- Follow existing hook patterns from `useAnalytics.ts`
- Charts will use ECharts (already integrated)
- All pages support dark mode via existing theme system
