# AI Insights Module Enhancement Plan v3.0

> **Document Version**: 3.3
> **Created**: 2025-01-08
> **Last Updated**: 2026-01-23
> **Status**: **Phase 6 Complete** - Batch Processing & Automation with Celery Beat
> **Author**: Claude Code Analysis

### Implementation Progress

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ **Complete** | Cost Optimization & Reliability (Prompt Caching, Tiered Models, Logging) |
| Phase 2 | ✅ **Complete** | Semantic Caching with pgvector |
| Phase 3 | ✅ **Complete** | RAG Layer for Document Intelligence |
| Phase 4 | ✅ **Complete** | Hallucination Prevention |
| Phase 5 | ✅ **Complete** | Streaming & Interactive Features (FastAPI SSE, AI Chat) |
| Phase 6 | ✅ **Complete** | Batch Processing & Automation (Celery Beat) |
| Phase 7 | 🔲 Pending | Frontend Enhancements (partial: Chat tab done) |

### Phase 3 Implementation Details (RAG Layer)

**Files Created:**
- `backend/apps/analytics/rag_service.py` - RAG document search with vector similarity
- `backend/apps/analytics/document_ingestion.py` - Automated ingestion pipeline for supplier profiles, contracts, policies
- `backend/apps/analytics/models.py` - `EmbeddedDocument` model with pgvector support
- `backend/apps/analytics/serializers.py` - RAG document serializers
- `backend/apps/analytics/urls.py` - RAG API endpoints

**API Endpoints:**
- `GET /api/v1/analytics/rag/documents/` - List documents
- `POST /api/v1/analytics/rag/documents/create/` - Create document
- `GET /api/v1/analytics/rag/search/` - Vector similarity search
- `POST /api/v1/analytics/rag/ingest/suppliers/` - Auto-ingest supplier profiles
- `POST /api/v1/analytics/rag/ingest/insights/` - Auto-ingest historical insights
- `POST /api/v1/analytics/rag/refresh/` - Refresh all documents
- `GET /api/v1/analytics/rag/stats/` - Document statistics

### Phase 4 Implementation Details (Hallucination Prevention)

**Files Created:**
- `backend/apps/analytics/ai_validation.py` - `LLMResponseValidator` class with comprehensive validation

**Validation Features:**
- Monetary value validation against total spend (prevents savings > spend claims)
- Supplier/category name verification against organization data
- Date range validation against transaction data bounds
- Percentage validation (0-100% range)
- Savings estimate cross-validation against predicted values

**Confidence Adjustment:**
- Critical errors: -30% confidence
- Errors: -15% confidence
- Warnings: -5% confidence

**Integration:**
- Validation integrated into `AIProviderManager.enhance_insights()`
- Validation integrated into `AIProviderManager.deep_analysis()`
- Validation integrated into `AIProviderManager.analyze_single_insight()`
- Validation results logged to `LLMRequestLog` for observability
- `CRITICAL CONSTRAINTS` added to `PROCUREMENT_SYSTEM_PROMPT`

### Phase 5 Implementation Details (Streaming & Interactive Features)

**Files Created:**
- `backend/ai_streaming/main.py` - FastAPI streaming service with SSE for real-time LLM responses
- `backend/ai_streaming/__init__.py` - Module initialization
- `frontend/src/components/AIInsightsChat.tsx` - Chat component with streaming support

**Files Modified:**
- `backend/requirements.txt` - Added FastAPI, uvicorn, pyjwt dependencies
- `backend/apps/analytics/views.py` - Added `ai_chat_stream()` and `ai_quick_query()` endpoints
- `backend/apps/analytics/urls.py` - Added chat streaming routes
- `frontend/src/hooks/useAIInsights.ts` - Added `useAIChatStream()` and `useAIQuickQuery()` hooks
- `frontend/src/pages/ai-insights/index.tsx` - Integrated AI Chat tab

**API Endpoints:**
- `POST /api/v1/analytics/ai-insights/chat/stream/` - Full chat streaming with message history
- `POST /api/v1/analytics/ai-insights/chat/quick/` - Single-turn quick query streaming

**Frontend Features:**
- SSE event parsing with AbortController for cancellable streams
- Suggested prompts for common procurement questions
- Message history with real-time streaming display
- Three-tab UI: Insights, ROI Tracking, AI Chat

**Verification:**
- TypeScript check: Passed
- Backend tests: 149 passed
- Frontend tests: 812 passed

