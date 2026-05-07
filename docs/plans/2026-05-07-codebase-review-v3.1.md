# Codebase Review v3.1 — Differential + Module Deep-Dive

**Date:** 2026-05-07
**Approach:** 6 parallel `feature-dev:code-reviewer` agents — 4 backend modules (auth, procurement, analytics, reports), full frontend, plus cross-cutting differential sweep (tests/infra/config/deps/observability).
**Premise:** v2.12 (45/45 closed 2026-05-06) and v3.0 (37 commits, 4 phases, closed 2026-05-06) just landed. This pass surfaces what those audits did NOT prioritize.
**Out of scope:** Already-closed findings; deferred items per `docs/REMEDIATION-OPEN-ITEMS.md` (Task 1.3 Report.is_public, Task 5.4 aging DB-side aggregation).

---

## Verification status (2026-05-07)

All 71 findings independently verified by 6 parallel `general-purpose` agents reading cited file:line locations. **Result: 71/71 verified in substance, 0 outright false-positives.**

| Section | Findings | Verified | Corrections | False-Positive | Reclassification |
|---|---|---|---|---|---|
| §2 Authentication | 9 | 9 | 0 | 0 | 0 |
| §3 Procurement | 15 | 15 | 2 (line/scope) | 0 | 0 |
| §4 Analytics | 18 | 18 | 1 (AN-TD4 framing) | 0 | 0 |
| §5 Reports | 12 | 12 | 1 (R-TD2 line) | 0 | 0 |
| §6 Frontend | 14 | 14 | 3 (scope/lines) | 0 | 1 (F-TD4) |
| §7 Cross-cutting | 17 | 17 | 3 (filename/scope) | 0 | 0 |
| **Total** | **71** | **71** | **10** | **0** | **1** |

### Corrections (substance preserved, details refined)

- **P-TD1** — Helper duplication is real but not uniform: GoodsReceiptAdmin has 2 of 4 methods, InvoiceAdmin has 3 of 4, PR/PO admins have all 4. Refactor target unchanged.
- **P-TD4** — Float→Decimal cast is on `seed_demo_data.py:323` (not 322-323).
- **AN-TD4** — Bug framing is wrong: `p2p_services.py:596-597` calls `inv.exception_resolved_at.date()` BEFORE subtracting from `invoice_date`, so the subtraction is `date - date`. The TZ-bug claim is incorrect; only the type-mismatch tech-debt aspect (DateTimeField for resolution vs DateField for invoice — meaning early-evening resolutions in non-UTC zones still record as UTC date, off by 1 day) stands. **Severity unchanged but rationale updated.**
- **R-TD2** — Bare `except:` keyword is at `excel.py:259`, `pass` at `:260`. Pattern verified.
- **F-H3 (scope expansion)** — `recharts` is imported by **21 files**, not just the 3 cited. Bundle-bloat impact is broader than originally stated; chunk fix more valuable.
- **F-TD1 (scope correction)** — `key={index}` exists in **7 page files**, not ~14. AI-insights cited lines `:435, :453` use `key={i}` (callback param `i` is acceptable); actual `key={index}` occurrences in that file are at `:501, :521`. Anti-pattern still real but smaller surface.
- **F-TD4 (RECLASSIFICATION)** — The `enhancement_status ?? "unavailable_no_key"` default is **deliberate per accuracy convention §6** with explicit justification comments at `index.tsx:1832-1836` ("backwards compatibility with cached payloads"). **Should be removed from tech-debt list** — it's working as designed.
- **XC-H2** — Cited file `test_switch_org_atomicity.py` doesn't exist; analogous file is `test_concurrent_jsonfield_writes.py`. `--reuse-db` + multiple `TransactionTestCase` claim still verified via `test_signal_on_commit.py`, `test_csv_idempotency.py`, `test_cross_org_fk_check.py`, `test_concurrent_jsonfield_writes.py`.
- **XC-M2** — `ci.yml:50` wraps **isort** (not flake8 as originally stated). Flake8 at `:52-55` does NOT have `continue-on-error`. Black (`:43`) and Prettier (`:287`) `continue-on-error` claims confirmed. Effective gates: 3 → 3 (Black, isort, Prettier).
- **XC-TD3** — `allowedHosts` uses leading-dot syntax (`.manus.computer`), not glob (`*.manus.computer`). Semantically equivalent in Vite (subdomain wildcard); claim's substance unchanged.

### Items that hold without modification

The four critical infrastructure findings I spot-verified myself before writing the report (XC-C1 Dockerfile, R-C2 celery beat, F-H4 vite plugin, X-1 port drift) all match the agent verification.

---

## Executive summary

| Severity | Count | Scope |
|---|---|---|
| **Critical** | 9 | Production correctness/security — fix before next deploy |
| **High** | 22 | Real bugs / leakage / perf cliffs — fix in next sprint |
| **Medium** | 18 | UX/perf degradation, brittle code |
| **Tech-Debt** | 22 | Refactor opportunities, dead code, doc drift (F-TD4 reclassified out → 21) |
| **Total** | **70 (71−1 reclass)** | After verification pass |

**Headline themes** (cross-cutting, addressed in §1 below):

