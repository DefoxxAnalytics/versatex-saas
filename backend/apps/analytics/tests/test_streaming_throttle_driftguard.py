"""Drift-guard: AI streaming endpoints must carry the throttle decorator.

Finding #7 (v2 review): unbounded LLM cost from a single authenticated session.
This test prevents regression by reading the source and asserting the decorator
is present on the two streaming view functions.
"""

import inspect

from apps.analytics import views


def _decorators_of(view_func):
    """Return throttle class names applied to a DRF function-based view."""
    cls = getattr(view_func, "cls", None)
    if cls is None:
        return []
    return [c.__name__ for c in getattr(cls, "throttle_classes", [])]


def test_ai_chat_stream_has_throttle():
    assert "AIInsightsThrottle" in _decorators_of(views.ai_chat_stream), (
        "ai_chat_stream must carry @throttle_classes([AIInsightsThrottle]). "
        "See Finding #7."
    )


def test_ai_quick_query_has_throttle():
    assert "AIInsightsThrottle" in _decorators_of(views.ai_quick_query), (
        "ai_quick_query must carry @throttle_classes([AIInsightsThrottle]). "
        "See Finding #7."
    )


def _ai_chat_stream_body_source():
    """Return the source of ``ai_chat_stream`` itself (not the DRF wrapper).

    ``views.ai_chat_stream`` is wrapped by ``@api_view`` which produces a
    class-based view; ``inspect.getsource`` on the wrapper returns the
    DRF-internal ``view(request, ...)`` shim, not the application code.
    Scan the module source instead.
    """
    import re

    module_src = inspect.getsource(views)
    match = re.search(
        r"^def ai_chat_stream\b.*?(?=^def |\Z)",
        module_src,
        re.DOTALL | re.MULTILINE,
    )
    assert match, "Could not locate ai_chat_stream in apps/analytics/views.py"
    return match.group(0)


def test_ai_chat_stream_validates_model_against_allowlist_phase_4():
    """Finding #8 permanent: ai_chat_stream must read 'model' from request.data
    AND validate the value against AI_CHAT_ALLOWED_MODELS.

    Replaces the Phase 0 drift-guard that forbade reading 'model' entirely;
    Phase 4 task 4.2 introduced a settings-driven allowlist + default model so
    legitimate-but-validated client model selection is allowed again.
    """
    import re

    src = _ai_chat_stream_body_source()
    # Must read model from request body (validated against allowlist below).
    assert re.search(r"request\.data\.get\(\s*['\"]model['\"]", src), (
        "ai_chat_stream must read 'model' from request.data after Phase 4 "
        "task 4.2 (with allowlist validation). If model is being hardcoded "
        "again, that's a Finding #8 regression."
    )
    # Must reference the allowlist setting.
    assert "AI_CHAT_ALLOWED_MODELS" in src, (
        "ai_chat_stream must validate the model against AI_CHAT_ALLOWED_MODELS. "
        "Reading from request.data without the allowlist is the Finding #8 "
        "client-controlled-model-escalation hole."
    )