### Phase 6 Implementation Details (Batch Processing & Automation)

**Files Modified:**
- `backend/apps/analytics/tasks.py` - Added 5 new batch processing tasks
- `backend/config/celery.py` - Added Celery Beat schedule configuration

**New Celery Tasks:**

| Task | Schedule | Purpose |
|------|----------|---------|
| `batch_generate_insights` | Daily 2:00 AM | Generate base AI insights for all active organizations |
| `batch_enhance_insights` | Daily 2:30 AM | Enhance insights with external AI for orgs with AI enabled |
| `cleanup_semantic_cache` | Daily 3:00 AM | Clean expired, orphaned, and low-value cache entries |
| `cleanup_llm_request_logs` | Daily 3:30 AM | Archive/delete LLM logs older than 30 days |
| `refresh_rag_documents` | Weekly Sunday 4:00 AM | Refresh RAG document embeddings for all organizations |

**Task Features:**
- All tasks use `@shared_task` with retry configuration (max_retries=2)
- Automatic retry with exponential backoff for transient failures
- Time limits (soft + hard) to prevent runaway tasks
- Comprehensive logging and result reporting
- Partial success handling - continues processing other orgs on individual failures

**Celery Beat Schedule:**
```python
app.conf.beat_schedule = {
    'nightly-insight-generation': {
        'task': 'batch_generate_insights',
        'schedule': crontab(hour=2, minute=0),
    },
    'nightly-insight-enhancement': {
        'task': 'batch_enhance_insights',
        'schedule': crontab(hour=2, minute=30),
    },
    'cleanup-semantic-cache': {
        'task': 'cleanup_semantic_cache',
        'schedule': crontab(hour=3, minute=0),
    },
    'cleanup-llm-logs': {
        'task': 'cleanup_llm_request_logs',
        'schedule': crontab(hour=3, minute=30),
    },
    'weekly-rag-refresh': {
        'task': 'refresh_rag_documents',
        'schedule': crontab(hour=4, minute=0, day_of_week='sunday'),
    },
}
```

**Verification:**
- Backend tests: 149 passed
- Celery configuration loads correctly with all 5 scheduled tasks
- All batch tasks import and register successfully

---

## Executive Summary

Transform the AI Insights module from a capable analytics tool into an **outstanding, production-grade LLM-powered procurement intelligence platform**. The current implementation has solid foundations (multi-provider LLM, async processing, caching, ROI tracking). This plan enhances it with cutting-edge patterns: **prompt caching (90% cost reduction)**, **semantic caching (73% additional savings)**, **RAG for document intelligence**, **streaming responses**, and **robust hallucination prevention**.

**Key Enhancements:**
1. Anthropic Prompt Caching - 90% cost reduction on repeated system prompts
2. Semantic Caching with pgvector - 73% fewer LLM calls for similar queries
3. RAG Layer - Document intelligence for supplier profiles, contracts, policies
4. Hallucination Prevention - Validation layer to catch fabricated data
5. Tiered Model Selection - Haiku for simple, Sonnet for standard, Opus for deep analysis
6. Streaming Responses - FastAPI microservice for real-time chat
7. Batch Processing - 50% discount on overnight insight generation
8. Conversational Interface - Interactive AI chat for procurement Q&A
9. LLM Observability - Cost tracking, latency metrics, cache efficiency

**Expected Results:**
- Cost per insight: $0.006 → <$0.001
- Cache hit rate: 30% → >80%
- Hallucination rate: Unknown → <1%
- Response latency (p95): 5s → <2s

---

## Current State Analysis

### Strengths (Keep)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Multi-provider LLM support | ✅ Done | Claude + OpenAI fallback in `ai_providers.py` |
| Tool/function calling | ✅ Done | Structured output via `INSIGHT_ENHANCEMENT_TOOL` |
| 4 insight types | ✅ Done | Cost, Risk, Anomaly, Consolidation |
| Redis caching (1hr TTL) | ✅ Done | `ai_cache.py` with hash-based keys |
| Async processing | ✅ Done | Celery tasks + polling endpoints |
| ROI tracking | ✅ Done | `InsightFeedback` model with full CRUD |
| Deduplication | ✅ Done | Priority-based savings deduplication |
| Deep analysis | ✅ Done | 7-part structured output per insight |

### Gaps (Fix)