1. **Documentation/port drift** — `docker-compose.yml` defaults to `8001`, CLAUDE.md says `8002`, README says `8001`, `useAIInsights.ts` SSE fallback hardcodes `8001`, axios fallback hardcodes `8000`. Five sources of truth disagree.
2. **Legacy `profile.organization` follow-up** — v2.12 fixed permission classes via `_resolve_target_org`. View `get_queryset` methods, the Reports admin queryset, the `report_share` user lookup, and `CanUploadData/CanDeleteData` were not migrated. Multi-org users see wrong data.
3. **Naive `datetime.now()` / `date.today()`** — v2.12 fixed compliance services. The same anti-pattern resurfaces in `predictive_services.py`, `services/trend.py`, `services/pareto.py`, multiple model properties (`Invoice.is_overdue`, `PR.is_overdue`, `Contract.days_to_expiry`), and `views.py:export_savings_config_pdf`. Affects timezone correctness for users outside server-local time.
4. **Python-side aggregation / N+1 pattern** — `get_supplier_payments_scorecard` (250 round-trips), `compliance_services.py` `prefetch_related` + `values_list` antipattern, `get_aging_overview` 4-pass list iteration, `services/yoy.py:get_detailed_year_over_year` materialises full transaction queryset. Task 5.4 explicitly capped scope; these go beyond.
5. **Deploy pipeline gate gaps** — `deploy.yml` does not depend on `ci.yml` success; `docker-build` job does not depend on `security-scan`. A failing CI commit can still publish a GHCR image.

---

## §1 — Cross-cutting consolidated findings

These are the highest-leverage fixes; each touches multiple files and modules.

### X-1 — Port/documentation drift (CRITICAL — wrong-action risk)

**Sources of truth in conflict:**
- `docker-compose.yml:52` — `BACKEND_PORT:-8001`
- `docker-compose.yml` (frontend) — defaults to `3000`
- `README.md:156-158` — documents `8001`
- `CLAUDE.md:243` — documents `8002` for backend, `3001` for frontend
- `frontend/src/lib/api.ts:1877-1878` — fallback `http://localhost:8000/api`
- `frontend/src/hooks/useAIInsights.ts:668,814` — fallback `http://127.0.0.1:8001/api` (different from axios fallback above)
- `.env.example` — `BACKEND_PORT` not defined
- `frontend/package.json` `generate-types` script — points at `localhost:8001/api/schema/`

**Impact:** Developers following CLAUDE.md set `VITE_API_URL=http://127.0.0.1:8002/api` while container is on 8001. AI chat streaming works on a different port than the rest of the app even when correctly configured. Generated types target a port that may not exist.

**Suggested fix:**
1. Pick canonical defaults (`BACKEND_PORT=8001`, `FRONTEND_PORT=3000` per docker-compose) — these match what's actually shipped.
2. Update CLAUDE.md port table.
3. Add `BACKEND_PORT=8001` and `FRONTEND_PORT=3000` to `.env.example`.
4. Extract `API_BASE_URL` from `frontend/src/lib/api.ts` into `frontend/src/lib/constants.ts`. Replace both fallbacks in `useAIInsights.ts:668,814` with the shared constant.

---

### X-2 — `profile.organization` legacy single-org pattern in non-permission code paths (HIGH — multi-org correctness)

v2.12 migrated permission classes to `_resolve_target_org` / `user_*_in_org` helpers. **Eight call sites** in views, admin, and models still use the legacy `request.user.profile.organization` / `profile.role` path:

| Site | File:Line | Behavior |
|---|---|---|
| `UserProfileViewSet.get_queryset` | `apps/authentication/views.py:407-414` | Returns profiles from primary org, ignores `?organization_id=` |
| `AuditLogViewSet.get_queryset` | `apps/authentication/views.py:429-436` | Returns audit logs from primary org only |
| `OrganizationViewSet.get_queryset` | `apps/authentication/views.py:381-384` | Returns single primary org for non-superusers |
| `CanUploadData` permission | `apps/authentication/permissions.py:123-135` | Uses `profile.can_upload_data()` → `profile.role` |
| `CanDeleteData` permission | `apps/authentication/permissions.py:138-146` | Same anti-pattern |
| `OrganizationSavingsConfigView.patch` | `apps/authentication/views.py:854-858` | Uses `profile.get_role_for_org` instead of `user_is_admin_in_org` |
| `ReportAdmin.get_queryset` | `apps/reports/admin.py:92-101` | Multi-org admins see only primary-org reports |
| `report_share` user lookup | `apps/reports/views.py:795-801` | Cannot share with members from secondary orgs |

**Impact:** Multi-org users (admins, the entire team-lead workflow) silently see/manage wrong data depending on path taken.

**Suggested fix:** Migrate each to `get_target_organization(request)` + `user_is_*_in_org(user, org)` from `apps/authentication/organization_utils.py`. Add a regression test covering each call site with a multi-org user fixture.

---

### X-3 — Naive `datetime.now()` / `date.today()` resurgence (HIGH — TZ correctness)

v2.12 closed `timezone.now()` violations in `compliance_services.py`. Same anti-pattern still present in:

| Site | File:Line | Symptom |
|---|---|---|
| `export_savings_config_pdf` footer | `apps/authentication/views.py:1028` | PDF timestamps off by server TZ offset |
| `Invoice.days_outstanding` | `apps/procurement/models.py:1022-1027` | Aging buckets flip at UTC midnight |
| `Invoice.days_overdue` / `is_overdue` / `discount_available` | `apps/procurement/models.py` | Same |
| `PurchaseRequisition.is_overdue` | `apps/procurement/models.py:665-671` | PR overdue flags off by 1 day for non-UTC users |
| `Contract.days_to_expiry` | `apps/procurement/models.py` | Contract expiry warnings off by 1 day |
| `predictive_services.py` cutoff | `apps/analytics/predictive_services.py:54` | Forecasting window includes 31×N days, not N calendar months |
| `services/trend.py:34` + `services/pareto.py:611` | `apps/analytics/services/` | Same naive-date pattern |
| `get_matching_overview` resolution time | `apps/analytics/p2p_services.py:584-601` | Compares tz-aware `exception_resolved_at` to naive `invoice_date` — adds spurious +1 day for late-evening US-Eastern resolutions |

**Impact:** Multi-tenant SaaS with users outside server timezone (i.e. all customers): aging, overdue, and resolution-time analytics are systematically off by 1 day for events near midnight.

