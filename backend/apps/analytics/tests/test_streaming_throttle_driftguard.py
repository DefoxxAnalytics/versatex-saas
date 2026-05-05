"""Drift-guard: AI streaming endpoints must carry the throttle decorator.

Finding #7 (v2 review): unbounded LLM cost from a single authenticated session.
This test prevents regression by reading the source and asserting the decorator
is present on the two streaming view functions.
"""
from apps.analytics import views


def _decorators_of(view_func):
    """Return throttle class names applied to a DRF function-based view."""
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
