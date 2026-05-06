# AI Insights — Claude Reference

> **When to read this:** Editing files in `backend/apps/analytics/ai_*.py`, `rag_*.py`, or anything touching `LLMRequestLog` / `SemanticCache` / `EmbeddedDocument` models, or frontend hooks in `useAIInsights.ts`.
> **You can skip this if:** Working on non-AI analytics, P2P, or frontend pages that don't render AI insights or chat.

## Core invariants

1. **No silent fallback when AI enhancement is unavailable (Convention §6).** When `AIInsightsService` cannot enhance because no API key is configured, the response MUST omit the `ai_enhancement` key, and the frontend MUST render a "(Deterministic)" label. **Never silently substitute deterministic output for AI-enhanced output.**
2. **Tri-state enhancement status is a future feature, not current.** §6 covers only the no-key case. LLM-failure fallback is currently silent and tracked as Cross-Module Open in `docs/ACCURACY_AUDIT.md`.
3. **`AIInsightsService` calls Django ORM directly, NOT analytics services.** This divergence is documented per Convention §8 ("document don't refactor"). Do not "fix" by routing through analytics services unless coordinating a Cross-Module Open close.
4. **All AI endpoints scope by `request.organization`** — same tenant isolation invariant as P2P.
5. **Sensitive preference keys must be added to BOTH `MASKED_PREFERENCE_KEYS` AND masking sites.** Per Convention §5: masking happens in `UserProfileSerializer.to_representation` AND `UserPreferencesView.get` (which bypasses the serializer). Both sites required.

## Primitives — use these, don't re-implement

| Primitive | Location | Purpose |
|---|---|---|
| `AIInsightsService.deduplicate_savings` | `backend/apps/analytics/ai_services.py:873` (instance method) | Prevents double-counting savings across insight types |
| `UserProfile.mask_preferences` | `backend/apps/authentication/models.py` (staticmethod) | Masks sensitive preference keys per `MASKED_PREFERENCE_KEYS` |

## Known divergences (and why they exist)

- **`AIInsightsService` direct ORM access.** Bypasses analytics services. Documented per Convention §8 — refactor only if user-visible wrong number, not for DRY-ness alone.
- **Silent LLM-failure fallback.** When the LLM call fails (network, rate limit, etc.), enhancement falls back silently. Tracked as Cross-Module Open. Do not change without addressing the broader tri-state design.

## Cross-cutting gotchas

- **Two-site preference allowlist gate (Convention §5).** New `UserProfile.preferences` keys must be added to BOTH:
  - `ALLOWED_PREFERENCE_KEYS` at `backend/apps/authentication/models.py:167-170`
  - An explicit `Field()` declaration on `UserPreferencesSerializer` at `backend/apps/authentication/serializers.py`

  Otherwise the key is silently dropped at one of the two layers.
- **Sensitive keys need three sites:** `ALLOWED_PREFERENCE_KEYS`, `MASKED_PREFERENCE_KEYS`, AND masking call in `UserPreferencesView.get`.
- **Prompt caching strategy (90% cost reduction on cached reads).** Anthropic prompt caching applied to system prompts. Don't break the cache by injecting per-request data into cached blocks.
- **Semantic cache 0.90 similarity threshold.** Below 0.90, treat as miss. Tunable via `SemanticCache` model — but changes affect cost/quality tradeoff materially.
- **RAG embedding refresh runs Sundays 4 AM (Celery Beat).** Re-embeds supplier profiles + insights. Don't trigger ad-hoc except via the management endpoint `/api/v1/analytics/rag/refresh/`.
- **Streaming chat uses SSE** at `/api/v1/analytics/ai-insights/chat/stream/`. Frontend uses `useAIChatStream()` hook which manages message state across stream events.

## API surface (orientation only)

AI Insights endpoints live under `/api/v1/analytics/ai-insights/` (insights, feedback, chat, usage) and `/api/v1/analytics/rag/` (documents, search, ingest). Routing in `backend/apps/analytics/urls.py`.

Frontend hooks in `frontend/src/hooks/useAIInsights.ts`.

To enumerate current endpoints: `grep -E "path\(" backend/apps/analytics/urls.py | grep -E "ai-insights|rag"`.

## Models

| Model | Purpose | Location |
|---|---|---|
| `LLMRequestLog` | Tracks all LLM calls — tokens, cost, latency, cache hit | `backend/apps/analytics/models.py` |
| `SemanticCache` | pgvector embeddings for similarity search | `backend/apps/analytics/models.py` |
| `EmbeddedDocument` | RAG document store with vector embeddings | `backend/apps/analytics/models.py` |
| `InsightFeedback` | ROI tracking — actions and outcomes | `backend/apps/analytics/models.py` |

## Celery Beat schedule

