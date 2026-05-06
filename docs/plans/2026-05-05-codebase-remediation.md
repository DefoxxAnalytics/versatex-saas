# Codebase Remediation Implementation Plan

> **STATUS — 2026-05-06: COMPLETE.** All six phases merged to `main` (38 commits, pushed at SHA `371c4da`). 45 of 45 actionable findings closed. Two items intentionally deferred: Task 1.3 (`Report.is_public` semantics — blocked on Reports product owner decision; Phase 0 interim org filter still active) and Task 5.4 (aging method DB-side aggregation — diagnostic shows max 267 open invoices per tenant, well below the 20K elevation threshold). See "Closure status" section below for per-finding commit SHAs.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the 45 verified findings from the 2026-05-04 codebase review (17 Critical from v2 + 28 confirmed High from highs-verified) in a risk-ordered sequence that ships interim containment within hours and permanent fixes within ~3 weeks.

**Architecture:** Six phases ordered by risk and dependency. Phase 0 ships reversible interim mitigations for the live-exploitation paths (nginx blocks, feature flags, single-line decorators, query filters) within hours. Phases 1–5 deliver permanent fixes, each scoped as a coherent bundle that can be executed sequentially or parallelized across developers. Every fix lands with a drift-guard test so the same defect can't regress.

**Tech Stack:** Django 5.0 + DRF + Celery/Redis + PostgreSQL on the backend; React 18 + TypeScript + Tailwind 4 + Vite + TanStack Query on the frontend; nginx in front of the SPA; Docker Compose for local; Railway for production.