| Gap | Impact | Priority |
|-----|--------|----------|
| No Anthropic prompt caching | 10x higher API costs | **Critical** |
| No semantic caching | Similar queries re-processed | High |
| No RAG/vector search | Limited document intelligence | High |
| No streaming responses | Poor UX for long responses | Medium |
| Basic hallucination prevention | Risk of inaccurate financial data | **Critical** |
| No tiered model selection | Over-paying for simple queries | High |
| No LLM cost tracking | No visibility into spend | Medium |
| No conversational interface | Limited interactivity | Medium |

---

## Enhancement Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AI Insights Module v3.0                           │
└─────────────────────────────────────────────────────────────────────────┘

┌────────────────────┐     ┌────────────────────┐     ┌──────────────────┐
│   Query Router     │────▶│   Model Selector   │────▶│  Response Flow   │
│  (Intent + Cost)   │     │  (Haiku/Sonnet/    │     │ (Stream/Batch/   │
│                    │     │   Opus)            │     │  Sync)           │
└────────────────────┘     └────────────────────┘     └──────────────────┘
         │                          │                          │
         ▼                          ▼                          ▼
┌────────────────────┐     ┌────────────────────┐     ┌──────────────────┐
│  Semantic Cache    │     │  Prompt Cache      │     │  Validation      │
│  (pgvector)        │     │  (Anthropic API)   │     │  Layer           │
│  Similarity: 0.90  │     │  90% cost savings  │     │  (Anti-halluc.)  │
└────────────────────┘     └────────────────────┘     └──────────────────┘
         │                          │                          │
         ▼                          ▼                          ▼
┌────────────────────┐     ┌────────────────────┐     ┌──────────────────┐
│  RAG Layer         │     │  Context Builder   │     │  Observability   │
│  (Supplier Docs,   │     │  (Organization,    │     │  (Cost, Latency, │
│   Contracts,       │     │   Industry,        │     │   Tokens, Cache) │
│   Best Practices)  │     │   Historical)      │     │                  │
└────────────────────┘     └────────────────────┘     └──────────────────┘
```

---

## Implementation Plan

### Phase 1: Cost Optimization & Reliability (Week 1-2)

#### 1.1 Implement Anthropic Prompt Caching

**File**: `backend/apps/analytics/ai_providers.py`

Add `cache_control` to system prompts for 90% cost reduction on cached reads:

```python
# Cache system prompt (rarely changes)
SYSTEM_PROMPT_BLOCK = {
    "type": "text",
    "text": PROCUREMENT_SYSTEM_PROMPT,
    "cache_control": {"type": "ephemeral"}  # 5-min cache
}

# Cache organization context (changes on data upload)
ORG_CONTEXT_BLOCK = {
    "type": "text",
    "text": json.dumps(organization_context),
    "cache_control": {"type": "ephemeral"}
}
```

**Changes**:
- Add `_build_cacheable_system_prompt()` method to AnthropicProvider
- Structure message blocks with cache_control where appropriate
- Track cache read/write metrics via response headers

#### 1.2 Add Tiered Model Selection

**File**: `backend/apps/analytics/ai_services.py`

Route queries to appropriate model tier based on complexity:

| Query Type | Model | Cost | Example |
|------------|-------|------|---------|
| Simple categorization | Haiku | $0.25/M | "What insight type is this?" |
| Standard analysis | Sonnet | $3/M | "Enhance these 5 insights" |
| Deep investigation | Opus | $15/M | "Complex root cause analysis" |

**Changes**:
- Add `classify_query_complexity()` method (use Haiku for classification)
- Add `select_model_for_task()` in AIProviderManager
- Update all enhancement/analysis methods to use dynamic model selection

#### 1.3 LLM Request Logging & Cost Tracking

**File**: `backend/apps/analytics/models.py`

```python
class LLMRequestLog(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=50)  # enhance, deep_analysis, chat
    model_used = models.CharField(max_length=50)
    tokens_input = models.IntegerField()
    tokens_output = models.IntegerField()
    latency_ms = models.IntegerField()
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6)
    cache_hit = models.BooleanField(default=False)
    prompt_cache_read_tokens = models.IntegerField(default=0)
    prompt_cache_write_tokens = models.IntegerField(default=0)
    validation_passed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Changes**:
- Add model with migration
- Log all LLM calls from AIProviderManager
- Add `/api/v1/analytics/ai-insights/usage/` endpoint for cost dashboard
- Add Prometheus metrics for LLM usage

---

### Phase 2: Semantic Caching (Week 2-3)

