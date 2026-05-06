# Codebase Review Remediation — Open Items

**Status as of 2026-05-06:** the v2.12 remediation cycle closed 45 of 45 actionable findings from the 2026-05-04 codebase review (see [docs/plans/2026-05-05-codebase-remediation.md § Closure status](plans/2026-05-05-codebase-remediation.md) for the per-finding SHA table). Two items remain open by deliberate decision:

| Item | Reason open | Owner | Status |
|---|---|---|---|
| **Task 1.3** — `Report.is_public` semantics | Blocked on product decision | Reports product owner | Phase 0 interim filter active; safe to ship |
| **Task 5.4** — Aging method DB-side aggregation | Deferred on scale criterion | Engineering (re-runs diagnostic) | No-op while no tenant >20K open invoices |

Neither item leaves a vulnerability or correctness gap on production today. Both can be picked up at any time. This document tells you everything you need to do that.

---

## Task 1.3 — `Report.is_public` semantics

### The finding (Critical #4)

`Report.can_access` at `backend/apps/reports/models.py:198-199` returns `True` for `is_public=True` reports without checking the user's organization. Without other gates, any authenticated user with a report's UUID could read any public report from any organization. The Phase 0 interim mitigation (commit `d6b84ed`) added an org filter at the four endpoint queries (`reports/views.py:417, 449, 480, 537`), so the cross-org read path is closed under all conditions today — including for legitimately-public reports.

### Why this is open

The fix branches on a product question that engineering can't answer alone:

