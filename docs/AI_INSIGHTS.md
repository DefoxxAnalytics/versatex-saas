# AI Insights Module Documentation

## Overview

The AI Insights module provides intelligent, actionable procurement recommendations by analyzing transaction patterns, identifying cost-saving opportunities, assessing supplier risks, detecting anomalies, and recommending supplier consolidation strategies.

This document covers:
1. **Insight Types & Methodologies** - How each insight is calculated
2. **Savings Calculation Logic** - Configurable rates, deduplication, and capping
3. **Business Decision Framework** - How to interpret and act on insights
4. **Configurable Benchmark Profiles** - Industry-backed savings rates
5. **API Reference** - Endpoints and data structures

---

## 1. Insight Types

The AI Insights module generates four types of insights, each targeting a specific procurement optimization opportunity.

### 1.1 Cost Optimization Insights

**Purpose**: Identify price variance between suppliers providing the same goods/services within a category and subcategory.

**Methodology**:

1. **Group Transactions**: Transactions are grouped by `(category, subcategory)` for apples-to-apples comparison
2. **Calculate Supplier Metrics**: For each group, compute:
   - Total spend per supplier
   - Transaction count per supplier
   - Average transaction amount per supplier
3. **Detect Price Variance**: Calculate variance using:
   ```
   Price Variance = (Max Avg Price - Min Avg Price) / Max Avg Price
   ```
4. **Flag Insights**: Generate insight if variance exceeds **15%** threshold
5. **Estimate Savings**:
   ```
   Raw Savings = Σ (Expensive Supplier Avg - Cheapest Avg) × Transaction Count
   Potential Savings = Raw Savings × Variance Capture Rate (configurable, default 40%)
   ```

**Severity Assignment**:
- **High**: Price variance > 30%
- **Medium**: Price variance 15-30%

**Confidence Score**: `min(0.95, 0.70 + (price_variance × 0.5))`

**Rationale**:
- The 15% threshold filters out normal market variations while surfacing meaningful discrepancies
- The variance capture rate (default 40%) reflects the realistic portion of theoretical savings that can be captured through negotiation (industry research suggests 20-80% capture rates)
- Grouping by subcategory ensures we're comparing like items (laptops vs laptops, not laptops vs monitors)

**Business Action**: Negotiate with higher-priced suppliers using the lowest price as leverage, or shift volume to the lowest-cost supplier.

---

### 1.2 Supplier Risk Insights

**Purpose**: Identify supplier concentration risk where a single supplier represents too large a portion of total spend.

**Methodology**:

1. **Calculate Total Spend**: Sum all transaction amounts
2. **Calculate Supplier Concentration**: For each supplier:
   ```
   Concentration = Supplier Spend / Total Spend
   ```
3. **Flag Insights**: Generate insight if concentration ≥ **30%**
4. **Assign Severity**:
   - **Critical**: Concentration > 50%
   - **High**: Concentration 30-50%

**Confidence Score**: Fixed at 0.90 (high confidence in concentration calculations)

**Rationale**:
- 30% threshold is industry-standard for concentration risk identification
- High supplier concentration creates supply chain vulnerability (single point of failure)
- No savings are attached to risk insights—these are about risk mitigation, not cost reduction

**Business Action**: Develop alternative suppliers, negotiate backup supply agreements, diversify supply base.

---

### 1.3 Anomaly Detection Insights

**Purpose**: Identify statistically unusual transactions that may indicate errors, fraud, or pricing issues.

**Methodology**:

1. **Calculate Category Statistics**: For each category with >5 transactions:
   ```
   Mean (μ) = Average transaction amount
   Standard Deviation (σ) = Std dev of transaction amounts
   ```
2. **Define Thresholds**:
   ```
   Upper Threshold = μ + (Z-Score × σ)
   Lower Threshold = max(0, μ - (Z-Score × σ))
   ```
   Default Z-Score: 2.0 (configurable sensitivity)
