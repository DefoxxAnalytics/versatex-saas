# AI Insights Module Documentation

## Overview

The AI Insights module provides intelligent, actionable procurement recommendations by analyzing transaction patterns, identifying cost-saving opportunities, assessing supplier risks, detecting anomalies, and recommending supplier consolidation strategies.

This document covers:
1. **Insight Types & Methodologies** - How each insight is calculated
2. **Savings Calculation Logic** - Configurable rates, deduplication, and capping
3. **Business Decision Framework** - How to interpret and act on insights
4. **Configurable Benchmark Profiles** - Industry-backed savings rates
5. **API Reference** - Endpoints and data structures
6. **AI Chat Interface** - Interactive Q&A with streaming responses
7. **LLM Cost Optimization** - Prompt caching, semantic caching, tiered models
8. **LLM Usage Tracking** - Cost dashboard and metrics
9. **RAG Document Intelligence** - Vector search for relevant context
10. **Automated Processing** - Scheduled batch jobs and cleanup tasks

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

### 5.1 Core Insight Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics/ai-insights/` | GET | All insights with deduplication |
| `/api/v1/analytics/ai-insights/cost/` | GET | Cost optimization only |
| `/api/v1/analytics/ai-insights/risk/` | GET | Supplier risk only |
| `/api/v1/analytics/ai-insights/anomalies/` | GET | Anomaly detection only |
| `/api/v1/analytics/ai-insights/feedback/` | POST | Record action on insight |
| `/api/v1/analytics/ai-insights/feedback/list/` | GET | List feedback entries |
| `/api/v1/analytics/ai-insights/feedback/effectiveness/` | GET | ROI metrics |
| `/api/v1/analytics/ai-insights/deep-analysis/request/` | POST | Request detailed analysis |

### 5.2 Chat & Streaming Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics/ai-insights/chat/stream/` | POST | Stream chat response (SSE) |
| `/api/v1/analytics/ai-insights/chat/quick/` | POST | Non-streaming quick query |

### 5.3 Usage & Cost Tracking Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics/ai-insights/usage/summary/` | GET | Usage summary (requests, cost, cache rates) |
| `/api/v1/analytics/ai-insights/usage/daily/` | GET | Daily usage trends |
| `/api/v1/analytics/ai-insights/metrics/` | GET | Internal metrics |
| `/api/v1/analytics/ai-insights/metrics/prometheus/` | GET | Prometheus format metrics |
| `/api/v1/analytics/ai-insights/cache/invalidate/` | POST | Invalidate AI cache |

### 5.4 RAG Document Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics/ai-insights/documents/` | GET | List embedded documents |
| `/api/v1/analytics/ai-insights/documents/search/` | GET | Vector search for relevant docs |
| `/api/v1/analytics/ai-insights/documents/ingest/` | POST | Trigger document ingestion |

### 5.5 Query Parameters

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

### 5.6 Response Structure

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

## 6. AI Chat Interface

The AI Chat provides an interactive conversational interface for procurement Q&A with real-time streaming responses.

### 6.1 Features

| Feature | Description |
|---------|-------------|
| **Streaming Responses** | Server-Sent Events (SSE) for real-time token streaming |
| **Suggested Prompts** | Pre-built procurement questions for quick access |
| **Message History** | Full conversation context maintained |
| **Abort Support** | Cancel in-flight requests via AbortController |
| **Quick Query Mode** | Non-streaming option for simple questions |

### 6.2 Example Questions

- "What suppliers have the highest risk concentration?"
- "Show me cost optimization opportunities in IT Equipment"
- "Explain why this anomaly was flagged"
- "Compare Q1 vs Q2 spending patterns"
- "Which categories have the most consolidation potential?"

### 6.3 Technical Implementation

**Backend**: Django SSE endpoint proxying to Anthropic Claude API with streaming enabled.

**Frontend**: React component with EventSource API for SSE consumption:

