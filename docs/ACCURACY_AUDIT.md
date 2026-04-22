# Analytics Accuracy Audit Ledger

Companion to `~/.claude/plans/i-would-like-to-functional-pudding.md`. The plan file owns workflow and pass status; this file owns per-finding detail.

## Cluster Map (Cluster 0 deliverable)

Read-only research, gathered once, referenced by every downstream module pass. When a later module surfaces a finding in one of these primitives, the ledger entry must cite the shared site and name the inheritance ("inherits from Cluster 2" / "cross-module shared with Supplier Payments" / etc).

### A. Fiscal-year math

- **Authoritative site:** `backend/apps/analytics/services/base.py:96-113` — `_get_fiscal_year()` / `_get_fiscal_month()` helpers on `BaseAnalyticsService` (Jul–Jun boundary).
- **Known direct caller:** `backend/apps/analytics/services/yoy.py` uses the base helpers.
- **Local re-implementation (divergence):** `backend/apps/analytics/services/seasonality.py:83-93` defines its own inline `get_fiscal_year` + `calendar_to_fiscal_month` inside `get_detailed_seasonality_analysis`. Should converge on the base helpers in Cluster 2 so a future FY-start override lands once.

### B. DPO computation — 8 sites (plan said 5)

Every site uses `(paid_date - invoice_date).days`. Uniformly `invoice_date` based, never `due_date`. That uniformity is good news — a single "proxy DPO" fix (or relabel to "Estimated DPO") can be applied in one place and propagated.

| Line (p2p_services.py) | Function | Notes |
|---|---|---|
| 135–137 | `get_aging_overview` | aging bucket calc |
| 202 | `get_aging_overview` | `F()` annotation |
| 238–240 | `get_aging_overview` | by-category breakdown |
| 276–278 | `get_aging_overview` | by-supplier breakdown |
| 976 | `get_aging_overview` | core DPO summary |
| 1435 | `get_supplier_payments_overview` | summary metric |
| 1484 | `get_supplier_payments_scorecard` | per-supplier DPO |
| 1552 | `get_supplier_payment_detail` | supplier detail |

### C. Invoice–PO arithmetic — 4 sites

`invoice_amount - purchase_order.total_amount`, consistent.

| Line (p2p_services.py) | Function |
|---|---|
| 717 | `get_price_variance_analysis` (percent) |
| 719 | `get_price_variance_analysis` (amount) |
| 821 | `get_invoice_match_detail` (variance) |
| 823 | `get_invoice_match_detail` (percent) |

Not duplicated in `contract_services.py` or `compliance_services.py`.

### D. Savings-rate multipliers — fragmented (audit risk)

Two incompatible models live side by side:

| Module | File:Line | Rate | Model |
|---|---|---|---|
| Seasonality | `services/seasonality.py:194-202` | 25 / 20 / 10% | Tiered by `seasonality_strength` |
| Tail Spend (consolidation) | `services/pareto.py:205` | 8% | Flat |
| Tail Spend (supplier) | `services/pareto.py:292` | 15% | Flat |
| Tail Spend (category) | `services/pareto.py:316, :358` | 10% | Flat |
| Trend | `services/trend.py:93` | 10% | Flat |
| Contracts (negotiation) | `contract_services.py:420` | 10% | Flat |
| Contracts (consolidation) | `contract_services.py:453` | 15% | Flat |

No central benchmark source, no `savings_config` integration. Candidate for a shared design decision once any one cluster needs to flip a rate.

### E. Threshold constants

All of the following are hardcoded literals, not yet wired into `Organization.savings_config`.

| Constant | File:Line | Value |
|---|---|---|
| HHI low | `services/spend.py:215` | 1500 |
| HHI moderate | `services/spend.py:217` | 2500 |
| Concentration high | `services/spend.py:120` | 70% |
| Concentration moderate | `services/spend.py:122` | 50% |
| Min suppliers (high risk) | `services/spend.py:120` | 3 |
| Min suppliers (med risk) | `services/spend.py:122` | 5 |
| Expiring contract window | `contract_services.py:58` | 90 days *(param defaulted, not hardcoded)* |
| Off-contract severity | `contract_services.py:424` | $50,000 |
| Maverick recommendation | `compliance_services.py:210` | $50,000 |
| Tail spend cutoff (default) | `services/pareto.py:61` | 20% *(param defaulted)* |
| Tail spend (generator) | `generators/tail_spend.py:25` | $50,000 *(param defaulted)* |
| Price-variance (AI) | `ai_services.py:278` | 15% |
| Concentration (AI) | `ai_services.py:279` | 30% |
| Contract utilization (renew-with-increase) | `contract_services.py:253` | 90% |
| Seasonality-strength filter | `services/seasonality.py:205` | 15% *(already in S4 log)* |

### F. Report-generator parity — zero divergence risk

Every generator in `backend/apps/reports/generators/` is a **wrapper** — it instantiates the analytics service and calls service methods. No generator re-implements aggregation logic. Therefore service-level fixes propagate automatically to PDF/Excel/CSV outputs; Definition-of-Done "report-generator parity" step reduces to a one-line ledger entry confirming "wrapper, in-sync" per module.

Generators confirmed wrapper-type: `executive.py`, `spend.py`, `supplier.py`, `pareto.py`, `compliance.py`, `seasonality.py`, `stratification.py`, `tail_spend.py`, `yoy.py`, `savings.py`, `p2p_ap_aging.py`, `p2p_po_compliance.py`, `p2p_pr_status.py`.

### G. AI-Insight consumer table — NONE of the 18 modules

`backend/apps/analytics/ai_services.py` does NOT call any method on `AnalyticsService`, `P2PAnalyticsService`, `ContractAnalyticsService`, `ComplianceService`, or `PredictiveAnalyticsService`. It performs its own direct ORM queries against `Transaction` / `Supplier` / `PurchaseOrder` / `Invoice` (see `ai_services.py:345-386` and `:505-844`). Grep-confirmed zero references to any of the 18 service methods.