- **Branch (a) — "public within the org":** `is_public=True` makes a report visible to all members of the same organization (regardless of `created_by`). Cross-org access stays blocked. The field arguably should be renamed `is_org_public` to make the within-org semantics explicit at every call site.
- **Branch (b) — "public platform-wide":** `is_public=True` makes a report visible to authenticated users in any organization (the field's literal pre-fix behavior). Need to gate WHO can flip the flag — superuser-only, or org admin, or a per-org "publish" role.

Both are defensible. The right choice depends on what Reports product owner intends `is_public` to mean — and we don't have that decision recorded anywhere.

### What's needed to unblock

**1. Branch decision (a or b)** — from whoever owns Reports product.

**2. Answers to the sub-decisions for the chosen branch:**

For (a):
- Should existing in-org admins / managers be able to mark a report `is_public=True`, or only admins? Or no one (just keep it for system-generated reports)?
- Same question for *unsetting* it.

For (b):
- Who can mark a report public? Superuser-only is safest; org admin is the most permissive defensible option.
- Should the publishing org's name/identity be visible to consumers in other orgs (i.e., is "Org X published a report" itself sensitive)?
- Is there an audit / notification requirement when public reports are created or modified?

### Data check before deciding

Run from the Django shell:

```python
from apps.reports.models import Report
from django.db.models import Count
list(Report.objects.filter(is_public=True).values('organization__name').annotate(n=Count('id')).order_by('-n'))
```

Interpretation:
- **0 public reports today** → either branch is a clean cutover; pick whichever matches product intent.
- **Public reports exist within a single org each** → branch (a) is closer to actual usage today.
- **Public reports being read cross-org** (check API logs for cross-org-UUID requests) → branch (b) is the live behavior; switching to (a) would break a customer flow.

### Effort estimate

| Branch | Effort | Why |
|---|---|---|
| (a) Within-org | 0.5–1 day | Remove the `is_public=True` short-circuit in `can_access`; optionally rename the field with a deprecated alias; the Phase 0 interim filter becomes the permanent fix. Mostly mechanical. |
| (b) Platform-wide | 1.5–2 days | Add a permission class for the setter; add mutation tests; possibly a migration for the `is_platform_public` rename; possibly an audit-log entry. More moving pieces. |

### How to resume

1. Get the product decision (a or b) and answers to the sub-decisions.
2. Reactivate the placeholder task in `docs/plans/2026-05-05-codebase-remediation.md § Phase 1 Task 1.3` — the file/line targets and remediation sketch are already there.
3. After the permanent fix lands, remove the Phase 0 interim filter from the four `reports/views.py` sites — grep for `# Finding #4` to find them.
4. Add a regression test asserting the new contract (within-org-only OR platform-wide-with-admin-gating).

### Risk if left open

- **Cross-org read blocked.** Phase 0 interim filter holds the line. No exploitable vulnerability today.
- **Multi-org users locked out of legitimate non-primary-org reports.** The Phase 0 filter uses `request.user.profile.organization` (single-org legacy), so multi-org users cannot view reports in any of their non-primary orgs through these endpoints. If you have multi-org users routinely viewing reports across their orgs, they're being silently locked out. For predominantly single-org users, this is invisible.

If multi-org access becomes a real friction point before product decides, escalate; that converts the deferral from "wait for product" to "ship branch (a) now, refine later."

---

## Task 5.4 — Aging method DB-side aggregation

### The finding (Critical #17)

`get_aging_overview` and `get_aging_by_supplier` in `backend/apps/analytics/p2p_services.py:963-1141` load unbounded `Invoice.objects.filter(...)` querysets into Python memory, then iterate four times for bucket assignment, plus six additional separate queries for the 6-month trend. At scale this is O(N) memory + 8 DB round-trips per page load.

The review classified this as **P0 at scale, P1 below the threshold.** Specifically: **OOM/timeout starts hurting at >20K open invoices per organization.** Below that, it's wasted work but not user-visible.

### Why this is open

At remediation time (2026-05-06), the diagnostic showed:

```
Bolt & Nuts Manufacturing: 267 open invoices
Pacific State University:  251 open invoices
Mercy Regional Medical Center: 244 open invoices
Max:                       267 (well below 20K threshold)
```

No tenant is anywhere near the 20K elevation criterion. The fix would be a sizeable refactor (rewrite four bucket assignments + the 6-month trend as DB-side aggregations) and would not change observable behavior at current scale. Phase 5 deferred this per the plan's gating rule.

### What triggers picking this up

Any of:
1. **Any tenant approaches the threshold** (>10K open invoices is a reasonable warning line; >20K is the elevation criterion).
2. **AP aging page latency** noticeably degrades (look for slow-query alerts on `Invoice` filters in `p2p_services.py`).
3. **Tenant onboarding** of a customer with materially larger invoice volume than the current demo orgs.

### Diagnostic query

Re-run from the Django shell at any time:

```python
from apps.procurement.models import Invoice
from django.db.models import Count
list(
    Invoice.objects
    .filter(paid_date__isnull=True)
    .values('organization__name')
    .annotate(n=Count('id'))
    .order_by('-n')[:10]
)
```

Run this on a quarterly cadence or when the warning signs above appear.

### Effort estimate

**Medium — 1.5–2 days.** Four bucket assignments rewritten as a single `GROUP BY`-style query with conditional aggregation, plus the 6-month trend converted to one window-function query (or six fewer round-trips via `Q`-based annotations). Drift-guard tests should pin the query count and assert result equivalence with the current Python-side bucketing.

### How to resume

1. Re-run the diagnostic above. If max >20K, **elevate this task to Phase 2 priority** (silent regression at scale).
2. Reactivate the task placeholder in `docs/plans/2026-05-05-codebase-remediation.md § Phase 5 Task 5.4`. The remediation sketch is already there.
3. Use the existing N+1 cluster fix (commit `aafb3fb`, which closed Findings B1/B2/B6/B7) as the implementation pattern reference — `services/spend.py:96-153` and `services/pareto.py:282-360` show the same shape of refactor (per-iteration aggregation → single GROUP BY).
4. Add `assertNumQueries` regression tests in `backend/apps/analytics/tests/test_n_plus_1_cluster.py` (the file already exists from the B-cluster fix).

### Risk if left open

**None at current scale.** The two methods work correctly; they're just inefficient. The page renders in acceptable time at 267 open invoices; the work-per-request scales linearly with invoice count, so you'd notice degradation before hitting OOM in a healthy monitoring setup.

---

## Pointers

- **Per-finding closure SHAs:** [docs/plans/2026-05-05-codebase-remediation.md § Closure status](plans/2026-05-05-codebase-remediation.md)
- **Original Critical-tier findings:** [docs/codebase-review-2026-05-04-v2.md](codebase-review-2026-05-04-v2.md) (Findings #4 and #17 in the verified list)
- **Architectural rationale (v2.12 release notes):** [docs/CHANGELOG.md § v2.12](CHANGELOG.md)
- **Pending follow-ups (non-blocking, captured in commit messages):** see the "Pending follow-ups" section of the plan file. None of those are in the same category as the two items above — they're code-quality polish, not deliberate deferrals waiting on a decision.

If a third item appears (a new finding from a future review, or one of the pending follow-ups becomes urgent), add a section here in the same format so this stays the single front door for "what's left from the remediation."