#### 2.1 Install pgvector Extension

**File**: `docker-compose.yml`

Add pgvector to PostgreSQL for vector similarity search.

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    # ... existing config
```

#### 2.2 Semantic Cache Model

**File**: `backend/apps/analytics/models.py`

```python
from pgvector.django import VectorField

class SemanticCache(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    query_text = models.TextField()
    query_embedding = VectorField(dimensions=1536)  # OpenAI text-embedding-3-small
    response_json = models.JSONField()
    query_hash = models.CharField(max_length=64, db_index=True)
    hit_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['organization', 'expires_at']),
        ]
```

#### 2.3 Semantic Cache Service

**New File**: `backend/apps/analytics/semantic_cache.py`

```python
class SemanticCacheService:
    SIMILARITY_THRESHOLD = 0.90

    def lookup(self, org_id: int, query: str) -> Optional[dict]:
        """Find semantically similar cached response"""
        embedding = self._get_embedding(query)

        similar = SemanticCache.objects.filter(
            organization_id=org_id,
            expires_at__gt=timezone.now()
        ).annotate(
            similarity=CosineDistance('query_embedding', embedding)
        ).filter(
            similarity__lte=(1 - self.SIMILARITY_THRESHOLD)
        ).order_by('similarity').first()

        if similar:
            similar.hit_count += 1
            similar.save(update_fields=['hit_count'])
            return similar.response_json
        return None

    def store(self, org_id: int, query: str, response: dict, ttl_hours: int = 1):
        """Cache response with embedding"""
        embedding = self._get_embedding(query)
        SemanticCache.objects.create(
            organization_id=org_id,
            query_text=query,
            query_embedding=embedding,
            response_json=response,
            query_hash=hashlib.sha256(query.encode()).hexdigest(),
            expires_at=timezone.now() + timedelta(hours=ttl_hours)
        )
```

**Expected Impact**: 73% cost reduction via semantic deduplication

---

### Phase 3: RAG for Document Intelligence (Week 3-4)

#### 3.1 Document Embedding Models

**File**: `backend/apps/analytics/models.py`

```python
class DocumentType(models.TextChoices):
    SUPPLIER_PROFILE = 'supplier_profile', 'Supplier Profile'
    CONTRACT = 'contract', 'Contract'
    POLICY = 'policy', 'Procurement Policy'
    BEST_PRACTICE = 'best_practice', 'Best Practice'
    HISTORICAL_INSIGHT = 'historical_insight', 'Historical Insight'

class EmbeddedDocument(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50, choices=DocumentType.choices)
    title = models.CharField(max_length=255)
    content = models.TextField()
    content_embedding = VectorField(dimensions=1536)
    metadata = models.JSONField(default=dict)  # supplier_id, category, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['organization', 'document_type']),
        ]
```

#### 3.2 RAG Service

**New File**: `backend/apps/analytics/rag_service.py`

```python
class RAGService:
    TOP_K = 5

    def search(self, org_id: int, query: str, doc_types: list = None) -> list[dict]:
        """Vector search for relevant documents"""
        embedding = self._get_embedding(query)

        qs = EmbeddedDocument.objects.filter(organization_id=org_id)
        if doc_types:
            qs = qs.filter(document_type__in=doc_types)

        return list(qs.annotate(
            similarity=1 - CosineDistance('content_embedding', embedding)
        ).filter(
            similarity__gte=0.7
        ).order_by('-similarity')[:self.TOP_K].values(
            'title', 'content', 'document_type', 'metadata', 'similarity'
        ))

    def augment_context(self, org_id: int, query: str, base_context: dict) -> dict:
        """Augment LLM context with relevant documents"""
        docs = self.search(org_id, query)

        if docs:
            base_context['relevant_documents'] = [
                {
                    'type': d['document_type'],
                    'title': d['title'],
                    'content': d['content'][:500],  # Truncate for token limit
                    'relevance': f"{d['similarity']:.2%}"
                }
                for d in docs
            ]

        return base_context