| # | Module | AI-Insight Consumer? |
|---|---|---|
| 1–18 | All audit modules | **No** |
| 19 | `AIInsightsService` itself | yes — feeds the 24h cache at `backend/apps/analytics/tasks.py:371` (`timeout=86400`) |

**Workflow consequences:**

- Per-module DoD step 6 ("Cache invalidation checklist") reduces to "Not a consumer, skip" for every one of the 18 modules. No per-pass invalidation playbook needed.
- Module fixes are visible immediately on deploy. No 24h cache delay.
- Cache invalidation only matters if/when we audit `ai_services.py` itself (Cluster 8).
- However: because `ai_services.py` re-implements aggregations directly instead of delegating, any shared-primitive fix (e.g., DPO proxy relabel) will NOT automatically reach AI-insight output. Cluster 8 must explicitly re-check those primitives inside `ai_services.py`.

## Completed

Each entry: `[Module] [Class/Severity] File:line — Finding (decision) SHA:<sha>`. SHA appended when the fix commit lands on `audit/accuracy-review`.

### AI Insights (Cluster 8)

Cluster 8 shipped as 2 PRs. PR-8a unblocked the External AI Enhancement feature (which had been dark in production due to a 4-site plumbing mismatch between UI, serializer, allowlist, and runtime consumers) and added security hygiene (response masking + admin exclusion + removed false "encrypted" UI claim). PR-8b audited the four deterministic insight generators plus the orchestrator-level savings dedup/cap.

**PR-8a — Unblock + hygiene (atomic):**

- **[Auth] [A/S1]** `aiApiKey` plaintext leak via outbound responses. Added `UserProfile.mask_preferences()` helper + `UserProfile.MASKED_PREFERENCE_KEYS` frozenset. Two-site masking: `UserProfileSerializer.to_representation` (covers login, register, `/auth/user/`) and `UserPreferencesView.get/patch/put` (inline mask for `/auth/preferences/` which bypasses the serializer). Mask format: `None` if absent, `'****' + key[-4:]` otherwise. Regression tests in `backend/apps/authentication/tests/test_preferences_masking.py::TestPreferencesMasking` (5 tests). (fixed) SHA:—
- **[Auth] [C/S2]** Django admin rendered raw `preferences` JSONField. Added `exclude = ['preferences']` and a `preferences_masked` readonly display method on `UserProfileAdmin`. Test in `TestAdminMaskedDisplay`. (fixed) SHA:—
- **[Settings] [D/S3]** UI text "Your API key is stored encrypted and never displayed" was false (no encryption layer in auth app). Severity kept at D/S3 — the feature was dark until this cluster, so no user had actually been misled by a stored-but-not-encrypted key. Changed `Settings.tsx:642` to "Stored in your user preferences. Treat as sensitive — visible to users with admin access to your account." Updated `useSettings.ts:55, :209` inline comments. Logged encryption-implementation as security-review follow-up. (fixed) SHA:—
- **[Auth/Analytics] [A/S1]** AI settings silently dropped across 4 sites. Root cause: three incompatible contracts — `UserProfileAdmin.ALLOWED_PREFERENCE_KEYS` didn't whitelist AI fields, `UserPreferencesSerializer` didn't declare them, `views.py:967` read a nonexistent `profile.ai_settings` attribute, and `tasks.py:181/261/457` expected a nested `ai_settings` sub-dict that the frontend never sent. Fix: added 6 AI fields (`useExternalAI`, `aiProvider`, `aiApiKey`, `forecastingModel`, `forecastHorizonMonths`, `anomalySensitivity`) to both the allowlist AND the serializer's explicit `Field()` declarations; removed `aiApiKey` strip from `useSettings.ts::toApiFormat()`; consolidated all 4 read sites to flat camelCase reads from `profile.preferences`. Full-pipeline regression test in `TestPreferencesPersistence::test_ai_settings_reach_ai_service_init` (mock-capture pattern — avoids the false-green of GET round-trip alone). (fixed) SHA:—
- **[AI Insights UI] [C/S2]** Silent fallback on `/ai-insights`: response omits `ai_enhancement` when no key is configured, but the page heading still said "AI Insights" with no indication that users were seeing deterministic-only output. Added label-only indicator (Cluster 3/4 precedent — no new response field): heading becomes "AI Insights (Deterministic)" with subtitle "Rule-based recommendations — External AI Enhancement not active" when `ai_enhancement` is absent. `enhancement_status` tri-state deferred as UX follow-up. (fixed) SHA:—
- **[Auth] [D/S3]** AI-settings changes did not invalidate the nightly AI-insight cache, so a provider/key swap could render stale enhancement for up to 24h. `UserPreferencesView.patch/put` now calls `AIInsightsCache.invalidate_org_cache(org_id)` when any of the 6 AI fields is in the payload. Rollback step in Shared Workflow Reference correspondingly updated (the earlier `cache.delete_pattern('versatex:ai_insights:*')` was a nonexistent API — `AIInsightsCache.invalidate_org_cache` is the actual mechanism). Regression test in `TestCacheBustOnAiSettingsChange` (fires on AI change, not on unrelated change). (fixed) SHA:—

**PR-8b — Deterministic generator audit:**