3. **Flag Anomalies**: Transactions outside thresholds
4. **Estimate Savings**:
   ```
   Total Anomaly Spend = Sum of high anomalies
   Potential Savings = Total Anomaly Spend × Anomaly Recovery Rate (configurable, default 0.8%)
   ```

**Severity Assignment**:
- **High**: More than 3 high anomalies
- **Medium**: 1-3 high anomalies

**Confidence Score**: Fixed at 0.75 (statistical detection has inherent uncertainty)

**Rationale**:
- Z-score of 2.0 captures ~2.5% of transactions on each tail (5% total), balancing sensitivity with false positives
- Low recovery rate (0.5-1.5% industry benchmark) reflects that most anomalies are legitimate—only a fraction are recoverable errors
- Requiring 5+ transactions ensures statistical validity

**Business Action**: Review flagged transactions for accuracy, verify pricing, check for duplicates, investigate supplier invoicing practices.

---

### 1.4 Consolidation Insights

**Purpose**: Identify opportunities to consolidate suppliers within a category/subcategory to negotiate better rates and reduce complexity.

**Methodology**:

1. **Group by Subcategory**: Transactions grouped by `(category, subcategory)`
2. **Count Distinct Suppliers**: For each group
3. **Flag Insights**: Generate if supplier count ≥ **3** (configurable)
4. **Analyze Supplier Distribution**:
   ```
   Top Supplier Share = Top Supplier Spend / Total Group Spend
   ```
5. **Estimate Savings**:
   ```
   Potential Savings = Total Group Spend × Consolidation Rate (configurable, default 3%)
   ```

**Severity Assignment**:
- **High**: 5+ suppliers in group
- **Medium**: 3-4 suppliers in group

**Confidence Score**: Fixed at 0.80

**Rationale**:
- Industry benchmarks (Deloitte 2024) suggest 1-8% savings from consolidation
- Multiple suppliers for the same item type indicates fragmented purchasing
- Consolidation reduces administrative overhead and enables volume discounts

**Business Action**: Evaluate primary supplier as preferred vendor, request volume discount proposals, develop preferred supplier program.

---

## 2. Savings Calculation Logic

### 2.1 Configurable Savings Rates

Organizations can configure savings rates via **Benchmark Profiles** in Settings. Rates are stored in `Organization.savings_config` and loaded at insight generation time.

| Rate | Description | Conservative | Moderate | Aggressive | Industry Source |
|------|-------------|--------------|----------|------------|-----------------|
| `consolidation_rate` | % savings from supplier consolidation | 1% | 3% | 5% | Deloitte 2024 |
| `anomaly_recovery_rate` | % of anomaly spend recoverable | 0.5% | 0.8% | 1.5% | Aberdeen Group |
| `price_variance_capture` | % of theoretical price savings achievable | 30% | 40% | 60% | Industry Standard |
| `specification_rate` | % savings from spec standardization | 2% | 3% | 4% | McKinsey 2024 |
| `payment_terms_rate` | % savings from payment optimization | 0.5% | 0.8% | 1.2% | Hackett Group |
| `process_savings_per_txn` | $ saved per automated transaction | $25 | $35 | $50 | APQC 2024 |

**Realization Probability by Profile**:
| Profile | Expected Realization | Confidence Range |
|---------|---------------------|------------------|
| Conservative | 90% | 85-95% |
| Moderate | 75% | 70-85% |
| Aggressive | 55% | 50-70% |

---

### 2.2 Savings Deduplication

**Problem**: Multiple insight types can target the same transactions/categories, leading to double-counted savings.

**Example Overlap**:
- Cost Optimization flags IT Equipment for price variance → $150K savings
- Consolidation flags IT Equipment for 5 suppliers → $100K savings
- Anomaly flags IT Equipment high transactions → $40K savings
- **Naive sum: $290K** (unrealistic on $500K spend)

