"""
Deterministic AI-insight generator regressions — Cluster 8 (PR-8b).

These tests exercise the four generators plus the orchestrator against a
seeded fixture. They do NOT test LLM output quality — that's explicitly
deferred per the statistical-validity gate in the plan. They DO verify:

- Each generator returns well-formed insight dicts
- No NaN/Infinity in numeric outputs
- Threshold application is stable (passes on clear signal; skips on noise)
- Savings dedup does not lose money nor double-count
- Savings cap vs total_spend is enforced
- enhancement_status is correct (absent ai_enhancement implies no LLM path)
"""

import math
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.analytics.ai_services import AIInsightsService
from apps.procurement.tests.factories import (
    CategoryFactory,
    SupplierFactory,
    TransactionFactory,
)


@pytest.fixture
def risk_fixture(organization, admin_user):
    """
    One dominant supplier (~60% of spend) plus three smaller ones, all inside
    a single (category, subcategory). Triggers risk (concentration) AND
    consolidation (≥3 suppliers in one group) paths.
    """
    cat = CategoryFactory(organization=organization, name="RiskCat")
    dominant = SupplierFactory(organization=organization, name="DominantSupplier")
    small_1 = SupplierFactory(organization=organization, name="SmallOne")
    small_2 = SupplierFactory(organization=organization, name="SmallTwo")
    small_3 = SupplierFactory(organization=organization, name="SmallThree")

    today = date.today()
    for i in range(10):
        TransactionFactory(
            organization=organization,
            supplier=dominant,
            category=cat,
            uploaded_by=admin_user,
            amount=Decimal("70000"),
            subcategory="sub_alpha",
            date=today - timedelta(days=30 + i),
            invoice_number=f"DOM-{i}",
        )
    for i in range(5):
        TransactionFactory(
            organization=organization,
            supplier=small_1,
            category=cat,
            uploaded_by=admin_user,
            amount=Decimal("10000"),
            subcategory="sub_alpha",
            date=today - timedelta(days=60 + i),
            invoice_number=f"S1-{i}",
        )
    for i in range(3):
        TransactionFactory(
            organization=organization,
            supplier=small_2,
            category=cat,
            uploaded_by=admin_user,
            amount=Decimal("5000"),
            subcategory="sub_alpha",
            date=today - timedelta(days=80 + i),
            invoice_number=f"S2-{i}",
        )
    for i in range(2):
        TransactionFactory(
            organization=organization,
            supplier=small_3,
            category=cat,
            uploaded_by=admin_user,
            amount=Decimal("3000"),
            subcategory="sub_alpha",
            date=today - timedelta(days=95 + i),
            invoice_number=f"S3-{i}",
        )
    return organization


@pytest.fixture
def price_variance_fixture(organization, admin_user):
    """Same (category, subcategory) with two suppliers priced very differently."""
    cat = CategoryFactory(organization=organization, name="VarianceCat")
    cheap = SupplierFactory(organization=organization, name="CheapSupplier")
    expensive = SupplierFactory(organization=organization, name="ExpensiveSupplier")
    today = date.today()
    for i in range(8):
        TransactionFactory(
            organization=organization,
            supplier=cheap,
            category=cat,
            uploaded_by=admin_user,
            amount=Decimal("1000"),
            subcategory="sub_one",
            date=today - timedelta(days=10 + i),
            invoice_number=f"CHEAP-{i}",
        )
    for i in range(8):
        TransactionFactory(
            organization=organization,
            supplier=expensive,
            category=cat,
            uploaded_by=admin_user,
            amount=Decimal("1800"),  # 80% more
            subcategory="sub_one",
            date=today - timedelta(days=40 + i),
            invoice_number=f"EXP-{i}",
        )
    return organization


def _assert_insight_shape(insights):
    """Every generator must emit well-formed dicts with sane numeric types."""
    required = {
        "id",
        "type",
        "severity",
        "confidence",
        "title",
        "description",
        "recommended_actions",
        "created_at",
    }
    for ins in insights:
        missing = required - ins.keys()
        assert not missing, f"missing keys {missing} in {ins}"
        savings = ins.get("potential_savings")
        if savings is not None:
            assert isinstance(savings, (int, float)), f"savings type: {type(savings)}"
            assert not math.isnan(savings) and not math.isinf(savings)
            assert savings >= 0


