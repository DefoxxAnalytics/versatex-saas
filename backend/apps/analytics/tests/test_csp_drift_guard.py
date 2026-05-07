"""Drift-guard for the v2.12 nginx CSP hardening (Finding #14).

Phase 5 task 5.2 removed `'unsafe-eval'` from the nginx CSP `script-src`
after verifying:
  1. Bundle scan: zero `eval(` and zero `new Function(` calls in the emitted JS.
  2. Smoke test: dashboard, suppliers, categories, pareto, p2p/cycle pages render
     with zero CSP violations.

If anyone re-adds `'unsafe-eval'` to the CSP (e.g., to silence a runtime warning
from a new dependency without auditing it), this test fails before the change
ships. The right path is to audit the dependency and either whitelist via
`'sha256-...'` / nonce, or drop the dependency.

`'unsafe-inline'` for script-src is intentionally KEPT (the Vite build emits an
inline `<script id="manus-runtime">` from `vite-plugin-manus-runtime`). Three
follow-up paths are documented in the nginx config comments — when one lands,
update the second assertion below.

See `frontend/nginx/nginx.conf` lines 48-87 for the full rationale, and
`docs/codebase-review-2026-05-06-second-pass.md` for the second-pass review.
"""

from pathlib import Path

import pytest

# Repo root: backend/apps/analytics/tests/ -> ../../../..
_REPO_ROOT = Path(__file__).resolve().parents[4]
_NGINX_CONF = _REPO_ROOT / "frontend" / "nginx" / "nginx.conf"


def _csp_directive(nginx_conf_text: str) -> str:
    """Extract the value of the Content-Security-Policy add_header directive.

    The directive lives on a single line in the conf, so a line scan is enough.
    Returns the policy string without surrounding quotes / nginx flags.
    """
    for line in nginx_conf_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("add_header") and "Content-Security-Policy" in stripped:
            # Format:  add_header Content-Security-Policy "..." always;
            start = stripped.find('"')
            end = stripped.rfind('"')
            if start != -1 and end != -1 and end > start:
                return stripped[start + 1 : end]
    raise AssertionError(
        "No Content-Security-Policy add_header directive found in nginx.conf — "
        "drift-guard cannot run. Was the security header block removed?"
    )


@pytest.fixture(scope="module")
def csp_directive() -> str:
    # given a production nginx config in the repo
    if not _NGINX_CONF.exists():
        # The dev backend container only mounts ./backend at /app, so the
        # frontend nginx.conf isn't reachable from inside the container. CI
        # checks out the full repo so the file exists there. Skip locally
        # rather than failing — the drift-guard still runs in CI on every
        # PR, which is where it actually matters.
        pytest.skip(
            f"nginx.conf not reachable at {_NGINX_CONF} (likely running "
            f"inside the backend Docker container). The CSP drift-guard "
            f"runs on the host / in CI where the full repo is mounted."
        )
    return _csp_directive(_NGINX_CONF.read_text(encoding="utf-8"))


class TestCspDriftGuard:
    """Drift-guard suite for the v2.12 CSP hardening (Finding #14)."""

    def test_csp_does_not_reintroduce_unsafe_eval(self, csp_directive: str) -> None:
        # when the CSP is parsed
        # then 'unsafe-eval' must not appear (Phase 5 task 5.2 removed it)
        assert "'unsafe-eval'" not in csp_directive, (
            "Finding #14 regression: 'unsafe-eval' is back in the nginx CSP. "
            "Phase 5 task 5.2 removed it after auditing the bundle. Re-adding it "
            "without re-auditing means any XSS via inline-injected eval is now "
            "exploitable. See frontend/nginx/nginx.conf comments for the audit "
            "checklist before reverting this guard."
        )

    def test_csp_keeps_default_src_self(self, csp_directive: str) -> None:
        # when the CSP is parsed
        # then default-src 'self' is still the baseline (no 'unsafe-*' wildcard)
        assert "default-src 'self'" in csp_directive, (
            "CSP no longer restricts default-src to 'self'. The whole policy "
            "leans on this baseline; loosening it without an explicit override "
            "per directive is a drift."
        )

    def test_csp_connect_src_is_self_only(self, csp_directive: str) -> None:
        # when the CSP is parsed
        # then connect-src is same-origin only (no localhost / railway.app whitelist)
        # API traffic goes through the /api/ proxy in nginx, so 'self' covers it.
        assert "connect-src 'self'" in csp_directive, (
            "CSP connect-src no longer locked to 'self'. The pre-v2.12 policy "
            "whitelisted http://localhost:8001 + https://*.railway.app for "
            "legacy cross-origin dev. Single-origin via nginx proxy is canonical "
            "now — re-adding wildcards opens data-exfil paths."
        )
        # Defensive: explicit checks against the historical wildcards.
        assert "*.railway.app" not in csp_directive
        assert "localhost:8001" not in csp_directive