**Solution: Priority-Based Deduplication**

Insights are processed in priority order. Higher-priority insights "claim" entities first:

| Priority | Insight Type | Rationale |
|----------|--------------|-----------|
| 1 | Anomaly | Most specific—individual transactions |
| 2 | Cost Optimization | Price variance on specific items |
| 3 | Consolidation | Broad category-level opportunity |
| 4 | Risk | No savings (risk only) |

**Deduplication Algorithm**:

1. Sort insights by priority
2. Track claimed entities (subcategory, category, supplier)
3. For each insight:
   - Calculate overlap with already-claimed entities
   - Reduce savings by overlap amount
   - Apply 30% diminishing returns factor for overlapping insights
4. Sum deduplicated savings

**Result**: Realistic, non-overlapping savings that sum correctly.

---

### 2.3 Savings Capping

**Rule**: `Total Potential Savings ≤ Total Spend`

After deduplication, a final safety cap ensures mathematical validity. If adjusted savings exceed total filtered spend, they are capped at 100% of spend.

**API Response Fields**:
```json
{
  "summary": {
    "total_potential_savings": 85000.00,      // Final capped value
    "total_potential_savings_raw": 92000.00,  // Pre-cap value
    "savings_capped": true,                   // Whether cap was applied
    "total_spend": 85000.00,
    "deduplication_applied": true,
    "overlap_summary": {
      "total_original_savings": 145000.00,
      "total_adjusted_savings": 92000.00,
      "total_overlap_reduction": 53000.00,
      "insights_with_overlap": 3,
      "deduplication_percentage": 36.6
    }
  }
}
```

---

## 3. Business Decision Framework

### 3.1 Interpreting Insights

| Severity | Urgency | Typical Action Timeframe |
|----------|---------|-------------------------|
| **Critical** | Immediate | Within 1 week |
| **High** | Urgent | Within 1 month |
| **Medium** | Standard | Within quarter |
| **Low** | Monitor | As capacity allows |

### 3.2 Acting on Cost Optimization Insights

**Decision Tree**:

1. **Verify the variance is real**
   - Are suppliers providing equivalent items? (Check subcategory grouping)
   - Are pricing differences due to volume, terms, or quality?

2. **Assess switching feasibility**
   - Supplier capacity constraints?
   - Contractual obligations?
   - Quality/service differences?

3. **Choose strategy**:
   - **Quick Win**: Use lowest price as negotiation leverage with current suppliers
   - **Medium Term**: Shift incremental volume to lowest-cost supplier
   - **Strategic**: Run formal RFP using benchmark pricing

**Expected ROI**: 30-60% of identified savings (reflected in variance_capture rate)

---

### 3.3 Acting on Risk Insights

**Decision Tree**:

1. **Assess dependency criticality**
   - Is this supplier providing critical items?
   - What's the lead time for alternatives?

2. **Identify alternatives**
   - Approved alternate suppliers exist?
   - Qualification time required?

3. **Choose strategy**:
   - **Immediate**: Negotiate supply agreements with backup suppliers
   - **Medium Term**: Qualify 1-2 alternative suppliers
   - **Strategic**: Implement dual/multi-sourcing policy

**Key Metric**: Reduce concentration below 30% for any single supplier.

---

### 3.4 Acting on Anomaly Insights

**Decision Tree**:

1. **Classify anomaly type**
   - Pricing error? → Request credit/refund
   - Duplicate entry? → Correct records, prevent future
   - Legitimate large purchase? → Document and dismiss
   - Potential fraud? → Escalate to audit

2. **Investigation steps**:
   - Pull original PO/Invoice
   - Verify quantity and unit price
   - Compare to catalog/contract pricing
   - Check approval workflow

**Expected Recovery**: 0.5-1.5% of flagged anomaly spend (reflected in anomaly_rate)

---

### 3.5 Acting on Consolidation Insights

**Decision Tree**:

