"""
Tests for AI Insights service.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from apps.analytics.ai_services import AIInsightsService
from apps.procurement.tests.factories import (
    TransactionFactory, SupplierFactory, CategoryFactory
)


@pytest.mark.django_db
class TestAIInsightsServiceInitialization:
    """Tests for AIInsightsService initialization."""

    def test_initialization_default(self, organization):
        """Test service initialization with default parameters."""
        service = AIInsightsService(organization)
        assert service.organization == organization
        assert service.use_external_ai is False
        assert service.ai_provider == 'anthropic'
        assert service.api_key is None

    def test_initialization_with_external_ai(self, organization):
        """Test service initialization with external AI enabled."""
        service = AIInsightsService(
            organization,
            use_external_ai=True,
            ai_provider='openai',
            api_key='test-key'
        )
        assert service.use_external_ai is True
        assert service.ai_provider == 'openai'
        assert service.api_key == 'test-key'


@pytest.mark.django_db
class TestCostOptimizationInsights:
    """Tests for cost optimization insights."""

    def test_cost_optimization_with_price_variance(self, organization, admin_user):
        """Test detecting price variance across suppliers in same category."""
        category = CategoryFactory(organization=organization, name='IT Equipment')

        # Create suppliers with different pricing
        supplier_cheap = SupplierFactory(organization=organization, name='Cheap Supplier')
        supplier_expensive = SupplierFactory(organization=organization, name='Expensive Supplier')

        # Create transactions - cheap supplier has lower avg transaction
        # Use same subcategory for apples-to-apples comparison
        for i in range(3):
            TransactionFactory(
                organization=organization,
                supplier=supplier_cheap,
                category=category,
                subcategory='Laptops',
                uploaded_by=admin_user,
                amount=Decimal('100.00'),
                invoice_number=f'CHEAP-{i}'
            )

        # Expensive supplier has higher avg transaction (>15% variance)
        for i in range(3):
            TransactionFactory(
                organization=organization,
                supplier=supplier_expensive,
                category=category,
                subcategory='Laptops',
                uploaded_by=admin_user,
                amount=Decimal('200.00'),
                invoice_number=f'EXPENSIVE-{i}'
            )

        service = AIInsightsService(organization)
        insights = service.get_cost_optimization_insights()

        # Should detect price variance
        assert len(insights) >= 1
        cost_insight = insights[0]
        assert cost_insight['type'] == 'cost_optimization'
        assert 'IT Equipment' in cost_insight['title']
        assert cost_insight['potential_savings'] > 0

    def test_cost_optimization_no_variance(self, organization, admin_user):
        """Test no insights when price variance is below threshold."""
        category = CategoryFactory(organization=organization, name='Office Supplies')
        supplier1 = SupplierFactory(organization=organization, name='Supplier 1')
        supplier2 = SupplierFactory(organization=organization, name='Supplier 2')

        # Similar pricing (< 15% variance)
        for i in range(3):
            TransactionFactory(
                organization=organization,
                supplier=supplier1,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('100.00'),
                invoice_number=f'S1-{i}'
            )
            TransactionFactory(
                organization=organization,
                supplier=supplier2,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('105.00'),
                invoice_number=f'S2-{i}'
            )

        service = AIInsightsService(organization)
        insights = service.get_cost_optimization_insights()

        # Should not detect variance for this category
        category_insights = [i for i in insights if 'Office Supplies' in i['title']]
        assert len(category_insights) == 0

    def test_cost_optimization_empty_data(self, organization):
        """Test cost optimization with no data."""
        service = AIInsightsService(organization)
        insights = service.get_cost_optimization_insights()
        assert insights == []


@pytest.mark.django_db
class TestSupplierRiskInsights:
    """Tests for supplier risk analysis insights."""

    def test_supplier_concentration_high(self, organization, category, admin_user):
        """Test detecting high supplier concentration (>30% spend)."""
        # Create one dominant supplier
        dominant_supplier = SupplierFactory(organization=organization, name='Dominant Supplier')
        small_supplier = SupplierFactory(organization=organization, name='Small Supplier')

        # Dominant supplier gets 70% of spend
        for i in range(7):
            TransactionFactory(
                organization=organization,
                supplier=dominant_supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                invoice_number=f'DOM-{i}'
            )

        # Small supplier gets 30%
        for i in range(3):
            TransactionFactory(
                organization=organization,
                supplier=small_supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                invoice_number=f'SMALL-{i}'
            )

        service = AIInsightsService(organization)
        insights = service.get_supplier_risk_insights()

        # Should detect concentration risk
        assert len(insights) >= 1
        risk_insight = insights[0]
        assert risk_insight['type'] == 'risk'
        assert 'Dominant Supplier' in risk_insight['title']
        assert risk_insight['severity'] in ['high', 'critical']

    def test_supplier_concentration_critical(self, organization, category, admin_user):
        """Test critical supplier concentration (>50% spend)."""
        dominant_supplier = SupplierFactory(organization=organization, name='Mega Supplier')
        other_supplier = SupplierFactory(organization=organization, name='Other Supplier')

        # Dominant supplier gets 80% of spend
        for i in range(8):
            TransactionFactory(
                organization=organization,
                supplier=dominant_supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                invoice_number=f'MEGA-{i}'
            )

        for i in range(2):
            TransactionFactory(
                organization=organization,
                supplier=other_supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                invoice_number=f'OTHER-{i}'
            )

        service = AIInsightsService(organization)
        insights = service.get_supplier_risk_insights()

        # Should be critical severity
        mega_insight = [i for i in insights if 'Mega Supplier' in i['title']]
        assert len(mega_insight) >= 1
        assert mega_insight[0]['severity'] == 'critical'

    def test_no_concentration_risk(self, organization, category, admin_user):
        """Test no risk insights when spend is distributed."""
        # Create 5 suppliers with equal spend
        for i in range(5):
            supplier = SupplierFactory(organization=organization, name=f'Equal Supplier {i}')
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                invoice_number=f'EQ-{i}'
            )

        service = AIInsightsService(organization)
        insights = service.get_supplier_risk_insights()

        # No supplier should trigger risk (each has 20% share)
        assert len(insights) == 0

    def test_supplier_risk_empty_data(self, organization):
        """Test supplier risk with no data."""
        service = AIInsightsService(organization)
        insights = service.get_supplier_risk_insights()
        assert insights == []


@pytest.mark.django_db
class TestAnomalyInsights:
    """Tests for anomaly detection insights."""

    def test_anomaly_detection_high_outliers(self, organization, supplier, category, admin_user):
        """Test detecting unusually high transactions."""
        # Create normal transactions
        for i in range(10):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('1000.00'),
                invoice_number=f'NORMAL-{i}'
            )

        # Create high outlier
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('10000.00'),
            invoice_number='OUTLIER-HIGH'
        )

        service = AIInsightsService(organization)
        insights = service.get_anomaly_insights()

        # Should detect anomaly
        assert len(insights) >= 1
        anomaly_insight = insights[0]
        assert anomaly_insight['type'] == 'anomaly'
        assert 'Unusual' in anomaly_insight['title']

    def test_anomaly_detection_sensitivity(self, organization, supplier, category, admin_user):
        """Test anomaly detection with different sensitivity levels."""
        # Create baseline transactions
        for i in range(15):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('1000.00'),
                invoice_number=f'BASE-{i}'
            )

        # Create moderate outlier
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('3000.00'),
            invoice_number='MODERATE-OUTLIER'
        )

        service = AIInsightsService(organization)

        # High sensitivity should detect it
        insights_high = service.get_anomaly_insights(sensitivity=1.5)

        # Low sensitivity may not detect it
        insights_low = service.get_anomaly_insights(sensitivity=3.0)

        # Higher sensitivity should find more or equal anomalies
        assert len(insights_high) >= len(insights_low)

    def test_anomaly_insufficient_data(self, organization, supplier, category, admin_user):
        """Test that anomaly detection requires minimum data points."""
        # Only create 3 transactions (below threshold of 5)
        for i in range(3):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('1000.00'),
                invoice_number=f'FEW-{i}'
            )

        service = AIInsightsService(organization)
        insights = service.get_anomaly_insights()

        # Should not flag with insufficient data
        assert len(insights) == 0

    def test_anomaly_empty_data(self, organization):
        """Test anomaly detection with no data."""
        service = AIInsightsService(organization)
        insights = service.get_anomaly_insights()
        assert insights == []


@pytest.mark.django_db
class TestConsolidationInsights:
    """Tests for supplier consolidation recommendations."""

    def test_consolidation_multiple_suppliers(self, organization, admin_user):
        """Test consolidation recommendation for category with many suppliers."""
        category = CategoryFactory(organization=organization, name='Consolidation Category')

        # Create 5 suppliers in same category and subcategory for apples-to-apples comparison
        for i in range(5):
            supplier = SupplierFactory(organization=organization, name=f'Consol Supplier {i}')
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                subcategory='Office Supplies',
                uploaded_by=admin_user,
                amount=Decimal(str(1000 * (i + 1))),
                invoice_number=f'CONSOL-{i}'
            )

        service = AIInsightsService(organization)
        insights = service.get_consolidation_recommendations()

        # Should recommend consolidation
        assert len(insights) >= 1
        consol_insight = insights[0]
        assert consol_insight['type'] == 'consolidation'
        assert 'Consolidation Category' in consol_insight['title']
        assert consol_insight['potential_savings'] > 0

    def test_no_consolidation_few_suppliers(self, organization, admin_user):
        """Test no consolidation when category has few suppliers."""
        category = CategoryFactory(organization=organization, name='Small Category')

        # Only 2 suppliers (below threshold of 3)
        for i in range(2):
            supplier = SupplierFactory(organization=organization, name=f'Small Cat Supplier {i}')
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('1000.00'),
                invoice_number=f'SMALL-CAT-{i}'
            )

        service = AIInsightsService(organization)
        insights = service.get_consolidation_recommendations()

        # Should not recommend consolidation
        small_cat_insights = [i for i in insights if 'Small Category' in i['title']]
        assert len(small_cat_insights) == 0

    def test_consolidation_empty_data(self, organization):
        """Test consolidation with no data."""
        service = AIInsightsService(organization)
        insights = service.get_consolidation_recommendations()
        assert insights == []


@pytest.mark.django_db
class TestGetAllInsights:
    """Tests for get_all_insights combined method."""

    def test_all_insights_combined(self, organization, admin_user):
        """Test that all insight types are combined correctly."""
        # Create data that will generate various insights
        category = CategoryFactory(organization=organization, name='Mixed Category')

        # Multiple suppliers for consolidation
        for i in range(4):
            supplier = SupplierFactory(organization=organization, name=f'Mixed Supplier {i}')
            # Different amounts for variance
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal(str(1000 * (i + 1))),
                invoice_number=f'MIXED-{i}'
            )

        service = AIInsightsService(organization)
        result = service.get_all_insights()

        assert 'insights' in result
        assert 'summary' in result
        assert 'total_insights' in result['summary']
        assert 'high_priority' in result['summary']
        assert 'total_potential_savings' in result['summary']
        assert 'by_type' in result['summary']

    def test_all_insights_sorted_by_severity(self, organization, admin_user):
        """Test that insights are sorted by severity."""
        category = CategoryFactory(organization=organization, name='Sorted Category')

        # Create dominant supplier for critical risk
        dominant = SupplierFactory(organization=organization, name='Dominant Sorted')
        for i in range(10):
            TransactionFactory(
                organization=organization,
                supplier=dominant,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                invoice_number=f'DOM-SORTED-{i}'
            )

        service = AIInsightsService(organization)
        result = service.get_all_insights()

        if len(result['insights']) > 1:
            severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            for i in range(len(result['insights']) - 1):
                current_severity = severity_order.get(result['insights'][i]['severity'], 4)
                next_severity = severity_order.get(result['insights'][i + 1]['severity'], 4)
                # Allow equal or increasing severity order
                assert current_severity <= next_severity or \
                       result['insights'][i].get('potential_savings', 0) >= result['insights'][i + 1].get('potential_savings', 0)

    def test_all_insights_empty_data(self, organization):
        """Test all insights with no data."""
        service = AIInsightsService(organization)
        result = service.get_all_insights()

        assert result['insights'] == []
        assert result['summary']['total_insights'] == 0
        assert result['summary']['high_priority'] == 0
        assert result['summary']['total_potential_savings'] == 0


@pytest.mark.django_db
class TestGetInsightsByType:
    """Tests for get_insights_by_type method."""

    def test_get_cost_insights(self, organization):
        """Test getting cost optimization insights by type."""
        service = AIInsightsService(organization)
        insights = service.get_insights_by_type('cost')
        assert isinstance(insights, list)

    def test_get_risk_insights(self, organization):
        """Test getting risk insights by type."""
        service = AIInsightsService(organization)
        insights = service.get_insights_by_type('risk')
        assert isinstance(insights, list)

    def test_get_anomaly_insights(self, organization):
        """Test getting anomaly insights by type."""
        service = AIInsightsService(organization)
        insights = service.get_insights_by_type('anomalies')
        assert isinstance(insights, list)

    def test_get_consolidation_insights(self, organization):
        """Test getting consolidation insights by type."""
        service = AIInsightsService(organization)
        insights = service.get_insights_by_type('consolidation')
        assert isinstance(insights, list)

    def test_invalid_insight_type(self, organization):
        """Test that invalid insight type raises error."""
        service = AIInsightsService(organization)
        with pytest.raises(ValueError):
            service.get_insights_by_type('invalid_type')


@pytest.mark.django_db
class TestOrganizationScoping:
    """Tests for organization data isolation."""

    def test_insights_scoped_to_organization(
        self, organization, other_organization, admin_user, other_org_user
    ):
        """Test that insights only include data from user's organization."""
        # Create data in main organization
        category1 = CategoryFactory(organization=organization, name='Org Category')
        supplier1 = SupplierFactory(organization=organization, name='Org Supplier')
        for i in range(5):
            TransactionFactory(
                organization=organization,
                supplier=supplier1,
                category=category1,
                uploaded_by=admin_user,
                amount=Decimal('1000.00'),
                invoice_number=f'ORG-{i}'
            )

        # Create data in other organization
        category2 = CategoryFactory(organization=other_organization, name='Other Category')
        supplier2 = SupplierFactory(organization=other_organization, name='Other Supplier')
        for i in range(5):
            TransactionFactory(
                organization=other_organization,
                supplier=supplier2,
                category=category2,
                uploaded_by=other_org_user,
                amount=Decimal('100000.00'),
                invoice_number=f'OTHER-{i}'
            )

        # Get insights for main organization
        service = AIInsightsService(organization)
        result = service.get_all_insights()

        # Should not include other organization's data
        for insight in result['insights']:
            if 'title' in insight:
                assert 'Other Category' not in insight['title']
                assert 'Other Supplier' not in insight['title']