```typescript
// Using the useAIChatStream hook
const { messages, isStreaming, sendMessage, cancelStream } = useAIChatStream();

// Send a message
sendMessage("What are my top cost savings opportunities?");

// Cancel if needed
cancelStream();
```

---

## 7. LLM Cost Optimization

The AI Insights module implements multiple cost optimization strategies to minimize API costs while maintaining quality.

### 7.1 Prompt Caching (Anthropic)

**Purpose**: Cache system prompts to reduce token costs by up to 90%.

**How it works**:
- System prompts marked with `cache_control: { type: "ephemeral" }` are cached for 5 minutes
- Subsequent requests reuse cached prompt tokens at 90% discount
- Organization context cached separately from base system prompt

**Cost Impact**:
| Scenario | Without Caching | With Caching |
|----------|-----------------|--------------|
| System prompt (2000 tokens) | $0.003 | $0.0003 |
| Org context (500 tokens) | $0.00075 | $0.000075 |

### 7.2 Semantic Caching (pgvector)

**Purpose**: Avoid re-processing semantically similar queries.

**How it works**:
1. Query text is embedded using text-embedding-3-small (1536 dimensions)
2. Vector similarity search against cached queries (cosine distance)
3. If similarity > 90%, return cached response
4. Otherwise, process query and cache response

**Configuration**:
- Similarity threshold: 0.90 (configurable)
- Cache TTL: 1 hour default
- Cache cleanup: Nightly Celery task

**Expected Savings**: 73% reduction in LLM API calls

### 7.3 Tiered Model Selection

**Purpose**: Route queries to appropriate model tier based on complexity.

| Query Type | Model | Cost/M tokens | Example |
|------------|-------|---------------|---------|
| Simple categorization | Haiku | $0.25 | "What insight type is this?" |
| Standard analysis | Sonnet | $3.00 | "Enhance these 5 insights" |
| Deep investigation | Opus | $15.00 | "Complex root cause analysis" |

**Routing Logic**:
1. Initial classification by Haiku (ultra-low cost)
2. Simple queries stay on Haiku
3. Standard insights use Sonnet
4. Deep analysis promoted to Opus

---

## 8. LLM Usage Tracking

Track and visualize LLM API usage, costs, and cache efficiency.

### 8.1 LLMRequestLog Model

Every LLM API call is logged with comprehensive metadata:

| Field | Description |
|-------|-------------|
| `request_type` | enhance, deep_analysis, chat, quick_query |
| `model_used` | claude-haiku, claude-sonnet, claude-opus |
| `tokens_input` | Input tokens consumed |
| `tokens_output` | Output tokens generated |
| `latency_ms` | Request duration |
| `cost_usd` | Calculated cost |
| `cache_hit` | Whether semantic cache was hit |
| `prompt_cache_read_tokens` | Tokens read from prompt cache |
| `prompt_cache_write_tokens` | Tokens written to prompt cache |
| `validation_passed` | Whether response passed hallucination validation |

### 8.2 Usage Dashboard

The Usage tab in AI Insights displays:

| Metric | Description |
|--------|-------------|
| **Total Requests** | LLM API calls in period |
| **Total Cost** | Sum of cost_usd |
| **Cache Hit Rate** | % of requests served from semantic cache |
| **Estimated Savings** | Cost avoided via caching |
| **Total Tokens** | Input + output tokens |
| **Avg Latency** | Mean response time |

**Visualizations**:
- Pie chart: Usage by request type
- Bar chart: Usage by provider
- Line chart: Daily usage trends
- Cache efficiency summary

### 8.3 Frontend Hooks

```typescript
// Fetch usage summary
const { data: summary } = useLLMUsageSummary(30); // Last 30 days

// Fetch daily breakdown
const { data: daily } = useLLMUsageDaily(30);

// Helper functions
formatCost(0.0123);     // "$0.01"
formatTokenCount(15000); // "15.0K"
getRequestTypeLabel("deep_analysis"); // "Deep Analysis"
getProviderLabel("anthropic_claude"); // "Claude"
```