1. **Evaluate current supplier base**
   - Which suppliers have best performance?
   - Volume distribution across suppliers?

2. **Assess consolidation potential**
   - Can top supplier handle additional volume?
   - What volume discount tiers are available?

3. **Choose strategy**:
   - **Quick Win**: Request volume discount from top supplier
   - **Medium Term**: Implement preferred supplier program
   - **Strategic**: Run supplier rationalization initiative

**Expected Savings**: 1-5% of consolidated spend (reflected in consolidation_rate)

---

## 4. Configurable Benchmark Profiles

### 4.1 Profile Selection Guide

| Profile | Best For | Risk Tolerance |
|---------|----------|----------------|
| **Conservative** | New to procurement optimization, limited negotiation leverage, risk-averse organizations | Low |
| **Moderate** | Established procurement processes, balanced approach | Medium |
| **Aggressive** | Mature procurement teams, strong supplier relationships, proven track records | High |
| **Custom** | Organizations with specific historical data or unique circumstances | Variable |

### 4.2 Changing Profiles

**Via Settings UI** (Admin only):
1. Navigate to Settings → Organization Settings
2. Select Benchmark Profile dropdown
3. For Custom, adjust individual rate sliders
4. Save changes

**Effect**: All AI Insights calculations will use the new rates immediately upon refresh.

### 4.3 Profile Comparison

When selecting a profile, consider:

| Factor | Conservative | Moderate | Aggressive |
|--------|--------------|----------|------------|
| Savings estimates | Lower, more achievable | Balanced | Higher, stretch targets |
| Risk of disappointment | Low | Medium | Higher |
| Negotiation leverage required | Low | Medium | High |
| Implementation effort | Lower | Standard | Higher |

---

## 5. API Reference

### 5.1 Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics/ai-insights/` | GET | All insights with deduplication |
| `/api/v1/analytics/ai-insights/cost/` | GET | Cost optimization only |
| `/api/v1/analytics/ai-insights/risk/` | GET | Supplier risk only |
| `/api/v1/analytics/ai-insights/anomalies/` | GET | Anomaly detection only |
| `/api/v1/analytics/ai-insights/feedback/` | POST | Record action on insight |
| `/api/v1/analytics/ai-insights/feedback/list/` | GET | List feedback entries |
| `/api/v1/analytics/ai-insights/feedback/effectiveness/` | GET | ROI metrics |
| `/api/v1/analytics/ai-insights/feedback/<uuid:id>/` | PATCH | Update outcome |
| `/api/v1/analytics/ai-insights/feedback/<uuid:id>/delete/` | DELETE | Delete feedback entry |
| `/api/v1/analytics/ai-insights/deep-analysis/request/` | POST | Request detailed analysis |
| `/api/v1/analytics/ai-insights/deep-analysis/status/<insight_id>/` | GET | Poll deep analysis status |
| `/api/v1/analytics/ai-insights/enhance/request/` | POST | Request async AI enhancement |
| `/api/v1/analytics/ai-insights/enhance/status/` | GET | Poll enhancement status |
| `/api/v1/analytics/ai-insights/metrics/` | GET | Internal metrics |
| `/api/v1/analytics/ai-insights/metrics/prometheus/` | GET | Prometheus format metrics |
| `/api/v1/analytics/ai-insights/cache/invalidate/` | POST | Invalidate AI cache |

### 5.2 Query Parameters

All insight endpoints support filters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `date_from` | date | Start date (YYYY-MM-DD) |
| `date_to` | date | End date (YYYY-MM-DD) |
| `supplier_ids` | int[] | Filter by supplier IDs |
| `category_ids` | int[] | Filter by category IDs |
| `subcategories` | string[] | Filter by subcategory names |
| `min_amount` | decimal | Minimum transaction amount |
| `max_amount` | decimal | Maximum transaction amount |
| `force_refresh` | boolean | Bypass cache |

### 5.3 Response Structure

