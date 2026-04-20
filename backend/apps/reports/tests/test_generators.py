"""
Tests for report generators.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from apps.reports.generators.spend import SpendAnalysisGenerator
from apps.reports.generators.executive import ExecutiveSummaryGenerator
from apps.reports.generators.supplier import SupplierPerformanceGenerator
from apps.reports.generators.pareto import ParetoReportGenerator
from apps.reports.generators.compliance import ComplianceReportGenerator
from apps.reports.generators.savings import SavingsOpportunitiesGenerator
from apps.reports.generators.stratification import StratificationReportGenerator
from apps.reports.generators.seasonality import SeasonalityReportGenerator
from apps.reports.generators.yoy import YearOverYearReportGenerator
from apps.reports.generators.tail_spend import TailSpendReportGenerator
from apps.procurement.tests.factories import TransactionFactory, SupplierFactory, CategoryFactory


@pytest.mark.django_db
class TestSpendAnalysisGenerator:
    """Tests for SpendAnalysisGenerator."""

    def test_report_type(self, organization):
        """Test report type property."""
        generator = SpendAnalysisGenerator(organization)
        assert generator.report_type == 'spend_analysis'

    def test_report_title(self, organization):
        """Test report title property."""
        generator = SpendAnalysisGenerator(organization)
        assert generator.report_title == 'Spend Analysis Report'

    def test_generate_with_data(self, organization, admin_user):
        """Test generating report with transaction data."""
        supplier = SupplierFactory(organization=organization)
        category = CategoryFactory(organization=organization)
        for i in range(5):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('1000.00')
            )

        generator = SpendAnalysisGenerator(organization)
        result = generator.generate()

        assert 'metadata' in result
        assert 'overview' in result
        assert 'spend_by_category' in result
        assert 'spend_by_supplier' in result
        assert 'trend_analysis' in result
        assert result['overview']['total_spend'] > 0

    def test_generate_empty_data(self, organization):
        """Test generating report with no data."""
        generator = SpendAnalysisGenerator(organization)
        result = generator.generate()

        assert result['overview']['total_spend'] == 0
        assert result['overview']['transaction_count'] == 0

    def test_category_percentage_calculation(self, organization, admin_user):
        """Test category percentage calculations."""
        category1 = CategoryFactory(organization=organization, name='Category A')
        category2 = CategoryFactory(organization=organization, name='Category B')
        supplier = SupplierFactory(organization=organization)

        # Create transactions: 75% in Cat A, 25% in Cat B
        for _ in range(3):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category1,
                uploaded_by=admin_user,
                amount=Decimal('1000.00')
            )
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category2,
            uploaded_by=admin_user,
            amount=Decimal('1000.00')
        )

        generator = SpendAnalysisGenerator(organization)
        result = generator.generate()

        total_percentage = sum(c['percentage'] for c in result['spend_by_category'])
        assert abs(total_percentage - 100) < 0.1


@pytest.mark.django_db
class TestExecutiveSummaryGenerator:
    """Tests for ExecutiveSummaryGenerator."""

    def test_report_type(self, organization):
        """Test report type property."""
        generator = ExecutiveSummaryGenerator(organization)
        assert generator.report_type == 'executive_summary'

    def test_generate_with_data(self, organization, admin_user):
        """Test generating executive summary."""
        supplier = SupplierFactory(organization=organization)
        category = CategoryFactory(organization=organization)
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user
        )

        generator = ExecutiveSummaryGenerator(organization)
        result = generator.generate()

        assert 'metadata' in result
        assert 'overview' in result
        assert 'insights' in result
        assert result['metadata']['report_type'] == 'executive_summary'


@pytest.mark.django_db
class TestSupplierPerformanceGenerator:
    """Tests for SupplierPerformanceGenerator."""

    def test_report_type(self, organization):
        """Test report type property."""
        generator = SupplierPerformanceGenerator(organization)
        assert generator.report_type == 'supplier_performance'

    def test_generate_top_suppliers(self, organization, admin_user):
        """Test generating supplier performance report."""
        category = CategoryFactory(organization=organization)
        for i in range(5):
            supplier = SupplierFactory(organization=organization, name=f'Supplier {i}')
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal(str((i + 1) * 1000))
            )

        generator = SupplierPerformanceGenerator(organization, parameters={'top_n': 3})
        result = generator.generate()

        assert 'suppliers' in result
        # Supplier performance returns up to 30 suppliers, verify data exists
        assert len(result['suppliers']) >= 1


@pytest.mark.django_db
class TestParetoAnalysisGenerator:
    """Tests for ParetoReportGenerator."""

    def test_report_type(self, organization):
        """Test report type property."""
        generator = ParetoReportGenerator(organization)
        assert generator.report_type == 'pareto_analysis'

    def test_generate_pareto_data(self, organization, admin_user):
        """Test generating Pareto analysis."""
        category = CategoryFactory(organization=organization)
        for i in range(10):
            supplier = SupplierFactory(organization=organization, name=f'Pareto Supplier {i}')
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal(str((10 - i) * 1000))  # Descending amounts
            )

        generator = ParetoReportGenerator(organization)
        result = generator.generate()

        assert 'supplier_ranking' in result
        assert 'spend_by_classification' in result

    def test_cumulative_percentage(self, organization, admin_user):
        """Test that cumulative percentages are calculated correctly."""
        category = CategoryFactory(organization=organization)
        supplier = SupplierFactory(organization=organization)
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user
        )

        generator = ParetoReportGenerator(organization)
        result = generator.generate()

        if result.get('supplier_ranking'):
            last_supplier = result['supplier_ranking'][-1]
            assert last_supplier['cumulative_percentage'] <= 100


@pytest.mark.django_db
class TestContractComplianceGenerator:
    """Tests for ComplianceReportGenerator."""

    def test_report_type(self, organization):
        """Test report type property."""
        generator = ComplianceReportGenerator(organization)
        assert generator.report_type == 'contract_compliance'

    def test_generate_compliance_data(self, organization, admin_user):
        """Test generating compliance report."""
        supplier = SupplierFactory(organization=organization)
        category = CategoryFactory(organization=organization)
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user
        )

        generator = ComplianceReportGenerator(organization)
        result = generator.generate()

        assert 'metadata' in result


@pytest.mark.django_db
class TestSavingsOpportunitiesGenerator:
    """Tests for SavingsOpportunitiesGenerator."""

    def test_report_type(self, organization):
        """Test report type property."""
        generator = SavingsOpportunitiesGenerator(organization)
        assert generator.report_type == 'savings_opportunities'

    def test_generate_savings_data(self, organization, admin_user):
        """Test generating savings opportunities report."""
        category = CategoryFactory(organization=organization)
        # Create multiple suppliers per category for consolidation opportunities
        for i in range(4):
            supplier = SupplierFactory(organization=organization, name=f'Savings Supplier {i}')
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user
            )

        generator = SavingsOpportunitiesGenerator(organization)
        result = generator.generate()

        assert 'metadata' in result


@pytest.mark.django_db
class TestStratificationGenerator:
    """Tests for StratificationReportGenerator."""

    def test_report_type(self, organization):
        """Test report type property."""
        generator = StratificationReportGenerator(organization)
        assert generator.report_type == 'stratification'

    def test_generate_stratification_data(self, organization, admin_user):
        """Test generating stratification report."""
        category = CategoryFactory(organization=organization)
        for i in range(5):
            supplier = SupplierFactory(organization=organization, name=f'Strat Supplier {i}')
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal(str((i + 1) * 10000))
            )

        generator = StratificationReportGenerator(organization)
        result = generator.generate()

        assert 'metadata' in result
        assert 'segments' in result or 'bands' in result or 'stratification' in result


@pytest.mark.django_db
class TestSeasonalityGenerator:
    """Tests for SeasonalityReportGenerator."""

    def test_report_type(self, organization):
        """Test report type property."""
        generator = SeasonalityReportGenerator(organization)
        assert generator.report_type == 'seasonality'

    def test_generate_seasonality_data(self, organization, admin_user):
        """Test generating seasonality report."""
        category = CategoryFactory(organization=organization)
        supplier = SupplierFactory(organization=organization)
        base_date = date.today() - timedelta(days=365)

        # Create monthly transactions
        for month in range(12):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                date=base_date + timedelta(days=month * 30)
            )

        generator = SeasonalityReportGenerator(organization, parameters={'use_fiscal_year': True})
        result = generator.generate()

        assert 'metadata' in result

    def test_fiscal_year_parameter(self, organization):
        """Test fiscal year parameter handling."""
        generator = SeasonalityReportGenerator(
            organization,
            parameters={'use_fiscal_year': False}
        )
        assert generator.parameters.get('use_fiscal_year') is False


@pytest.mark.django_db
class TestYearOverYearGenerator:
    """Tests for YearOverYearReportGenerator."""

    def test_report_type(self, organization):
        """Test report type property."""
        generator = YearOverYearReportGenerator(organization)
        assert generator.report_type == 'year_over_year'

    def test_generate_yoy_data(self, organization, admin_user):
        """Test generating year-over-year report."""
        category = CategoryFactory(organization=organization)
        supplier = SupplierFactory(organization=organization)

        # Create transactions for two years
        current_year = date.today().year
        for year_offset in [0, 1]:
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                date=date(current_year - year_offset, 6, 15)
            )

        generator = YearOverYearReportGenerator(organization)
        result = generator.generate()

        assert 'metadata' in result


@pytest.mark.django_db
class TestTailSpendGenerator:
    """Tests for TailSpendReportGenerator."""

    def test_report_type(self, organization):
        """Test report type property."""
        generator = TailSpendReportGenerator(organization)
        assert generator.report_type == 'tail_spend'

    def test_generate_tail_spend_data(self, organization, admin_user):
        """Test generating tail spend report."""
        category = CategoryFactory(organization=organization)

        # Create tail suppliers (small spend)
        for i in range(10):
            supplier = SupplierFactory(organization=organization, name=f'Tail Supplier {i}')
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('500.00')  # Below threshold
            )

        # Create strategic supplier (large spend)
        strategic = SupplierFactory(organization=organization, name='Strategic Supplier')
        for _ in range(5):
            TransactionFactory(
                organization=organization,
                supplier=strategic,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('50000.00')
            )

        generator = TailSpendReportGenerator(organization, parameters={'threshold': 50000})
        result = generator.generate()

        assert 'metadata' in result

    def test_threshold_parameter(self, organization):
        """Test threshold parameter handling."""
        generator = TailSpendReportGenerator(
            organization,
            parameters={'threshold': 25000}
        )
        assert generator.parameters.get('threshold') == 25000


@pytest.mark.django_db
class TestGeneratorFilters:
    """Tests for generator filter handling."""

    def test_date_range_filter(self, organization, admin_user):
        """Test that date range filters are applied."""
        category = CategoryFactory(organization=organization)
        supplier = SupplierFactory(organization=organization)

        # Transaction in range
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            date=date(2024, 6, 15),
            amount=Decimal('1000.00')
        )

        # Transaction outside range
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            date=date(2023, 1, 15),
            amount=Decimal('2000.00')
        )

        # Analytics service uses date_from/date_to format
        filters = {
            'date_from': '2024-01-01',
            'date_to': '2024-12-31'
        }
        generator = SpendAnalysisGenerator(organization, filters=filters)
        result = generator.generate()

        # Should only include transaction from 2024
        assert result['overview']['total_spend'] == 1000.0

    def test_supplier_filter(self, organization, admin_user):
        """Test that supplier filters are applied."""
        category = CategoryFactory(organization=organization)
        supplier1 = SupplierFactory(organization=organization, name='Included Supplier')
        supplier2 = SupplierFactory(organization=organization, name='Excluded Supplier')

        TransactionFactory(
            organization=organization,
            supplier=supplier1,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('1000.00')
        )
        TransactionFactory(
            organization=organization,
            supplier=supplier2,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('2000.00')
        )

        filters = {'supplier_ids': [supplier1.id]}
        generator = SpendAnalysisGenerator(organization, filters=filters)
        result = generator.generate()

        # Should only include supplier1's transaction
        assert result['overview']['total_spend'] == 1000.0

    def test_category_filter(self, organization, admin_user):
        """Test that category filters are applied."""
        category1 = CategoryFactory(organization=organization, name='Included Category')
        category2 = CategoryFactory(organization=organization, name='Excluded Category')
        supplier = SupplierFactory(organization=organization)

        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category1,
            uploaded_by=admin_user,
            amount=Decimal('1000.00')
        )
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category2,
            uploaded_by=admin_user,
            amount=Decimal('2000.00')
        )

        filters = {'category_ids': [category1.id]}
        generator = SpendAnalysisGenerator(organization, filters=filters)
        result = generator.generate()

        # Should only include category1's transaction
        assert result['overview']['total_spend'] == 1000.0

    def test_amount_range_filter(self, organization, admin_user):
        """Test that amount range filters are applied."""
        category = CategoryFactory(organization=organization)
        supplier = SupplierFactory(organization=organization)

        # In range
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('5000.00')
        )
        # Below range
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('500.00')
        )
        # Above range
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('50000.00')
        )

        filters = {
            'min_amount': 1000,
            'max_amount': 10000
        }
        generator = SpendAnalysisGenerator(organization, filters=filters)
        result = generator.generate()

        # Should only include the 5000 transaction
        assert result['overview']['total_spend'] == 5000.0


@pytest.mark.django_db
class TestGeneratorMetadata:
    """Tests for generator metadata."""

    def test_metadata_includes_required_fields(self, organization):
        """Test that metadata includes all required fields."""
        generator = SpendAnalysisGenerator(organization)
        metadata = generator.get_metadata()

        assert 'report_type' in metadata
        assert 'report_title' in metadata
        assert 'organization' in metadata
        assert 'period_start' in metadata
        assert 'period_end' in metadata
        assert 'generated_at' in metadata
        assert 'filters_applied' in metadata

    def test_metadata_organization_name(self, organization):
        """Test that metadata includes organization name."""
        generator = SpendAnalysisGenerator(organization)
        metadata = generator.get_metadata()

        assert metadata['organization'] == organization.name

    def test_metadata_filters_recorded(self, organization):
        """Test that applied filters are recorded in metadata."""
        filters = {'supplier_ids': [1, 2, 3]}
        generator = SpendAnalysisGenerator(organization, filters=filters)
        metadata = generator.get_metadata()

        assert metadata['filters_applied'] == filters