```

#### 3.3 Document Ingestion Pipeline

**New File**: `backend/apps/analytics/document_ingestion.py`

- Import supplier profiles from Supplier model
- Import contracts (new Contract model or file upload)
- Import procurement policies (markdown files)
- Embed successful historical insights (from InsightFeedback with outcome=success)

---

### Phase 4: Hallucination Prevention (Week 4-5)

#### 4.1 Validation Layer

**New File**: `backend/apps/analytics/ai_validation.py`

```python
class LLMResponseValidator:
    """Post-LLM validation to prevent hallucinations"""

    def validate(self, response: dict, source_data: dict, org_id: int) -> dict:
        errors = []

        # Validate monetary values against database
        if 'total_savings' in response:
            db_max = source_data.get('total_spend', 0)
            if response['total_savings'] > db_max:
                errors.append({
                    'field': 'total_savings',
                    'issue': f"Claimed savings ${response['total_savings']:,.2f} exceeds total spend ${db_max:,.2f}",
                    'severity': 'critical'
                })

        # Validate supplier names exist
        for supplier in response.get('suppliers', []):
            if not Supplier.objects.filter(
                organization_id=org_id,
                name__iexact=supplier
            ).exists():
                errors.append({
                    'field': 'suppliers',
                    'issue': f"Unknown supplier: {supplier}",
                    'severity': 'warning'
                })

        # Validate category names
        for category in response.get('categories', []):
            if not Category.objects.filter(
                organization_id=org_id,
                name__iexact=category
            ).exists():
                errors.append({
                    'field': 'categories',
                    'issue': f"Unknown category: {category}",
                    'severity': 'warning'
                })

        # Validate date ranges
        if 'date_range' in response:
            if response['date_range']['start'] > response['date_range']['end']:
                errors.append({
                    'field': 'date_range',
                    'issue': 'Start date after end date',
                    'severity': 'error'
                })

        # Calculate adjusted confidence
        critical_errors = len([e for e in errors if e['severity'] == 'critical'])
        warning_errors = len([e for e in errors if e['severity'] == 'warning'])

        original_confidence = response.get('confidence', 0.8)
        adjusted_confidence = original_confidence * (
            1 - (critical_errors * 0.3) - (warning_errors * 0.05)
        )

        return {
            'validated': len([e for e in errors if e['severity'] in ['critical', 'error']]) == 0,
            'errors': errors,
            'confidence_original': original_confidence,
            'confidence_adjusted': max(0, adjusted_confidence),
            'warnings_count': warning_errors,
            'critical_count': critical_errors
        }
```

#### 4.2 Enhanced Prompts with Constraints

**File**: `backend/apps/analytics/ai_services.py`

Add constraint block to all prompts:

```python
VALIDATION_CONSTRAINTS = """
CRITICAL CONSTRAINTS:
1. NEVER state monetary values without citing source data
2. NEVER extrapolate trends beyond provided date range
3. NEVER reference suppliers/categories not in the provided data
4. ALWAYS flag uncertainty with confidence scores
5. ALWAYS validate percentages sum correctly (e.g., category breakdown = 100%)

REQUIRED CITATIONS:
- Spending claims: Reference specific data points
- Supplier counts: Exact from provided data
- Date ranges: Only within {start_date} to {end_date}

IF UNCERTAIN: State "Based on available data, [claim] (confidence: X%)"
"""
```

---

### Phase 5: Streaming & Interactive Features (Week 5-6)

#### 5.1 FastAPI Streaming Service

**New File**: `backend/ai_streaming/main.py`

Separate FastAPI service for streaming LLM responses:

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from anthropic import AsyncAnthropic

app = FastAPI()
client = AsyncAnthropic()

@app.post("/api/ai/stream")
async def stream_response(request: Request):
    data = await request.json()

    async def event_stream():
        async with client.messages.stream(
            model=data.get('model', 'claude-sonnet-4-20250514'),
            max_tokens=data.get('max_tokens', 2000),
            system=data['system_prompt'],
            messages=data['messages']
        ) as stream:
            async for text in stream.text_stream:
                yield f"data: {json.dumps({'token': text})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

#### 5.2 Conversational AI Chat

**New File**: `frontend/src/components/AIInsightsChat.tsx`

Add chat interface for interactive procurement Q&A:

- "What suppliers have the highest risk concentration?"
- "Show me cost optimization opportunities in IT Equipment"
- "Explain why this anomaly was flagged"
- "Compare Q1 vs Q2 spending patterns"

**Features**:
- Streaming response display
- Message history with context
- Quick action buttons for common queries
- Export conversation as report

---

### Phase 6: Batch Processing & Automation (Week 6-7)

#### 6.1 Batch API for Overnight Insights

**File**: `backend/apps/analytics/tasks.py`

```python
@shared_task(name='batch_generate_insights')
def batch_generate_insights():
    """Nightly batch generation using Anthropic Batch API (50% discount)"""
    organizations = Organization.objects.filter(is_active=True)

    batch_requests = []
    for org in organizations:
        insights = AIInsightsService(org).generate_base_insights()

        if insights:
            batch_requests.append({
                "custom_id": f"insights_{org.id}",
                "params": {
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 2048,
                    "messages": [build_enhancement_prompt(insights, org)]
                }
            })

    if batch_requests:
        batch_job = client.batches.create(requests=batch_requests)
        # Store job ID, poll for completion
        cache.set(f'batch_job_{batch_job.id}', 'processing', timeout=86400)
        return batch_job.id