**Suggested fix:** Sweep replace `datetime.now()`/`date.today()` with `timezone.now()`/`timezone.now().date()`. Add a flake8 plugin or pre-commit hook (`flake8-datetimez` or custom rule) to prevent regression. For `relativedelta` cases, prefer `dateutil.relativedelta` over day-count approximations.

---

### X-4 — N+1 / Python-side aggregation (HIGH — perf cliff)

**Critical N+1:**
- `P2PAnalyticsService.get_supplier_payments_scorecard` — 5 queries × up to 50 suppliers = 250 round-trips per request (`apps/analytics/p2p_services.py:1540-1606`).
- `MaverickSpendService` contracted-categories loop — `prefetch_related('categories')` defeated by `values_list` re-query (`apps/analytics/compliance_services.py:131-133`).

**Python-side materialisation when DB-side aggregation possible:**
- `get_aging_overview` — 4 list-comprehension passes over the same materialised queryset (`p2p_services.py:996-1014`).
- `get_pr_overview` / `get_pr_approval_analysis` — Python loop summing approval days (`p2p_services.py:1241-1252, 1834-1848`).
- `get_cycle_time_by_category` / `get_cycle_time_by_supplier` — full paid-invoice materialisation (`p2p_services.py:262-300, 303-343`).
- `services/yoy.py:get_detailed_year_over_year:142-143` — `list(...)` on full transaction queryset.
- `compliance_services.py:72-78` — `len()` on values_list queryset instead of `.count()`.

**Impact:** Today scale (max 267 open invoices per `_industry_profiles.py` diagnostic) hides this. At 5K+ suppliers or 50K+ paid invoices, request times become unacceptable. Most are also covered by no `test_n_plus_1_*` regression test — easy to regress further.

**Suggested fix:** Convert to DB-side `Avg`/`Sum`/`Count` with `.annotate()`. Add `test_n_plus_1_*` coverage for each (existing pattern: `apps/analytics/tests/test_n_plus_1_cluster.py`).

---

### X-5 — Deploy pipeline does not enforce CI gates (CRITICAL — release safety)

**Findings:**
- `.github/workflows/deploy.yml` triggers on `push: main` directly; no `workflow_run` dependency on `ci.yml`.
- `.github/workflows/ci.yml:365-393` — `docker-build` job has `needs: [backend-test, frontend-build]` but **not** `needs: security-scan` — Trivy CRITICAL/HIGH vulns do not block image publication.

**Impact:** A commit that fails Django tests, Trivy security scan, OR the formatting gates can still publish a GHCR Docker image tagged with the commit SHA. The image is then deployable via the documented `APP_VERSION=<sha>` rollout (`docs/deployment/DEPLOY-PLAYBOOK.md`).

**Suggested fix:**
1. Add `needs: security-scan` to `docker-build`.
2. Change `deploy.yml` trigger to `workflow_run` gated on `ci.yml` `conclusion == 'success'`.
3. Promote the two `continue-on-error: true` formatting gates (Black, Prettier) to hard gates with a tracked deadline (currently tagged "out of scope for v3.0" with no follow-up).

---

## §2 — Backend / Authentication

### CRITICAL

**A-C1** — `UserPreferencesView.put` lacks the `transaction.atomic + select_for_update` guard that `patch` got in v3.0 Task S-#4.
- **Location:** `backend/apps/authentication/views.py:577-604`
- **Impact:** Two concurrent `PUT /preferences/` from same user (e.g., two browser tabs) silently lose one submission. Drift-guard test `test_concurrent_jsonfield_writes.py` exercises only `patch`.
- **Fix:** Mirror the `patch` pattern — wrap `put` write in `transaction.atomic()` with `select_for_update()` after the lock is acquired.

**A-C2** — Three `get_queryset` methods scope by `profile.organization` instead of `get_target_organization(request)`.
- **Locations:** `views.py:381-384, 407-414, 429-436` (Org/Profile/AuditLog viewsets)
- **Impact:** See X-2 — multi-org admin sees only primary-org data regardless of `?organization_id=` query param.
- **Fix:** Migrate all three to `get_target_organization` with profile-org fallback for single-org users.

### HIGH

**A-H1** — `CanUploadData` / `CanDeleteData` permission classes use legacy `profile.role`.
- **Location:** `permissions.py:123-146`
- **Impact:** Multi-org users with mixed roles (admin in A, viewer in B) get wrong permission decision on CSV upload + bulk delete.
- **Fix:** Replace with `user_can_upload_in_org` / `user_can_delete_in_org` from `organization_utils`.

**A-H2** — `export_savings_config_pdf` uses `datetime.now()` (naive).
- **Location:** `views.py:1028`
- **Fix:** `from django.utils import timezone; timezone.now().strftime(...)` (already imported in admin.py).

**A-H3** — `create_tenant` management command not atomic; `except Exception` swallows errors.
- **Location:** `management/commands/create_tenant.py:80-81`
- **Impact:** Half-provisioned tenants (Org + User created, no Profile) cause the documented "Login 403/500" error; re-running fails because user exists.
- **Fix:** Wrap in `with transaction.atomic():`. Re-raise for traceback visibility.

### MEDIUM

**A-M1** — `OrganizationSavingsConfigView.patch` uses `profile.get_role_for_org` instead of `user_is_admin_in_org` helper.
- **Location:** `views.py:854-858`
- **Fix:** Use canonical helper per CLAUDE.md §9.

### TECH DEBT

**A-TD1** — `AuditLog.save()` calls `full_clean()`; bypassed by `bulk_create`/`update`. Document the contract or add a regression test for `ALLOWED_DETAIL_KEYS` drift. `models.py:487-490`
**A-TD2** — `CanUploadData/CanDeleteData` lack `has_object_permission`; bundle fix with A-H1. `permissions.py:123-146`
**A-TD3** — `UserOrganizationMembershipSerializer` imported inside class body; move to module-level. `views.py:722-723`

