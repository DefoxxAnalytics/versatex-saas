"""
Readiness endpoint — probes DB + cache dependencies.

Consumed by:
- docker-compose prod healthcheck (replaces the fragile ADMIN_URL-based one)
- Uptime Kuma monitoring probes
- Cloudflare Tunnel / external probe from Healthchecks.io

Returns 200 with {"db":"ok","redis":"ok"} when healthy, 503 with the same
shape but "error" values when any dependency fails. Shape is stable so
alerting rules can parse it.
"""

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

HEALTH_PROBE_KEY = "_health_probe"


@csrf_exempt
@never_cache
@require_GET
def health(request):
    checks = {"db": "ok", "redis": "ok"}
    status_code = 200

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        checks["db"] = "error"
        status_code = 503

    try:
        cache.set(HEALTH_PROBE_KEY, "1", timeout=5)
        if cache.get(HEALTH_PROBE_KEY) != "1":
            raise RuntimeError("cache read-back mismatch")
    except Exception:
        checks["redis"] = "error"
        status_code = 503

    return JsonResponse(checks, status=status_code)
