# P2P (Procure-to-Pay) Module — Claude Reference

> **When to read this:** Editing files in `backend/apps/procurement/` that touch P2P models (PR/PO/GR/Invoice), or `backend/apps/analytics/p2p_*.py`, or any frontend hook in `useP2PAnalytics.ts`.
> **You can skip this if:** Working only on Transaction-level analytics, AI Insights, or unrelated frontend pages.

## Core invariants

1. **Document chain order is rigid: PR → PO → GR → Invoice → Payment.** No skipping stages. Models live in `backend/apps/procurement/models.py`.
2. **Match exceptions never delete invoices** — they set `Invoice.match_status='exception'` and surface in the matching API at `backend/apps/analytics/p2p_views.py`.
3. **`P2PAnalyticsService` does NOT inherit from `BaseAnalyticsService`.** This divergence is intentional, tracked in `docs/ACCURACY_AUDIT.md` Cross-Module Open. Filter validation is ad-hoc until that lands. **Do not refactor without coordination.**
4. **All P2P endpoints scope by `request.organization`** — never query unscoped or you leak across tenants.
5. **`P2PImportMixin` at `backend/apps/procurement/admin.py:1334`** is the source of truth for admin CSV column ordering. The drift-guard test at `backend/apps/authentication/tests/test_admin_export.py::TestColumnDriftGuard` will fail loudly if the export column constants drift from this importer — fix the cause, don't suppress the test.

## Primitives — use these, don't re-implement

| Primitive | Location | Purpose |
|---|---|---|
| `P2PAnalyticsService._avg_days_to_pay` | `backend/apps/analytics/p2p_services.py` (staticmethod) | Canonical "days from invoice to payment" calc — 8 call sites consolidated here |
| `P2PImportMixin` | `backend/apps/procurement/admin.py:1334` | Admin CSV import for PR/PO/GR/Invoice |
| `BaseAnalyticsService._get_fiscal_year` / `_get_fiscal_month` | `backend/apps/analytics/services/base.py:96-113` | FY math — but `P2PAnalyticsService` doesn't inherit, see divergence below |

## Known divergences (and why they exist)

- **`P2PAnalyticsService` doesn't inherit from `BaseAnalyticsService`.** Tracked as Cross-Module Open in `docs/ACCURACY_AUDIT.md`. Until consolidation lands, P2P services duplicate filter validation and FY math. Document divergence rather than refactor — see Accuracy Convention §8 in root CLAUDE.md.

## Cross-cutting gotchas

- **Amount-weighted rate companion fields (Convention §1).** Any new count-based rate (match rate, compliance rate, on-time rate) MUST also emit an `*_by_amount` companion. Example: `exception_rate_by_amount` at `backend/apps/analytics/p2p_services.py`.
- **3-Way Matching exception flow.** Mismatched invoices set `match_status='exception'`, do NOT delete. UI presents them via `/api/v1/analytics/matching/exceptions/`.
- **Bulk resolution endpoint exists.** `/api/v1/analytics/matching/exceptions/bulk-resolve/` — single notes modal applies to all selected violations. Frontend at `frontend/src/pages/Matching.tsx`.
- **Industry-aware seeding.** `seed_demo_data --industry healthcare` swaps in industry-specific departments, cost-center prefixes, payment terms, and policies. See `docs/DEMO_DATA.md`.
- **Cross-org FK enforcement is at the DB layer (v2.12).** Postgres triggers from migration `0009_cross_org_fk_check_constraints` raise on `Transaction.organization_id != supplier.organization_id` (and parallel for `Contract`, `PurchaseOrder`, `Invoice`) on any INSERT/UPDATE. ORM bypass paths (admin shell, raw SQL, `.update()`) cannot violate the invariant. Tests skip on SQLite (`settings_test`); CI Postgres exercises them. See `backend/apps/procurement/tests/test_cross_org_fk_check.py`.
- **N+1 cluster eliminated (v2.12).** `get_detailed_category_analysis` in `services/spend.py`, `get_detailed_tail_spend` in `services/pareto.py` (3 sites), `get_p2p_cycle_overview` in `p2p_services.py`, and `get_exceptions_by_supplier` in `p2p_services.py` all use single-query / DB-side aggregation. `get_exceptions_by_supplier` specifically uses a `Subquery(OuterRef(...))` annotation — see `p2p_services.py:670-720`. Don't reintroduce per-row Python loops in these methods. Drift-guard test: `backend/apps/analytics/tests/test_n_plus_1_cluster.py` uses `assertNumQueries` to pin the bound.
- **CSV upload observability (v2.12).** `process_csv_upload` writes per-batch entries to `DataUpload.error_log` (JSONField) with `kind='batch'` discriminator. Format: `{kind, batch_index, first_row_number, last_row_number, status, first_failed_row_number, error_class, message}`. `progress_message` carries the human-readable summary truncated to 255 chars. Status semantics: `partial` when at least one batch failed but others committed; do NOT remap to `failed` for scheduled uploads since prior rows are persisted.
- **Celery CSV upload re-checks membership at task entry (v2.12).** Finding C4: `process_csv_upload` calls `UserOrganizationMembership.objects.filter(user=upload.uploaded_by, organization=upload.organization, is_active=True).exists()` before any row writes. A user removed/deactivated between `delay()` and execution gets a `failed` upload with `MEMBERSHIP_REVOKED_ERROR` in `error_log`.

## API surface (orientation only)

P2P endpoints live under `/api/v1/analytics/p2p/`, `/api/v1/analytics/matching/`, `/api/v1/analytics/aging/`, `/api/v1/analytics/requisitions/`, `/api/v1/analytics/purchase-orders/`, `/api/v1/analytics/supplier-payments/`. Routing in `backend/apps/analytics/p2p_urls.py`.

Frontend hooks in `frontend/src/hooks/useP2PAnalytics.ts`.

To enumerate current endpoints: `grep -E "path\(" backend/apps/analytics/p2p_urls.py`.

## Test patterns

- P2P generator tests: `backend/apps/reports/tests/test_p2p_generators.py`
- Admin export drift-guard: `backend/apps/authentication/tests/test_admin_export.py`
- Run: `docker-compose exec backend pytest backend/apps/reports/tests/test_p2p_generators.py -v`
- Factory: `backend/apps/authentication/tests/factories.py::DemoOrganizationFactory(OrganizationFactory)` — has `is_demo=True`

## See also

- `backend/apps/procurement/models.py` — P2P model definitions
- `backend/apps/analytics/p2p_services.py` — `P2PAnalyticsService`
- `backend/apps/analytics/p2p_views.py` — DRF views
- `backend/apps/analytics/p2p_urls.py` — URL routing
- `frontend/src/hooks/useP2PAnalytics.ts` — frontend hooks
- `docs/ACCURACY_AUDIT.md` — Cross-Module Open ledger
- `docs/CHANGELOG.md` — v2.5 (P2P launch) and v2.11 (admin export) historical context
