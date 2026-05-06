"""Finding #6 perm + B13 + B14: typed error codes through SSE / MV / provider.

The Phase 0 fix to Finding #6 sanitized leaked exception text out of the SSE
error frames but emitted a generic 'AI service error' message. This file pins
the permanent fix:

* SSE error frames carry an `error_code` companion to `error` so the frontend
  can branch (auth vs rate-limit vs unknown).
* MV refresh distinguishes "clean refresh" from "blocking-fallback succeeded"
  via a separate `warnings` list (Finding B13).
* Provider manager records typed `{code, message}` per-provider on failover
  and exposes the last error code so the orchestrator can hydrate
  `enhancement_error_code` instead of the hardcoded 'llm_call_failed'
  (Finding B14).
"""
import json

from unittest.mock import patch, MagicMock

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.analytics.llm_error_codes import (
    AIErrorCode,
    classify_anthropic_error,
)


def _make_anthropic_error(error_cls, message="bad key"):
    """Construct an anthropic.* error compatibly across SDK versions."""
    try:
        return error_cls(message=message, response=MagicMock(), body=None)
    except TypeError:
        try:
            return error_cls(message)
        except TypeError:
            return error_cls()


class TestErrorClassification:
    """classify_anthropic_error maps SDK exception types to AIErrorCode."""

    def test_classify_authentication_error(self):
        import anthropic
        exc = _make_anthropic_error(anthropic.AuthenticationError)
        assert classify_anthropic_error(exc) == AIErrorCode.AUTH_ERROR

    def test_classify_rate_limit_error(self):
        import anthropic
        exc = _make_anthropic_error(anthropic.RateLimitError, "rate limit")
        assert classify_anthropic_error(exc) == AIErrorCode.RATE_LIMITED

    def test_classify_api_connection_error(self):
        import anthropic
        # APIConnectionError takes a `request` kwarg in modern SDKs.
        try:
            exc = anthropic.APIConnectionError(request=MagicMock())
        except TypeError:
            exc = _make_anthropic_error(anthropic.APIConnectionError, "conn")
        assert classify_anthropic_error(exc) == AIErrorCode.SERVICE_UNAVAILABLE

    def test_classify_bad_request_error(self):
        import anthropic
        exc = _make_anthropic_error(anthropic.BadRequestError, "bad")
        assert classify_anthropic_error(exc) == AIErrorCode.BAD_REQUEST

    def test_classify_generic_exception(self):
        assert classify_anthropic_error(RuntimeError("boom")) == AIErrorCode.UNKNOWN

    def test_classify_value_error(self):
        assert classify_anthropic_error(ValueError("v")) == AIErrorCode.UNKNOWN


def _consume(streaming_response):
    """Drain the StreamingHttpResponse and return the decoded body."""
    return b"".join(streaming_response.streaming_content).decode("utf-8")


@pytest.mark.django_db
class TestSSETypedErrors:
    """SSE error frames now carry both error_code and error."""

    @override_settings(ANTHROPIC_API_KEY="test-key-not-used-mock-takes-over")
    def test_streaming_auth_error_sends_typed_code(self, authenticated_client):
        import anthropic
        url = reverse("ai-chat-stream")
        mock_client = MagicMock()
        mock_client.messages.stream.side_effect = _make_anthropic_error(
            anthropic.AuthenticationError, "Invalid API key sk-ant-LEAKY"
        )

        with patch("anthropic.Anthropic", return_value=mock_client):
            response = authenticated_client.post(
                url,
                {"messages": [{"role": "user", "content": "hi"}]},
                format="json",
            )
            body = _consume(response)

        assert AIErrorCode.AUTH_ERROR in body, (
            f"AUTH_ERROR code missing from SSE body: {body[:300]}"
        )
        assert "sk-ant-LEAKY" not in body, (
            "Raw exception text leaked despite typed-code refactor"
        )
        # Frame must be JSON-parseable with both keys
        for line in body.splitlines():
            if line.startswith("data: ") and "error_code" in line:
                payload = json.loads(line[6:])
                assert payload["error_code"] == AIErrorCode.AUTH_ERROR
                assert "error" in payload, "Missing user-facing error message"
                break
        else:
            pytest.fail(f"No SSE frame with error_code found: {body[:300]}")

    @override_settings(ANTHROPIC_API_KEY="test-key-not-used-mock-takes-over")
    def test_streaming_generic_exception_sends_unknown_code(
        self, authenticated_client
    ):
        url = reverse("ai-chat-stream")
        mock_client = MagicMock()
        mock_client.messages.stream.side_effect = RuntimeError("boom")

        with patch("anthropic.Anthropic", return_value=mock_client):
            response = authenticated_client.post(
                url,
                {"messages": [{"role": "user", "content": "hi"}]},
                format="json",
            )
            body = _consume(response)

        assert AIErrorCode.UNKNOWN in body, (
            f"UNKNOWN code missing from SSE body: {body[:300]}"
        )

    @override_settings(ANTHROPIC_API_KEY="test-key-not-used-mock-takes-over")
    def test_quick_query_rate_limit_sends_typed_code(self, authenticated_client):
        import anthropic
        url = reverse("ai-quick-query")
        mock_client = MagicMock()
        mock_client.messages.stream.side_effect = _make_anthropic_error(
            anthropic.RateLimitError, "rate"
        )

        with patch("anthropic.Anthropic", return_value=mock_client):
            response = authenticated_client.post(
                url,
                {"query": "hi", "include_context": False},
                format="json",
            )
            body = _consume(response)

        assert AIErrorCode.RATE_LIMITED in body, (
            f"RATE_LIMITED code missing from SSE body: {body[:300]}"
        )