---

## §3 — Backend / Procurement

### CRITICAL

**P-C1** — `CSVProcessor._process_row` `@transaction.atomic` + `IntegrityError` handling can abort the outer upload transaction.
- **Location:** `services.py:451-460, 474-478`
- **Impact:** A row that hits `IntegrityError` aborts the savepoint; subsequent ORM calls in the outer transaction raise `TransactionAborted`, collapsing the entire CSV upload to 0 successful rows. Stats counters also go negative.
- **Fix:** Remove `@transaction.atomic` decorator from `_process_row`; rely on the row-level `get_or_create_supplier`/`get_or_create_category` savepoints. OR wrap only `Transaction.objects.create(...)` in a savepoint and handle `TransactionAbortedError` explicitly.

**P-C2** — Admin invoice import duplicate-skip omits `supplier` from `unique_together`.
- **Location:** `admin.py:2267-2272`
- **Evidence:** Filter `(organization, invoice_number)`; model has `unique_together=['organization', 'invoice_number', 'supplier']`.
- **Impact:** Two suppliers with same invoice number (real-world common) — second supplier's invoice silently dropped, no error surfaced. AP aging and 3-way matching show wrong counts.
- **Fix:** Add `supplier=supplier` to the filter; surface skip count distinctly from failure count.

### HIGH

**P-H1** — `CSVProcessor` rejects negative amounts; `test_edge_cases.py:86-95` asserts they should be accepted (credit memos). One of the two is wrong.
- **Locations:** `services.py:422-424` vs `tests/test_edge_cases.py:94-95`
- **Impact:** Sync uploads reject credit memos; Celery async path accepts them. Inconsistent behavior; spend over-counted on sync uploads.
- **Decision needed:** Are credit memos valid? Then drop the guard. If not, fix the test.

**P-H2** — `Invoice.aging_bucket` returns `'90+'` for paid invoices with long payment cycles.
- **Location:** `models.py:1022-1054`
- **Impact:** Paid invoices appear in AP aging analysis as overdue, inflating buckets.
- **Fix:** `if self.status == 'paid' or self.paid_date: return 'paid'` at top of `aging_bucket`.

**P-H3** — `GoodsReceipt` not in cross-org FK trigger coverage.
- **Location:** `migrations/0009_cross_org_fk_check_constraints.py:48-69`
- **Impact:** A GR with `organization=A` linked to `purchase_order` in org B silently corrupts 3-way matching (false `missing_gr` exceptions). API path is guarded; admin shell / bulk import is not.
- **Fix:** New migration adding trigger for `procurement_goodsreceipt` covering `purchase_order_id`.

**P-H4** — `ColumnMappingTemplate.save()` race on `is_default` uniqueness.
- **Location:** `models.py:231-238`, also `admin.py:906-913`
- **Impact:** Concurrent saves can leave 0 OR 2 default templates.
- **Fix:** Wrap in `transaction.atomic()` with `select_for_update()` on the affected rows.

**P-H5** — `SupplierViewSet.perform_create` / `CategoryViewSet.perform_create` always write to `request.user.profile.organization`, ignoring `?organization_id=`.
- **Location:** `views.py:96-105, 162-171`
- **Impact:** Superuser switching to org B and creating a supplier writes it to their own primary org silently.
- **Fix:** Use `get_target_organization(request)` in `perform_create`, matching `get_queryset`.

### MEDIUM

**P-M1** — Date parser tries `%m/%d/%Y` then `%d/%m/%Y` — `05/03/2024` always parses as US format. `tasks.py:540-555` and `admin.py:1127-1143`.
**P-M2** — `seed_demo_data` violation_types omits `'restricted_category'`. Demo always shows 0% for that compliance metric. `seed_demo_data.py:211`.
**P-M3** — Admin sync `_process_csv_sync` wraps entire upload in single `transaction.atomic()` — `skip_invalid=True` doesn't actually skip rows on `IntegrityError`. Same family as P-C1. `admin.py:1252-1319`.
**P-M4** — `PurchaseRequisition.is_overdue` (and 4 other model properties) use `date.today()`. See X-3.

### TECH DEBT

**P-TD1** — `_parse_date`, `_parse_decimal`, `_get_or_create_*` copy-pasted across 4 P2P admin classes. Move to `P2PImportMixin`. `admin.py:1691-1725, 1911-1945, 2101-2117, 2355-2380`
**P-TD2** — `PurchaseOrder.amount_variance` / `GoodsReceipt.quantity_variance` / `Invoice.price_variance` cast `Decimal → float` in serializer — precision loss for high-value POs. `models.py:802-804, 880-883, 1070-1074`
**P-TD3** — `DataUpload.error_log` is `JSONField(default=list)` but `tasks.py` writes `json.dumps(...)` (str) → double-encoded. `admin.py:974` works around it. `models.py:283`, `tasks.py:338-390`
**P-TD4** — `seed_demo_data._seed_pos` passes `rng.uniform()` float through `Decimal(str(...))`, producing 15-decimal Decimals that round on insert. Quantize after division. `seed_demo_data.py:322-323`

---

## §4 — Backend / Analytics

### CRITICAL

**AN-C1** — `get_all_insights` enhancement gate checks `self.api_key` (singular); `_provider_manager` keyed on `self.api_keys` (plural).
- **Location:** `ai_services.py:483`
- **Impact:** Multi-provider callers (only `api_keys={'anthropic':'...'}`) get `enhancement_status='unavailable_no_key'` even though provider manager is initialised. LLM enhancement silently never fires. Affects `enhance_insights_async` Celery task and any internal call that constructs the service with `api_keys` only.
- **Fix:** Line 483 → `if not (self.use_external_ai and (self.api_key or self.api_keys)):`