@pytest.mark.django_db
class TestDeduplicateSavings:
    """Tests for savings deduplication logic."""

    def test_deduplication_no_overlap(self, organization):
        """Test deduplication with no overlapping insights."""
        service = AIInsightsService(organization)

        insights = [
            {
                'id': 'insight-1',
                'type': 'cost_optimization',
                'severity': 'high',
                'potential_savings': 1000,
                '_attribution': {
                    'subcategory_keys': [('Category A', 'Subcategory 1')],
                    'supplier_ids': ['sup-1', 'sup-2'],
                    'spend_basis': 5000,
                }
            },
            {
                'id': 'insight-2',
                'type': 'consolidation',
                'severity': 'medium',
                'potential_savings': 500,
                '_attribution': {
                    'subcategory_keys': [('Category B', 'Subcategory 2')],
                    'supplier_ids': ['sup-3', 'sup-4'],
                    'spend_basis': 5000,
                }
            }
        ]

        deduplicated, total = service.deduplicate_savings(insights)

        # No overlap, savings should remain unchanged
        assert total == 1500
        assert len(deduplicated) == 2

    def test_deduplication_with_overlap(self, organization):
        """Test deduplication when insights share entities."""
        service = AIInsightsService(organization)

        # Same subcategory key in both insights
        insights = [
            {
                'id': 'insight-1',
                'type': 'cost_optimization',
                'severity': 'high',
                'potential_savings': 1000,
                '_attribution': {
                    'subcategory_keys': [('Category A', 'Subcategory 1')],
                    'supplier_ids': ['sup-1', 'sup-2'],
                    'spend_basis': 5000,
                }
            },
            {
                'id': 'insight-2',
                'type': 'consolidation',
                'severity': 'medium',
                'potential_savings': 800,
                '_attribution': {
                    'subcategory_keys': [('Category A', 'Subcategory 1')],  # Same as above
                    'supplier_ids': ['sup-1', 'sup-2', 'sup-3'],  # Overlapping suppliers
                    'spend_basis': 5000,
                }
            }
        ]

        deduplicated, total = service.deduplicate_savings(insights)

        # Consolidation should be reduced due to overlap
        cost_opt = next(i for i in deduplicated if i['type'] == 'cost_optimization')
        consolidation = next(i for i in deduplicated if i['type'] == 'consolidation')

        # Cost optimization (higher priority) keeps full savings
        assert cost_opt['potential_savings'] == 1000

        # Consolidation should be reduced (overlap with cost_optimization)
        assert consolidation['potential_savings'] < 800

        # Total should be less than sum of original
        assert total < 1800

    def test_deduplication_priority_order(self, organization):
        """Test that higher priority insights get processed first."""
        service = AIInsightsService(organization)

        insights = [
            {
                'id': 'consolidation',
                'type': 'consolidation',  # Priority 3
                'severity': 'medium',
                'potential_savings': 1000,
                '_attribution': {
                    'subcategory_keys': [('Cat', 'Sub')],
                    'supplier_ids': ['sup-1'],
                    'spend_basis': 10000,
                }
            },
            {
                'id': 'cost_opt',
                'type': 'cost_optimization',  # Priority 2
                'severity': 'high',
                'potential_savings': 500,
                '_attribution': {
                    'subcategory_keys': [('Cat', 'Sub')],
                    'supplier_ids': ['sup-1'],
                    'spend_basis': 5000,
                }
            },
            {
                'id': 'anomaly',
                'type': 'anomaly',  # Priority 1 (highest)
                'severity': 'high',
                'potential_savings': 200,
                '_attribution': {
                    'category_ids': ['cat-1'],
                    'transaction_ids': ['tx-1'],
                    'spend_basis': 1000,
                }
            }
        ]

        deduplicated, total = service.deduplicate_savings(insights)

        # Anomaly (highest priority) should keep full savings
        anomaly = next(i for i in deduplicated if i['type'] == 'anomaly')
        assert anomaly['potential_savings'] == 200

    def test_deduplication_risk_insights_unchanged(self, organization):
        """Test that risk insights (no savings) pass through unchanged."""
        service = AIInsightsService(organization)

        insights = [
            {
                'id': 'risk-1',
                'type': 'risk',
                'severity': 'high',
                'potential_savings': None,
            }
        ]

        deduplicated, total = service.deduplicate_savings(insights)

        assert len(deduplicated) == 1
        assert total == 0
        risk = deduplicated[0]
        # _original_savings is 0 because None is converted to 0 in calculation
        assert risk['_original_savings'] == 0

    def test_deduplication_no_attribution(self, organization):
        """Test handling of insights without attribution."""
        service = AIInsightsService(organization)

        insights = [
            {
                'id': 'no-attr',
                'type': 'cost_optimization',
                'severity': 'high',
                'potential_savings': 1000,
                # No _attribution field
            }
        ]

        deduplicated, total = service.deduplicate_savings(insights)

        assert len(deduplicated) == 1
        assert deduplicated[0]['potential_savings'] == 1000
        assert deduplicated[0]['_overlap_reduction'] == 0

    def test_get_entity_keys(self, organization):
        """Test entity key extraction from attribution."""
        service = AIInsightsService(organization)

        attribution = {
            'subcategory_keys': [('Category A', 'Subcategory 1')],
            'category_ids': ['cat-uuid-1'],
            'supplier_ids': ['sup-1', 'sup-2'],
        }

        keys = service._get_entity_keys(attribution)

        # Should include all key types
        assert ('subcat', 'Category A', 'Subcategory 1') in keys
        assert ('cat', 'cat-uuid-1') in keys
        assert ('sup', 'sup-1') in keys
        assert ('sup', 'sup-2') in keys

    def test_calculate_overlap_summary(self, organization):
        """Test overlap summary calculation."""
        service = AIInsightsService(organization)

        insights = [
            {
                'potential_savings': 800,
                '_original_savings': 1000,
                '_overlap_reduction': 200,
            },
            {
                'potential_savings': 500,
                '_original_savings': 500,
                '_overlap_reduction': 0,
            }
        ]

        summary = service._calculate_overlap_summary(insights)

        assert summary['total_original_savings'] == 1500
        assert summary['total_adjusted_savings'] == 1300
        assert summary['total_overlap_reduction'] == 200
        assert summary['insights_with_overlap'] == 1
        assert summary['deduplication_percentage'] > 0

    def test_all_insights_includes_deduplication_summary(self, organization, admin_user):
        """Test that get_all_insights includes deduplication metadata."""
        category = CategoryFactory(organization=organization, name='Dedup Category')

        # Create data that generates both cost optimization and consolidation
        for i in range(5):
            supplier = SupplierFactory(organization=organization, name=f'Dedup Supplier {i}')
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                subcategory='Same Subcategory',
                uploaded_by=admin_user,
                amount=Decimal(str(1000 * (i + 1))),
                invoice_number=f'DEDUP-{i}'
            )

        service = AIInsightsService(organization)
        result = service.get_all_insights()

        # Summary should include deduplication info
        assert 'deduplication_applied' in result['summary']
        assert result['summary']['deduplication_applied'] is True
        assert 'overlap_summary' in result['summary']

    def test_all_insights_strips_internal_fields(self, organization, admin_user):
        """Test that internal _attribution fields are stripped from response."""
        category = CategoryFactory(organization=organization, name='Strip Category')
        supplier = SupplierFactory(organization=organization, name='Strip Supplier')

        for i in range(6):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('1000.00'),
                invoice_number=f'STRIP-{i}'
            )

        service = AIInsightsService(organization)
        result = service.get_all_insights()

        # No insight should have _attribution or other underscore-prefixed keys
        for insight in result['insights']:
            for key in insight.keys():
                assert not key.startswith('_'), f"Found internal field: {key}"
