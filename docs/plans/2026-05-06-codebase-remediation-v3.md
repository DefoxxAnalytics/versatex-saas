# Codebase Remediation v3.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the ~72 net-new findings from the second-pass codebase review (`docs/codebase-review-2026-05-06-second-pass.md`) — including 5 Critical items the v2.12 cycle missed because the first review excluded their angles (deps, prod posture, concurrency, Mediums tier).

**Architecture:** Four phases ordered by risk. Phase 0 ships dependency upgrades + auth fallback fix + lockfile cleanup within hours (security exposure today). Phase 1 lands concurrency / data-integrity permanent fixes within ~1 week. Phase 2 hardens production posture (Docker, CI gating, prod settings). Phase 3 cleans up Mediums + observability gaps. Each fix lands with a drift-guard test where applicable.

**Tech Stack:** Same as v2.12 — Django 5.0 + DRF + Celery/Redis + PostgreSQL + React 18 + TypeScript + Tailwind 4 + Vite + nginx + Docker Compose + Railway.

**Companion documents:**
- `docs/codebase-review-2026-05-06-second-pass.md` — second-pass findings (the source of all tasks in this plan)
- `docs/codebase-review-2026-05-04-v2.md` — first review (Criticals)
- `docs/codebase-review-2026-05-04-highs-verified.md` — first review (Highs)
- `docs/plans/2026-05-05-codebase-remediation.md` — v2.12 remediation (Phases 0-5 closure SHAs)
- `docs/REMEDIATION-OPEN-ITEMS.md` — v2.12 deferred items (still open after v3.0)

**Conventions:**
- Findings prefixed `S-#N` are Critical from the second-pass review
- Findings prefixed `S-HX` are High from the second-pass review
- Findings prefixed `M-XX` are Mediums from the second-pass Agent 2 verification
- All test commands assume `docker-compose up -d` is running; prefix with `docker-compose exec backend ` for backend tests

---

## Phase Index & Sequencing

| Phase | Bundle | Findings | Effort | Ship gate |
|---|---|---|---|---|
| **Phase 0** | Security exposure (deps + auth + lockfile) | S-#1, S-#2, S-#3, deps cluster | 4–8 hours | All Tier 1 items live |
| **Phase 1** | Concurrency & data integrity (permanent) | S-#4, S-#5, S-HA, S-HC, signal-handler I/O, JSON race | 4–6 days | No silent data loss vectors |
| **Phase 2** | Production hardening | Dockerfile multi-stage, CI gating, base-image pins, settings hardening | 2–3 days | Production-readiness gates pass |
| **Phase 3** | Mediums + observability | AI deep-analysis hardening, cache patterns, index cleanup, Postgres-CI matrix, drift-guards | 5–7 days | Mediums backlog cleared |

**Phase dependencies:**
- Phase 0 must ship first (security exposure is real today).
- Phase 1, 2, 3 are mutually independent and can be parallelized.
- The two existing v2.12 deferrals (Task 1.3 `is_public` semantics, Task 5.4 aging aggregation) remain in `docs/REMEDIATION-OPEN-ITEMS.md` and are NOT scheduled in v3.0.

**Out of scope of this plan:**
- The 11 unenumerated Backend(6) + Silent Failures(5) Mediums from the first review (cannot verify without re-running the original domain agents).
- Pending follow-ups already captured in v2.12 commit messages: vite-plugin-manus-runtime gating, HSTS preload, `consecutive_failures` counter, `reschedule_report.delay()` broker resilience, Vite transformer flake.
- The deferred v2.12 items (Task 1.3, Task 5.4).

---

## Phase 0 — Security Exposure (4–8 hours)

**Goal:** Close the security exposure that's live in production today: known CVEs in pinned dependencies + auth design bypass + lockfile drift undermining a Phase 5 pin.

**Branch strategy:** Single branch `fix/v3-phase-0-security-exposure`. One PR with all 5 tasks. Reviewers focus on: do the upgrades break tests? does the auth fix preserve programmatic-API access?

**Pre-flight:**
- [ ] Confirm `docker-compose up -d` runs cleanly
- [ ] Run baseline tests: `docker-compose exec backend pytest -x` and `cd frontend && pnpm test:run`
- [ ] Note the baseline pass counts: backend 851, frontend 887 (clean run)
- [ ] Create branch: `git checkout -b fix/v3-phase-0-security-exposure`

---

### Task 0.1 — Upgrade Django to 5.0.14+ (S-#1, ~23 advisories)

**Files:**
- Modify: `backend/requirements.txt` — bump `Django` pin

- [ ] **Step 1: Locate the current pin**

```bash
grep -n "^Django" backend/requirements.txt
```