**AN-C2** — After `unavailable_failed`, `PerInsightEnhancer` fires up to 5 additional LLM calls anyway.
- **Location:** `ai_services.py:531-538`
- **Impact:** When top-level LLM fails (rate limit, auth), per-insight calls hit the same broken provider, accumulate cost, and burn `30/hour` throttle quota faster than necessary.
- **Fix:** Gate `PerInsightEnhancer` invocation on `if ai_enhancement:` (succeed branch).

**AN-C3** — `get_process_funnel` PR stage respects date filter; PO/GR/Invoice stages use org-lifetime totals.
- **Location:** `p2p_services.py:523-538`
- **Impact:** With a "last 90 days" filter, funnel shows e.g. 40 PRs → 500 POs → 1200 GRs — visually nonsensical. Conversion rates >100%.
- **Fix:** Apply `_apply_date_filters(qs, 'created_date')` to each stage queryset.

**AN-C4** — `get_supplier_payments_scorecard` is 5×N queries (up to 50 suppliers = 250 round-trips per request).
- **Location:** `p2p_services.py:1540-1606`
- **Fix:** Single grouped aggregation; pattern in `get_payment_terms_compliance:1165-1195` shows the right approach.

### HIGH

**AN-H1** — `get_aging_overview` 4-pass list iteration over materialised queryset; `inv.days_outstanding` accesses `date.today()` per item.
- **Location:** `p2p_services.py:996-1014`
- **Fix:** Single-pass with bucket dispatch; long-term: DB-side `Case`/`When`.

**AN-H2** — `on_time_rate` numerator re-iterates `paid_invoices` queryset (duplicating data-quality filter); convention §9 violation.
- **Locations:** `p2p_services.py:1032-1036, 1510-1514, supplier_payment_detail`
- **Fix:** Have `_avg_days_to_pay` return `(avg, sample_size, eligible_qs)`; reuse the filtered set.

**AN-H3** — `MaverickSpendService` `prefetch_related('categories')` defeated by subsequent `values_list` re-query.
- **Location:** `compliance_services.py:131-133`
- **Fix:** `Category.objects.filter(contracts__in=active_contracts).values_list('id', flat=True)`.

**AN-H4** — `ai_insights_usage` / `ai_insights_usage_daily` use bare `int(query_params.get('days', 30))` → `ValueError` becomes 500.
- **Location:** `views.py:1596, 1636`
- **Fix:** Use existing `validate_int_param(request, 'days', default=30, min_val=1, max_val=90)`.

**AN-H5** — `AIInsightsCache._track_org_key` read-modify-write race (list append).
- **Location:** `ai_cache.py:129-136`
- **Impact:** Concurrent `cache_enhancement` calls drop tracked keys; `invalidate_org_cache` then misses them; stale AI insights served after data upload.
- **Fix:** Switch to Redis `SADD`-based set, or rely on key-prefix scan + accept staleness window.

### MEDIUM

**AN-M1** — `get_pr_overview` / `get_pr_approval_analysis` materialise approved PRs for Python loop avg. `p2p_services.py:1241-1252, 1834-1848`
**AN-M2** — `get_cycle_time_by_category` / `_by_supplier` materialise all paid invoices unbounded. `p2p_services.py:262-300, 303-343`
**AN-M3** — `services/yoy.py:get_detailed_year_over_year` `list(...)` on full transaction queryset; sister method `get_year_over_year_comparison` correctly does DB-side. `services/yoy.py:142-143`
**AN-M4** — `get_year_over_year_comparison` `Count('month', distinct=True)` references annotation by name; may not GROUP BY correctly across Django versions. No test catches this. `services/yoy.py:87-96`
**AN-M5** — `compliance_services.py:72-78` uses `len(values_list_qs)` instead of `.count()`.

### TECH DEBT

**AN-TD1** — `services_legacy.py.bak` committed to repo. Delete. `apps/analytics/services_legacy.py.bak`
**AN-TD2** — `_enhance_with_claude_structured` / `_enhance_with_openai_structured` (~120 lines) unreachable when `self.api_keys` is non-empty (always, when `use_external_ai=True`); model name hardcoded bypasses `AI_CHAT_ALLOWED_MODELS`. `ai_services.py:1164-1201, 1219`
**AN-TD3** — `get_supplier_payments_scorecard` emits `on_time_rate` (count-based) without `on_time_rate_by_amount` companion → Convention §1 violation. `p2p_services.py:1598-1599`
**AN-TD4** — `get_matching_overview` resolution time compares tz-aware `exception_resolved_at` with naive `invoice_date`; same fix as v3.0 compliance_resolved_at TZ test was not applied here. `p2p_services.py:584-601`
**AN-TD5** — Naive datetime in `predictive_services.py`, `services/trend.py`, `services/pareto.py`. See X-3.

---

## §5 — Backend / Reports

### CRITICAL

**R-C1** — `report_preview` has no throttle decorator; synchronous full analytics pipeline on the worker thread.
- **Location:** `views.py:292-353`
- **Impact:** DoS vector. Single authenticated user can saturate gunicorn workers; only the global `user: 1000/hour` burst applies (no `report_generate: 20/hour` scope).
- **Fix:** Add `@throttle_classes([ReportGenerateThrottle])`. Long-term: route large org previews through async path or cap data size in `_generate_data` before generation, not after.

**R-C2** — `process_scheduled_reports` and `cleanup_expired_reports` are NOT in `celery beat_schedule`.
- **Location:** `backend/config/celery.py:14-42` (verified — only 6 tasks scheduled, neither report task present)
- **Impact:** Every `is_scheduled=True` report silently never fires. Users create weekly/monthly schedules that do nothing. Stale completed reports accumulate indefinitely in the DB (no TTL cleanup).
- **Fix:** Add Beat entries (use full dotted path or add `name=` kwarg to `@shared_task`):
  ```python
  'process-scheduled-reports': {'task': 'apps.reports.tasks.process_scheduled_reports', 'schedule': crontab(minute=0)},
  'cleanup-expired-reports': {'task': 'apps.reports.tasks.cleanup_expired_reports', 'schedule': crontab(hour=1, minute=0)},
  ```

