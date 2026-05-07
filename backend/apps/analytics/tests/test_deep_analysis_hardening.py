"""v3.0 Phase 3 Task 3.1 — AI deep-analysis hardening (M-AI2 + M-AI3).

Three concurrency / privacy fixes on the deep-analysis path:

a) Drift-guard the Celery decorator's time_limit/soft_time_limit. Without
   them, a runaway LLM call (provider hang, infinite tool loop) would hold
   a worker indefinitely.

b) Per-field caps on insight_data.title and .description before the data
   reaches Celery / the LLM. The pre-existing payload bound caps total
   request size; this prevents a single-field cost-blast inside the bound.

c) Semantic cache key includes user_id. Two users in the same org sharing
   an insight ID would otherwise receive each other's cached analytical
   responses — a privacy leak in multi-user organizations.
"""
import json
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import Organization, UserProfile
from apps.analytics.tasks import perform_deep_analysis_async
from apps.analytics.ai_providers import AIProviderManager

User = get_user_model()


class TestDeepAnalysisCeleryTimeLimit(APITestCase):
    """Sub-fix 3.1a — drift-guard the Celery decorator time limits.

    Direct integration tests against Celery's hard kill are flaky; this
    asserts the decorator carries the documented values so a future
    refactor cannot silently drop them.
    """

    def test_celery_task_has_time_limits(self):
        # Celery surfaces decorator options as task attributes.
        self.assertEqual(
            perform_deep_analysis_async.soft_time_limit,
            270,
            "soft_time_limit must be 270s (4.5min) — gives the task a chance "
            "to clean up via SoftTimeLimitExceeded before the hard kill.",
        )
        self.assertEqual(
            perform_deep_analysis_async.time_limit,
            300,
            "time_limit must be 300s (5min) — hard ceiling; without it a "
            "runaway LLM call holds a Celery worker indefinitely.",
        )


class TestDeepAnalysisInsightDataCaps(APITestCase):
    """Sub-fix 3.1b — title and description capped at 1000 chars before
    being passed to Celery / the LLM."""

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Org DA", slug="org-da")

    def setUp(self):
        self.user = User.objects.create_user(username="da_user", password="pw")
        UserProfile.objects.create(
            user=self.user, organization=self.org, role="viewer"
        )
        self.client.force_authenticate(self.user)
        self.url = reverse("request-deep-analysis")

    @patch("apps.analytics.tasks.perform_deep_analysis_async")
    def test_oversized_title_and_description_are_truncated(self, mock_task):
        mock_task.delay.return_value = MagicMock(id="task-fake-id")

        payload = {
            "insight": {
                "id": "insight-1",
                "type": "cost_optimization",
                "title": "T" * 5000,
                "description": "D" * 5000,
                "potential_savings": 12345.67,
            }
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        mock_task.delay.assert_called_once()
        call_kwargs = mock_task.delay.call_args.kwargs
        sanitized = call_kwargs["insight_data"]

        self.assertEqual(len(sanitized["title"]), 1000)
        self.assertEqual(len(sanitized["description"]), 1000)
        # Other fields preserved untouched.
        self.assertEqual(sanitized["id"], "insight-1")
        self.assertEqual(sanitized["type"], "cost_optimization")
        self.assertEqual(sanitized["potential_savings"], 12345.67)

    @patch("apps.analytics.tasks.perform_deep_analysis_async")
    def test_short_title_and_description_pass_through_unchanged(self, mock_task):
        mock_task.delay.return_value = MagicMock(id="task-fake-id")

        payload = {
            "insight": {
                "id": "insight-2",
                "type": "risk",
                "title": "Short title",
                "description": "Short description",
            }
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        sanitized = mock_task.delay.call_args.kwargs["insight_data"]
        self.assertEqual(sanitized["title"], "Short title")
        self.assertEqual(sanitized["description"], "Short description")

    @patch("apps.analytics.tasks.perform_deep_analysis_async")
    def test_missing_title_and_description_handled_safely(self, mock_task):
        mock_task.delay.return_value = MagicMock(id="task-fake-id")

        payload = {
            "insight": {
                "id": "insight-3",
                "type": "anomaly",
            }
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        sanitized = mock_task.delay.call_args.kwargs["insight_data"]
        self.assertEqual(sanitized["title"], "")
        self.assertEqual(sanitized["description"], "")


class TestDeepAnalysisCacheKeyUserScoping(APITestCase):
    """Sub-fix 3.1c — semantic cache key for deep_analysis is per-user.

    We don't need a real provider or live cache: the cache_key is built at
    the very top of ``AIProviderManager.deep_analysis`` from a JSON dict.
    Capture that dict by inspecting what the lookup is called with.
    """

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Org CK", slug="org-ck")

    def _build_manager(self):
        manager = AIProviderManager.__new__(AIProviderManager)
        manager.primary_provider = "anthropic"
        manager.api_keys = {}
        manager.fallback_order = ["anthropic", "openai"]
        manager.enable_fallback = True
        manager.organization_id = self.org.id
        manager.enable_logging = False
        manager.enable_semantic_cache = True
        manager.enable_rag = False
        manager.enable_validation = False
        manager._providers = {}
        manager._provider_errors = {}
        manager._last_error_code = None
        manager._last_successful_provider = None
        manager._semantic_cache = MagicMock()
        manager._semantic_cache.lookup.return_value = None
        manager._rag_service = None
        manager._validator = None
        return manager

    def _capture_cache_key(self, manager, *, user_id, insight_id="insight-X"):
        manager._semantic_cache.lookup.reset_mock()
        manager.deep_analysis(
            insight_data={
                "id": insight_id,
                "type": "cost_optimization",
                "title": "Reduce supplier consolidation",
                "description": "Long form description",
            },
            context={"spending": {"total_ytd": 1_000_000}},
            tool_schema={},
            skip_rag=True,
            user_id=user_id,
        )
        # First positional arg to lookup() is the cache_key string.
        call = manager._semantic_cache.lookup.call_args
        return call.args[0] if call.args else call.kwargs["query"]

    def test_different_users_same_org_get_different_cache_keys(self):
        manager = self._build_manager()
        key_user_1 = self._capture_cache_key(manager, user_id=101)
        key_user_2 = self._capture_cache_key(manager, user_id=202)

        self.assertNotEqual(
            key_user_1,
            key_user_2,
            "Cache keys for different users in the same org must differ — "
            "otherwise User A's cached analysis is served to User B "
            "(M-AI2 privacy leak).",
        )
        # Sanity-check both keys actually carry the user_id field.
        self.assertEqual(json.loads(key_user_1)["user_id"], 101)
        self.assertEqual(json.loads(key_user_2)["user_id"], 202)

    def test_same_user_same_insight_produces_stable_cache_key(self):
        manager = self._build_manager()
        key_first = self._capture_cache_key(manager, user_id=101)
        key_second = self._capture_cache_key(manager, user_id=101)

        self.assertEqual(
            key_first,
            key_second,
            "Repeated calls by the same user for the same insight must "
            "produce the same cache key — otherwise the cache never hits.",
        )

    def test_cache_key_is_user_scoped_even_when_user_id_omitted(self):
        """Defensive: when user_id is not provided (legacy call sites), the
        key still includes a ``user_id`` field set to None, so a future call
        that does pass a user_id will not collide with legacy entries."""
        manager = self._build_manager()
        key = self._capture_cache_key(manager, user_id=None)
        self.assertIn("user_id", json.loads(key))
        self.assertIsNone(json.loads(key)["user_id"])