Confirm current is `Django==5.0.1`.

- [ ] **Step 2: Read Django 5.0 release notes for breaking changes**

Quickly check `https://docs.djangoproject.com/en/5.0/releases/` for any breaking changes between 5.0.1 and 5.0.14. Most patch-version changes are bug fixes only; this should be safe.

- [ ] **Step 3: Bump the pin**

In `backend/requirements.txt`, change:

```
Django==5.0.1
```

to:

```
Django==5.0.14
```

- [ ] **Step 4: Rebuild the backend container**

```bash
docker-compose build backend
```

- [ ] **Step 5: Run the full backend suite**

```bash
docker-compose up -d --force-recreate backend
docker-compose exec backend pytest -x
```

Expected: 851 pass (or whatever baseline you noted), no new failures. If any test breaks due to a Django patch-version behavior change, investigate before proceeding — most likely it's a deprecation that was previously a warning becoming an error.

- [ ] **Step 6: Verify pip-audit no longer flags Django**

```bash
docker-compose exec backend pip-audit --skip-editable 2>&1 | grep -i "django " | head
```

Expected: no Django-related advisories (or significantly fewer).

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore(deps): upgrade Django 5.0.1 → 5.0.14 (S-#1, ~23 CVEs)

Multiple SQL injection (PYSEC-2024-156, PYSEC-2024-157, CVE-2025-57833),
DoS (PYSEC-2024-47, PYSEC-2025-1), and PII oracle (PYSEC-2024-58)
advisories against the previously-pinned 5.0.1.

Refs: docs/codebase-review-2026-05-06-second-pass.md Critical #1"
```

---

### Task 0.2 — Upgrade DRF + simplejwt + gunicorn (S-#1 cluster)

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Update three pins**

In `backend/requirements.txt`, change:

```
djangorestframework==3.14.0
djangorestframework-simplejwt==5.3.1
gunicorn==21.2.0
```

to:

```
djangorestframework==3.15.2
djangorestframework-simplejwt==5.5.1
gunicorn==22.0.0
```

- [ ] **Step 2: Rebuild and run tests**

```bash
docker-compose build backend
docker-compose up -d --force-recreate backend celery
docker-compose exec backend pytest -x
```

Expected: 851 pass. simplejwt 5.5.x changed some default settings; if tests break check `SIMPLE_JWT` config in settings.py.

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore(deps): DRF 3.15.2 + simplejwt 5.5.1 + gunicorn 22.0.0 (S-#1)

- DRF: CVE-2024-21520 (XSS in browsable API)
- simplejwt: CVE-2024-22513 (deactivated users can still authenticate)
- gunicorn: CVE-2024-1135, CVE-2024-6827 (HTTP request smuggling — production WSGI)

Refs: docs/codebase-review-2026-05-06-second-pass.md Critical #1"
```

---

### Task 0.3 — Upgrade frontend deps (axios, vite, pnpm)

**Files:**
- Modify: `frontend/package.json`
- Regenerate: `frontend/pnpm-lock.yaml`

- [ ] **Step 1: Bump direct deps**

In `frontend/package.json`:

```json
"axios": "^1.15.2",
```

(was `^1.12.0`). For dev deps:

```json
"vite": "^7.3.2",
```

(was `^7.1.7`). pnpm itself is set via the engines field or CI; bump the engines field if present.

- [ ] **Step 2: Regenerate lockfile**

```bash
cd frontend && pnpm install --no-frozen-lockfile
```

- [ ] **Step 3: Run frontend test suite**

```bash
cd frontend && pnpm test:run
```

Expected: 887 pass (or whatever the baseline was). Note: there's a known ~30% Vite-transformer flake. Re-run if a non-deterministic suite fails.

- [ ] **Step 4: Run TS check**

```bash
cd frontend && pnpm check
```

- [ ] **Step 5: Verify pnpm audit no longer flags these as High**

```bash
cd frontend && pnpm audit | grep -i high | head
```

Expected: significantly fewer High advisories.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml
git commit -m "chore(deps): axios 1.15.2 + vite 7.3.2 (S-#1 cluster)

- axios: 5 advisories (proto-pollution gadgets, DoS, header injection)
- vite: 2 advisories (server.fs.deny bypass, arbitrary file read in dev)

Refs: docs/codebase-review-2026-05-06-second-pass.md Critical #1"
```

---

### Task 0.4 — Delete `package-lock.json`, add CI lockfile-drift guard (S-#3)

**Files:**
- Delete: `frontend/package-lock.json`
- Modify: `.github/workflows/ci.yml` — add lockfile-existence check
- Optionally modify: `frontend/package.json` to add `packageManager` field (silences npm if used)

- [ ] **Step 1: Confirm pnpm is the source of truth**

```bash
cat .github/workflows/ci.yml | grep -E "pnpm|npm install" | head
```

CI uses pnpm (`pnpm install --frozen-lockfile`). The npm-style `package-lock.json` is stale and shows `streamdown@1.6.10` while `pnpm-lock.yaml` shows `1.4.0` — exact thing the Phase 5 task 5.16 pin was meant to prevent.

- [ ] **Step 2: Delete the stale lockfile**

```bash
git rm frontend/package-lock.json
```

- [ ] **Step 3: Add `packageManager` to package.json**

In `frontend/package.json`, after the `"version"` field, add:

```json
"packageManager": "pnpm@10.18.1",
```

This signals that npm/yarn aren't supported and prevents accidental npm regeneration.

- [ ] **Step 4: Add CI guard**

In `.github/workflows/ci.yml`, in the `frontend-test` job (or any frontend job), add a step before the `pnpm install` step:

```yaml
      - name: Lockfile drift guard
        run: |
          if [ -f frontend/package-lock.json ]; then
            echo "::error::frontend/package-lock.json should not exist; project uses pnpm. Delete it."
            exit 1
          fi
          if [ -f frontend/yarn.lock ]; then
            echo "::error::frontend/yarn.lock should not exist; project uses pnpm. Delete it."
            exit 1
          fi
        shell: bash
```

- [ ] **Step 5: Verify locally**

```bash
ls frontend/package-lock.json 2>&1
```

Expected: `No such file or directory`.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json .github/workflows/ci.yml
git commit -m "chore(deps): delete stale package-lock.json, add CI drift guard (S-#3)

The Phase 5 task 5.16 pinned streamdown to exact 1.4.0 in package.json
(no caret). pnpm-lock.yaml respected the pin; package-lock.json was
never regenerated and resolved streamdown@1.6.10 — an entirely different
sanitization profile, silently undermining the Phase 5 audit posture.

Project uses pnpm. Removed package-lock.json. Added packageManager field
to make pnpm explicit. CI guard fails the build if package-lock.json or
yarn.lock reappear.

Refs: docs/codebase-review-2026-05-06-second-pass.md Critical #3"
```

---

### Task 0.5 — Gate `CookieJWTAuthentication` header fallback (S-#2)

**Files:**
- Modify: `backend/apps/authentication/backends.py:22-32`
- New test: `backend/apps/authentication/tests/test_cookie_auth_no_header_fallback.py`

- [ ] **Step 1: Read the current implementation**

```bash
sed -n '1,60p' backend/apps/authentication/backends.py
```

Note the exact class structure and where the parent class is called.

- [ ] **Step 2: Write the failing test**

Create `backend/apps/authentication/tests/test_cookie_auth_no_header_fallback.py`:

```python
"""Critical S-#2: CookieJWTAuthentication must NOT fall through to the
Authorization: Bearer header for browser clients. The cookie-XSS protection
design requires that XSS-stolen tokens cannot be replayed via the header.
"""
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from apps.authentication.backends import CookieJWTAuthentication

User = get_user_model()


class TestCookieAuthNoHeaderFallback(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username="ch_u", password="pw")
        self.token = str(AccessToken.for_user(self.user))

    @override_settings(DEBUG=False)
    def test_header_only_request_rejected_in_production(self):
        """In prod (DEBUG=False), bearer-header-only requests must NOT
        authenticate via CookieJWTAuthentication."""
        request = self.factory.get("/api/v1/whatever/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token}"
        # No cookie set.
        result = CookieJWTAuthentication().authenticate(request)
        self.assertIsNone(result,
            "Bearer-header-only request authenticated despite no cookie. "
            "S-#2: this nullifies the HTTP-only cookie XSS protection.")

    @override_settings(DEBUG=False)
    def test_cookie_only_request_authenticates(self):
        """Cookie alone must still authenticate."""
        request = self.factory.get("/api/v1/whatever/")
        request.COOKIES["access_token"] = self.token
        result = CookieJWTAuthentication().authenticate(request)
        self.assertIsNotNone(result)

    @override_settings(DEBUG=True)
    def test_header_fallback_allowed_in_debug(self):
        """DEBUG mode keeps the header fallback for local dev tooling
        (curl, postman) — this is the only intended use."""
        request = self.factory.get("/api/v1/whatever/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token}"
        result = CookieJWTAuthentication().authenticate(request)
        self.assertIsNotNone(result,
            "DEBUG mode should keep the header fallback for dev tooling.")
```

- [ ] **Step 3: Run, expect FAIL**

```bash
docker-compose exec backend pytest apps/authentication/tests/test_cookie_auth_no_header_fallback.py -v
```

Expected: `test_header_only_request_rejected_in_production` FAILS — current code falls through to header.

- [ ] **Step 4: Modify backends.py to gate the fallback on DEBUG**

In `backend/apps/authentication/backends.py`, find the `authenticate` method. The current pattern likely calls `super().authenticate(request)` after the cookie lookup fails. Change to:

```python
from django.conf import settings
# (verify the import is already present at the top of the file)

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Try cookie first.
        raw_token = request.COOKIES.get('access_token')
        if raw_token:
            try:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token
            except (InvalidToken, AuthenticationFailed):
                pass  # fall through

        # S-#2: only honor the Authorization header in DEBUG (local dev tooling).
        # In production, browser clients MUST use the cookie path. Programmatic
        # clients should use a separate auth path with explicit opt-in.
        if not getattr(settings, 'DEBUG', False):
            return None

        return super().authenticate(request)
```

(Adapt to the actual existing implementation — read the file first to match the existing imports and exception handling.)

- [ ] **Step 5: Verify pass**

```bash
docker-compose exec backend pytest apps/authentication/tests/test_cookie_auth_no_header_fallback.py -v
```

Expected: 3 PASS.

- [ ] **Step 6: Run full auth suite**

```bash
docker-compose exec backend pytest apps/authentication -x
```

Expected: 175+ pass (was 175 in v2.12 + 3 new tests). If any existing test that was using header-based auth in production-DEBUG-False mode breaks, investigate — that test was relying on the bug.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/authentication/backends.py backend/apps/authentication/tests/test_cookie_auth_no_header_fallback.py
git commit -m "fix(security): gate Authorization-header fallback on DEBUG (S-#2)

CookieJWTAuthentication fell through to the Authorization: Bearer header
on cookie-miss for browser clients. Combined with the residual unsafe-inline
CSP (Phase 5 task 5.2 retains it for vite-plugin-manus-runtime), an XSS
becomes token exfiltration — defeating the entire HTTP-only cookie design
from Phase 1.

Header fallback now only fires when DEBUG=True (local dev with curl/postman).
Production browser clients use the cookie path exclusively. Programmatic API
clients needing header auth should use a separate authentication class.

Refs: docs/codebase-review-2026-05-06-second-pass.md Critical #2"
```

---

### Phase 0 Wrap-up

- [ ] **Run the full suites**

```bash
docker-compose exec backend pytest -x
cd frontend && pnpm test:run
cd frontend && pnpm check
```

Expected: backend ≥854 pass, frontend ≥887 pass (or higher with new tests), TS clean.

- [ ] **Push the branch and open a PR**

```bash
git push -u origin fix/v3-phase-0-security-exposure
gh pr create --title "v3.0 Phase 0: security exposure (Django + DRF + axios + auth + lockfile)" --body "$(cat <<'EOF'
## Summary

Resolves the 5 Critical findings from docs/codebase-review-2026-05-06-second-pass.md:
- S-#1 dependency CVE cluster: Django 5.0.1→5.0.14, DRF 3.14→3.15.2, simplejwt 5.3.1→5.5.1, gunicorn 21.2→22.0, axios 1.12→1.15.2, vite 7.1→7.3.2
- S-#2 CookieJWTAuthentication header fallback gated on DEBUG=True
- S-#3 Stale package-lock.json deleted; CI guard added

## Test plan

- [ ] `docker-compose exec backend pytest -x` — full backend suite
- [ ] `cd frontend && pnpm test:run` — full frontend suite
- [ ] `cd frontend && pnpm check` — TypeScript clean
- [ ] Manual: cookie-based login still works end-to-end at http://localhost:3001
- [ ] Manual: `curl -H "Authorization: Bearer <token>" http://localhost:8002/api/v1/auth/user/` returns 401 (was 200) when DEBUG=False

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Confirm CI passes** before merging.

---

## Phase 1 — Concurrency & Data Integrity (4–6 days)

> **Detail level:** task-level outline. Each task can be expanded into Phase-0-style bite-sized TDD steps on request.

**Goal:** Eliminate the silent-data-loss vectors and missed Phase-1-task-1.5 site uncovered in the second-pass review.

### Task 1.1 — Fix JSONField lost-update on UserPreferences + SavingsConfig (S-#4)

**Files:**
- Modify: `backend/apps/authentication/views.py:545-553` (`UserPreferencesView.patch`)
- Modify: `backend/apps/authentication/views.py:856-859` (`OrganizationSavingsConfigView.put`)
- New test: `backend/apps/authentication/tests/test_concurrent_preferences_update.py`

**Approach:** Wrap the read-merge-write in `transaction.atomic()` + `select_for_update()` on the row. Pattern matches Phase 1 task 1.4 (`switch_organization` atomicity). Test simulates concurrent writes via patched `.update()` raising mid-flight, asserts the second writer's blob doesn't overwrite the first.

### Task 1.2 — Fix CSV `get_or_create __iexact` race (S-#5)

**Files:**
- Modify: `backend/apps/procurement/tasks.py:178-190` (and 5 other sites — see second-pass review)
- New test: `backend/apps/procurement/tests/test_csv_supplier_case_collision.py`

**Approach:** Normalize supplier name to canonical case (`supplier_name = supplier_name.strip()`) BEFORE `get_or_create(organization=..., name=supplier_name)` — drop the `__iexact` lookup. This makes the unique constraint align with the lookup key. Test forces a case-collision via parallel-style fixture (two batches with `"ACME"` and `"acme"`) and asserts the first one's case wins, the second is matched not re-created, and the surrounding batch's `transaction.atomic()` is NOT poisoned.

### Task 1.3 — Apply payload bounds to `ai_quick_query` (S-HC, B10 half-fix)

**Files:**
- Modify: `backend/apps/analytics/views.py:3273` (`ai_quick_query` signature + bounds insertion)
- Extend: `backend/apps/analytics/tests/test_streaming_payload_bounds.py` to cover `ai_quick_query`

**Approach:** Apply `AI_CHAT_MAX_MESSAGE_CONTENT_CHARS` to the `query` string (single-message equivalent) and `AI_CHAT_MAX_PAYLOAD_BYTES` to total `request.data` size. Mirror the `ai_chat_stream` pattern from Phase 4 task 4.1.

### Task 1.4 — Apply membership-aware role check to `report_delete` (S-HA)

**Files:**
- Modify: `backend/apps/reports/views.py:500` (replace `profile.role == 'admin'`)
- Extend: `backend/apps/reports/tests/test_views.py` with multi-org admin delete-report case

**Approach:** Replace with `user_is_admin_in_org(request.user, report.organization)`. Follow the Phase 1 task 1.5b pattern from `delete_insight_feedback`. Drift-guard test: multi-org user who is admin of report's org can delete; user who is admin of a different org cannot.

### Task 1.5 — Move `post_save` signal handlers to `transaction.on_commit` (concurrency High)

**Files:**
- Modify: `backend/apps/procurement/signals.py:36-71`
- New test: `backend/apps/procurement/tests/test_signal_no_redis_in_transaction.py`

**Approach:** Wrap the `AIInsightsCache.invalidate_org_cache()` call in `transaction.on_commit(lambda: ...)`. This ensures the Redis I/O happens AFTER the DB transaction commits, releasing row locks before the network call. Also gate the per-`Transaction` post_save handler on bulk path detection (`kwargs.get('raw') or upload_batch`) so 100K signals don't fire 100K Redis calls.

Test: bulk-create 100 transactions inside a `transaction.atomic()` block; assert `cache.invalidate_org_cache` is called once at most (or N times outside the transaction context, but never inside).

### Task 1.6 — Apply `cache.add` + `cache.incr` to AI cache stats (concurrency High)

**Files:**
- Modify: `backend/apps/analytics/ai_cache.py:173-174` and `:131-135`
- New test: `backend/apps/analytics/tests/test_ai_cache_atomic_stats.py`

**Approach:** Pattern from Phase 5 task 5.6. Replace `current = cache.get(key) or 0; cache.set(key, current + 1, TTL)` with `cache.add(key, 0, TTL); cache.incr(key)`. For org-key tracking (`_track_org_key`), switch to a Redis SET via the underlying client.

### Task 1.7 — Make `process_csv_upload` idempotent on Celery retry (concurrency High)

**Files:**
- Modify: `backend/apps/procurement/tasks.py:329-340` (catch-all retry block)
- Modify: `backend/apps/procurement/models.py` — add `last_processed_batch_index` field
- New migration

**Approach:** Track `last_processed_batch_index` on `DataUpload`. On task retry, resume from `last_processed_batch_index + 1` instead of restarting at row 0. Combined with Task 1.2's normalized supplier names, this makes the task safely retriable.

### Task 1.8 — Add `lock_timeout` and `atomic=False` to migration 0009 (concurrency Medium escalated)

**Files:**
- Modify: `backend/apps/procurement/migrations/0009_cross_org_fk_check_constraints.py`

**Approach:** At the start of `install_triggers`, run `SET LOCAL lock_timeout='5s'`. On `LockNotAvailable`, retry up to 3 times then abort cleanly. Add `atomic = False` on the Migration class so each table's trigger creation is its own transaction. Document the prerequisite: deploy during low-traffic window or with manual coordination.

---

## Phase 2 — Production Hardening (2–3 days)

### Task 2.1 — Multi-stage backend Dockerfile

**Files:** `backend/Dockerfile`. Compile Python wheels in a builder stage (with gcc/python3-dev/musl-dev/libpq-dev), copy into a slim runtime stage. Drops ~200 MB and removes compilers from runtime image.

### Task 2.2 — Frontend nginx as non-root

**Files:** `frontend/Dockerfile`. Add `USER nginx` after the static-files copy. May need `chown` of `/var/cache/nginx`, `/var/run`, `/usr/share/nginx/html`.

### Task 2.3 — Pin Docker base images to digests

**Files:** `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`. Replace floating tags (`:alpine`, `python:3.11-slim`, `:latest` defaults) with `image@sha256:...` digest pins. Also change `${APP_VERSION:-latest}` to `${APP_VERSION:?APP_VERSION required}` so undefined env fails loudly.

### Task 2.4 — Trivy gating in CI

**Files:** `.github/workflows/ci.yml`. Remove `continue-on-error: true` from the Trivy step and the SARIF upload. Add `severity: 'CRITICAL,HIGH'` filter so Medium/Low don't break the build. Pin `aquasecurity/trivy-action@<commit-sha>` instead of `@master`.

### Task 2.5 — Coverage threshold enforcement

**Files:** `.github/workflows/ci.yml`, `backend/.coveragerc`. Add `--cov-fail-under=55` to the backend pytest invocation. For frontend, add a `vitest.config.ts` `test.coverage.thresholds` block.

### Task 2.6 — Remove `continue-on-error` from lint jobs

**Files:** `.github/workflows/ci.yml:40, 44, 176`. Either commit to enforced linting or remove the lint jobs. Half-enforced is worst.

### Task 2.7 — Production deploy step (or remove `deploy.yml`)

**Files:** `.github/workflows/deploy.yml`. Either implement the actual Railway deploy commands (`railway up`, etc.) or convert to a manual-deploy doc reference. Currently echo placeholders create false confidence.

### Task 2.8 — DB SSL option

**Files:** `backend/config/settings.py:113-127`. Add `'sslmode': config('DB_SSLMODE', default='prefer')` to `DATABASES['default']['OPTIONS']`. Document `DB_SSLMODE=require` in `.env.example`.

### Task 2.9 — Production-validator CI test

**Files:** `.github/workflows/ci.yml`. Add a separate job that runs `python manage.py check --deploy` against `DEBUG=False` with a real test secret. Ensures the production-validation paths in `settings.py:562-585` don't regress silently.

### Task 2.10 — Strip Flower public port in prod

**Files:** `docker-compose.prod.yml:138-140`. Either remove the `5555` port mapping or bind to `127.0.0.1:5555` and put behind an nginx auth proxy.

### Task 2.11 — Production startup warning when `TRUSTED_PROXIES` empty

**Files:** `backend/config/settings.py` (near line 52). Add a `logging.warning` when `not DEBUG and not TRUSTED_PROXIES` — first-deploy footgun.

### Task 2.12 — Fix `DEFAULT_FROM_EMAIL` domain

**Files:** `backend/config/settings.py:338`. Change `noreply@analytics.com` to `noreply@versatexanalytics.com` (or whatever the project's actual domain is). DMARC/SPF will fail on the wrong domain.

---

## Phase 3 — Mediums + Observability (5–7 days)

### Task 3.1 — AI deep-analysis hardening (M-AI2 + M-AI3 escalated)

**Files:**
- Modify: `backend/apps/analytics/tasks.py:239-247` (add `soft_time_limit` and `time_limit`)
- Modify: `backend/apps/analytics/views.py:1293-1306` (sanitize/cap `insight_data` field lengths)
- Modify: `backend/apps/analytics/ai_providers.py:1455-1460` (scope deep-analysis cache by `user.id`)

**Approach:** `time_limit=300, soft_time_limit=270` on the Celery task. Cap `insight_data['description']`, `insight_data['title']` at 1000 chars each. Add `user.id` to the deep-analysis cache key so two users in the same org don't share each other's insights.

### Task 3.2 — Postgres-CI matrix for trigger tests

**Files:**
- Modify: `.github/workflows/ci.yml` — add a job variant
- Optionally new: `backend/config/settings_test_postgres.py` (or override `DJANGO_SETTINGS_MODULE` env var)

**Approach:** The 8 cross-org-FK-trigger tests skip silently in CI today because `pytest.ini` hard-pins `settings_test` (SQLite). Add a CI matrix variant that runs `pytest --ds=config.settings -m postgres` against the Postgres service container, OR mark the trigger tests `@pytest.mark.postgres` and run them in a separate job.

### Task 3.3 — Drift-guard tests for v2.12 invariants

**Files:**
- New: `backend/apps/analytics/tests/test_csp_drift_guard.py` (asserts nginx.conf doesn't reintroduce `'unsafe-eval'`)
- New: `backend/apps/authentication/tests/test_security_headers.py` (asserts HSTS header emitted with `DEBUG=False`)
- New: `frontend/src/lib/__tests__/streamdown-pin-drift.test.ts` (asserts package.json shows `"streamdown": "1.4.0"` exact)

**Approach:** Each test reads the relevant config artifact and asserts the post-Phase-5 invariant. Cheap regression net for a class of silent regressions that wouldn't otherwise surface until a runtime smoke test.

### Task 3.4 — RegisterView happy-path role assertion

**Files:** `backend/apps/authentication/tests/test_views.py:18-36` (`test_register_success`)

**Approach:** Add `assert UserProfile.objects.get(user__username='newuser').role == 'viewer'` to the happy-path test. Closes the drift-guard hole identified in second-pass Agent 6.

### Task 3.5 — `ai_chat_stream` / `ai_quick_query` happy-path body content tests

**Files:** Extend `backend/apps/analytics/tests/test_streaming_model_allowlist.py`

**Approach:** Mock anthropic to return `["Hello", " world"]` chunks; consume the streaming body; assert SSE `data: ` lines contain the tokens in order; assert a terminal event/sentinel emits. Pins the streaming-format contract that the frontend depends on.

### Task 3.6 — Index cleanup migration (M-DB5, M-DB6)

**Files:** `backend/apps/procurement/models.py` (4+ models) + new migration

**Approach:** Drop redundant `db_index=True` from UUID fields that already have `unique=True`. Drop explicit `Index(fields=['organization', 'name'])` from Meta when `unique_together = ('organization', 'name')` is present. Pure migration churn; zero behavior change. Cuts index count significantly across 12 models.

### Task 3.7 — `cache.get → cache.set` audit cleanup

**Files:** Various — grep for the pattern across the codebase

**Approach:** Apply Phase 5 task 5.6's `cache.add` + `cache.incr` pattern wherever `current = cache.get(key) or 0; cache.set(key, current + 1, TTL)` exists. The Phase 1 task 1.6 already fixes `ai_cache.py`; this task sweeps any others.

### Task 3.8 — `frontend isAuthenticated()` deduplication (M-F2)

**Files:** `frontend/src/hooks/useSettings.ts:304` — replace inline `localStorage.getItem("user") !== null` with `import { isAuthenticated } from "@/lib/auth"`

**Approach:** Currently divergent: `lib/auth.ts:23` does session-timeout check + USER_KEY constant; `useSettings.ts:304` is naive presence check. The naive version sees timed-out users as authenticated. Single-line fix.

### Task 3.9 — Payment-terms compliance DB-side aggregation (M-DB1)

**Files:** `backend/apps/analytics/p2p_services.py:1155-1185`

**Approach:** Replace per-row Python iteration with a single `aggregate(...)` annotation using `Avg(F('paid_date') - F('invoice_date'))`. Pattern from Phase 5 task 5.8 (N+1 cluster fix).

### Task 3.10 — Multi-stage migrations on heavy DDL (M-DB3)

**Files:** `backend/apps/procurement/migrations/0006_add_vector_indexes.py` (and any future DDL)

**Approach:** Add `atomic = False` on Migration class and use `CONCURRENTLY` for index creation. Currently builds the IVFFlat index inside `ACCESS EXCLUSIVE`, blocking reads. Low priority because vector tables are small today; matters at deploy time once they grow.

### Task 3.11 — Logging PII filter

**Files:** `backend/config/settings.py:528-556`

**Approach:** Add a `LOG_REDACTION` filter to the security file handler that masks `aiApiKey`, `password`, `Authorization` header values, and other sensitive keys. Currently the `verbose` formatter could capture these from exception messages.

### Task 3.12 — File upload size alignment

**Files:** `backend/config/settings.py:193-194` and `frontend/nginx/nginx.conf:113`

**Approach:** Choose 50 MB or 100 MB and align both. Currently nginx accepts 100 MB but Django rejects > 50 MB with a confusing error.

---

## Self-Review

**1. Spec coverage:**
- Phase 0 covers all 5 Critical findings (S-#1 dep cluster + S-#2 auth fallback + S-#3 lockfile drift; S-#4 + S-#5 bumped to Phase 1 due to scope).
- Phase 1 covers 5 of 5 concurrency Highs + 3 of 3 diff-regression Highs (S-#4, S-#5, S-HA, S-HC, signal handler I/O, JSON race, cache patterns, idempotency, migration locking).
- Phase 2 covers 7 of 7 production-posture Critical/High items + 5 Mediums (Dockerfile, CI, base images, Trivy gating, coverage, deploy step, DB SSL, validator test, Flower port, TRUSTED_PROXIES warning, FROM_EMAIL).
- Phase 3 covers AI hardening cluster (escalated Mediums) + 4 drift-guard gaps from Agent 6 + 5 Mediums from Agent 2 + 2 minor cleanups.

**Gaps surfaced (intentional):**
- The 11 unenumerated Backend(6) + Silent Failures(5) Mediums from the v1 review — cannot verify without re-running domain agents. Not scheduled.
- vite-plugin-manus-runtime gating (would let CSP drop `unsafe-inline`) — captured as v2.12 follow-up; not in v3.0 scope.
- HSTS preload submission — captured as v2.12 follow-up.
- `consecutive_failures` counter on scheduled reports — captured as v2.12 follow-up.
- xlsx migration to `exceljs` — captured but deferred (medium effort, not security-urgent).

**2. Placeholder scan:** Phase 0 fully detailed. Phases 1–3 are deliberately task-level outlines (mirror v2.12's pattern). Each task has files + approach + test approach + commit message hint. Engineer can request expansion of any task.

**3. Type consistency:** N/A — most fixes are isolated. Cross-task references called out at both ends (e.g., Task 0.5's auth fallback fix has a follow-up implication for any test that relied on header-only auth in DEBUG=False mode; called out in Step 6).

**4. Decisions required (escalation gates):**
- Phase 0 Task 0.1 — Django 5.0.14 vs 5.2.x branch decision. Recommend 5.0.14 (LTS) for low-risk patch; 5.2.x for fresh features (deferred).
- Phase 1 Task 1.7 — `last_processed_batch_index` model field requires migration; engineer should confirm with ops before deploy if there are in-flight uploads.
- Phase 2 Task 2.7 — actual deploy implementation needs Railway-specific setup (token, env vars). Engineer confirms with deploy owner before implementing.

---

## Closure status (2026-05-06)

All 4 phases complete. Merged to `main` and pushed to `origin/main`.

| Phase | Tasks | Commits | Merge SHA | Backend tests after |
|---|---|---|---|---|
| 0 — Critical CVEs / auth / lockfile | 5 | `fdda892`, `fef7dc7`, `b86da1c`, `9111ca6`, `ef115f2` | `bc83d48` | 855 (+4 new auth tests) |
| 1 — Concurrency & data integrity | 8 | `273766a`, `9da1a06`, `becb623`, `43972a8`, `185e345`, `91019f6`, `d73ef70`, `3339288` | `ec48e44` | 905 (+50) |
| 2 — Production hardening | 12 (in 6 commits) | `2794982`, `17bd844`, `c5e1e6e`, `beade15`, `f7a3f1a`, `ab0b1ab` | `f71df1d` | 905 (no app-code change) |
| 3 — Mediums + observability | 12 (in 7 commits) | `9f688ce`, `9ff004c`, `c029a65`, `8a3ad6e`, `78498c8`, `9b7dd2f`, `46fbda0` | `398aa74` | 923 (+18) |

**Total: 37 commits, 50 distinct sub-fixes (some bundled). Backend tests 855 → 923 (+68). Frontend +3 drift-guard tests.**

**Open follow-ups (deliberately not in v3.0 scope):**
- Black/isort/Prettier `continue-on-error: true` retained (191/119/24 files would reformat in bulk; deferred to dedicated cleanup commit)
- drf_spectacular W001/W002 + HSTS subdomain/preload remain at `--fail-level=ERROR` (not WARNING)
- `urls.W005 'reports' namespace not unique` — pre-existing real bug, not introduced by remediation
- Other compose files (monitoring, tunnel) still use floating tags
- Vite-transformer suite-load flake (~30%) on frontend tests — upstream issue
- `consecutive_failures` counter on scheduled reports — captured for future cycle

**Inherited deferrals from v2.12 (still open):**
- Task 1.3 — `Report.is_public` semantics pending product decision
- Task 5.4 — aging method DB-side aggregation gated on >20K open invoices threshold

See `docs/REMEDIATION-OPEN-ITEMS.md` for both.

---

*Plan written 2026-05-06 for code state at commit `9545754`. Closure recorded 2026-05-06 at merge SHA `398aa74`. Companion to `docs/codebase-review-2026-05-06-second-pass.md` and `docs/plans/2026-05-05-codebase-remediation.md`.*