**R-C3** — `Content-Disposition` filename built from user-controlled `report_name` with only `space/slash` sanitisation.
- **Locations:** `views.py:601`, `renderers/base.py:51-57`
- **Impact:** A report name containing `\r\n` or `"` allows HTTP response header injection / breaks out of `filename="..."` token. Header injection can plant arbitrary response headers (`Set-Cookie`, etc.).
- **Fix:** Strip `[^A-Za-z0-9._-]` or use RFC 5987 `filename*=UTF-8''<encoded>` form. Minimum: `.replace('"','').replace('\r','').replace('\n','')`.

### HIGH

**R-H1** — `Report.can_access` `shared_with` check has no organization guard.
- **Location:** `models.py:198-206`
- **Impact:** Cross-org user added to `shared_with` passes `can_access`. Combined with `report_delete`'s multi-org `get_user_organizations` scoping (vs Phase 0's profile-org scoping for read), a multi-org user with shared access can delete reports they shouldn't be able to.
- **Fix:** Filter `shared_with` query by `profile__organization=self.organization`. Long-term: separate `can_read` and `can_write` semantics before Task 1.3 ships.

**R-H2** — `process_scheduled_reports` test-and-set race.
- **Location:** `tasks.py:34-75`
- **Impact:** Beat tick overlap (worker restart, hourly cron firing while previous still running) double-dispatches the same report; both calls advance `next_run`, double-skipping a cycle.
- **Fix:** Atomic test-and-set: `Report.objects.filter(pk=pk, status='scheduled').update(status='generating')` returns row count; only dispatch if `1`.

**R-H3** — Throttle scope mismatch: `report_download: 60/hour` (settings) vs CLAUDE.md documented `exports: 30/hour`.
- **Locations:** `settings.py:260`, `views.py:153-155`
- **Impact:** Operators tuning `exports` rate per CLAUDE.md don't affect report downloads. Documentation says one number, code enforces another.
- **Fix:** Either rename scope to `exports` and unify, or add CLAUDE.md note that downloads use a separate scope.

**R-H4** — `BaseReportGenerator.get_date_range` reads `filters['date_range']['start']/['end']`; `_generate_data` writes `filters['date_from']/['date_to']`. Two paths disconnected.
- **Locations:** `generators/base.py:65-78`, `services.py:229-233`
- **Impact:** Report PDF/Excel headers always show "now minus 30 days" regardless of user-selected period. Analytics queries use the right dates (different code path); only the metadata in the rendered report header is wrong.
- **Fix:** In `get_date_range`, fall back to `self.filters.get('date_from')` / `date_to` before defaulting. Or have `_generate_data` populate both keys.

### MEDIUM

**R-M1** — `cleanup_expired_reports` filters `status='completed'` only; abandoned `'generating'` reports (worker crash) accumulate forever. `tasks.py:141-155`
**R-M2** — `ReportScheduleSerializer` allows `is_scheduled=False` to keep stale `schedule_frequency` + `next_run`; re-enabling silently fires immediately on next Beat tick. `serializers.py:180-189`, `views.py:692-706`
**R-M3** — `report_share` user lookup uses legacy `profile__organization`; can't share with secondary-org members. See X-2. `views.py:795-801`
**R-M4** — `ReportAdmin.get_queryset` legacy single-org filter. See X-2. `admin.py:92-101`

### TECH DEBT

**R-TD1** — When fixing R-C2, use full dotted path or add `name=` to `@shared_task` for consistency. `config/celery.py`
**R-TD2** — Bare `except: pass` in `ExcelRenderer._auto_fit_columns`. `renderers/excel.py:259`
**R-TD3** — `calculate_next_run` uses `timedelta(days=30)` for monthly, `timedelta(days=90)` for quarterly — calendar drift over time. Use `dateutil.relativedelta`. `models.py:162-174`
**R-TD4** — No throttle test for `report_preview`; combined with R-C1 means missing throttle could be reintroduced silently. `tests/test_views.py:142-166`

---

## §6 — Frontend

### CRITICAL

**F-C1** — `useAIChatStream.sendMessage` stale closure on `state.messages`; chat history truncated on rapid follow-up.
- **Location:** `hooks/useAIInsights.ts:642, 670, 760`
- **Impact:** Second message sent before state flush includes pre-first-message snapshot in `messagesToSend`. Backend LLM gets context-incomplete history. Manifests on every fast follow-up — not a timing race.
- **Fix:** `messagesRef = useRef(state.messages)`; sync in setState; read from ref in callback.

**F-C2** — Hardcoded port `8001` fallback in SSE `fetch()` differs from axios fallback (`8000`); also CLAUDE.md says `8002`. See X-1. `hooks/useAIInsights.ts:668, 814`

**F-C3** — `as any` cast on already-typed `PaginatedResponse<Supplier>` — violates CLAUDE.md hard ban.
- **Location:** `hooks/useAnalytics.ts:41-52`
- **Fix:** Remove cast; `.results` is in the type.

### HIGH

**F-H1** — SSE streaming `fetch()` bypasses axios 401-refresh interceptor.
- **Location:** `hooks/useAIInsights.ts:675-686, 816`
- **Impact:** Token expiry mid-stream throws "HTTP error: 401"; user has working app but broken chat until hard-refresh.
- **Fix:** Catch 401, call `authAPI.refreshToken()`, retry once. Or pre-flight axios call before opening stream.