- **[AI Insights] [audit, no defects found]** `get_cost_optimization_insights`, `get_supplier_risk_insights`, `get_anomaly_insights`, `get_consolidation_recommendations` all pass regression tests on seeded fixtures: well-formed insight dicts, no NaN/Infinity, stable threshold application, empty-org returns empty list. Tests in `backend/apps/analytics/tests/test_ai_insights_deterministic.py::TestDeterministicGenerators` (5 tests). No correctness bugs found in the generators themselves.
- **[AI Insights] [audit, no defects]** `deduplicate_savings` (instance method at `:873`) and the `get_all_insights` orchestrator: savings cap vs `total_spend` enforced; dedup never inflates total beyond naive sum; empty-input handled; `ai_enhancement` correctly absent when `use_external_ai=False`. Tests in `TestGetAllInsightsAggregation` (5 tests). Critic's latent edge case (cap uses filtered-queryset total when user filters by category, not org total) confirmed to be the correct behavior — filtering scopes all numbers consistently.
- **[AI Insights] [C/S3, logged only]** `ai_services.py:505-844` direct-ORM queries diverge from the audited analytics services (HHI in `spend.py`, amount-weighted rates in `p2p_services.py`, etc.). Per the plan's document-don't-refactor default, delegation is not performed in this cluster. Divergence notes and a refactor-for-DRY follow-up are filed in Cross-Module Open. (deferred) SHA:—

### Contracts (Cluster 7)

- **[Contracts] [A/S1]** `backend/apps/analytics/contract_services.py:get_contracts_list` — Pre-fix: `supplier_spend` was a single all-time dict (`self.transactions.values_list('supplier_id').annotate(total=Sum('amount'))`), so utilization = all-time supplier spend ÷ contract total_value. A supplier with 5 years of prior spend who signed a $2M contract last month appeared as "1200% utilized" in the Contracts list on day 30. Post-fix: load relevant transactions once, then per-contract scope to `[start_date, min(end_date, today)]` before summing. Regression test in `TestContractsListUtilization`. (fixed) SHA:—
- **[Contracts] [A/S2]** `contract_services.py:get_contract_overview` — `contract_coverage_percentage` summed ALL-TIME `total_spend` and ALL-TIME spend from currently-contracted suppliers, then divided. A supplier who recently became contracted had their entire pre-contract history counted as "covered," producing artificially high coverage for long-tenured orgs. Post-fix: scope both numerator and denominator to trailing 365 days (industry-standard contract-coverage window); added `contract_coverage_window_days: 365` to the response so consumers know the window explicitly. Regression test in `TestContractCoverageWindow`. (fixed) SHA:—
- **[Contracts] [A/S1]** `contract_services.py:get_contract_performance` — `actual_monthly = total_spend / len(monthly_data)` used months-with-activity as the denominator, but `expected_monthly` used full duration_months. For sporadic contracts, this compared apples-to-oranges: a $30K-spend-in-3-months-of-12-month-contract showed `actual_monthly = $10K` ≈ `expected_monthly = $10K` (false "on-target") instead of the true $2.3K/month under-spend. Post-fix: `actual_monthly = total_spend / duration_months`; added `active_spend_months` and `duration_months` to the response so consumers can see both denominators. Regression test in `TestContractPerformanceMonthlyAverage`. (fixed) SHA:—
- **[Contracts] [D/S4]** `contract_services.py:get_contract_vs_actual_spend`, `get_savings_opportunities` — `elapsed_days` could be negative for future-dated contracts, producing negative `expected_spend` and flipping variance sign. Clamped `elapsed_days = max(0, ...)` at both sites. (fixed, defensive) SHA:—
- **[Contracts] [B/S3]** *(cross-module, pre-existing)* Renewal utilization tier thresholds (>90 increase / >70 same / >50 decrease / else evaluate) at `:253-264` and `:520-539`, savings multipliers 10% / 15% at `:420, :453`, expiring window 90-day default at `:58, :217`, off-contract severity $50K at `:424`. Already in Cross-Module Open → "Hardcoded savings multipliers (global)". No change this pass.

### Predictive (Cluster 5)

Gate note: the plan's statistical-validity gate applies. `MAPE` and `R²` on <12 months are acknowledged noise — not fixed, not flagged. Only concrete correctness issues below.