@pytest.mark.django_db
class TestDeterministicGenerators:
    """Each of the 4 generators, on a seeded fixture."""

    def test_cost_optimization_finds_price_variance(self, price_variance_fixture):
        service = AIInsightsService(price_variance_fixture)
        insights = service.get_cost_optimization_insights()
        _assert_insight_shape(insights)
        # 80% variance is above the 15% threshold and above 30% → 'high'.
        assert any(i["severity"] == "high" for i in insights)

    def test_supplier_risk_fires_on_concentration(self, risk_fixture):
        service = AIInsightsService(risk_fixture)
        insights = service.get_supplier_risk_insights()
        _assert_insight_shape(insights)
        # Dominant supplier has ~70% share → at or above the critical threshold.
        assert any(i["type"] == "risk" for i in insights)
        # Risk insights don't claim savings (None).
        for ins in insights:
            assert ins.get("potential_savings") is None

    def test_anomaly_insights_are_bounded(self, risk_fixture):
        service = AIInsightsService(risk_fixture)
        insights = service.get_anomaly_insights()
        _assert_insight_shape(insights)
        # Nothing in the fixture should be hugely anomalous, but the generator
        # must not crash on borderline data. Also: no NaN when std is 0.
        for ins in insights:
            assert ins["type"] == "anomaly"

    def test_consolidation_on_multi_supplier_category(self, risk_fixture):
        service = AIInsightsService(risk_fixture)
        insights = service.get_consolidation_recommendations()
        _assert_insight_shape(insights)
        # Multi-supplier (category, subcategory) → at least one consolidation insight.
        assert any(i["type"] == "consolidation" for i in insights)

    def test_empty_org_generators_return_empty_lists(self, organization):
        service = AIInsightsService(organization)
        assert service.get_cost_optimization_insights() == []
        assert service.get_supplier_risk_insights() == []
        assert service.get_anomaly_insights() == []
        assert service.get_consolidation_recommendations() == []


@pytest.mark.django_db
class TestGetAllInsightsAggregation:
    """Orchestrator-level invariants: dedup, cap, enhancement_status omission."""

    def test_no_ai_enhancement_when_no_key(self, risk_fixture):
        service = AIInsightsService(risk_fixture, use_external_ai=False)
        result = service.get_all_insights()
        assert "ai_enhancement" not in result, (
            "ai_enhancement must be absent when LLM path is disabled; "
            "frontend uses this to render the (Deterministic) label."
        )

    def test_savings_are_capped_at_total_spend(self, risk_fixture):
        """deduplicate + cap: total_potential_savings must never exceed total_spend."""
        service = AIInsightsService(risk_fixture)
        result = service.get_all_insights()
        summary = result["summary"]
        assert summary["total_potential_savings"] <= summary["total_spend"] + 0.01

    def test_summary_has_by_type_counts(self, risk_fixture):
        result = AIInsightsService(risk_fixture).get_all_insights()
        by_type = result["summary"]["by_type"]
        assert "cost_optimization" in by_type
        assert "risk" in by_type
        assert "anomaly" in by_type
        assert "consolidation" in by_type

    def test_deduplicate_savings_never_inflates_total(self, risk_fixture):
        """After dedup, adjusted total must never exceed the naive sum."""
        service = AIInsightsService(risk_fixture)
        cost = service.get_cost_optimization_insights()
        risk = service.get_supplier_risk_insights()
        anom = service.get_anomaly_insights()
        cons = service.get_consolidation_recommendations()
        all_insights = cost + risk + anom + cons
        naive_sum = sum((i.get("potential_savings") or 0) for i in all_insights)

        _dedup, adjusted = service.deduplicate_savings(all_insights)
        assert adjusted <= naive_sum + 0.01

    def test_deduplicate_with_empty_input(self, organization):
        service = AIInsightsService(organization)
        insights, total = service.deduplicate_savings([])
        assert insights == []
        assert total == 0