**F-H2** — `useAIChatStream` partial SSE chunks across `\n` boundaries silently dropped.
- **Location:** `hooks/useAIInsights.ts:704-749`, also `useAIQuickQuery:848+`
- **Impact:** TCP segmentation may split `data: {...}` mid-line; `JSON.parse` fails; `try/catch` swallows. Short tokens (1-3 chars) frequently dropped from rendered output.
- **Fix:** Maintain `buffer` string across `read()` iterations; keep incomplete trailing line.

**F-H3** — `recharts` not in Vite `manualChunks`; bundled into multiple page chunks (verified — `vite.config.ts:37-61` lists only `echarts` for `vendor-charts`).
- **Locations:** `pages/ai-insights/index.tsx:143-149`, `pages/p2p/SupplierPayments.tsx`, `pages/p2p/PurchaseOrders.tsx`
- **Impact:** Recharts (~600 KB unminified) duplicated across 2+ page chunks.
- **Fix:** Add `"vendor-recharts": ["recharts"]` to `manualChunks`.

**F-H4** — `vitePluginManusRuntime` + `jsxLocPlugin` injected into production builds; only gated on `isTest`, not `command === 'build'` (verified `vite.config.ts:14-19`).
- **Impact:** ~365 KB IDE-tooling script in every production HTML; requires `'unsafe-inline'` in CSP `script-src`, neutralising the v2.12 CSP hardening.
- **Fix:** Gate also on `command === 'build'`. After this, drop `'unsafe-inline'` from nginx CSP. Also remove `*.manus*.computer` entries from `server.allowedHosts`.

### MEDIUM

**F-M1** — `OrganizationContext` builds synthetic `Organization` with `slug: ""` for legacy single-org users. Any UI consuming `activeOrganization.slug` for URLs/display gets empty string. `contexts/OrganizationContext.tsx:135-145`
**F-M2** — `ManusDialog.tsx` is dead code (zero imports verified). Delete. Also evaluate `vite-plugin-manus-runtime` for removal entirely. `components/ManusDialog.tsx`
**F-M3** — `useAIChatStream` no `useEffect` cleanup; stream survives unmount, fires `setState` on unmounted component, burns LLM credits. `hooks/useAIInsights.ts:640, 762`
**F-M4** — `OrganizationContext` org-switcher hits `/auth/organizations/` without pagination iteration; superuser with >page_size orgs sees truncated list. `contexts/OrganizationContext.tsx:152-154`

### TECH DEBT

**F-TD1** — `key={index}` in 14 page files. Interactive lists (feedback, reports) at risk for stale form state. `pages/**/*.tsx`
**F-TD2** — `getOrgKeyPart()` reads localStorage at render time; not reactive to org switch. Use `OrganizationContext` instead. `hooks/useAIInsights.ts:49, 67` (and ~10 sibling sites)
**F-TD3** — `AgingOverview.trend` interface — both `days_to_pay?` and `avg_days_to_pay?` optional, neither documented as canonical. `InvoiceAging.tsx:298` does 4-level fallback. Pick one. `lib/api.ts:3061-3066`
**F-TD4** — `enhancement_status` fallback to `unavailable_no_key` for absent field can misclassify `unavailable_failed` cached payloads after backend upgrade. Narrow window but exact scenario CLAUDE.md §6 was written to prevent. `pages/ai-insights/index.tsx:1835-1838`

---

## §7 — Cross-cutting (tests / infra / config / deps / observability)

### CRITICAL

**XC-C1** — `Dockerfile:51` runs `python manage.py collectstatic --noinput || true` at build time without `SECRET_KEY` injection (verified Dockerfile content).
- **Impact:** In production mode (`DEBUG=False`), `collectstatic` either silently no-ops or panics — both swallowed by `|| true`. Image ships without collected static files. Admin panel unstyled in prod; API docs may 500.
- **Fix:** Move `collectstatic` to entrypoint script (runs before gunicorn with real env). Or inject build-time `SECRET_KEY=dummy DEBUG=True` scoped to that single RUN.

### HIGH

**XC-H1** — PII redaction filter wired only to `security_file` handler, not `console`. `settings.py:534-571`
- **Impact:** On Railway (target deployment), stdout streams to platform log collector. Credentials, JWT, API keys logged unredacted to a searchable index.
- **Fix:** Add `'filters': ['redact_sensitive']` to `console` handler.

**XC-H2** — `pytest.ini` includes `--reuse-db` by default; fragile with `TransactionTestCase`. `pytest.ini:4`
- **Impact:** Local flaky failures after a `TransactionTestCase` failure; CI unaffected (`--create-db` there).
- **Fix:** Remove `--reuse-db` from `addopts`; document as opt-in.

**XC-H3** — `conftest.py:317-322` overrides `django_db_setup` with unconditional `migrate`, defeating `--reuse-db` benefit anyway. Tech-debt twin of XC-H2.

**XC-H4** — `deploy.yml` does not depend on `ci.yml` success; `docker-build` does not depend on `security-scan`. See X-5.

**XC-H5** — `celery==5.3.4` outdated; `autoretry_for=(Exception,)` retries non-transient errors. `requirements.txt:53`, `apps/analytics/tasks.py:27,98,162,243,332,530,603,656,724`
- **Fix:** Bump to `>=5.4.0`. Narrow retry sets to transient exceptions per task.

**XC-H6** — `psycopg2-binary==2.9.9` pinned; consider non-binary `psycopg2` to avoid libssl conflicts on managed Postgres (Railway). `requirements.txt:7`

### MEDIUM

