"""
Finding #9 — `enhancement_status` tri-state (Cross-Module Open).

CLAUDE.md Rule 6 covered only the no-API-key case (omit `ai_enhancement`,
render "(Deterministic)" in the UI). When a key IS configured but the LLM
call fails, the response previously also omitted `ai_enhancement` — making
LLM-failure indistinguishable from no-key.

This contract test pins the orchestrator to always emit `enhancement_status`
in {enhanced, unavailable_no_key, unavailable_failed} and to omit
`ai_enhancement` in both unavailable states.
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.analytics.ai_services import AIInsightsService
from apps.procurement.tests.factories import (
    CategoryFactory, SupplierFactory, TransactionFactory,
)


@pytest.fixture
def populated_org(organization, admin_user):
    """Minimum data for the orchestrator to emit insights."""
    cat = CategoryFactory(organization=organization, name='StatusCat')
    a = SupplierFactory(organization=organization, name='SupA')
    b = SupplierFactory(organization=organization, name='SupB')

    today = date.today()
    for i in range(8):
        TransactionFactory(
            organization=organization, supplier=a, category=cat,
            uploaded_by=admin_user, amount=Decimal('1000'),
            subcategory='sub_one',
            date=today - timedelta(days=10 + i),
            invoice_number=f'A-{i}',
        )
    for i in range(8):
        TransactionFactory(
            organization=organization, supplier=b, category=cat,
            uploaded_by=admin_user, amount=Decimal('1800'),
            subcategory='sub_one',
            date=today - timedelta(days=40 + i),
            invoice_number=f'B-{i}',
        )
    return organization


@pytest.mark.django_db
class TestEnhancementStatusTriState:
    """The orchestrator must emit enhancement_status in all three states."""

    def test_enhanced_when_llm_succeeds(self, populated_org):
        """API key present + LLM returns enhancement → status='enhanced'."""
        fake_enhancement = {
            'priority_actions': [],
            'risk_assessment': {'overall_risk_level': 'low', 'key_risks': []},
            'quick_wins': [],
            'strategic_summary': 'ok',
            'provider': 'anthropic',
            'generated_at': '2026-01-01T00:00:00',
        }
        service = AIInsightsService(
            populated_org,
            use_external_ai=True,
            ai_provider='anthropic',
            api_key='sk-ant-test-key',
        )
        with patch.object(
            AIInsightsService, '_enhance_with_external_ai',
            return_value=fake_enhancement,
        ):
            result = service.get_all_insights(force_refresh=True)

        assert result.get('enhancement_status') == 'enhanced', (
            "When LLM succeeds, enhancement_status must be 'enhanced'."
        )
        assert 'ai_enhancement' in result, (
            "Successful LLM enhancement must include the ai_enhancement payload."
        )
        assert result['ai_enhancement']['provider'] == 'anthropic'

    def test_unavailable_no_key_when_external_ai_disabled(self, populated_org):
        """use_external_ai=False → status='unavailable_no_key', no ai_enhancement."""
        service = AIInsightsService(
            populated_org,
            use_external_ai=False,
        )
        result = service.get_all_insights()

        assert result.get('enhancement_status') == 'unavailable_no_key', (
            "Without LLM enabled, status must be 'unavailable_no_key'."
        )
        assert 'ai_enhancement' not in result, (
            "ai_enhancement must be absent when no API key path is taken."
        )

    def test_unavailable_no_key_when_use_external_but_no_key(self, populated_org):
        """use_external_ai=True but no api_key → status='unavailable_no_key'."""
        service = AIInsightsService(
            populated_org,
            use_external_ai=True,
            ai_provider='anthropic',
            api_key=None,
        )
        result = service.get_all_insights()

        assert result.get('enhancement_status') == 'unavailable_no_key'
        assert 'ai_enhancement' not in result

    def test_unavailable_failed_when_llm_returns_none(self, populated_org):
        """API key present + LLM returns None → status='unavailable_failed'."""
        service = AIInsightsService(
            populated_org,
            use_external_ai=True,
            ai_provider='anthropic',
            api_key='sk-ant-test-key',
        )
        with patch.object(
            AIInsightsService, '_enhance_with_external_ai',
            return_value=None,
        ):
            result = service.get_all_insights(force_refresh=True)

        assert result.get('enhancement_status') == 'unavailable_failed', (
            "When LLM call fails (returns None), status must be "
            "'unavailable_failed' so the UI can distinguish it from no-key."
        )
        assert 'ai_enhancement' not in result, (
            "Failed enhancement must NOT include ai_enhancement."
        )

    def test_unavailable_failed_when_llm_raises(self, populated_org):
        """API key present + LLM raises → status='unavailable_failed'."""
        service = AIInsightsService(
            populated_org,
            use_external_ai=True,
            ai_provider='anthropic',
            api_key='sk-ant-test-key',
        )
        with patch.object(
            AIInsightsService, '_enhance_with_external_ai',
            side_effect=RuntimeError('simulated provider blow-up'),
        ):
            result = service.get_all_insights(force_refresh=True)

        assert result.get('enhancement_status') == 'unavailable_failed'
        assert 'ai_enhancement' not in result
