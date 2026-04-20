# P2P Analytics Module - User Guide

This guide covers how to use the Procure-to-Pay (P2P) Analytics module in Versatex Analytics.

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [P2P Dashboard Pages](#p2p-dashboard-pages)
   - [P2P Cycle Dashboard](#p2p-cycle-dashboard)
   - [3-Way Match Center](#3-way-match-center)
   - [Invoice Aging Dashboard](#invoice-aging-dashboard)
   - [Requisitions Analysis](#requisitions-analysis)
   - [Purchase Orders Analysis](#purchase-orders-analysis)
   - [Supplier Payments](#supplier-payments)
4. [Importing P2P Data](#importing-p2p-data)
   - [Admin CSV Import](#admin-csv-import)
   - [CSV Templates](#csv-templates)
5. [P2P Reports](#p2p-reports)
6. [Understanding Key Metrics](#understanding-key-metrics)
7. [Role-Based Access](#role-based-access)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The P2P Analytics module provides comprehensive visibility into your Procure-to-Pay process, from purchase requisitions through to supplier payments. It helps organizations:

- **Track cycle times** - Identify bottlenecks in PR-to-PO-to-Receipt-to-Payment workflow
- **Manage invoice matching** - Automated 3-way matching with exception handling
- **Monitor AP aging** - Track outstanding payables and optimize cash flow
- **Improve compliance** - Ensure contract coverage and policy adherence
- **Benchmark suppliers** - Score supplier payment performance

### Key Documents Tracked

| Document | Abbreviation | Description |
|----------|--------------|-------------|
| Purchase Requisition | PR | Initial request for goods/services |
| Purchase Order | PO | Formal commitment to supplier |
| Goods Receipt | GR | Confirmation of delivery |
| Invoice | INV | Supplier billing document |

---

## Getting Started

### Prerequisites

1. **User Account** - Active user with appropriate role (Viewer, Manager, or Admin)
2. **P2P Data** - P2P documents imported into the system (PRs, POs, GRs, Invoices)
3. **Organization** - User must be assigned to an organization

### Accessing P2P Analytics

Navigate to the P2P section in the sidebar menu:

```
Dashboard
├── Overview
├── Analytics
│   ├── Spend by Category
│   ├── Spend by Supplier
│   └── ...
├── P2P Analytics
│   ├── P2P Cycle          # End-to-end process visibility
│   ├── 3-Way Matching     # Invoice matching & exceptions
│   ├── Invoice Aging      # AP aging analysis
│   ├── Requisitions       # PR analysis
│   ├── Purchase Orders    # PO analysis
│   └── Supplier Payments  # Payment performance (Admin only)
└── Reports
```

---

## P2P Dashboard Pages

### P2P Cycle Dashboard

**Purpose**: End-to-end visibility of your P2P process with cycle time metrics.

**Key Metrics**:

| Metric | Description |
|--------|-------------|
| **PR → PO** | Average days from requisition creation to PO approval |
| **PO → GR** | Average days from PO sent to goods received |
| **GR → INV** | Average days from receipt to invoice received |
| **INV → PAY** | Average days from invoice to payment |
| **Total Cycle** | End-to-end average cycle time |

**Features**:

1. **Process Funnel** - Visual flow showing document counts at each stage
2. **Cycle Time Trends** - Monthly trend chart showing improvements/regressions
3. **Bottleneck Table** - Stages exceeding target times flagged in red
4. **Drill-downs** - Click any stage to see the 10 slowest items

**How to Use**:
- Review KPI cards to assess overall process health
- Click "View Details" on bottleneck stages to identify specific delays
- Use category/supplier filters to analyze specific spend areas
- Export data for reporting to stakeholders

---

### 3-Way Match Center

**Purpose**: Monitor invoice matching rates and manage exceptions.

**Understanding 3-Way Matching**:

```
PO Amount ($10,000) ←→ GR Amount ($10,000) ←→ Invoice Amount ($10,000)
         ✓ Match              ✓ Match              ✓ 3-Way Matched
```

**Key Metrics**:

| Metric | Description |
|--------|-------------|
| **Match Rate** | Percentage of invoices with successful 3-way match |
| **Exceptions** | Number of invoices requiring manual review |
| **Exception $** | Total dollar value at risk from unresolved exceptions |
| **Avg Resolve Time** | Average days to resolve exceptions |

**Exception Types**:

| Type | Description | Common Causes |
|------|-------------|---------------|
| **Price Variance** | Invoice price differs from PO | Price changes, surcharges |
| **Quantity Variance** | Received qty differs from ordered | Partial shipments, over/under delivery |
| **No PO** | Invoice received without matching PO | Maverick spending, emergency purchases |
| **Duplicate** | Potential duplicate invoice | Data entry error, resent invoice |
| **Missing GR** | Invoice exists but no goods receipt | Receiving delay, services |

**Resolving Exceptions** (Manager/Admin only):

1. Navigate to the exception table
2. Click "View" on the exception to review details
3. Review PO, GR, and Invoice side-by-side
4. Click "Resolve Exception"
5. Enter resolution notes explaining the action taken
6. Click "Submit"

**Bulk Resolution**:
1. Select multiple exceptions using checkboxes
2. Click "Resolve Selected"
3. Enter common resolution notes
4. Click "Submit"

---

### Invoice Aging Dashboard

**Purpose**: Track accounts payable aging and optimize payment timing.

**Aging Buckets**:

| Bucket | Description | Risk Level |
|--------|-------------|------------|
| **Current (0-30)** | Not yet due | Low |
| **31-60 days** | Coming due soon | Medium |
| **61-90 days** | Overdue | High |
| **90+ days** | Significantly overdue | Critical |

**Key Metrics**:

| Metric | Description |
|--------|-------------|
| **Total AP** | Total outstanding accounts payable |
| **Overdue** | Amount past due date |
| **DPO** | Days Payable Outstanding (average days to pay) |
| **On-Time %** | Percentage of invoices paid within terms |

**Features**:

1. **Aging Bar Chart** - Visual breakdown of AP by aging bucket
2. **Top Aged Suppliers** - Suppliers with highest aged balances
3. **Cash Flow Forecast** - Projected payments for next 4 weeks
4. **Payment Terms Compliance** - On-time rate by payment terms (Net 30, Net 45, etc.)

**How to Use**:
- Monitor the 90+ bucket to prioritize payment discussions
- Use cash flow forecast for treasury planning
- Review supplier-level aging to identify relationship risks
- Track DPO trends to assess working capital efficiency

---

### Requisitions Analysis

**Purpose**: Analyze purchase requisition patterns and approval efficiency.

**Key Metrics**:

| Metric | Description |
|--------|-------------|
| **Total PRs** | Number of requisitions in period |
| **Conversion Rate** | Percentage of PRs converted to POs |
| **Avg Approval Time** | Average days to approve a PR |
| **Rejection Rate** | Percentage of PRs rejected |

**Features**:

1. **Status Funnel** - PRs by status (Created → Submitted → Approved → Converted)
2. **Department Breakdown** - PR volume and value by department
3. **Approval Time Distribution** - Histogram of approval times
4. **Pending Approvals** - Table of PRs awaiting approval (sorted by age)

**How to Use**:
- Identify departments with high rejection rates for training needs
- Review pending approvals to clear backlogs
- Track approval time improvements over time
- Analyze conversion rates to optimize the PR process

---

### Purchase Orders Analysis

**Purpose**: Track PO compliance, contract coverage, and amendments.

**Key Metrics**:

| Metric | Description |
|--------|-------------|
| **Total POs** | Number of POs in period |
| **PO Value** | Total committed spend |
| **Contract %** | Percentage of spend on-contract |
| **Amendment Rate** | Percentage of POs with change orders |

**Understanding Contract Coverage**:

```
On-Contract (72.3%)     - POs backed by approved contracts
Preferred (15.2%)       - POs with preferred suppliers (no contract)
Maverick (12.5%)        - Off-contract, non-preferred spending
```

**Features**:

1. **Contract vs Maverick Pie** - Visual breakdown of spending compliance
2. **PO Leakage by Category** - Categories with highest maverick spend
3. **Amendment Analysis** - Trends in PO changes and root causes
4. **Supplier PO Table** - PO metrics by supplier

**How to Use**:
- Focus on categories with high maverick spend for contracting opportunities
- Review amendment patterns to improve initial PO accuracy
- Track contract coverage improvement over time
- Use leakage data to inform strategic sourcing decisions

---

### Supplier Payments

**Purpose**: Supplier-centric view of payment performance and relationships.

> **Note**: This page is only visible to Admin users.

**Key Metrics**:

| Metric | Description |
|--------|-------------|
| **Suppliers with AP** | Number of suppliers with outstanding balances |
| **Overall On-Time %** | Organization-wide on-time payment rate |
| **Avg DPO** | Average days payable outstanding across suppliers |
| **Exception Rate** | Average exception rate across suppliers |

**Supplier Scorecard**:

Each supplier receives a score (0-100) based on:
- **AP Balance** - Current outstanding amount
- **DPO** - Days payable for this supplier
- **On-Time %** - Historical on-time payment rate
- **Exception Rate** - Frequency of invoice exceptions

**Supplier Detail View**:

Click any supplier to see:
- Payment timeline chart
- Exception breakdown by type
- Aging bucket distribution
- Recent invoice history

---

## Importing P2P Data

### Admin CSV Import

P2P data is imported via the Django Admin panel.

**Steps**:

1. Log in to Django Admin (`/admin`)
2. Navigate to **Procurement** section
3. Click on the document type to import:
   - Purchase Requisitions
   - Purchase Orders
   - Goods Receipts
   - Invoices
4. Click **"Import CSV"** button
5. Select target organization (superusers only)
6. Choose your CSV file
7. Click **"Import Data"**

**Import Results**:
- **Successful**: Records created
- **Skipped**: Duplicate records (based on document number)
- **Failed**: Invalid data (see error messages)

### CSV Templates

Download templates from each import page or use these formats:

#### Purchase Requisitions

| Column | Required | Description |
|--------|----------|-------------|
| pr_number | Yes | Unique PR identifier |
| department | No | Requesting department |
| cost_center | No | Cost center code |
| description | No | PR description |
| estimated_amount | Yes | Estimated value |
| currency | No | Currency code (default: USD) |
| budget_code | No | Budget code |
| status | No | draft/pending_approval/approved/rejected/converted_to_po/cancelled |
| priority | No | low/medium/high/critical |
| created_date | No | Creation date (YYYY-MM-DD) |
| submitted_date | No | Submission date |
| approval_date | No | Approval date |
| supplier_suggested | No | Suggested supplier name |
| category | No | Category name |

#### Purchase Orders

| Column | Required | Description |
|--------|----------|-------------|
| po_number | Yes | Unique PO identifier |
| supplier_name | Yes | Supplier name |
| total_amount | Yes | Total PO value |
| currency | No | Currency code (default: USD) |
| tax_amount | No | Tax amount |
| freight_amount | No | Freight/shipping amount |
| status | No | draft/pending_approval/approved/sent_to_supplier/acknowledged/partially_received/fully_received/closed/cancelled |
| category | No | Category name |
| created_date | No | Creation date (YYYY-MM-DD) |
| approval_date | No | Approval date |
| sent_date | No | Date sent to supplier |
| required_date | No | Delivery required date |
| promised_date | No | Supplier promised date |
| pr_number | No | Links to existing PR |
| is_contract_backed | No | true/false |

#### Goods Receipts

| Column | Required | Description |
|--------|----------|-------------|
| gr_number | Yes | Unique GR identifier |
| po_number | Yes | Links to existing PO |
| received_date | Yes | Receipt date (YYYY-MM-DD) |
| quantity_ordered | No | Original ordered quantity |
| quantity_received | Yes | Quantity received |
| quantity_accepted | No | Quantity accepted after inspection |
| amount_received | No | Value received |
| status | No | pending/received/inspected/accepted/rejected |
| inspection_notes | No | Inspection notes |

#### Invoices

| Column | Required | Description |
|--------|----------|-------------|
| invoice_number | Yes | Unique invoice identifier |
| supplier_name | Yes | Supplier name |
| invoice_amount | Yes | Invoice total |
| invoice_date | Yes | Invoice date (YYYY-MM-DD) |
| due_date | Yes | Payment due date |
| currency | No | Currency code (default: USD) |
| tax_amount | No | Tax amount |
| net_amount | No | Net amount before tax |
| payment_terms | No | Terms description (e.g., "Net 30") |
| payment_terms_days | No | Payment terms in days |
| status | No | received/pending_match/matched/exception/approved/on_hold/paid/disputed |
| match_status | No | unmatched/2way_matched/3way_matched/exception |
| po_number | No | Links to existing PO |
| gr_number | No | Links to existing GR |
| received_date | No | Date invoice received |
| approved_date | No | Date approved for payment |
| paid_date | No | Date paid |
| has_exception | No | true/false |
| exception_type | No | price_variance/quantity_variance/no_po/duplicate/missing_gr/other |
| exception_amount | No | Exception amount |
| exception_notes | No | Exception description |

---

## P2P Reports

Three P2P-specific reports are available in the Reports module:

### PR Status Report

**Purpose**: Purchase requisition workflow analysis

**Contents**:
- Overview KPIs (total PRs, conversion rate, rejection rate)
- Status breakdown table
- Department analysis with approval rates
- Pending approvals list

### PO Compliance Report

**Purpose**: Contract coverage and maverick spend analysis

**Contents**:
- Compliance KPIs (contract %, maverick rate)
- Contract vs off-contract breakdown
- Maverick spend by category
- Amendment analysis

### AP Aging Report

**Purpose**: Accounts payable aging analysis

**Contents**:
- Aging bucket breakdown (Current, 31-60, 61-90, 90+)
- DPO trend (6 months)
- Aging by supplier
- Cash flow forecast

**Generating P2P Reports**:

1. Navigate to **Reports** page
2. Scroll to **P2P Analytics** section (teal/cyan theme)
3. Click on the desired report type
4. Configure date range and filters
5. Choose format (PDF, Excel, CSV)
6. Click **Generate Report**

---

## Understanding Key Metrics

### Days Payable Outstanding (DPO)

DPO measures how long it takes to pay suppliers on average.

```
DPO = (Accounts Payable / Cost of Goods Sold) × 365
```

| DPO Range | Assessment |
|-----------|------------|
| < 30 days | Paying quickly (possible early discount capture) |
| 30-45 days | Industry standard |
| 45-60 days | Extended terms (good for cash flow) |
| > 60 days | May strain supplier relationships |

### 3-Way Match Rate

Measures invoice processing efficiency.

```
Match Rate = (3-Way Matched Invoices / Total Invoices) × 100
```

| Rate | Assessment |
|------|------------|
| > 90% | Excellent - Highly automated |
| 80-90% | Good - Minor exceptions |
| 70-80% | Fair - Process improvement needed |
| < 70% | Poor - Significant manual effort |

### Contract Coverage

Measures purchasing compliance.

```
Contract Coverage = (On-Contract Spend / Total Spend) × 100
```

| Coverage | Assessment |
|----------|------------|
| > 85% | Excellent - Strong compliance |
| 70-85% | Good - Room for improvement |
| 50-70% | Fair - Sourcing opportunity |
| < 50% | Poor - Significant maverick spend |

---

## Role-Based Access

| Feature | Viewer | Manager | Admin |
|---------|--------|---------|-------|
| View P2P Cycle Dashboard | Yes | Yes | Yes |
| View 3-Way Match Center | Yes | Yes | Yes |
| Resolve Exceptions | No | Yes | Yes |
| View Invoice Aging | Yes | Yes | Yes |
| View Requisitions | Yes | Yes | Yes |
| View Purchase Orders | Yes | Yes | Yes |
| View Cash Flow Forecast | No | Yes | Yes |
| View Supplier Payments | No | No | Yes |
| Import P2P Data | No | No | Yes |
| Generate P2P Reports | Yes | Yes | Yes |

---

## Troubleshooting

### Common Issues

**Issue**: No data showing on P2P dashboards
- **Cause**: No P2P documents imported for your organization
- **Solution**: Import P2P data via Admin panel or contact your administrator

**Issue**: Cannot resolve exceptions
- **Cause**: Insufficient permissions (Viewer role)
- **Solution**: Contact administrator to upgrade to Manager role

**Issue**: Supplier Payments page not visible
- **Cause**: Page restricted to Admin users only
- **Solution**: Contact administrator if you need access

**Issue**: Import failed with "PO not found" error (Goods Receipts)
- **Cause**: Importing GRs before the linked POs exist
- **Solution**: Import Purchase Orders first, then Goods Receipts

**Issue**: Import shows all records as "skipped"
- **Cause**: Duplicate document numbers
- **Solution**: The system prevents duplicates; check if data was already imported

### Getting Help

- Check the [API Documentation](/api/docs) for technical details
- Review the [P2P Implementation Plan](P2P_ANALYTICS_SUITE.md) for architecture details
- Contact support at support@versatex.com

---

## Appendix: Date Formats Supported

The import process accepts multiple date formats:

- `YYYY-MM-DD` (ISO format, recommended)
- `MM/DD/YYYY` (US format)
- `DD/MM/YYYY` (European format)
- `MM-DD-YYYY`
- `DD-MM-YYYY`
- `YYYY/MM/DD`

---

*Last Updated: January 2025*