**XC-M1** — Backend port default mismatch between `docker-compose.yml`, `CLAUDE.md`, `README.md`, `useAIInsights.ts`, `package.json`. See X-1.
**XC-M2** — Black + Prettier gates `continue-on-error: true` indefinitely; no tracked deadline; ~191 Python files + 23 TS files would reformat. `.github/workflows/ci.yml:43, 50, 287`
**XC-M3** — Backend `.coveragerc fail_under = 55` low for 923-test suite; CI does not pass `--cov-fail-under` flag. `.coveragerc:24`, `ci.yml:138-141`
**XC-M4** — `analytics/migrations/0006_add_vector_indexes.py:59-67` — `CREATE INDEX CONCURRENTLY` may leave INVALID index without detection; Django records migration as applied; subsequent `IF NOT EXISTS` no-ops, hiding the failure.
- **Fix:** Post-create `pg_index.indisvalid` check; raise on `false`.
**XC-M5** — `deploy.yml` triggers on `push: main` without CI dependency. See X-5.

### TECH DEBT

**XC-TD1** — `frontend/package.json` has `express` as production dep; zero imports in `src/`. Remove. `package.json:55`
**XC-TD2** — `xlsx@^0.18.5` (SheetJS Community) in deps; zero source imports; known prototype-pollution advisories on 0.18.x. Remove or pin via overrides. `package.json:74`
**XC-TD3** — `vite.config.ts:71-78` `allowedHosts` contains `*.manus*.computer` IDE preview domains in committed config. Move to `.env.local` or gate by env var.
**XC-TD4** — `batch_generate_insights` / `batch_enhance_insights` lack idempotency lock. Use `cache.add` pattern from v3.0 Task 3.7. `apps/analytics/tasks.py:433-500`
**XC-TD5** — `README.md:156-158` documents port `8001`; CLAUDE.md says `8002`. Twin of X-1.
**XC-TD6** — `conftest.py` custom `django_db_setup` overrides pytest-django; pgvector init should be a separate fixture. `backend/conftest.py:317-322`

---

## §8 — Suggested remediation phases

### Phase 0 — Production safety (do before next deploy)
- **XC-C1** Move `collectstatic` out of build step
- **XC-H1** Wire PII redaction filter to `console` handler
- **R-C2** Add `process_scheduled_reports` + `cleanup_expired_reports` to Beat
- **R-C3** Sanitise `Content-Disposition` filename
- **F-H4** Gate Manus plugins on `command === 'build'`; drop `unsafe-inline` from CSP
- **X-5** (XC-H4 + XC-M5) Wire deploy gates: `docker-build needs: security-scan`; `deploy.yml needs: ci.yml`

### Phase 1 — Critical bugs (next sprint)
- **A-C1** Add atomic guard to `UserPreferencesView.put`
- **A-C2** + **X-2** consolidated migration of 8 `profile.organization` call sites
- **P-C1** Remove `@transaction.atomic` from `_process_row` (or make savepoint explicit)
- **P-C2** Add `supplier` to invoice duplicate-skip filter
- **P-H3** Add `GoodsReceipt` cross-org FK trigger migration
- **AN-C1** Fix `api_key`/`api_keys` gate
- **AN-C2** Gate `PerInsightEnhancer` on top-level success
- **AN-C3** Apply date filters to all 4 funnel stages
- **AN-C4** Convert supplier scorecard to single grouped query
- **R-C1** Add throttle to `report_preview`
- **R-H1** Org-guard `Report.can_access` `shared_with` path
- **R-H2** Atomic test-and-set on scheduled-report dispatch
- **F-C1** Ref-based fix for `useAIChatStream` stale closure
- **F-H1** + **F-H2** SSE 401-refresh + chunk-buffer fixes
- **F-C3** Remove `as any` from `useAnalytics`

### Phase 2 — Perf/quality (after Phase 1)
- **AN-H1** Single-pass aging + DB-side bucket dispatch
- **AN-H2** Reuse filtered queryset across rate calcs
- **AN-H3** Fix `prefetch_related` + `values_list` antipattern
- **AN-H4/AN-H5** Param validation + cache-key tracking race
- All AN-M / P-M (perf-tier mediums)
- **F-H3** Add recharts to manualChunks
- **F-M1/M3/M4** Org-context fixes

### Phase 3 — Convention/typo/tech-debt cleanup
- **X-3** Naive datetime sweep (12 sites) + flake8-datetimez gate
- **R-H3** Throttle scope unification
- **R-H4** Date-range key consolidation
- **AN-TD1** Delete `services_legacy.py.bak`
- **AN-TD2** Delete unreachable LLM legacy paths
- **XC-TD1/TD2** Remove `express`, `xlsx` from frontend deps
- **XC-M2** Promote Black/Prettier to hard gates
- **XC-M3** Ratchet `fail_under` upward

### Open product decisions (not bugs)
- Negative amount handling in CSV uploads (P-H1) — credit memo policy
- Throttle scope rename (R-H3) — operator-facing API contract
- `xlsx` package — confirm not transitively required

---

## §9 — Methodology notes

- 6 parallel `feature-dev:code-reviewer` agents, each given:
  - Pointers to v2.12 + v3.0 plan files (avoid re-surfacing closed findings)
  - Pointers to root + subdir CLAUDE.md, ACCURACY_AUDIT.md, P2P/AI canonical docs
  - Severity rubric and category definitions
  - Module-specific focus areas matching CLAUDE.md "load-bearing gotchas"
  - Hard `MUST NOT DO` boundaries (no edits, no closed-finding re-files, no deferred-item refiles)
- Findings cross-checked: the 4 most consequential infra claims spot-verified by direct reads (`Dockerfile`, `docker-compose.yml`, `vite.config.ts`, `celery.py`).
- Confidence noted per finding by source agents; carry-through preserved.
- Cross-agent duplicates consolidated in §1 (e.g., port drift mentioned by 4 agents → one X-1).

**Limitations**:
- No runtime testing — findings are static-analysis only.
- Coverage gaps assumed based on test-file naming; not measured.
- Some MEDIUM perf claims contingent on tenant scale (~267 invoice cap noted per Task 5.4); flagged as latent rather than active where applicable.