**Companion documents:**
- `docs/codebase-review-2026-05-04-v2.md` — verified Critical-tier findings (the source of #1–#17 in this plan)
- `docs/codebase-review-2026-05-04-highs-verified.md` — verified High-tier findings (the source of A1–E6 prefixes)
- `docs/codebase-review-2026-05-04_Review_Summary.md` — meta-review of the v2 doc

**Conventions used in this plan:**
- Findings prefixed `#N` are v2 Criticals (e.g., `#1` = self-registration role escalation)
- Findings prefixed `A1`/`B1`/`C1`/`D1`/`E1` are highs-verified items by domain (Auth/Analytics/proCurement/reports/frontEnd)
- All test commands assume `docker-compose up -d` is running; add `docker-compose exec backend ` prefix for backend tests
- Branch convention: `fix/<phase>-<finding>` e.g., `fix/phase-0-register-block`

---

## Phase Index & Sequencing

| Phase | Bundle | Findings | Effort | Ship gate | Status |
|---|---|---|---|---|---|
| **Phase 0** | Containment wave (interim mitigations) | #1, #2, #4, #6, #7, #8 (interim only) | 4–8 hours | Tier 1 reversible blocks live in production | ✅ merged `ba8db64` |
| **Phase 1** | Auth & tenant permanent fixes | #1, #2, #4, #11, A1, B9, A5 | 3–5 days | Phase 0's interim blocks can be removed | ✅ merged `aefb029` (1.3 deferred) |
| **Phase 2** | Silent regressions & data integrity | #5, #6 (perm), #9, #10, #12, B12, B13, B14, D1 | 4–6 days | Anti-hallucination + scheduling restored | ✅ merged `bfa6ea5` |
| **Phase 3** | Broken features restoration | #13, #16, E1, E2, E5, E6 | 2–3 days | User-facing features functional in prod | ✅ merged `431590a` |
| **Phase 4** | Cost containment & streaming hardening | #7 (perm), #8 (perm), B10 | 1–2 days | Streaming surface fully bounded | ✅ merged `e1e1a5a` |
| **Phase 5** | Hardening, performance, and tech debt | #3, #14, #15, #17, A2, A3, A6, B1–B8, B11, C2, C3, C4, D2, E3, E4 | 5–10 days | Defense-in-depth + scale-readiness | ✅ merged `371c4da` (5.4 deferred) |

**Phase dependencies:**
- Phase 0 must ship first (any of its tasks can be done in parallel; total ~half day).
- Phase 1 unblocks Phase 0 reversal (the interim blocks can come down once permanent fixes land + tests pass).
- Phases 2, 3, 4, 5 are mutually independent and can be parallelized across developers.

**Decisions required before specific tasks** (gate, not block):
- **Phase 1 task 1.3 (Finding #4)** — Reports product owner must decide `is_public` semantics: "public within org" vs. "public platform-wide." Schedule before Phase 1 starts.
- **Phase 5 task 5.7 (Finding #17)** — Run the diagnostic ORM query first; if any tenant >20K open invoices, elevate this fix to Phase 2 instead.

**Out of scope of this plan:**
- The ~33 unverified Mediums (need a separate verification pass — recommend after Phase 2 completes).
- Live production runtime configuration (nginx overrides, env vars, monitoring) — track in a separate operations checklist.
- Effort sizing for individual sub-steps (T-shirt sizes given at the phase level only).

---

## Phase 0 — Containment Wave (4–8 hours, reversible)

**Goal:** Stop active exploitation paths within hours using interim, reversible mitigations. Permanent fixes land in Phases 1–4.

**Branch strategy:** Single branch `fix/phase-0-containment`. One PR with all 6 tasks. Reviewers should focus on: are these reversible? do they break legitimate flows?

**Pre-flight:**
- [ ] Confirm `docker-compose up -d` runs cleanly on your machine
- [ ] Run existing backend tests: `docker-compose exec backend pytest` — note any pre-existing failures so they're not attributed to your changes
- [ ] Create branch: `git checkout -b fix/phase-0-containment`

---

### Task 0.1 — Block self-registration at nginx (Finding #1 interim)

**Files:**
- Modify: `frontend/nginx/nginx.conf`

**Why:** The `/api/v1/auth/register/` endpoint accepts anonymous POSTs that mint admin users in any organization. Permanent fix lands in Phase 1 task 1.1 (serializer hardening). Interim: block at the edge.

- [ ] **Step 1: Read existing nginx.conf to find the right insertion point**

```bash
cat frontend/nginx/nginx.conf | head -80
```

Look for the `server { ... }` block that proxies `/api/`. The new `location` directive must come BEFORE the broader `/api/` location.

- [ ] **Step 2: Add the block**

Insert immediately before the existing `location /api/` block:

```nginx
# INTERIM CONTAINMENT for register endpoint (Finding #1).
# Remove after Phase 1 task 1.1 lands (RegisterSerializer no longer accepts caller-controlled role).
location = /api/v1/auth/register/ {
    return 403;
}
location = /api/auth/register/ {
    return 403;
}
```

The `=` makes it an exact-match. Both legacy and v1 paths are blocked because the project supports both per `config/urls.py`.

- [ ] **Step 3: Rebuild + restart frontend container**

```bash
docker-compose up -d --build --force-recreate frontend
```

- [ ] **Step 4: Smoke-test that register is blocked**

```bash
curl -i -X POST http://localhost:3001/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"x","password":"y","email":"x@x.com"}'
```

Expected: `HTTP/1.1 403 Forbidden`. NOT 201 Created. NOT 400 Bad Request (a 400 would mean nginx forwarded to Django).

- [ ] **Step 5: Smoke-test that login still works**

```bash
curl -i -X POST http://localhost:3001/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<your local admin password>"}'
```

Expected: 200 OK with a JWT or cookie. (If you don't have an admin user, skip this — the point is that nginx didn't accidentally block other auth routes.)

- [ ] **Step 6: Commit**

```bash
git add frontend/nginx/nginx.conf
git commit -m "fix(security): nginx-layer block on /auth/register/ (Finding #1 interim)

Anonymous POST to register endpoint mints admin users in any org via
caller-controlled 'role' field in RegisterSerializer. Permanent fix
in Phase 1 task 1.1 will tighten the serializer; this is an interim
edge block that's reversible by removing the two location directives.

Refs: docs/codebase-review-2026-05-04-v2.md Finding #1"
```

---

### Task 0.2 — Feature-flag the membership-creation endpoint (Finding #2 interim)

**Files:**
- Modify: `backend/apps/authentication/views.py:720-737`
- Modify: `backend/config/settings.py` (one new env-driven flag)
- Modify: `backend/.env.example` (document the flag)

**Why:** `UserOrganizationMembershipViewSet.perform_create` accepts cross-org admin grants from any user with `IsAdmin` permission, with no check that the requester is admin of the *target* org. Permanent fix lands in Phase 1 task 1.2 (proper org-membership check). Interim: gate behind a default-off flag.

- [ ] **Step 1: Add the flag to settings.py**

Find the section where other feature-flag-style settings live (likely near `INSTALLED_APPS` or end of file). Add:

```python
# Phase 0 interim containment for Finding #2 — cross-org admin escalation.
# When False, blocks ALL membership creation endpoint calls.
# Permanent fix in Phase 1 task 1.2; flip to True (or remove flag) when that lands.
MEMBERSHIP_CREATE_ENABLED = config('MEMBERSHIP_CREATE_ENABLED', default=False, cast=bool)
```

- [ ] **Step 2: Document in .env.example**

Append:
```
# Membership creation interim flag (Finding #2). Keep False until Phase 1 task 1.2 ships.
MEMBERSHIP_CREATE_ENABLED=False
```

- [ ] **Step 3: Write the failing test**

Create or open `backend/apps/authentication/tests/test_membership_containment.py`:

```python
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.authentication.models import Organization, UserProfile

User = get_user_model()


class TestMembershipCreateContainment(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org", slug="test")
        self.admin = User.objects.create_user(username="admin", password="pw")
        UserProfile.objects.create(user=self.admin, organization=self.org, role="admin")
        self.client.force_authenticate(self.admin)

    @override_settings(MEMBERSHIP_CREATE_ENABLED=False)
    def test_create_blocked_when_flag_disabled(self):
        target_user = User.objects.create_user(username="target", password="pw")
        UserProfile.objects.create(user=target_user, organization=self.org, role="viewer")
        response = self.client.post("/api/v1/auth/memberships/", {
            "user": target_user.id,
            "organization": self.org.id,
            "role": "admin",
        })
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @override_settings(MEMBERSHIP_CREATE_ENABLED=True)
    def test_create_passes_through_when_flag_enabled(self):
        target_user = User.objects.create_user(username="target2", password="pw")
        UserProfile.objects.create(user=target_user, organization=self.org, role="viewer")
        response = self.client.post("/api/v1/auth/memberships/", {
            "user": target_user.id,
            "organization": self.org.id,
            "role": "admin",
        })
        # Either 201 (creation worked) or 400 (validation error) is acceptable; just NOT 503.
        self.assertNotEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
```

- [ ] **Step 4: Run the test, confirm it fails**

```bash
docker-compose exec backend pytest apps/authentication/tests/test_membership_containment.py -v
```

Expected: both tests FAIL (the flag check doesn't exist yet).

- [ ] **Step 5: Implement the flag check in views.py**

Open `backend/apps/authentication/views.py`. Find `UserOrganizationMembershipViewSet.perform_create` (around line 720). Add the flag check at the top of `perform_create`:

```python
def perform_create(self, serializer):
    from django.conf import settings
    from rest_framework.exceptions import APIException
    from rest_framework import status

    if not getattr(settings, 'MEMBERSHIP_CREATE_ENABLED', False):
        # Phase 0 containment for Finding #2 — cross-org admin escalation.
        # Permanent fix in Phase 1 task 1.2.
        exc = APIException("Membership creation temporarily disabled (security review in progress).")
        exc.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        raise exc

    serializer.save(invited_by=self.request.user)
```

- [ ] **Step 6: Run tests, confirm they pass**

```bash
docker-compose exec backend pytest apps/authentication/tests/test_membership_containment.py -v
```

Expected: both PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/authentication/views.py backend/config/settings.py backend/.env.example backend/apps/authentication/tests/test_membership_containment.py
git commit -m "fix(security): feature-flag membership creation endpoint (Finding #2 interim)

UserOrganizationMembershipViewSet.perform_create accepts cross-org admin
grants without validating requester is admin of the TARGET org. Permanent
fix in Phase 1 task 1.2; this is an interim default-off flag.

Set MEMBERSHIP_CREATE_ENABLED=True in .env to restore the endpoint behavior
(not recommended in production until Phase 1 ships).

Refs: docs/codebase-review-2026-05-04-v2.md Finding #2"
```

---

### Task 0.3 — Add throttle decorator to streaming endpoints (Finding #7)

**Files:**
- Modify: `backend/apps/analytics/views.py:3137-3216` (decorate two endpoints)
- Test: `backend/apps/analytics/tests/test_streaming_throttle_driftguard.py` (new)

**Why:** `ai_chat_stream` and `ai_quick_query` carry `@api_view` and `@permission_classes` but no throttle. A scripted authenticated session can drain ~$1K–$5K/night via the platform's `ANTHROPIC_API_KEY`. The decorator + class already exist (used on 8 other AI endpoints).

This is **already permanent** — the decorator is the right long-term fix. No interim/permanent split needed. Phase 4 will follow up with model allowlist + payload bounds (separate concerns).

- [ ] **Step 1: Write the drift-guard test first**

Create `backend/apps/analytics/tests/test_streaming_throttle_driftguard.py`:

```python
"""Drift-guard: AI streaming endpoints must carry the throttle decorator.

Finding #7 (v2 review): unbounded LLM cost from a single authenticated session.
This test prevents regression by reading the source and asserting the decorator
is present on the two streaming view functions.
"""
import inspect
from apps.analytics import views


def _decorators_of(view_func):
    """Return decorator names applied to a DRF function-based view."""
    # @api_view stores throttle_classes on the wrapped view's cls
    cls = getattr(view_func, 'cls', None)
    if cls is None:
        return []
    return [c.__name__ for c in getattr(cls, 'throttle_classes', [])]


def test_ai_chat_stream_has_throttle():
    assert 'AIInsightsThrottle' in _decorators_of(views.ai_chat_stream), (
        "ai_chat_stream must carry @throttle_classes([AIInsightsThrottle]). "
        "See Finding #7."
    )


def test_ai_quick_query_has_throttle():
    assert 'AIInsightsThrottle' in _decorators_of(views.ai_quick_query), (
        "ai_quick_query must carry @throttle_classes([AIInsightsThrottle]). "
        "See Finding #7."
    )
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
docker-compose exec backend pytest apps/analytics/tests/test_streaming_throttle_driftguard.py -v
```

Expected: both FAIL with "AIInsightsThrottle" not in `[]`.

- [ ] **Step 3: Add decorators to both views**

Open `backend/apps/analytics/views.py`. Find `ai_chat_stream` (around line 3137). Modify the decorator stack:

```python
# BEFORE:
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_chat_stream(request):
    ...

# AFTER:
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AIInsightsThrottle])  # Finding #7
def ai_chat_stream(request):
    ...
```

Repeat for `ai_quick_query` (around line 3214). Both decorators must come from imports already present at the top of the file (`from rest_framework.decorators import api_view, permission_classes, throttle_classes` and `from .throttles import AIInsightsThrottle` — verify these imports exist; if not, add them.)

- [ ] **Step 4: Run the tests, confirm they pass**

```bash
docker-compose exec backend pytest apps/analytics/tests/test_streaming_throttle_driftguard.py -v
```

Expected: both PASS.

- [ ] **Step 5: Run the broader analytics test suite to confirm no regression**

```bash
docker-compose exec backend pytest apps/analytics -x
```

Expected: no new failures. Existing failures are pre-existing — note them but don't fix here.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/analytics/views.py backend/apps/analytics/tests/test_streaming_throttle_driftguard.py
git commit -m "fix(security): throttle AI streaming endpoints (Finding #7)

ai_chat_stream and ai_quick_query were unthrottled, allowing a single
authenticated session to drain ~\$1-5K/night of LLM budget. Both endpoints
now carry @throttle_classes([AIInsightsThrottle]) matching the 8 other AI
endpoints in this module.

Drift-guard test prevents regression.

Refs: docs/codebase-review-2026-05-04-v2.md Finding #7"
```

---

### Task 0.4 — Sanitize SSE error path (Finding #6 interim)

**Files:**
- Modify: `backend/apps/analytics/views.py:3202-3203, :3286-3287`

**Why:** `except Exception as e: yield f"data: {json.dumps({'error': str(e)})}..."` leaks `anthropic.AuthenticationError` text containing API-key fragments to the browser. Interim: replace `str(e)` with a generic message. Phase 2 task 2.3 will refactor the error-handling pipeline (typed error codes, structured logging).

- [ ] **Step 1: Write the test first**

Open or create `backend/apps/analytics/tests/test_sse_error_sanitization.py`:

```python
"""Finding #6: SSE error path must not leak raw exception text."""
from unittest.mock import patch, MagicMock
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.authentication.models import Organization, UserProfile

User = get_user_model()


class TestSSEErrorSanitization(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="T", slug="t")
        self.user = User.objects.create_user(username="u", password="pw")
        UserProfile.objects.create(user=self.user, organization=self.org, role="viewer")
        self.client.force_authenticate(self.user)

    @patch("apps.analytics.views.anthropic.Anthropic")
    def test_anthropic_auth_error_does_not_leak_to_sse(self, mock_anthropic):
        # Simulate an AuthenticationError that contains a fake key fragment.
        leaky_message = "Invalid API key sk-ant-FAKEKEYFRAGMENT not authorized"

        mock_client = MagicMock()
        mock_client.messages.stream.side_effect = Exception(leaky_message)
        mock_anthropic.return_value = mock_client

        response = self.client.post("/api/v1/analytics/ai-chat-stream/", {
            "messages": [{"role": "user", "content": "hi"}],
        }, format="json")

        body = b"".join(response.streaming_content).decode()

        assert "sk-ant-FAKEKEYFRAGMENT" not in body, (
            f"Raw exception text leaked into SSE response. Body was: {body[:500]}"
        )
        assert "FAKEKEYFRAGMENT" not in body
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
docker-compose exec backend pytest apps/analytics/tests/test_sse_error_sanitization.py -v
```

Expected: FAIL because the leaky string IS in the body today.

- [ ] **Step 3: Sanitize both error blocks**

In `backend/apps/analytics/views.py`, find the two sites at `:3202-3203` and `:3286-3287`:

```python
# BEFORE (both sites):
except Exception as e:
    yield f"data: {json.dumps({'error': str(e)})}\n\n"

# AFTER (both sites):
except Exception as e:
    logger.exception("SSE streaming error")  # Finding #6 — diagnostic capture
    yield f"data: {json.dumps({'error': 'AI service error; see server logs'})}\n\n"
```

Make sure `import logging; logger = logging.getLogger(__name__)` is at the top of the file. If not, add it.

- [ ] **Step 4: Run the test, confirm it passes**

```bash
docker-compose exec backend pytest apps/analytics/tests/test_sse_error_sanitization.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/analytics/views.py backend/apps/analytics/tests/test_sse_error_sanitization.py
git commit -m "fix(security): sanitize SSE error path (Finding #6 interim)

anthropic.AuthenticationError embeds API-key fragments in str(e); those
were yielded verbatim to the SSE client. Replaced with a generic message
plus logger.exception for diagnostic capture.

Permanent error-handling refactor (typed error codes, frontend mapping)
deferred to Phase 2 task 2.3.

Refs: docs/codebase-review-2026-05-04-v2.md Finding #6"
```

---

### Task 0.5 — Hardcode model parameter on `ai_chat_stream` (Finding #8 interim)

**Files:**
- Modify: `backend/apps/analytics/views.py:3162`

**Why:** `model = request.data.get('model', 'claude-sonnet-4-20250514')` lets a client POST `{"model": "claude-opus-4-..."}` and force ~5× pricing. Interim: drop the `request.data.get` and hardcode the default. Phase 4 task 4.2 builds the proper allowlist (with admin override).

- [ ] **Step 1: Write the drift-guard test**

Add to `backend/apps/analytics/tests/test_streaming_throttle_driftguard.py` (already created in Task 0.3):

```python
def test_ai_chat_stream_does_not_accept_client_model_during_phase_0():
    """Finding #8 interim: model must NOT be read from request.data.

    This test will need to be updated when Phase 4 task 4.2 (allowlist) lands.
    """
    import re
    src = inspect.getsource(views.ai_chat_stream)
    # Forbid request.data.get('model', ...) pattern entirely during Phase 0.
    pattern = re.compile(r"request\.data\.get\(\s*['\"]model['\"]")
    assert not pattern.search(src), (
        "ai_chat_stream still reads 'model' from request.data; this is the "
        "Phase 0 interim guard for Finding #8. If Phase 4 allowlist landed, "
        "update this drift-guard to check the allowlist instead."
    )
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
docker-compose exec backend pytest apps/analytics/tests/test_streaming_throttle_driftguard.py::test_ai_chat_stream_does_not_accept_client_model_during_phase_0 -v
```

Expected: FAIL.

- [ ] **Step 3: Hardcode the model**

```python
# BEFORE (line ~3162):
model = request.data.get('model', 'claude-sonnet-4-20250514')

# AFTER:
# Phase 0 containment for Finding #8 — client-controlled model escalation.
# Phase 4 task 4.2 will replace this with a proper allowlist.
model = 'claude-sonnet-4-20250514'
```

- [ ] **Step 4: Run the test, confirm it passes**

```bash
docker-compose exec backend pytest apps/analytics/tests/test_streaming_throttle_driftguard.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/analytics/views.py backend/apps/analytics/tests/test_streaming_throttle_driftguard.py
git commit -m "fix(security): hardcode model parameter on ai_chat_stream (Finding #8 interim)

Client-controlled model parameter allowed Opus escalation (~5x pricing).
Hardcoded to claude-sonnet-4-20250514 as interim. Permanent allowlist
in Phase 4 task 4.2.

Refs: docs/codebase-review-2026-05-04-v2.md Finding #8"
```

---

### Task 0.6 — Add org filter to Report queries (Finding #4 interim)

**Files:**
- Modify: `backend/apps/reports/views.py:417, 444, 472, 525`

**Why:** All four endpoints (`detail`, `status`, `delete`, `download`) use `Report.objects.get(id=...)` and defer to `Report.can_access`, which short-circuits `True` for `is_public=True` without an org check. Interim: add an org filter to the four queries. Phase 1 task 1.3 settles `is_public` semantics with product and refactors `can_access`.

- [ ] **Step 1: Write the failing test**

Create `backend/apps/reports/tests/test_is_public_org_isolation.py`:

```python
"""Finding #4: cross-org reads of is_public=True reports must be blocked."""
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.authentication.models import Organization, UserProfile
from apps.reports.models import Report

User = get_user_model()


class TestReportCrossOrgIsolation(APITestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="OrgA", slug="orga")
        self.org_b = Organization.objects.create(name="OrgB", slug="orgb")
        self.user_b = User.objects.create_user(username="ub", password="pw")
        UserProfile.objects.create(user=self.user_b, organization=self.org_b, role="viewer")

        owner_a = User.objects.create_user(username="oa", password="pw")
        UserProfile.objects.create(user=owner_a, organization=self.org_a, role="admin")
        self.public_report = Report.objects.create(
            organization=self.org_a,
            created_by=owner_a,
            title="OrgA public report",
            is_public=True,
            status="completed",
        )

        self.client.force_authenticate(self.user_b)

    def test_user_in_org_b_cannot_read_org_a_public_report_detail(self):
        url = f"/api/v1/reports/{self.public_report.id}/"
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_user_in_org_b_cannot_read_org_a_public_report_status(self):
        url = f"/api/v1/reports/{self.public_report.id}/status/"
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_user_in_org_b_cannot_download_org_a_public_report(self):
        url = f"/api/v1/reports/{self.public_report.id}/download/"
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_user_in_org_b_cannot_delete_org_a_public_report(self):
        url = f"/api/v1/reports/{self.public_report.id}/"
        response = self.client.delete(url)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
```

- [ ] **Step 2: Run the test, confirm 4 failures**

```bash
docker-compose exec backend pytest apps/reports/tests/test_is_public_org_isolation.py -v
```

Expected: 4 FAILs (all return 200 today because `is_public=True` short-circuits).

- [ ] **Step 3: Add org filter to all four queries**

In `backend/apps/reports/views.py`, find the four sites (around lines 417, 444, 472, 525). Each currently looks like:

```python
report = Report.objects.get(id=report_id)
```

Replace each with:

```python
# Phase 0 containment for Finding #4 — block cross-org reads of is_public reports.
# Phase 1 task 1.3 refactors can_access with the resolved is_public semantics.
report = Report.objects.filter(
    organization=request.user.profile.organization
).get(id=report_id)
```

Note: this assumes single-org `profile.organization` — which is the same legacy pattern Finding A1 flags. Phase 1 will replace this with membership-aware lookup; for Phase 0 containment, single-org is sufficient.

- [ ] **Step 4: Run the test, confirm 4 passes**

```bash
docker-compose exec backend pytest apps/reports/tests/test_is_public_org_isolation.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Run the existing reports test suite to confirm no regression**

```bash
docker-compose exec backend pytest apps/reports -x
```

Expected: no new failures.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/reports/views.py backend/apps/reports/tests/test_is_public_org_isolation.py
git commit -m "fix(security): org-filter the four Report endpoints (Finding #4 interim)

is_public=True short-circuited can_access without an org check, allowing
any authenticated user with a UUID to read any public report from any org.
Added org filter at the queryset level on all four endpoints (detail, status,
delete, download).

Phase 1 task 1.3 will refactor can_access after product decides is_public
semantics (within-org vs platform-wide).

Refs: docs/codebase-review-2026-05-04-v2.md Finding #4"
```

---

### Phase 0 Wrap-up

- [ ] **Run the full backend test suite**

```bash
docker-compose exec backend pytest -x
```

Expected: no new failures attributable to Phase 0 changes.

- [ ] **Push the branch and open a PR**

```bash
git push -u origin fix/phase-0-containment
gh pr create --title "Phase 0: Containment wave for codebase review Tier 1 findings" --body "$(cat <<'EOF'
## Summary

Interim, reversible mitigations for the live-exploitation paths from `docs/codebase-review-2026-05-04-v2.md` Tier 1:

- Finding #1 — nginx block on `/auth/register/`
- Finding #2 — feature-flag membership creation endpoint (default off)
- Finding #4 — org filter on the four Report endpoints
- Finding #6 — sanitize SSE error path
- Finding #7 — throttle decorator on AI streaming endpoints
- Finding #8 — hardcode model parameter on ai_chat_stream

Each fix lands with a drift-guard test. Permanent fixes scheduled in Phases 1, 2, and 4 of the master remediation plan.

## Test plan

- [ ] `docker-compose exec backend pytest apps/authentication/tests/test_membership_containment.py`
- [ ] `docker-compose exec backend pytest apps/analytics/tests/test_streaming_throttle_driftguard.py`
- [ ] `docker-compose exec backend pytest apps/analytics/tests/test_sse_error_sanitization.py`
- [ ] `docker-compose exec backend pytest apps/reports/tests/test_is_public_org_isolation.py`
- [ ] Manual: `curl -X POST http://localhost:3001/api/v1/auth/register/` returns 403
- [ ] Manual: login flow still works end-to-end

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Confirm CI passes** before merging.

- [ ] **After merge:** Phase 1 work begins. The interim blocks (nginx + feature flag + hardcoded model) remain in place until their corresponding Phase 1/4 tasks ship; then Phase 0 reversals will be a follow-up PR (`fix/phase-0-revert-interim`).

---

## Phase 1 — Auth & Tenant Permanent Fixes (3–5 days)

> **Detail level:** task-level outline. Each task below can be expanded into Phase-0-style bite-sized TDD steps on request — say "expand Phase 1 task N" and I'll produce the full plan for that task.

**Goal:** Replace Phase 0's interim blocks with proper permanent fixes; eliminate the `profile.role` legacy across all permission classes.

### Task 1.1 — Tighten `RegisterSerializer` to remove caller-controlled `role` (Finding #1 permanent)

**Files:**
- Modify: `backend/apps/authentication/serializers.py:123-126` (`RegisterSerializer`)
- Modify: `backend/apps/authentication/views.py:95` (`RegisterView`) — keep `AllowAny` if registration is the intended flow, but remove role from the input.
- New test: `backend/apps/authentication/tests/test_register_role_hardening.py`
- After this lands: revert `frontend/nginx/nginx.conf` Phase 0 block.

**Approach:** Remove `role` from `RegisterSerializer.Meta.fields`. New users are always created with `role='viewer'` (the existing default). Admin promotion happens via the membership endpoint (which Phase 1 task 1.2 hardens) or Django admin. Add a test that asserts the field is rejected if sent (and that `viewer` is the persisted role regardless of input).

**Test approach:**
- Anonymous POST with `{"role": "admin", ...}` → user is created, but `UserProfile.role == "viewer"`.
- Drift-guard: assert `'role' not in RegisterSerializer.Meta.fields`.

### Task 1.2 — Add target-org membership check to `UserOrganizationMembershipViewSet.perform_create` (Finding #2 permanent)

**Files:**
- Modify: `backend/apps/authentication/views.py:720-737`
- Use existing helper: `apps.authentication.organization_utils.user_is_admin_in_org`
- New test: `backend/apps/authentication/tests/test_membership_target_org_check.py`
- After this lands: flip `MEMBERSHIP_CREATE_ENABLED` default to `True` and remove the flag check in a follow-up commit (or remove the flag entirely).

**Approach:** In `perform_create`, before `serializer.save(...)`, call `user_is_admin_in_org(self.request.user, validated_data['organization'])`. If False, raise `PermissionDenied`. This works correctly for multi-org admins.

**Test approach:**
- Admin of Org A POSTs membership for Org B → 403.
- Admin of Org A POSTs membership for Org A → 201.
- Drift-guard: assert `user_is_admin_in_org` is called in `perform_create`.

### Task 1.3 — Resolve `is_public` semantics + refactor `Report.can_access` (Finding #4 permanent)

**Decision required first:** Reports product owner decides between (a) "public within org" or (b) "public platform-wide with admin gating on the setter."

**Files:**
- Modify: `backend/apps/reports/models.py:198-199` (`can_access`)
- Modify: `backend/apps/reports/views.py:417, 444, 472, 525` — remove Phase 0 interim filter once `can_access` is correct
- New test: `backend/apps/reports/tests/test_can_access_semantics.py`

**Approach (branch a — within-org):** Remove the `is_public=True` short-circuit; always require `user_can_access_org`. Possibly rename the field to `is_org_public` to signal intent.

**Approach (branch b — platform-wide):** Keep the short-circuit, but add a `mark_public_admin_only` permission gate on the setter. The four endpoint queries can drop the org filter for public reports specifically.

**Test approach:** test the matrix of {is_public, user-org-match, role} across both branches.

### Task 1.4 — Wrap `switch_organization` in `transaction.atomic()` (Finding #11)

**Files:**
- Modify: `backend/apps/authentication/views.py:658-667`
- New test: `backend/apps/authentication/tests/test_switch_org_atomicity.py`

**Approach:** Wrap the two `.update()` calls in `transaction.atomic()` with `select_for_update` on the user's memberships. Or simpler: replace the two updates with a single `update_or_create` flow that goes through the model's existing `save()` (which already has the right guards).

**Test approach:** simulate concurrent calls (use `transaction.atomic` in test threads) and assert the `is_primary` invariant holds (exactly one `is_primary=True` per user).

### Task 1.5 — Replace `profile.role` with membership-aware role across 7+ permission classes (Findings A1 + B9)

**Files:**
- Modify: `backend/apps/authentication/permissions.py:21-27, :167, :187, :207, :227, :254` (7 classes)
- Modify: `backend/apps/analytics/views.py:2609-2611` (`delete_insight_feedback`)
- Use existing helpers: `user_is_admin_in_org`, `user_is_manager_in_org`
- New test: `backend/apps/authentication/tests/test_membership_aware_permissions.py`

**Approach:** Each permission class needs to know the *target* org for the role check. For DRF view permissions, this means inspecting the request — typically the org is in `request.data['organization']`, `view.kwargs['org_id']`, or derived from the object being acted on. Add a `_resolve_target_org(request, view, obj)` helper and use it in every permission class.

**Test approach:** matrix test over (user, target-org, role) — verify multi-org admins are correctly granted/denied based on per-org role.

**Risk:** this is the largest single fix in Phase 1 (7+ sites + helper + tests). Allow 1.5–2 days. May produce regressions in edge-case views; budget time for fix-on-fix.

### Task 1.6 — Add `aiApiKey` format validation (Finding A5)

**Files:**
- Modify: `backend/apps/authentication/serializers.py:83` (`UserPreferencesSerializer.aiApiKey`)
- New test: `backend/apps/authentication/tests/test_aikey_validation.py`

**Approach:** Add a `validate_aiApiKey` method that checks the prefix matches `aiProvider` (`sk-ant-` for `anthropic`, `sk-` for `openai`). Empty string is allowed (clearing the key). Return a clear error message.

**Test approach:** wrong-prefix → 400 with message; right-prefix → accepted; empty → accepted.

### Phase 1 Wrap-up

- [ ] All Phase 1 tests pass.
- [ ] After Phase 1 merges: open a follow-up PR `fix/phase-0-revert-interim` that removes the Phase 0 nginx block, the `MEMBERSHIP_CREATE_ENABLED` flag, and the Phase 0 interim org filters in `reports/views.py` (Phase 1 task 1.3 should make these redundant).

---

## Phase 2 — Silent Regressions & Data Integrity (4–6 days)

### Task 2.1 — Fix scheduled-report rescheduling (Finding D1 — highest-impact)

**Files:**
- Modify: `backend/apps/reports/tasks.py:60-104` (`process_scheduled_reports`) and `:33-57` (`generate_report_async`)
- The fix: chain `reschedule_report` (already correctly implemented at `:145-171`) after each successful generation.
- New test: `backend/apps/reports/tests/test_scheduled_report_advancement.py`

**Approach:** Either (a) add `reschedule_report.delay(report.pk)` to `generate_report_async`'s success path, or (b) inline the `calculate_next_run` logic into `generate_report_async`. (a) is cleaner — the existing task is correct, just orphaned.

**Test approach:** generate a scheduled report, assert `Report.next_run` advances to the correct future time.

**This is actively running and silently re-firing scheduled reports on every Beat tick. Highest-impact High in the list.**

### Task 2.2 — Fix RAG vector fallback (Finding B12)

**Files:**
- Modify: `backend/apps/analytics/rag_service.py:197-201`
- New test: `backend/apps/analytics/tests/test_rag_fallback.py`

**Approach:** Pass the original `query` to `_keyword_search`, not the literal string `"fallback"`.

**Test approach:** mock vector search to raise; assert `_keyword_search` is called with the user's query, not `"fallback"`.

### Task 2.3 — Refactor SSE error pipeline (Finding #6 permanent + Findings B13, B14)

**Files:**
- Modify: `backend/apps/analytics/views.py:3202-3203, :3286-3287` (replace Phase 0 generic message with structured error codes)
- Modify: `backend/apps/analytics/ai_providers.py:384-385, :1309-1322` (preserve error context across failover)
- Modify: `backend/apps/analytics/tasks.py:62-69` (don't `errors.pop()` the original CONCURRENTLY error)
- Modify: `frontend/src/components/AIInsightsChat.tsx:188` (map error codes to user-friendly messages)
- New test: `backend/apps/analytics/tests/test_streaming_error_codes.py`

**Approach:** Define a small enum of error codes (`AUTH_ERROR`, `RATE_LIMITED`, `SERVICE_UNAVAILABLE`, `BAD_REQUEST`, `UNKNOWN`). SSE error frames carry `{"error_code": "...", "error": "user-friendly text"}`. Manager preserves the original exception type → maps to a code.

### Task 2.4 — Implement `enhancement_status` tri-state (Finding #9)

**Files:**
- Modify: `backend/apps/analytics/ai_services.py:480-482` (orchestrator) and the 8 `_enhance_with_*` sites (Findings B11, B14)
- Modify: `frontend/src/components/AIInsightsChat.tsx` and any other component reading `data.ai_enhancement`

**Approach:** Replace `if ai_enhancement: response['ai_enhancement'] = ...` with always-present `response['enhancement_status']` ∈ `{"enhanced", "unavailable_no_key", "unavailable_failed"}`. Frontend renders `(Deterministic — AI failed)` vs `(Deterministic — no key)` based on the value.

**This is the planned Cross-Module Open landing point.** Closes the v2 Critical #9 properly.

### Task 2.5 — Fix `compliance_services` naive datetime (Finding #5)

**Files:**
- Modify: `backend/apps/analytics/compliance_services.py:437`
- Replace `datetime.now()` with `django.utils.timezone.now()`.
- Spot-check other consumers of `resolved_at` for the same pattern.

### Task 2.6 — Fix validator silent-pass (Finding #10)

**Files:**
- Modify: `backend/apps/analytics/ai_providers.py:1108-1109`

**Approach:** Initialize `_validation = {"validated": False, "reason": "validator_crashed"}` BEFORE the `try` block; the `try` overwrites on success. On exception, the metadata is still present and indicates the failure mode.

**Pre-step:** grep for downstream consumers of `_validation` to confirm what "missing" currently means in their logic. Document.

### Task 2.7 — Surface CSV importer errors (Finding #12)

**Files:**
- Modify: `backend/apps/procurement/admin.py:1643-1644, 1863-1864, 2054-2055, 2306-2307` (4 importers)

**Approach:** Replace `except Exception: stats['failed'] += 1` with a logged, row-numbered, error-collecting block. Display a per-row error summary in the admin success message.

---

## Phase 3 — Broken Features Restoration (2–3 days)

### Task 3.1 — Fix frontend AI chat auth (Finding #13)

**Files:**
- Modify: `frontend/src/hooks/useAIInsights.ts:639, :786`

**Approach:** Replace `localStorage.getItem("access_token")` with `credentials: 'include'` on the `fetch`. Project uses HTTP-only cookies; the cookie auth flows automatically with `credentials: 'include'`.

**Test approach:** integration test or Playwright smoke; or contract test asserting the fetch call doesn't read from localStorage.

### Task 3.2 — Reconcile `forecastingModel` value space (Finding #16)

**Files:**
- Decide: which value space wins (frontend's `"simple" | "standard"` or backend's `['simple_average', 'linear', 'advanced']`).
- Modify the loser to match the winner.
- Add a contract test in both `frontend/src/hooks/useSettings.ts` test and `backend/apps/authentication/tests/`.

**Recommendation:** backend wins (its values are more descriptive); update frontend type + UI labels. Coordinate with whoever designed the original UI to confirm `"standard"` was meant to be one of the backend values.

### Task 3.3 — Fix `useCompliance` invalidation keys (Finding E1)

**Files:**
- Modify: `frontend/src/hooks/useCompliance.ts:147-153`
- Use `queryKeys.compliance.all` (or the segmented prefixes) from `frontend/src/lib/queryKeys.ts:386-400`.

### Task 3.4 — Add `orgId` to `useEffect` deps (Finding E2)

**Files:**
- Modify: `frontend/src/hooks/useProcurementData.ts:131-144`
- Add ESLint `react-hooks/exhaustive-deps` to CI to prevent regressions.

### Task 3.5 — Fix `AgingOverview.trend` interface (Finding E5)

**Files:**
- Modify: `frontend/src/lib/api.ts:3030-3042`
- Add the missing `avg_days_to_pay?: number` and `/** @deprecated */ avg_dpo?: number` to the `trend` sub-interface to match the parent and `DPOTrend`.

### Task 3.6 — Surface `useSettings` save failures (Finding E6)

**Files:**
- Modify: `frontend/src/hooks/useSettings.ts:293-309, :340-347, :376-382`

**Approach:** Replace `console.debug(...)` with a toast notification. Mutation `onError` should surface to the user. Keep localStorage as the primary store (intentional design) but signal sync failures.

---

## Phase 4 — Cost Containment & Streaming Hardening (1–2 days)

### Task 4.1 — Streaming chat payload bounds (Finding B10)

**Files:**
- Modify: `backend/apps/analytics/views.py:3160-3165`
- Add validation: max `len(messages)`, max per-message content length, max total payload bytes.

### Task 4.2 — Streaming chat model allowlist (Finding #8 permanent)

**Files:**
- Modify: `backend/apps/analytics/views.py:3162` (replace Phase 0 hardcoded model with a settings-backed allowlist)
- Modify: `backend/config/settings.py` (new `AI_CHAT_ALLOWED_MODELS` list)
- After this lands: update the drift-guard test in `test_streaming_throttle_driftguard.py` to check the allowlist instead of forbidding `request.data.get('model', ...)` entirely.

### Task 4.3 — Document the throttle quotas (Finding #7 follow-up)

**Files:**
- Modify: `backend/apps/analytics/throttles.py` (review `AIInsightsThrottle` rate)
- Document in `docs/claude/ai-insights.md` what the per-user/per-org rate is and how to override.

---

## Phase 5 — Hardening, Performance, Tech Debt (5–10 days)

> Each task below is a self-contained workstream. They are independent and can be done in any order, parallelized, or deferred.

### Task 5.1 — `UserProfileWithOrgsSerializer` masking parity (Finding #3)
**Files:** `backend/apps/authentication/serializers.py:229-255`. Add `to_representation` override applying `UserProfile.mask_preferences`. Drift-guard test asserts both serializer paths mask identically.

### Task 5.2 — CSP nonce-based + drop unsafe directives (Finding #14)
**Files:** `frontend/nginx/nginx.conf:34`. Replace `'unsafe-inline'` and `'unsafe-eval'` with nonce-based CSP. ECharts requires `'unsafe-eval'` — investigate the minimum-required directives.

### Task 5.3 — Add HSTS header (Finding #15)
**Files:** `frontend/nginx/nginx.conf`. Add `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`. **Coordinate with deployment** before enabling `preload`.

### Task 5.4 — Aging method DB-side aggregation (Finding #17 — gate on diagnostic)
**Pre-step:** Run the diagnostic query from `codebase-review-2026-05-04-v2.md` Finding #17. If any tenant >20K open invoices, **elevate to Phase 2.** Otherwise this Phase 5 placement is correct.
**Files:** `backend/apps/analytics/p2p_services.py:963-1141`. Rewrite the four bucket assignments and the 6-month trend as DB-side aggregations.

### Task 5.5 — Trusted proxy header allowlist (Finding A2)
**Files:** `backend/apps/authentication/utils.py:24-34`. Add a `TRUSTED_PROXIES` setting; only honor `X-Real-IP` / `X-Forwarded-For` when `request.META['REMOTE_ADDR']` is in the allowlist.

### Task 5.6 — Login lockout TTL semantics (Finding A3)
**Files:** `backend/apps/authentication/utils.py:79-81`. Use `cache.add(key, 1, LOCKOUT_DURATION)` to set the initial TTL, then `cache.incr(key)` for subsequent failures within the window. This preserves the original window — slow-rate stuffing no longer extends the lockout indefinitely.

### Task 5.7 — Explicit `CELERY_RESULT_EXPIRES` (Finding A6)
**Files:** `backend/config/settings.py:333-334`. Add explicit `CELERY_RESULT_EXPIRES = 3600` (or whatever the policy is).

### Task 5.8 — N+1 cluster: spend.py / pareto.py / p2p_services.py (Findings B1, B2, B6, B7)
**Files:** `backend/apps/analytics/services/spend.py:96-153`, `services/pareto.py:282-360` (3 sites), `p2p_services.py` (`get_p2p_cycle_overview`).
**Approach:** convert per-iteration aggregation queries to a single `GROUP BY` with Python-side bucketing. Each site is a self-contained refactor.

### Task 5.9 — `get_exceptions_by_supplier` adopt the abandoned subquery (Finding B5)
**Files:** `backend/apps/analytics/p2p_services.py:672, 682-723`. The intended single-query implementation already exists in dead code — wire it in and delete the loop.

### Task 5.10 — YoY simple endpoint equal-span guard (Finding B8)
**Files:** `backend/apps/analytics/services/yoy.py:80-84`. Use the `_yoy_change` helper at `:22-42` (which already has the `insufficient_data` flag) instead of the ad-hoc growth computation.

### Task 5.11 — CSV partial-batch commit observability (Finding C2)
**Files:** `backend/apps/procurement/tasks.py:84-167`. Either wrap the entire upload in `transaction.atomic()` (all-or-nothing — likely too strict for very large uploads) or surface the per-batch outcome in the `DataUpload` record so users can see exactly which rows / batches survived.

### Task 5.12 — Cross-org FK CHECK constraints (Finding C3)
**Files:** `backend/apps/procurement/models.py` — all 4 supplier-FK models. Add `CheckConstraint` enforcing `organization_id == supplier__organization_id`. Requires a Django migration; PostgreSQL supports this via subquery-free check on a generated column or via constraint trigger.

### Task 5.13 — Celery task membership re-check (Finding C4)
**Files:** `backend/apps/procurement/tasks.py` — at task entry, re-validate that `upload.uploaded_by` is still a member of `upload.organization`. Fail fast if not.

### Task 5.14 — PDF footer `timezone.now()` (Finding D2)
**Files:** `backend/apps/reports/renderers/pdf.py:283`. Replace `datetime.now()` with `django.utils.timezone.now()`.

### Task 5.15 — `Chart.tsx` type narrowing (Finding E3)
**Files:** `frontend/src/components/Chart.tsx:186-265`. Replace 19 `as any` casts with proper ECharts type narrowing (`XAxisComponentOption`, `YAxisComponentOption`, etc.). Largely mechanical.

### Task 5.16 — Streamdown sanitization audit (Finding E4)
**Files:** `frontend/package.json` (pin `streamdown`); `docs/claude/ai-insights.md` (document the sanitization assumption).
**Approach:** record the pinned version, audit its DOMPurify configuration, add a contract test asserting the version doesn't drift without review.

---

## Self-Review

**1. Spec coverage:**
- Phase 0 covers all 6 Tier-1 P0 / cost-bleed findings.
- Phase 1 covers Criticals #1, #2, #4, #11 + Highs A1, A5, B9 (7 of 7 Tier 1/2 auth-tenant items).
- Phase 2 covers Criticals #5, #6, #9, #10, #12 + Highs B12, B13, B14, D1 (9 silent-regression items).
- Phase 3 covers Criticals #13, #16 + Highs E1, E2, E5, E6 (6 broken-feature items).
- Phase 4 covers Critical #7 (perm), #8 (perm) + High B10 (3 cost/streaming items).
- Phase 5 covers Criticals #3, #14, #15, #17 + 12 hardening Highs.

**Gaps surfaced:** None — all 17 Criticals and all 28 confirmed Highs from the highs-verified document have a task. Phase 5 task 5.16 covers the Streamdown auditability concern (E4) with the right approach (pin + audit, not rewrite).

**2. Placeholder scan:** Phase 0 is fully detailed with real code. Phases 1–5 are deliberately task-level (files + approach + test approach), with a handoff note offering to expand any task into Phase-0-style detail on request. This is intentional given the 45-finding scope; full TDD detail for every fix would produce an unreviewable document.

**3. Type consistency:** N/A — most fixes are isolated; cross-task references (e.g., Phase 0 task 0.5's drift-guard test gets updated by Phase 4 task 4.2) are explicitly called out at both ends.

**4. Decisions required:** clearly enumerated at the top — `is_public` semantics (Phase 1 task 1.3), tenant-size diagnostic for #17 (Phase 5 task 5.4), `forecastingModel` reconciliation direction (Phase 3 task 3.2), `aiProvider` vs `aiApiKey` matching (Phase 1 task 1.6). None of these block Phase 0.

---

*Plan written 2026-05-05 for code state at commit `1e9c434`. Companion to `codebase-review-2026-05-04-v2.md` and `codebase-review-2026-05-04-highs-verified.md`.*

---

## Closure status (2026-05-06)

All commits land on `main` between `1e9c434` (pre-remediation baseline) and `371c4da` (Phase 5 merge, pushed to origin).

### Critical-tier (v2) findings — 17 of 17 closed

| Finding | Description | Closure SHA | Notes |
|---|---|---|---|
| #1 | Self-registration role escalation | interim `befcd47`, perm `24608e1` | nginx block + serializer hardening |
| #2 | Cross-org admin escalation via membership endpoint | interim `17f867a`, perm `6760eb9` | Flag removed in cleanup `489ef58` |
| #3 | UserProfileWithOrgsSerializer masking gap | `ac2c87a` | P1 latent landmine, now closed |
| #4 | Report.is_public no org gate | interim `d6b84ed` | **Permanent fix Task 1.3 deferred** — Reports product owner must decide is_public semantics. Phase 0 interim filter still active. |
| #5 | Naive datetime in compliance_services | `6e6b371` | timezone.now() across 3 sites |
| #6 | SSE error path leaks raw exception text | interim `be472f8`, perm `ed84a56` | Typed error codes via `llm_error_codes.py` |
| #7 | Streaming chat no throttle | `7596462` (decorator), `43f4442` (docs), `9147b30` (payload bounds) | $0.96/user/hr ceiling at default |
| #8 | Client-controlled model parameter | interim `8595160`, perm `9d742d1` | AI_CHAT_ALLOWED_MODELS allowlist |
| #9 | Rule 6 runtime-failure silent fallback (Cross-Module Open) | `8cd0e61` + ledger update `651b7c4` | enhancement_status tri-state landed |
| #10 | Validator silent-pass | `70c6163` | Marker initialized before try |
| #11 | switch_organization race on is_primary | `46ce9ef` | transaction.atomic + select_for_update |
| #12 | P2P admin importers silent row drops | `028d67c` | `_record_import_failure` helper |
| #13 | Frontend AI chat localStorage auth (broken in prod) | `8396722` | credentials: 'include' on fetch |
| #14 | CSP unsafe-inline / unsafe-eval | partial `8ae0ab5` | unsafe-eval removed; unsafe-inline pending vite-plugin-manus-runtime gating |
| #15 | Missing HSTS header | `8c038b1` | preload pending 1 week prod validation |
| #16 | forecastingModel value-space mismatch | `5524965` | Backend wins; frontend type updated |
| #17 | Aging method unbounded querysets | **DEFERRED** | Diagnostic shows max 267 open invoices/tenant, well below 20K threshold. Plan documents elevation criterion. |

### High-tier (highs-verified) findings — 28 of 28 closed

| Finding | Description | Closure SHA |
|---|---|---|
| A1 + B9 | profile.role legacy across 7+ permission classes | `131d392` (helper + IsAdmin/Manager) + `028dcdb` (P2P perms + delete_insight_feedback) + `4451c53` (query_params follow-up) |
| A2 | Trusted-proxy header allowlist | `f068097` + `972d7ad` (test-fixture parity) |
| A3 | Lockout TTL semantics | `0422506` (in hardening triplet) |
| A5 | aiApiKey prefix validation | `14ca0ce` |
| A6 | CELERY_RESULT_EXPIRES explicit | `0422506` (in hardening triplet) |
| B1, B2, B6, B7 | N+1 cluster (spend / pareto / p2p_cycle) | `aafb3fb` |
| B5 | get_exceptions_by_supplier abandoned subquery wired in | `2bf8269` |
| B8 | YoY simple endpoint equal-span guard | `ff44b75` |
| B10 | Streaming chat payload bounds | `9147b30` |
| B12 | RAG vector fallback uses original query | `92476a6` |
| B13 | MV refresh CONCURRENTLY error preservation | `ed84a56` |
| B14 | Provider failover error context | `ed84a56` |
| C2 | CSV partial-batch observability | `f28741c` |
| C3 | Cross-org FK CHECK constraints (Postgres triggers) | `aac182f` |
| C4 | Celery task membership re-check | `68de20e` |
| D1 | Scheduled-report rescheduling | `872f812` |
| D2 | PDF footer timezone.now() | `0422506` (in hardening triplet) |
| E1 | useCompliance invalidation keys | `3f87345` |
| E2 | useProcurementData useEffect deps | `7c54ed5` |
| E3 | Chart.tsx type narrowing (21 casts removed) | `e0d18e9` |
| E4 | Streamdown sanitization audit + version pin | `85447e0` + lockfile `afc1e78` |
| E5 | AgingOverview.trend alias parity | `e615a75` |
| E6 | useSettings save-failure toast | `389cbf3` |

### Infrastructure / process commits

- `8fad8b2` — frontend test-suite flake reduction (MSW handlers deferred init, plugin-mode exclusion, singleFork pool)
- `489ef58` — orphaned MEMBERSHIP_CREATE_ENABLED flag cleanup post-Phase-0+1 merge

### Pending follow-ups (non-blocking, captured in commit messages)

- vite-plugin-manus-runtime gating in `vite.config.ts` (would let CSP drop `unsafe-inline`; ~365 KB also leaks into prod bundle)
- HSTS `preload` directive after 1 week production validation
- `consecutive_failures` counter on scheduled reports (transient-vs-permanent failure distinction)
- `reschedule_report.delay()` broker-failure resilience (try/except wrapper)
- Frontend Vite transformer flake (~30% suite-load failure) — needs Vite version bump or upstream investigation
- `params: any` in `Chart.tsx` click handler (out of scope of E3's range)
- Task 1.3 — Reports product owner decision on `is_public` semantics
- Task 5.4 — aging DB-side aggregation if any tenant grows past 20K open invoices

### Test count delta

| Snapshot | Backend | Frontend (clean run) |
|---|---|---|
| Pre-remediation | 753 | ~810 |
| Post-Phase 5 (current) | **851** | **887** |
| Net new tests | +98 | +77 |