---

## 9. RAG Document Intelligence

Retrieval-Augmented Generation enhances AI responses with relevant organizational context.

### 9.1 Document Types

| Type | Source | Use Case |
|------|--------|----------|
| `supplier_profile` | Supplier model | Supplier context in risk analysis |
| `contract` | Contract model | Contract terms in compliance checks |
| `policy` | Uploaded markdown | Policy context in recommendations |
| `best_practice` | Seeded content | Industry benchmarks |
| `historical_insight` | Successful insights | Similar past recommendations |

### 9.2 EmbeddedDocument Model

Documents are chunked, embedded, and stored with metadata:

| Field | Description |
|-------|-------------|
| `document_type` | One of the types above |
| `title` | Document/chunk title |
| `content` | Text content |
| `content_embedding` | 1536-dim vector (pgvector) |
| `metadata` | JSON with source refs (supplier_id, category, etc.) |

### 9.3 Vector Search

```python
# RAGService.search() example
results = rag_service.search(
    org_id=1,
    query="supplier risk for IT equipment",
    doc_types=['supplier_profile', 'historical_insight'],
    top_k=5
)
# Returns: [{title, content, similarity, metadata}, ...]
```

**Search Parameters**:
- `similarity_threshold`: 0.70 minimum
- `top_k`: 5 documents max
- `doc_types`: Optional filter

### 9.4 Context Augmentation

Before LLM calls, relevant documents are injected into the prompt:

```json
{
  "organization_context": {...},
  "relevant_documents": [
    {
      "type": "supplier_profile",
      "title": "TechSupply Inc",
      "content": "Primary IT vendor since 2020...",
      "relevance": "92%"
    }
  ]
}
```

---

## 10. Automated Processing

Celery Beat schedules background tasks for maintenance and batch operations.

### 10.1 Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `batch_generate_insights` | 2:00 AM daily | Generate insights for all active orgs |
| `batch_enhance_insights` | 2:30 AM daily | AI-enhance pending insights |
| `cleanup_semantic_cache` | 3:00 AM daily | Remove expired cache entries |
| `cleanup_llm_request_logs` | 3:30 AM daily | Archive old request logs |
| `refresh_rag_documents` | 4:00 AM Sundays | Re-embed documents for freshness |

### 10.2 Batch API (50% Cost Discount)

Overnight insight generation uses Anthropic's Batch API:

```python
@shared_task(name='batch_generate_insights')
def batch_generate_insights():
    # Build batch requests for all orgs
    batch_requests = [...]

    # Submit to Batch API (50% discount)
    batch_job = client.batches.create(requests=batch_requests)

    # Poll for completion
    while not batch_job.is_complete:
        time.sleep(60)

    # Process results
    for result in batch_job.results:
        save_enhanced_insight(result)
```

### 10.3 Configuration

In `backend/config/celery.py`:

```python
app.conf.beat_schedule = {
    'nightly-insight-generation': {
        'task': 'batch_generate_insights',
        'schedule': crontab(hour=2, minute=0),
    },
    # ... other tasks
}
```

---

## 11. Hallucination Prevention

The validation layer prevents LLM outputs containing fabricated data.

### 11.1 Validation Checks

| Check | Description | Severity |
|-------|-------------|----------|
| **Savings Cap** | Total savings ≤ total spend | Critical |
| **Supplier Exists** | Referenced suppliers in database | Warning |
| **Category Exists** | Referenced categories in database | Warning |
| **Date Range Valid** | Dates within data range | Error |
| **Percentage Sum** | Breakdowns sum to 100% | Warning |

### 11.2 Confidence Adjustment

Original confidence is adjusted based on validation:

```
adjusted_confidence = original_confidence × (
    1 - (critical_errors × 0.3) - (warnings × 0.05)
)
```

### 11.3 Validation Response