```json
{
  "insights": [
    {
      "id": "uuid",
      "type": "cost_optimization|risk|anomaly|consolidation",
      "severity": "critical|high|medium|low",
      "confidence": 0.85,
      "title": "Price variance detected in IT Equipment > Laptops",
      "description": "Found 4 suppliers with 25% price variance...",
      "potential_savings": 15000.00,
      "affected_entities": ["Category > Subcategory", "Supplier A", "Supplier B"],
      "recommended_actions": ["Action 1", "Action 2"],
      "created_at": "2024-01-15T10:30:00Z",
      "details": { ... }
    }
  ],
  "summary": {
    "total_insights": 12,
    "high_priority": 4,
    "total_potential_savings": 125000.00,
    "total_spend": 2500000.00,
    "by_type": {
      "cost_optimization": 3,
      "risk": 2,
      "anomaly": 4,
      "consolidation": 3
    }
  }
}
```

---

## 6. Frontend Hooks Reference

### Core Insight Hooks

| Hook | Purpose |
|------|---------|
| `useAIInsights()` | Fetch all insights with deduplication |
| `useRefreshAIInsights()` | Force refresh (bypass cache) |
| `useAIInsightsCost()` | Cost optimization insights only |
| `useAIInsightsRisk()` | Supplier risk insights only |
| `useAIInsightsAnomalies(sensitivity)` | Anomaly detection with configurable Z-score |

### Feedback & ROI Tracking Hooks

| Hook | Purpose |
|------|---------|
| `useRecordInsightFeedback()` | Record action taken on an insight |
| `useUpdateInsightOutcome()` | Update outcome for recorded feedback |
| `useDeleteInsightFeedback()` | Delete feedback entry (owner/admin only) |
| `useInsightFeedbackList(params)` | List feedback history with filters |
| `useInsightEffectiveness()` | Get ROI and effectiveness metrics |

### Async Enhancement Hooks

| Hook | Purpose |
|------|---------|
| `useRequestAsyncEnhancement()` | Request background AI enhancement |
| `useAsyncEnhancementStatus(enabled, pollInterval)` | Poll enhancement status |

### Deep Analysis Hooks

| Hook | Purpose |
|------|---------|
| `useRequestDeepAnalysis()` | Request detailed AI analysis for an insight |
| `useDeepAnalysisStatus(insightId, enabled, pollInterval)` | Poll analysis status |

### Helper Functions

| Function | Purpose |
|----------|---------|
| `filterInsightsByType(insights, type)` | Filter insights by type |
| `sortInsights(insights)` | Sort by severity and savings |
| `getInsightTypeLabel(type)` | Display label for insight type |
| `getInsightTypeColor(type)` | CSS classes for insight type badge |
| `getSeverityColor(severity)` | CSS classes for severity badge |
| `getActionLabel(action)` | Display label for action taken |
| `getActionColor(action)` | CSS classes for action badge |
| `getOutcomeLabel(outcome)` | Display label for outcome |
| `getOutcomeColor(outcome)` | CSS classes for outcome badge |

---

## 7. Glossary

| Term | Definition |
|------|------------|
| **Apples-to-Apples** | Comparing only like items (same subcategory) |
| **Deduplication** | Removing overlapping savings claims |
| **Realization Rate** | % of projected savings actually achieved |
| **Variance Capture** | % of price difference achievable through negotiation |
| **Z-Score** | Standard deviations from mean (anomaly detection) |
| **Concentration Risk** | Over-reliance on a single supplier |
| **Benchmark Profile** | Preset savings rates based on industry research |

---

## 8. Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.7 | 2024-01 | Configurable savings rates, benchmark profiles, PDF export |
| 2.6 | 2024-01 | ROI tracking, feedback system, deep analysis |
| 2.5 | 2023-12 | Filter support, subcategory grouping, deduplication |
| 2.0 | 2023-11 | Initial AI Insights module |