class TestMVRefreshWarnings:
    """Finding B13: errors.pop() removed; warnings list preserves original error."""

    def test_clean_refresh_has_no_warnings(self):
        from apps.analytics.tasks import refresh_materialized_views
        with patch("apps.analytics.tasks.connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.execute.return_value = None  # all CONCURRENTLY succeed

            result = refresh_materialized_views.run()

        assert result['errors'] == [], "Clean refresh should have no errors"
        assert result['warnings'] == [], "Clean refresh should have no warnings"
        assert result['status'] == 'success'

    def test_concurrently_failed_with_fallback_records_warning_and_error(self):
        from apps.analytics.tasks import refresh_materialized_views

        with patch("apps.analytics.tasks.connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

            call_count = {'n': 0}

            def execute_side_effect(sql):
                call_count['n'] += 1
                # First view's CONCURRENTLY fails, fallback succeeds
                if call_count['n'] == 1:
                    raise Exception("CONCURRENTLY failed: missing unique index")
                return None

            mock_cursor.execute.side_effect = execute_side_effect

            result = refresh_materialized_views.run()

        # The CONCURRENTLY error MUST remain in errors (was previously popped)
        assert len(result['errors']) >= 1, (
            "Original CONCURRENTLY error should be preserved in `errors` so "
            "monitoring can still see it. Got: {!r}".format(result['errors'])
        )
        # New: warnings list should record the blocking-fallback success
        assert len(result['warnings']) >= 1, (
            f"Expected `warnings` entry for fallback success: {result!r}"
        )
        first_warning = result['warnings'][0]
        assert first_warning['reason'] == 'concurrently_failed_used_blocking_fallback'
        assert 'view' in first_warning
        assert 'original_error' in first_warning


@pytest.mark.django_db
class TestProviderManagerLastErrorCode:
    """Finding B14: provider manager exposes typed last-error code."""

    def test_no_failures_returns_none(self, organization):
        from apps.analytics.ai_providers import AIProviderManager
        manager = AIProviderManager(
            primary_provider='anthropic',
            api_keys={'anthropic': 'sk-ant-test'},
            organization_id=organization.id,
            enable_logging=False,
            enable_semantic_cache=False,
            enable_rag=False,
            enable_validation=False,
        )
        assert manager.get_last_error_code() is None

    def test_auth_error_recorded_as_auth_code(self, organization):
        import anthropic
        from apps.analytics.ai_providers import AIProviderManager

        manager = AIProviderManager(
            primary_provider='anthropic',
            api_keys={'anthropic': 'sk-ant-test'},
            enable_fallback=False,
            organization_id=organization.id,
            enable_logging=False,
            enable_semantic_cache=False,
            enable_rag=False,
            enable_validation=False,
        )
        # Force a failure on the anthropic provider's enhance_insights
        provider = manager._providers.get('anthropic')
        assert provider is not None
        with patch.object(
            provider, 'enhance_insights',
            side_effect=_make_anthropic_error(
                anthropic.AuthenticationError, "bad key"
            ),
        ), patch.object(provider, 'is_available', return_value=True):
            result = manager.enhance_insights(
                insights=[{'type': 'test', 'title': 't'}],
                context={'spending': {'total_ytd': 0}},
                tool_schema={'name': 'tool', 'description': 'x',
                             'input_schema': {'type': 'object', 'properties': {}}},
            )

        assert result is None, "Failed enhancement should return None"
        assert manager.get_last_error_code() == AIErrorCode.AUTH_ERROR
        recorded = manager._provider_errors.get('anthropic')
        assert isinstance(recorded, dict), (
            f"_provider_errors entry must be dict, got {type(recorded)}: {recorded!r}"
        )
        assert recorded['code'] == AIErrorCode.AUTH_ERROR
        assert 'message' in recorded


@pytest.mark.django_db
class TestOrchestratorEnhancementErrorCode:
    """Finding B14: orchestrator pulls typed code from manager into response."""

    def test_enhancement_error_code_reflects_manager_state(
        self, organization, admin_user
    ):
        import anthropic
        from datetime import date, timedelta
        from decimal import Decimal
        from apps.analytics.ai_services import AIInsightsService
        from apps.procurement.tests.factories import (
            CategoryFactory, SupplierFactory, TransactionFactory,
        )

        # Seed minimal data so insights can generate
        cat = CategoryFactory(organization=organization, name='ErrCat')
        sup = SupplierFactory(organization=organization, name='ErrSup')
        today = date.today()
        for i in range(8):
            TransactionFactory(
                organization=organization, supplier=sup, category=cat,
                uploaded_by=admin_user, amount=Decimal('1500'),
                subcategory='se',
                date=today - timedelta(days=10 + i),
                invoice_number=f'E-{i}',
            )

        service = AIInsightsService(
            organization,
            use_external_ai=True,
            ai_provider='anthropic',
            api_key='sk-ant-test',
        )
        # Stub the provider's enhance to raise an Anthropic AuthenticationError
        # so the manager records AUTH_ERROR before returning None.
        provider = service._provider_manager._providers.get('anthropic')

        with patch.object(
            provider, 'enhance_insights',
            side_effect=_make_anthropic_error(
                anthropic.AuthenticationError, "bad key"
            ),
        ), patch.object(provider, 'is_available', return_value=True):
            result = service.get_all_insights(force_refresh=True)

        assert result.get('enhancement_status') == 'unavailable_failed'
        assert result.get('enhancement_error_code') == AIErrorCode.AUTH_ERROR, (
            f"Expected enhancement_error_code={AIErrorCode.AUTH_ERROR}, got "
            f"{result.get('enhancement_error_code')!r}"
        )