- **[Predictive] [A/S1]** `backend/apps/analytics/predictive_services.py:497, 504, 511` — Growth-metric fallback `sum(values[:-N])` compared a 12-month sum to a 1-month sum on 13-month orgs, producing nonsense `yoy_growth ≈ 1100%`. Same bug for 6-month and 3-month windows. Rewrote to emit each metric ONLY when a full equal-length prior window exists (`>= 24 mo` for YoY, `>= 12 mo` for 6-mo, `>= 6 mo` for 3-mo); consumers receive the key only when it's meaningful. (fixed) SHA:—
- **[Predictive] [FALSE POSITIVE]** `predictive_services.py:238, 269` — The initial review agent claimed an off-by-one between forecast (`slope * (data_points + i - 1)`, starting at x=n for i=1) and MAPE validation (`slope * (len(train_values) + i)`, starting at x=n-3 for i=0). Verified: both are internally consistent — the forecast projects one month beyond the last training point at x=n-1, and the MAPE validation is a SEPARATE regression on the first n-3 points predicting the 3 held-out points at x=n-3 to n-1. No bug. Logged here to prevent re-flagging by future reviewers.
- **[Predictive] [C/S4]** *(auto-deferred)* `predictive_services.py:164-169` — CI lower bounds clamped to `max(0, ...)`. For heavily declining forecasts this clamp erases the "model is uncertain enough to go negative" signal. Acceptable design choice for a procurement-spend forecast (negative spend isn't meaningful to show users). Logged only.
- **[Predictive] [C/S4]** *(auto-deferred)* `predictive_services.py:277, 518` — Field `monthly_change_rate` is slope / mean (linear slope as % of baseline), but the UI label `"+10%/month"` reads as compounded growth. Low-signal UX refinement.
- Regression tests in `apps/analytics/tests/test_p2p_services.py::TestPredictiveGrowthWindows` (4 tests).

### Matching / Compliance / PO / Requisitions (Cluster 6)

- **[Matching] [C/S1]** `p2p_services.py:586-589, 614-617` (in `get_matching_overview`) — `exception_rate` was `count/total`, which shows 10 small exceptions + 1 huge matched invoice as "90.9% exception rate" while only ~1% of spend had exceptions. Added `exception_rate_by_amount` + per-bucket `percentage_by_amount` on `three_way_matched`, `two_way_matched`, and `exceptions`. Count-based fields retained for back-compat. (fixed) SHA:—
- **[Compliance] [C/S1]** `compliance_services.py:68-71` (in `get_compliance_overview`) — `compliance_rate` was count-based, masking a $1M violation among 1000 compliant $1K txns as "99.9% compliant" when 50% of spend was non-compliant. Added `compliance_rate_by_amount` alongside. (fixed) SHA:—
- **[PO] [C/S2]** `p2p_services.py:1368-1376` (in `get_po_leakage`) — "Leakage" here identifies off-contract POs by the `is_contract_backed` flag, NOT actual $-overspend against a contract cap. An in-authorization PO with `is_contract_backed=False` is still labeled maverick. Clarified via expanded docstring; relabel of the response field deferred to avoid rippling into generators and frontend. (fixed, docstring only) SHA:—
- **[PO] [C/S2]** `p2p_services.py:get_po_by_supplier` — On-time rate used `received_count` as denominator, which included POs where `required_date` was null (not classifiable) and inflated the rate. Switched denominator to `on_time_eligible` (POs with both `required_date` AND `goods_receipts__received_date` populated). Numeric 100-fallback retained when `eligible == 0` so existing downstream generators still work, but a new `on_time_eligible_count` field lets consumers render "n/a" when the denominator is zero instead of trusting the 100. (fixed) SHA:—
- **[Requisitions] [C/S1]** `p2p_services.py:get_pr_overview` — Field `total_value` was sourced from PR `estimated_amount` (an estimate, not actual PO-committed value). Added canonical `total_estimated_value` + `estimated_value` on the `by_status` breakdown; legacy `total_value` / `value` kept as deprecated aliases for one release. (fixed) SHA:—
- Regression tests in `apps/analytics/tests/test_p2p_services.py::TestCluster6Relabels` (amount-weighted matching rates) + `::TestComplianceAmountWeightedRate` (amount-weighted compliance rate).

### YoY (Cluster 5 — YoY only)

- **[YoY] [C/S1]** `backend/apps/analytics/services/yoy.py` — Seven call sites with the pattern `(y2 − y1)/y1 * 100 if y1 > 0 else (100 if y2 > 0 else 0)` — for brand-new categories/suppliers (y1 = 0), the API returned `change_pct = 100`, indistinguishable from a category that genuinely doubled ($2.5M → $5M). Extracted shared helper `_yoy_change(y1, y2)` returning `(change_pct, is_new, is_discontinued)`. `change_pct` retains the 100 / −100 placeholders for back-compat; new `is_new` / `is_discontinued` flags let the frontend render a "New" / "Discontinued" badge instead of a misleading percentage. Applied to monthly comparison, category comparison, supplier comparison, and both drilldowns. (fixed) SHA:—
- **[YoY] [A/S1]** `yoy.py:116-118` — Single-year edge case: when only one year of data exists, the code set `year1 = year2 = the_only_year`, causing `spend_change_pct` to equal 0 — user sees "0% YoY growth" rather than "insufficient data." Added `insufficient_data_for_yoy: bool` flag to the summary dict and the drilldown responses; frontend can now render a clear empty-state instead of a fake-flat chart. (fixed) SHA:—
- **[YoY] [A/S1]** `yoy.py:106, 140, 311, 367, 438, 494` — After Cluster 2 extended `_get_fiscal_month` with a `use_fiscal_year` toggle, YoY still called it without the toggle AND hardcoded `fiscal_month_names = ['Jul'…'Jun']`. When a user selected calendar year, totals were calendar-scoped but monthly axis labels were still Jul-start fiscal — a silent mislabeling. Added module-level `CALENDAR_MONTH_NAMES` / `FISCAL_MONTH_NAMES` constants and threaded `use_fiscal_year` through every `_get_fiscal_month` call; month label array is selected per toggle. (fixed) SHA:—
- **[YoY] [D/S4]** *(auto-deferred)* `yoy.py:120` — Fallback `year1, year2 = 2024, 2025` is unreachable because the empty-transactions early-return at `yoy.py:79` fires first. Dead code; now marked with `insufficient_data_for_yoy = True` as a defensive signal if it ever becomes reachable.
- Regression tests in `backend/apps/analytics/tests/test_yoy_service.py` — `TestYoyChangeHelper` (5 tests on the helper) + `TestYoyDetailedAccuracy` (4 integration tests: new-category flag, single-year insufficient-data flag, calendar-month label switching, new-categories excluded from top_gainers).

### Spend-aggregation cluster (Cluster 4)

Audit outcome: **no correctness defects found in Overview, Suppliers/HHI, Pareto, Tail Spend, or Stratification.** Every division, aggregate null-coercion, and empty-list access in these five modules is already guarded. HHI formula confirmed correct (`Σ(percent_of_total ** 2)` with percentages scaled 0–100, range 0–10,000). Categories had one Class-C label ambiguity, now fixed. Cluster-4-specific findings below. All pre-existing hardcoded thresholds (HHI 1500/2500, concentration 70/50, supplier diversity 3/5, tail multipliers 8/15/10%, stratification 30/15%, tail default 20%) remain in Cross-Module Open → "Hardcoded savings multipliers (global)" and are owned by the first cluster that needs to flip one.

- **[Categories] [C/S2]** `backend/apps/analytics/services/spend.py:117` + `frontend/src/pages/Categories.tsx:258,443,634` — Field labeled "Concentration" / "% concentration" in UI was `top_subcategory_spend / category_total`, i.e. a single-bucket share, not a distributional concentration measure (HHI/Gini). Users reading "concentration" infer the latter. Relabeled UI strings to "Top Subcat %" (table header with hover-tooltip), "top-subcategory share" (KPI card and drill-down). Backend response field `concentration` preserved for API stability; added service-layer comment clarifying the single-bucket semantics. (fixed, label + docstring) SHA:—
- **[Stratification] [D/S4]** *(auto-deferred)* `backend/apps/analytics/services/stratification.py:149` — Segment assignment uses `band_min >= seg.min and band_min < seg.max`. Correct today because `SPEND_BANDS` and `SEGMENTS` in `constants.py` are aligned so no band spans two segments. Latent fragility: if a future SPEND_BAND is added that crosses a segment boundary, the entire band's spend is attributed to whichever segment owns `band_min`. Worth a docstring invariant but no crash or wrong-output today.
- **[Pareto/Tail] [D/S4]** *(auto-deferred)* `pareto.py:296, 320, 362` — Consolidation-opportunity result lists truncated to top-10 with no signal in the payload about how many opportunities were suppressed. UX truncation, not a correctness bug — user can't tell if they're seeing "all 7" or "10 of 400". Consider adding a `total_opportunities` field to the response in a future UX polish.
- **[Overview] [D/S4]** *(auto-deferred)* `overview.py:39-43` — All aggregates correctly use `or 0` fallback for `Sum`/`Avg` nulls and `Count` non-null. Dashboard renders 0 on an empty org rather than a "no data" state. Standard SaaS convention; flagging only in case a future UX pass wants to distinguish zero-spend from no-data.

### DPO cluster (Cluster 3)

**Primary relabel (C/S1)** — Metric labeled "DPO" / "Days Payable Outstanding" across backend and frontend was `mean(paid_date − invoice_date)` — avg days from invoice issuance to payment — NOT balance-sheet DPO (`AP / COGS × 365`). Relabeled to "Avg Days to Pay". Legacy field names retained as deprecated aliases so pre-fix `Report.summary_data` snapshots still parse.

- **[P2PServices] [C/S1]** `backend/apps/analytics/p2p_services.py` — New `_avg_days_to_pay(paid_invoices)` staticmethod. All 5 labeled methods (`get_aging_overview`, `get_supplier_payments_overview`, `get_supplier_payments_scorecard`, `get_supplier_payment_detail`, `get_dpo_trends`) route through the helper — including `get_dpo_trends` after the critic pass (earlier ledger draft overstated consolidation; that is now fact). Every response payload exposes the canonical `avg_days_to_pay` / `days_to_pay` / `current_days_to_pay` keys AND the deprecated `avg_dpo` / `dpo` / `current_dpo` aliases. (fixed) SHA:—
- **[P2PServices] [D/S2]** `p2p_services.py:210` — `get_cycle_time_trends` previously used `Avg(F('paid_date') - F('invoice_date'))` at the ORM layer with no data-quality gate. Negative-duration invoices (paid before issued) pulled the monthly average down. Added `paid_date__gte=F('invoice_date')` filter to match the Python-side helper's gate. (fixed as side effect of critic review) SHA:—
- **[P2PServices] [D/S3]** `p2p_services.py:get_supplier_payments_overview` — Added three frontend-KPI-compatibility aliases: `total_suppliers`, `avg_on_time_rate`, `avg_exception_rate`. The frontend KPI cards on SupplierPayments.tsx read these keys, but the backend previously only emitted `total_suppliers_with_ap`, `overall_on_time_rate`, `exception_rate`. Cards silently rendered 0. Pre-existing bug surfaced by the critic pass; fixed here. (fixed) SHA:—
- **[P2PServices] [D/S4]** *(auto-deferred → fixed as side effect)* — On-time rate numerator/denominator mismatch: previously `on_time` iterated the full queryset while the DPO `days` list dropped data-quality rejects. On-time numerator now applies the same `paid_date >= invoice_date` gate and divides by `sample_size` from the helper. (fixed) SHA:—
- **[Frontend] [C/S1]** `frontend/src/pages/p2p/InvoiceAging.tsx` + `frontend/src/pages/p2p/SupplierPayments.tsx` + `frontend/src/lib/api.ts` — All user-visible DPO labels renamed to "Avg Days to Pay" (KPI cards, trend chart title, supplier scorecard column, comparison chart title, tooltips, page subtitles, component interface names). Legacy field fallbacks kept: reads `avg_days_to_pay ?? days_to_pay ?? avg_dpo ?? dpo` so consumer works against both post-fix and pre-fix server versions. (fixed) SHA:—
- **[Frontend] [C/S2]** `InvoiceAging.tsx` aging subtitle — "Outstanding AP by days since invoice issuance". `Invoice.days_outstanding` property at `backend/apps/procurement/models.py:1015-1020` returns `today − invoice_date` for unpaid invoices and `paid_date − invoice_date` for paid ones; aging queryset at `p2p_services.py:952` filters to unpaid statuses, so the "today − invoice_date" formula is always the effective one in bucket context. Functionally correct; narrative now matches. Due-date-based past-due view remains a deferred follow-up. (fixed, label-only) SHA:—
- **[Reports] [C/S2]** `backend/apps/reports/generators/p2p_ap_aging.py` — Generator emitted user-visible "DPO" strings in PDF/Excel insights, risk factors, recommendations (e.g. "Extended DPO", "High DPO Risk", "DPO of X days"). All rewritten to "Avg Days to Pay" / "Payment Cycle". Summary key `current_dpo` and top-level `dpo_trend` retained as aliases for pre-fix `Report.summary_data` snapshots; canonical keys are `current_days_to_pay` and `days_to_pay_trend`. (fixed) SHA:—
- **[Reports] [D/S3]** `backend/apps/reports/views.py:138` + `backend/apps/reports/services.py:321` — Report-template description strings ("Accounts payable aging buckets, DPO trends, and payment performance") rewritten to "…avg days-to-pay trends…". Visible in the Reports picker UI. (fixed) SHA:—
- **[P2PViews] [D/S3]** `backend/apps/analytics/p2p_views.py` — OpenAPI `@extend_schema` summary/description strings and view docstrings updated (surface via `/api/docs` and IDE hovers). `summary='Get DPO trends'` → `'Get avg days-to-pay trends (legacy: DPO)'`; scorecard docstring column `- DPO` → `- Avg Days to Pay`; supplier-payment-detail docstring `Payment metrics (DPO, on-time rate)` → `(avg days to pay, on-time rate)`. URL path `/aging/dpo-trends/` and Python symbols `get_dpo_trends` / `dpo_trends` / `useDPOTrends` / `DPOTrend` deliberately kept to preserve caller and SDK stability. (fixed) SHA:—
- **[Tests] [D/S2]** `backend/apps/analytics/tests/test_p2p_services.py::TestDaysToPayResponseKeys` — Added 6 integration tests that call each of the 5 refactored service methods against a seeded org and assert both canonical and deprecated field names are present in the response, plus a separate test verifying the data-quality-reject invoice is excluded from the average. Future removal of a canonical key now fails loudly. (added) SHA:—
- **[Tests] [D/S2]** `backend/apps/reports/tests/test_p2p_generators.py` — `test_generate_with_data` and `test_dpo_trends` now assert BOTH canonical (`current_days_to_pay`, `days_to_pay_trend`) and deprecated-alias (`current_dpo`, `dpo_trend`) keys, plus equality between them. (added) SHA:—

### BaseAnalyticsService (Cluster 2)

- **[Base] [D/S2]** `backend/apps/analytics/services/base.py:__init__` — No guard on inverted `date_from` / `date_to`. Added `_validate_filters()` that raises `ValueError` when `date_from > date_to`. Silent empty-queryset behavior no longer possible. Regression tests in `backend/apps/analytics/tests/test_services.py::TestBaseFilterValidation`. (fixed) SHA:—
- **[Base] [D/S2]** `backend/apps/analytics/services/base.py:__init__` — No numeric validation on `min_amount`/`max_amount`; bad string values would crash at query time. `_validate_filters()` coerces via `Decimal(str(value))` and raises `ValueError` on failure. Empty strings still ignored. (fixed) SHA:—
- **[Base] [D/S4]** `backend/apps/analytics/services/base.py:_get_fiscal_month` — Added `use_fiscal_year` toggle to match `_get_fiscal_year`'s signature. Returns calendar month when `False`. (fixed, inline cleanup) SHA:—
- **[Seasonality] [D/S3]** `backend/apps/analytics/services/seasonality.py:83-93, 279-283` — Inline `get_fiscal_year` and `calendar_to_fiscal_month` helpers removed. All call sites now use `self._get_fiscal_year(date, use_fiscal_year)` / `self._get_fiscal_month(date, use_fiscal_year)` from the base class. Converges the FY math to a single source of truth so a future per-org override lands once. Seasonality regression tests (`TestSeasonalityOrdering`, `TestSeasonalityGeneratorParity`) pass unchanged. (fixed) SHA:—

### Seasonality (Cluster 1)

- **[Seasonality] [A/S1]** `backend/apps/analytics/services/seasonality.py:244` — `category_seasonality` was sorted by `savings_potential`, but frontend cards at `frontend/src/pages/Seasonality.tsx:479,511` label positions `[0]` and `[-1]` as "Highest/Lowest Seasonality". Swapped sort key to `seasonality_strength`. Regression tests in `backend/apps/analytics/tests/test_services.py::TestSeasonalityOrdering` and `backend/apps/reports/tests/test_seasonality_generator.py::TestSeasonalityGeneratorParity`. (fixed) SHA:—

## Deferred

Class-B / Class-C items the user has chosen not to address in the current pass. Each entry carries a reason so they re-surface at end-of-audit review.

### Seasonality

- **[Seasonality] [B/S3]** `backend/apps/analytics/services/seasonality.py:194-202` — Hardcoded savings-rate tiers (25% / 20% / 10%). Candidate for `Organization.savings_config` override at `backend/apps/authentication/models.py:65-74`. (deferred — queued for post-Phase-0a revisit on the `audit/accuracy-review` branch)
- **[Seasonality] [B/S3]** `backend/apps/analytics/services/seasonality.py:83-93` — Fiscal-year start hardcoded to July. Blast radius includes every `BaseAnalyticsService` consumer. (deferred — see Cross-module open below; decision blocks on Cluster 2)

### DPO cluster

- **[InvoiceAging] [B/S3]** `p2p_services.py:956-961` (`bucket_definitions` list) — Aging bucket boundaries 0/30/60/90 hardcoded; not payment-terms-aware. Candidate for `Organization.savings_config` or a per-org bucket override. (deferred)
- **[InvoiceAging] [C/S2]** — Standard AP-aging convention uses past-due-days (`paid_date − due_date`), not days-since-invoice. Adding a due-date-based bucket view (kept in parallel with the existing issuance-based one) is a follow-up. Non-trivial because it affects every dollar in every bucket. (deferred to future cluster)
- **[P2PCycle] [B/S3]** `p2p_services.py:182, 188, 194, 200, 207` — Stage targets 3/7/3/30 (and 43-total) hardcoded in `get_p2p_cycle_overview`. Should be per-org configurable. (deferred)
- **[P2PCycle] [B/S3]** `p2p_services.py:170-176` (`get_status` nested helper) — Variance thresholds 0%/25% for on-track/warning/critical hardcoded. (deferred)
- **[SupplierPayments] [B/S3]** `p2p_services.py:1525` — Reliability score uses `abs(avg_days_to_pay - 30) * 2` as the days-to-pay term, treating 30-day cycles as ideal. Not payment-terms-aware (ignores per-supplier `payment_terms_days`). (deferred)
- **[Naming] [B/S4]** Python method `get_dpo_trends`, Django URL name `'dpo-trends'`, React hook `useDPOTrends`, TypeScript interface `DPOTrend`, API client `getDPOTrends`. URL *path* is preserved for caller stability; the Python + TS symbols are also kept to avoid a wide-ripple rename. Consider aliasing (`get_avg_days_to_pay_trends = get_dpo_trends`) in a follow-up if the symbol names become a friction point. (deferred, naming ripple)
- **[Deprecation] [B/S4]** The "deprecated for one release" language on the alias keys is vague because this project has no defined release cadence. Before an alias is actually removed, add concrete trigger criteria (version number or date) and grep-anchor comments (`# TODO(deprecation): ...`). (deferred)

## Cross-Module Open

Shared-primitive findings that span modules and should be resolved once at the cluster boundary, not re-decided per module.

- **Fiscal-year start month — per-org override (global)** — After Cluster 2, the FY helpers are the single source of truth (Seasonality's duplicate was removed), but Jul–Jun is still hardcoded in `backend/apps/analytics/services/base.py`. A per-org override (`Organization.fiscal_year_start_month` IntegerField + schema migration + `Transaction.fiscal_year` backfill) was deferred from Cluster 2 because no demo org currently requires non-Jul-Jun — decision gate: trigger when the first real or demo org declares a different fiscal calendar. Owner: future follow-up cluster, not yet scheduled.
- **Hardcoded savings multipliers (global)** — Savings-rate constants appear in Seasonality (25/20/10% tiered), Tail Spend (8/15/10% flat), Trend (10%), Contracts (10/15%), Maverick (10%). Two incompatible models co-exist (tiered vs flat). Recommend converging on `Organization.ALLOWED_SAVINGS_CONFIG_KEYS` and picking one model. Owner: first cluster that needs to flip a rate.
- **`ai_services.py` re-implements aggregations** — Instead of delegating to the analytics services, `backend/apps/analytics/ai_services.py` queries `Transaction`/`Supplier`/`Invoice`/`PurchaseOrder` directly (see `:345-386`, `:505-844`). Fixes to shared primitives (DPO relabel, variance-threshold changes, HHI threshold tweaks) will NOT automatically reach AI-insight output. Cluster 8 (AI Insights) must explicitly re-audit each shared primitive inside `ai_services.py`. Owner: Cluster 8.
- **`P2PAnalyticsService` does not inherit `BaseAnalyticsService`** — `backend/apps/analytics/p2p_services.py:26` defines its own `__init__`, `_parse_date`, and `_apply_date_filters(date_field=...)`. Filter parity with the analytics hierarchy is ad-hoc: `supplier_ids`, `category_ids`, `min_amount`, `max_amount`, date-range validation all diverge or are missing. Cluster 2's new `_validate_filters` does not protect P2P callers. Options: (a) make P2PAnalyticsService inherit from Base and use the shared queryset-building primitives — requires rework because P2P queries `Invoice`/`PO`/etc. not `Transaction`; (b) factor the filter-validation + parsing into a mixin both hierarchies consume. **Previously tagged for Cluster 3 but not addressed there** (Cluster 3 was scoped to the DPO relabel). Re-assigned owner: **dedicated P2P-filter-parity pass**, scheduling TBD — trigger when a real consumer hits a filter mismatch, or when Cluster 6 (Matching/Compliance) needs the same primitives.

## S4 Deferred Log

Auto-deferred per S4 rule. Review as a single batch at end of audit; individually low-signal.

### Seasonality

- **[Seasonality] [B/S4]** `backend/apps/analytics/services/seasonality.py:248` — `opportunities_found = len([c for c in category_seasonality if c['seasonality_strength'] > 15])` always equals `categories_analyzed` because the list is already filtered to `strength > 15` at `:205`. Either raise one threshold (e.g., `> 30` for stricter opportunities), drop the redundant metric, or document intentional equality.
- **[Seasonality] [B/S4]** `backend/apps/analytics/services/seasonality.py:205` — `if seasonality_strength <= 15: continue` hard-codes the inclusion floor. Keep but expose as kwarg and document.
- **[Seasonality] [D/S4]** `backend/apps/analytics/services/seasonality.py:146-148, :230` — Categories grouped by `category__name` (string); `category_id` back-filled from `cat_transactions[0]`. Safe under org-scoped querysets, fragile if grouping is ever broadened. Consider keying on `(category_id, name)` as the drilldown function already does at `:330`.
- **[Seasonality] [D/S4]** `backend/apps/analytics/services/seasonality.py:176` — `low_month_index = cat_monthly_spend.index(min_spend) if min_spend > 0 else 0`. The `else 0` fallback is unreachable: `non_zero_spends` at `:172` is already filtered to strictly-positive values and the `total_spend == 0` guard at `:165` skips all-zero categories entirely. No observable wrong output; cosmetic cleanup only.
- **[Seasonality] [B/S4]** `frontend/src/pages/Seasonality.tsx:465` — When `category_seasonality.length === 1`, both the "Highest Seasonality" and "Lowest Seasonality" cards render the same category. Consider collapsing to a single "Seasonality Profile" card when `length === 1`.

### DPO cluster

- **[InvoiceAging] [B/S4]** `p2p_services.py:952` — Aging queryset `status__in=['received', 'pending_match', 'matched', 'approved', 'on_hold']` excludes `'disputed'` status. Disputed invoices still represent financial exposure; consider including with a visual flag.
- **[P2PCycle] [D/S4]** `p2p_services.py:455-456` — `variance / target * 100 if target > 0 else 0` short-circuits when target is zero. Safe today (all stage targets are > 0); latent if a future stage target is zero.
- **[Scorecard] [D/S4]** `p2p_services.py:get_supplier_payments_scorecard` — Per-row dict emits `supplier` (name) and `ap_balance`, but the TypeScript `SupplierPaymentScore` interface also declares `total_ap` and `performance_score` as optional-aliases that frontend code reads. Pre-existing inconsistency not addressed in this cluster because scorecard is stable and the score/ap_balance → performance_score/total_ap mapping is effectively dead alias code. Log for a future consistency pass.

---

## Audit Summary — closed 2026-04-22

The accuracy audit is complete. 18 modules across 8 clusters reviewed against the charter "accuracy of numbers the customer sees."

### Counts by class

| Class | Fixed in audit | Deferred (ledger) | Auto-deferred (S4) |
|---|---|---|---|
| **A — Correctness bug** | 11 | 0 | 0 |
| **B — Design default** | 0 | 14 (mostly hardcoded thresholds — Cross-Module Open) | 7 |
| **C — Proxy / mislabel** | 8 | 3 | 0 |
| **D — Latent / edge** | 5 | 4 | 8 |
| **Total** | **24 fixes** | **21 deferred** | **15 S4** |

### Modules with zero defects found

Overview, Suppliers/HHI, Pareto, Tail Spend, Stratification (all in Cluster 4). Read end-to-end; existing guards and formulas verified correct. Only the Categories "Concentration" label was adjusted (C/S2 → "Top Subcat %") in that cluster.

### Notable fixes by visibility

**User-visible "wrong number" bugs fixed:**
1. Seasonality sort-key (Cluster 1) — "Highest Seasonality" now shows the actual most-seasonal category, not the highest-savings one.
2. DPO mislabeled (Cluster 3) — "Days Payable Outstanding" was invoice-to-payment cycle days, not balance-sheet DPO. Relabeled to "Avg Days to Pay" across 5 service methods + 2 frontend pages.
3. Categories "Concentration" (Cluster 4) — renamed "Top Subcat %" to match the actual single-bucket formula.
4. YoY new-category inflation (Cluster 5) — `+100%` placeholder for brand-new categories replaced with `is_new` / `is_discontinued` flags.
5. Single-year YoY "0% growth" (Cluster 5) — now returns `insufficient_data_for_yoy: true`.
6. Predictive 13-month YoY ~1100% anomaly (Cluster 5) — growth windows require full equal-span prior window.
7. 3-Way Matching / Compliance count-based rates (Cluster 6) — `rate_by_amount` companion fields added.
8. PO "leakage" (Cluster 6) — docstring + `on_time_eligible_count` denominator clarity.
9. Requisitions `total_value` (Cluster 6) — renamed `total_estimated_value` (alias kept).
10. Contracts utilization including pre-contract history (Cluster 7) — scoped to per-contract date window. Contract coverage scoped to trailing 12 months. Monthly variance uses full duration.
11. External AI Enhancement dark feature (Cluster 8) — 4-site plumbing fix + API-key masking + admin exclusion + "AI Insights (Deterministic)" label.

### Deferred items with owners

Every item in `Cross-Module Open` has a named disposition:

- **FY per-org override** — owner: future cluster-2 follow-up when a real org requires non-Jul-Jun. Currently documented, no demo org requires.
- **Hardcoded savings multipliers** — owner: first cluster that needs to flip one. Deferred.
- **`ai_services.py` re-implements aggregations / DRY-delegation refactor** — owner: future tech-debt pass; divergence notes in Cluster 8 ledger entry.
- **`P2PAnalyticsService` does not inherit BaseAnalyticsService** — owner: dedicated P2P-filter-parity pass.
- **`aiApiKey` storage encryption** — owner: security-review TBD. Label fix (remove false "stored encrypted" text) shipped in Cluster 8.
- **AI-enhanced insight accuracy acceptance criteria** — owner: future initiative TBD. LLM correctness explicitly out of charter.
- **`enhancement_status` tri-state UX** — owner: future UX pass. Label-only indicator shipped instead.

### Branch + test state at close

- Branch: `audit/accuracy-review` (working branch during audit; not yet merged to main).
- Backend regression: **577 passing** (`apps/analytics/tests/` + `apps/reports/tests/` + `apps/authentication/tests/`). 418 baseline at audit start + 159 added across 8 clusters.
- Frontend: rebuilt at each cluster boundary; manual smoke verified against 3 demo orgs (eaton, uch, tsu).
- 0 regressions across all 8 clusters.

### Conventions established by the audit

Captured in `CLAUDE.md` "Analytics accuracy conventions" section:

1. **Amount-weighted rates** — Count-based rates must be accompanied by `*_by_amount` companion fields wherever the UI exposes them.
2. **Deprecated alias lifetime** — When renaming a response field, keep the old key as a deprecated alias for one release; update TypeScript interface with `@deprecated` JSDoc.
3. **FY helpers** — All FY math routes through `BaseAnalyticsService._get_fiscal_year` / `_get_fiscal_month`. No inline re-implementations.
4. **Equal-span growth windows** — Any YoY / 6-mo / 3-mo growth metric must omit its key when fewer than 2 full windows of data exist. No fallback to partial windows.
5. **`ALLOWED_PREFERENCE_KEYS` gate** — New keys on `UserProfile.preferences` must be added to both the allowlist AND explicitly declared on `UserPreferencesSerializer`.
6. **No-silent-fallback rule (no-key case)** — When `AIInsightsService` cannot enhance because no key is configured, the response must omit `ai_enhancement` AND the frontend must render a "(Deterministic)" label.
7. **Label-only Class-C relabels** — New response fields are feature additions, not audit-scope work. Class-C proxy fixes change UI labels or response-field names (with deprecated aliases), not add new fields.
8. **Document-don't-refactor default** — When a shared primitive is re-implemented in another service, document the divergence first; only refactor if divergence produces a user-visible wrong number.
9. **Helper primitives for reuse** — `P2PAnalyticsService._avg_days_to_pay` (Cluster 3), `apps.analytics.services.yoy._yoy_change` (Cluster 5 module-level function), `AIInsightsService.deduplicate_savings` (Cluster 8 instance method), `UserProfile.mask_preferences` (Cluster 8 static helper).