```

#### 6.2 Scheduled Insight Refresh

**File**: `backend/config/celery.py`

```python
app.conf.beat_schedule = {
    'nightly-insight-generation': {
        'task': 'batch_generate_insights',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'cleanup-expired-cache': {
        'task': 'cleanup_semantic_cache',
        'schedule': crontab(hour=3, minute=0),
    },
}
```

---

### Phase 7: Frontend Enhancements (Week 7-8)

#### 7.1 Enhanced AI Insights Page

**File**: `frontend/src/pages/ai-insights/index.tsx`

**New Features**:
- **AI Chat Tab**: Conversational interface with streaming
- **Cost Dashboard**: LLM usage and savings from caching
- **Document Intelligence**: RAG search for supplier docs
- **Comparison Mode**: Side-by-side insight analysis
- **Bulk Actions**: Select multiple insights for batch operations
- **Timeline View**: Historical insights with outcomes

#### 7.2 New Hooks

**File**: `frontend/src/hooks/useAIInsights.ts`

```typescript
// Streaming chat
export function useAIChatStream() { ... }

// LLM usage metrics
export function useLLMUsageMetrics() { ... }

// Document search (RAG)
export function useDocumentSearch(query: string) { ... }

// Semantic cache stats
export function useCacheEfficiency() { ... }
```

---

## File Changes Summary

### New Files

| Path | Purpose |
|------|---------|
| `backend/apps/analytics/semantic_cache.py` | Semantic caching service |
| `backend/apps/analytics/rag_service.py` | RAG document search |
| `backend/apps/analytics/document_ingestion.py` | Document embedding pipeline |
| `backend/apps/analytics/ai_validation.py` | Hallucination prevention |
| `backend/ai_streaming/main.py` | FastAPI streaming service |
| `frontend/src/components/AIInsightsChat.tsx` | Chat interface |

### Modified Files

| Path | Changes |
|------|---------|
| `backend/apps/analytics/ai_providers.py` | Add prompt caching, tiered models |
| `backend/apps/analytics/ai_services.py` | Integrate validation, RAG, semantic cache |
| `backend/apps/analytics/models.py` | Add LLMRequestLog, SemanticCache, EmbeddedDocument |
| `backend/apps/analytics/views.py` | Add usage, chat, document endpoints |
| `backend/apps/analytics/tasks.py` | Add batch processing |
| `backend/config/celery.py` | Add scheduled tasks |
| `docker-compose.yml` | Add pgvector, FastAPI service |
| `frontend/src/pages/ai-insights/index.tsx` | Add chat, usage dashboard |
| `frontend/src/hooks/useAIInsights.ts` | Add streaming, usage hooks |

---

## Cost Impact Analysis

### Current State (Estimated)

- 10K insights/month
- 2000 tokens avg/request
- All Sonnet: ~$60/month

### After Optimization

| Optimization | Reduction |
|--------------|-----------|
| Prompt caching | 90% on cached portions |
| Semantic caching | 73% fewer LLM calls |
| Tiered models | 50% (simple queries use Haiku) |
| Batch API | 50% on overnight jobs |

**Projected Cost**: ~$5-10/month for same volume

### ROI

- Engineering effort: ~8 weeks
- Monthly savings: ~$50 (at 10K requests)
- Real value: 10x better UX, 99% fewer hallucinations, document intelligence

---

## Verification Plan

### Backend Testing

```bash
# Run AI insights tests
docker-compose exec backend pytest apps/analytics/tests/test_ai_services.py -v

# Test semantic cache
docker-compose exec backend pytest apps/analytics/tests/test_semantic_cache.py -v

# Test RAG service
docker-compose exec backend pytest apps/analytics/tests/test_rag_service.py -v

# Test validation layer
docker-compose exec backend pytest apps/analytics/tests/test_ai_validation.py -v
```

### Frontend Testing

```bash
cd frontend
pnpm test:run src/pages/ai-insights/
pnpm test:run src/hooks/__tests__/useAIInsights.test.ts
```

### Integration Testing

1. Generate insights with prompt caching enabled
2. Query similar questions to verify semantic cache hits
3. Upload supplier doc, verify RAG retrieval
4. Test streaming chat response
5. Verify validation catches fabricated supplier names
6. Check LLM usage dashboard metrics

### Manual Verification

1. Compare insight quality before/after
2. Verify cost reduction in Anthropic dashboard
3. Test chat for procurement questions
4. Verify documents appear in relevant insights

---

## Dependencies

### Python Packages

```txt
anthropic>=0.40.0       # Prompt caching support
pgvector>=0.3.0         # PostgreSQL vector search
sentence-transformers>=2.0.0  # For embeddings (alternative to OpenAI)
fastapi>=0.110.0        # Streaming service
uvicorn>=0.27.0         # ASGI server
```

### Infrastructure

- PostgreSQL with pgvector extension
- Redis (existing)
- Optional: Separate container for FastAPI streaming service

---

## Timeline Summary

| Week | Phase | Key Deliverables |
|------|-------|------------------|
| 1-2 | Cost Optimization | Prompt caching, tiered models, usage logging |
| 2-3 | Semantic Caching | pgvector setup, similarity search, cache service |
| 3-4 | RAG Layer | Document models, embedding pipeline, search API |
| 4-5 | Validation | Hallucination prevention, constraint prompts |
| 5-6 | Streaming | FastAPI service, chat interface |
| 6-7 | Batch Processing | Overnight jobs, scheduled refresh |
| 7-8 | Frontend Polish | Usage dashboard, chat tab, bulk actions |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| LLM cost per insight | ~$0.006 | <$0.001 |
| Cache hit rate | 30% (hash) | >80% (semantic) |
| Hallucination rate | Unknown | <1% (validated) |
| Response latency (p95) | 5s | <2s (streaming) |
| User satisfaction | N/A | >4.5/5 stars |
| Document retrieval relevance | N/A | >85% |

---

## References

### LLM Integration & Observability
- [Top 10 LLM observability tools - Braintrust](https://www.braintrust.dev/articles/top-10-llm-observability-tools-2025)
- [Enterprise LLM Integration - Nitor Infotech](https://www.nitorinfotech.com/blog/enterprise-llm-integration-challenges-and-best-practices/)

### Claude for Financial Services
- [Claude for Financial Services - Anthropic](https://www.anthropic.com/news/claude-for-financial-services)
- [S&P Global and Anthropic Integration](https://press.spglobal.com/2025-07-15-S-P-Global-and-Anthropic-Announce-Integration)

### Prompt Engineering
- [Financial Analysis with Amazon Bedrock - AWS](https://aws.amazon.com/blogs/industries/empowering-analysts-to-perform-financial-statement-analysis)
- [Prompt Engineering for Finance - Deloitte](https://www.deloitte.com/us/en/services/consulting/articles/prompt-engineering-for-finance.html)

### RAG & Caching
- [What is RAG? - AWS](https://aws.amazon.com/what-is/retrieval-augmented-generation/)
- [Semantic caching for LLMs - Redis](https://redis.io/blog/what-is-semantic-caching/)
- [Prompt caching - Claude Docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

### Hallucination Prevention
- [Mitigating LLM Hallucination in Banking - MIT](https://dspace.mit.edu/bitstream/handle/1721.1/162944/sert-dsert-meng-eecs-2025-thesis.pdf)
- [LLM Hallucination Detection - DeepChecks](https://www.deepchecks.com/llm-hallucination-detection-and-mitigation-best-techniques/)

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-08 | Claude Code | Initial document |
| 2.0 | 2026-01-09 | Claude Code | Updated status for implemented features |
| 3.0 | 2026-01-23 | Claude Code | Major revision: prompt caching, semantic caching, RAG, validation layer, streaming, batch processing |
| 3.1 | 2026-01-23 | Claude Code | Phase 4 complete: Hallucination Prevention with LLMResponseValidator |
| 3.2 | 2026-01-23 | Claude Code | Phase 5 complete: FastAPI SSE streaming, Django chat endpoints, AIInsightsChat component |

---

*This document is part of the Versatex Analytics technical documentation.*
