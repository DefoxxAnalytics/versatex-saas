"""Tests for the send_llm_cost_digest Celery task."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.analytics.models import LLMRequestLog
from apps.analytics.tasks import send_llm_cost_digest


def _yesterday_at(hour, minute=0):
    """Return a datetime at the given hour on the previous UTC day."""
    now = timezone.now()
    base = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    return base + timedelta(hours=hour, minutes=minute)


@pytest.fixture
def yesterday_logs(db, organization):
    """Two cost-bearing LLMRequestLog records yesterday, one today (excluded)."""
    LLMRequestLog.objects.create(
        organization=organization,
        request_type='enhance',
        model_used='claude-3-5-sonnet',
        provider='anthropic',
        cost_usd=Decimal('0.1234'),
        tokens_input=1000,
        tokens_output=500,
    )
    LLMRequestLog.objects.create(
        organization=organization,
        request_type='chat',
        model_used='gpt-4o-mini',
        provider='openai',
        cost_usd=Decimal('0.0050'),
        tokens_input=200,
        tokens_output=100,
    )
    # Shift the above two to yesterday (bypass auto_now_add by update).
    LLMRequestLog.objects.all().update(created_at=_yesterday_at(12))
    # Today's record should not appear in the digest.
    LLMRequestLog.objects.create(
        organization=organization,
        request_type='chat',
        model_used='gpt-4o-mini',
        provider='openai',
        cost_usd=Decimal('99.9999'),
    )


@pytest.mark.django_db
class TestSendLlmCostDigest:
    def test_aggregates_yesterday_only(self, yesterday_logs):
        with override_settings(COST_ALERT_WEBHOOK_URL=''):
            summary = send_llm_cost_digest()
        assert summary['request_count'] == 2
        assert summary['total_cost_usd'] == pytest.approx(0.1284)  # 0.1234 + 0.0050
        assert summary['webhook_posted'] is False
        assert summary['webhook_skip_reason'] == 'COST_ALERT_WEBHOOK_URL not set'

    def test_by_provider_grouping(self, yesterday_logs):
        with override_settings(COST_ALERT_WEBHOOK_URL=''):
            summary = send_llm_cost_digest()
        providers = {row['provider']: row for row in summary['by_provider']}
        assert set(providers) == {'anthropic', 'openai'}
        assert providers['anthropic']['count'] == 1
        assert providers['anthropic']['cost'] == pytest.approx(0.1234)
        assert providers['openai']['count'] == 1
        assert providers['openai']['cost'] == pytest.approx(0.0050)

    def test_by_request_type_grouping(self, yesterday_logs):
        with override_settings(COST_ALERT_WEBHOOK_URL=''):
            summary = send_llm_cost_digest()
        types = {row['type']: row for row in summary['by_request_type']}
        assert set(types) == {'enhance', 'chat'}
        assert types['enhance']['cost'] == pytest.approx(0.1234)
        assert types['chat']['cost'] == pytest.approx(0.0050)

    def test_empty_window_returns_zero_cost(self):
        with override_settings(COST_ALERT_WEBHOOK_URL=''):
            summary = send_llm_cost_digest()
        assert summary['request_count'] == 0
        assert summary['total_cost_usd'] == 0.0
        assert summary['by_provider'] == []
        assert summary['by_request_type'] == []

    def test_posts_to_webhook_when_configured(self, yesterday_logs):
        with patch('requests.post') as mock_post, \
             override_settings(COST_ALERT_WEBHOOK_URL='https://ntfy.sh/versatex-test'):
            mock_post.return_value.status_code = 200
            summary = send_llm_cost_digest()
        assert summary['webhook_posted'] is True
        assert summary['webhook_status_code'] == 200
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://ntfy.sh/versatex-test'
        body = call_args[1]['data'].decode('utf-8')
        assert 'LLM cost digest for' in body
        assert '0.1284' in body

    def test_webhook_failure_does_not_raise(self, yesterday_logs):
        with patch('requests.post', side_effect=Exception('network down')), \
             override_settings(COST_ALERT_WEBHOOK_URL='https://ntfy.sh/versatex-test'):
            summary = send_llm_cost_digest()
        assert summary['webhook_posted'] is False
        assert summary['webhook_error'] == 'Exception'
        # Aggregation result still present.
        assert summary['request_count'] == 2