```json
{
  "validated": true,
  "errors": [],
  "confidence_original": 0.85,
  "confidence_adjusted": 0.85,
  "warnings_count": 0,
  "critical_count": 0
}
```

### 11.4 Prompt Constraints

All LLM prompts include validation constraints:

```
CRITICAL CONSTRAINTS:
1. NEVER state monetary values without citing source data
2. NEVER extrapolate trends beyond provided date range
3. NEVER reference suppliers/categories not in the provided data
4. ALWAYS flag uncertainty with confidence scores
5. ALWAYS validate percentages sum correctly

IF UNCERTAIN: State "Based on available data, [claim] (confidence: X%)"
```

---

## 12. Frontend Hooks Reference

### 12.1 Core Insight Hooks

| Hook | Purpose |
|------|---------|
| `useAIInsights()` | Fetch all insights |
| `useRefreshAIInsights()` | Force refresh (bypass cache) |
| `useAIInsightsCost()` | Cost optimization only |
| `useAIInsightsRisk()` | Risk insights only |
| `useAIInsightsAnomalies(sensitivity)` | Anomaly detection |
| `useRecordInsightFeedback()` | Record action taken |
| `useInsightFeedbackList(params)` | List feedback history |
| `useInsightEffectiveness()` | ROI metrics |
| `useRequestDeepAnalysis()` | Request detailed AI analysis |
| `useDeepAnalysisStatus(insightId)` | Poll analysis status |

### 12.2 Chat Hooks

| Hook | Purpose |
|------|---------|
| `useAIChatStream()` | SSE streaming with message state |
| `useAIQuickQuery()` | Non-streaming quick queries |

### 12.3 Usage Tracking Hooks

| Hook | Purpose |
|------|---------|
| `useLLMUsageSummary(days)` | Usage summary data |
| `useLLMUsageDaily(days)` | Daily usage trends |

### 12.4 Helper Functions

| Function | Purpose |
|----------|---------|
| `formatCost(cost)` | Format currency display |
| `formatTokenCount(count)` | Format with K/M suffix |
| `getRequestTypeLabel(type)` | Display labels for request types |
| `getProviderLabel(provider)` | Display labels for LLM providers |
| `getActionLabel(action)` | Display labels for feedback actions |
| `getOutcomeLabel(outcome)` | Display labels for outcomes |

---

## 13. Glossary

| Term | Definition |
|------|------------|
| **Apples-to-Apples** | Comparing only like items (same subcategory) |
| **Deduplication** | Removing overlapping savings claims |
| **Realization Rate** | % of projected savings actually achieved |
| **Variance Capture** | % of price difference achievable through negotiation |
| **Z-Score** | Standard deviations from mean (anomaly detection) |
| **Concentration Risk** | Over-reliance on a single supplier |
| **Benchmark Profile** | Preset savings rates based on industry research |
| **Prompt Caching** | Caching LLM system prompts to reduce API costs |
| **Semantic Caching** | Caching responses by query similarity (vector search) |
| **RAG** | Retrieval-Augmented Generation - enhancing prompts with relevant docs |
| **SSE** | Server-Sent Events - unidirectional streaming from server to client |
| **pgvector** | PostgreSQL extension for vector similarity search |
| **Hallucination** | LLM fabricating facts not present in source data |

---

## 14. Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.9 | 2026-01 | AI Chat streaming, LLM usage dashboard, RAG document intelligence, semantic caching, prompt caching, hallucination prevention, tiered model selection, batch processing, Celery Beat scheduled tasks |
| 2.8 | 2025-12 | Management documentation, screenshot capture, PDF/PPTX generation |
| 2.7 | 2024-01 | Configurable savings rates, benchmark profiles, PDF export |
| 2.6 | 2024-01 | ROI tracking, feedback system, deep analysis |
| 2.5 | 2023-12 | Filter support, subcategory grouping, deduplication |
| 2.0 | 2023-11 | Initial AI Insights module |