| Task | Schedule | Purpose |
|---|---|---|
| `batch_generate_insights` | 2:00 AM daily | Generate insights for all orgs |
| `batch_enhance_insights` | 2:30 AM daily | AI-enhance for orgs with API keys |
| `cleanup_semantic_cache` | 3:00 AM daily | Remove expired/orphaned entries |
| `cleanup_llm_request_logs` | 3:30 AM daily | Archive logs older than 30 days |
| `refresh_rag_documents` | 4:00 AM Sundays | Re-embed supplier profiles + insights |

## Test patterns

- AI service tests: `backend/apps/analytics/tests/test_ai_services.py`
- Run: `docker-compose exec backend pytest backend/apps/analytics/tests/test_ai_services.py -v`
- Mock LLM calls — never hit the live API in tests

## AI streaming throttle quotas (Finding #7 follow-up)

The two streaming endpoints (`ai_chat_stream`, `ai_quick_query`) carry `@throttle_classes([AIInsightsThrottle])` (added Phase 0 task 0.3 — drift-guard test at `backend/apps/analytics/tests/test_streaming_throttle_driftguard.py`).

**Rate:** `30/hour` per authenticated user. Settings-driven via `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['ai_insights']` at `backend/config/settings.py:224`. The throttle class itself is a thin `ScopedRateThrottle` subclass at `backend/apps/analytics/views.py:180-182` (scope `'ai_insights'`).

**Scope key:** DRF's `ScopedRateThrottle.get_cache_key` keys by `request.user.pk` for authenticated requests. The 30/hour budget is per-user, not per-org. An org with N active users gets up to N × 30 calls/hour collectively.

**Cost ceiling per user under throttle:**

Per-call cost ~$0.032 at default Sonnet model (500 input + 2K output tokens, list pricing as of 2026-05-04 — see Finding #7 in `docs/codebase-review-2026-05-04-v2.md`).

| Window | Calls | Cost |
|---|---|---|
| Per hour, per user | 30 | $0.96 |
| Per day, per user | 720 | $23.04 |
| Per day, 50-user org (worst case, all users saturating) | 36,000 | ~$1,152 |

The 50-user assumption is illustrative — actual per-org ceiling scales linearly with active-user count. Real-world spend is far lower because typical sessions don't saturate the throttle. The number worth communicating to ops is **per-user-per-day max ≈ $23**.

**Override (emergency rate change):**

Edit `DEFAULT_THROTTLE_RATES['ai_insights']` at `backend/config/settings.py:224` and redeploy. The rate is settings-driven, so an env-var override is a one-line patch (`'ai_insights': config('AI_INSIGHTS_THROTTLE_RATE', default='30/hour')`) if zero-deploy override becomes a requirement — not currently wired.

There is no admin-UI / runtime path to change the rate. By design — throttle rate is an operational guarantee, not a tunable.

For per-user exceptions (a power user needs more headroom), DRF supports a `get_cache_key` override pattern; not currently configured. If implemented, document the override path here at the time of implementation.

**Related cost-containment controls:**

- **Payload bounds (Finding B10, Phase 4 task 4.1):** `AI_CHAT_MAX_MESSAGES`, `AI_CHAT_MAX_MESSAGE_CONTENT_CHARS`, `AI_CHAT_MAX_PAYLOAD_BYTES` at `backend/config/settings.py:458-464`. Prevents single-call cost-blast (e.g., one 10MB chat history hitting the LLM with millions of input tokens) that the per-call throttle alone cannot stop.
- **Model allowlist (Finding #8 permanent, Phase 4 task 4.2):** `AI_CHAT_ALLOWED_MODELS` / `AI_CHAT_DEFAULT_MODEL` at `backend/config/settings.py:475-483`. Prevents Opus escalation (~5× Sonnet pricing) via client-supplied `model` parameter.

These three controls (throttle + payload bounds + model allowlist) together form the streaming cost-containment story. Throttle bounds call volume; payload bounds cap per-call input size; model allowlist caps per-token unit cost.

## See also

- `backend/apps/analytics/ai_services.py` — `AIInsightsService`
- `backend/apps/analytics/rag_services.py` — RAG / embedding service
- `backend/apps/analytics/models.py` — `LLMRequestLog`, `SemanticCache`, `EmbeddedDocument`, `InsightFeedback`
- `frontend/src/hooks/useAIInsights.ts` — frontend hooks
- `docs/ACCURACY_AUDIT.md` — Conventions §5 (preferences), §6 (no silent fallback), §8 (document don't refactor)
- `docs/CHANGELOG.md` — v2.6 (AI Insights ROI) and v2.9 (LLM enhancement) historical context
- `docs/codebase-review-2026-05-04-v2.md` — Finding #7 (throttle), Finding #8 (model allowlist), Finding B10 (payload bounds)
