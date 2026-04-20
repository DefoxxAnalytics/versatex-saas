"""
Report generation service.
Orchestrates report generation, rendering, and storage.
"""
import logging
from decimal import Decimal
from datetime import date, datetime
from io import BytesIO
from django.utils import timezone
from apps.analytics.services import AnalyticsService
from .models import Report


def make_json_serializable(obj):
    """
    Recursively convert non-JSON-serializable types to serializable ones.
    Handles Decimal, date, datetime, and other common types.
    """
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(make_json_serializable(item) for item in obj)
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        # Handle model instances or other objects
        return str(obj)
    return obj


from .generators import (
    ExecutiveSummaryGenerator,
    SpendAnalysisGenerator,
    SupplierPerformanceGenerator,
    ParetoReportGenerator,
    ComplianceReportGenerator,
    SavingsOpportunitiesGenerator,
    StratificationReportGenerator,
    SeasonalityReportGenerator,
    YearOverYearReportGenerator,
    TailSpendReportGenerator,
    # P2P Report generators
    PRStatusReportGenerator,
    POComplianceReportGenerator,
    APAgingReportGenerator,
)
from .renderers import PDFRenderer, ExcelRenderer, CSVRenderer

logger = logging.getLogger(__name__)


class ReportingService:
    """
    Service for orchestrating report generation.
    Handles generator selection, data generation, and rendering.
    """

    # Map report types to generators
    GENERATOR_MAP = {
        'executive_summary': ExecutiveSummaryGenerator,
        'spend_analysis': SpendAnalysisGenerator,
        'supplier_performance': SupplierPerformanceGenerator,
        'pareto_analysis': ParetoReportGenerator,
        'contract_compliance': ComplianceReportGenerator,
        'savings_opportunities': SavingsOpportunitiesGenerator,
        'stratification': StratificationReportGenerator,
        'seasonality': SeasonalityReportGenerator,
        'year_over_year': YearOverYearReportGenerator,
        'tail_spend': TailSpendReportGenerator,
        'price_trends': SpendAnalysisGenerator,  # Reuse spend analysis
        'custom': SpendAnalysisGenerator,  # Default to spend analysis
        # P2P Report types
        'p2p_pr_status': PRStatusReportGenerator,
        'p2p_po_compliance': POComplianceReportGenerator,
        'p2p_ap_aging': APAgingReportGenerator,
    }

    # Map formats to renderers
    RENDERER_MAP = {
        'pdf': PDFRenderer,
        'xlsx': ExcelRenderer,
        'csv': CSVRenderer,
    }

    def __init__(self, organization, user=None):
        """
        Initialize service for an organization.

        Args:
            organization: Organization instance
            user: Optional user for ownership tracking
        """
        self.organization = organization
        self.user = user
        self.analytics = AnalyticsService(organization)

    def create_report(
        self,
        report_type,
        report_format='pdf',
        name=None,
        description='',
        period_start=None,
        period_end=None,
        filters=None,
        parameters=None,
    ):
        """
        Create a report record (without generating data).
        Used for async generation.

        Returns:
            Report instance with 'generating' status
        """
        report = Report.objects.create(
            organization=self.organization,
            created_by=self.user,
            report_type=report_type,
            report_format=report_format,
            name=name or '',
            description=description,
            period_start=period_start,
            period_end=period_end,
            filters=filters or {},
            parameters=parameters or {},
            status='generating',
        )
        return report

    def generate_report(
        self,
        report_type,
        report_format='pdf',
        name=None,
        description='',
        period_start=None,
        period_end=None,
        filters=None,
        parameters=None,
    ):
        """
        Generate a report synchronously.

        Returns:
            Report instance with 'completed' status and summary_data populated
        """
        # Create report record
        report = self.create_report(
            report_type=report_type,
            report_format=report_format,
            name=name,
            description=description,
            period_start=period_start,
            period_end=period_end,
            filters=filters,
            parameters=parameters,
        )

        try:
            # Generate data
            summary_data = self._generate_data(
                report_type=report_type,
                period_start=period_start,
                period_end=period_end,
                filters=filters or {},
                parameters=parameters or {},
            )

            # Mark as completed
            report.mark_completed(summary_data)

            return report

        except Exception as e:
            logger.exception(f"Error generating report {report.id}: {e}")
            report.mark_failed(str(e))
            raise

    def generate_report_data(self, report):
        """
        Generate data for an existing report record.
        Used by async tasks.

        Args:
            report: Report instance

        Returns:
            dict: Generated summary_data
        """
        try:
            report.status = 'generating'
            report.save(update_fields=['status'])

            summary_data = self._generate_data(
                report_type=report.report_type,
                period_start=report.period_start,
                period_end=report.period_end,
                filters=report.filters,
                parameters=report.parameters,
            )

            report.mark_completed(summary_data)
            return summary_data

        except Exception as e:
            logger.exception(f"Error generating report {report.id}: {e}")
            report.mark_failed(str(e))
            raise

    def _generate_data(self, report_type, period_start, period_end, filters, parameters):
        """
        Generate report data using the appropriate generator.

        Returns:
            dict: Report data for storage in summary_data
        """
        # Get generator class
        generator_class = self.GENERATOR_MAP.get(report_type)
        if not generator_class:
            raise ValueError(f"Unknown report type: {report_type}")

        # Build filters with date range
        combined_filters = filters.copy()
        if period_start:
            combined_filters['date_from'] = str(period_start)
        if period_end:
            combined_filters['date_to'] = str(period_end)

        # Create generator instance
        generator = generator_class(
            organization=self.organization,
            filters=combined_filters,
            parameters=parameters,
        )

        # Generate data and convert to JSON-serializable format
        data = generator.generate()
        return make_json_serializable(data)

    def render_report(self, report, output_format=None):
        """
        Render a completed report to a file format.

        Args:
            report: Report instance with summary_data
            output_format: Override format (pdf, xlsx, csv)

        Returns:
            tuple: (BytesIO buffer, content_type, filename)
        """
        if report.status != 'completed':
            raise ValueError(f"Report not ready. Status: {report.status}")

        if not report.summary_data:
            raise ValueError("Report has no data")

        # Determine format
        fmt = output_format or report.report_format

        # Get renderer class
        renderer_class = self.RENDERER_MAP.get(fmt)
        if not renderer_class:
            raise ValueError(f"Unknown format: {fmt}")

        # Get organization branding for PDF reports
        branding = None
        if fmt == 'pdf' and hasattr(report.organization, 'get_branding'):
            branding = report.organization.get_branding()

        # Create renderer
        renderer = renderer_class(
            report_data=report.summary_data,
            report_name=report.name,
            branding=branding,
        )

        # Render to buffer
        buffer = renderer.render()
        content_type = renderer.content_type
        filename = renderer.get_filename()

        return buffer, content_type, filename

    def get_report_types(self):
        """
        Get list of available report types with descriptions.
        """
        return [
            {
                'value': choice[0],
                'label': choice[1],
                'description': self._get_type_description(choice[0]),
            }
            for choice in Report.REPORT_TYPE_CHOICES
        ]

    def _get_type_description(self, report_type):
        """Get description for a report type."""
        descriptions = {
            'spend_analysis': 'Detailed breakdown by category, supplier, and time period',
            'supplier_performance': 'Top suppliers, concentration analysis, and risk assessment',
            'savings_opportunities': 'Consolidation opportunities and estimated savings',
            'price_trends': 'Historical price analysis and trends',
            'contract_compliance': 'Maverick spend analysis and policy violations',
            'executive_summary': 'High-level KPIs and strategic insights',
            'pareto_analysis': '80/20 analysis with supplier classifications',
            'stratification': 'Kraljic matrix analysis with strategic, leverage, routine, and tactical segments',
            'seasonality': 'Monthly spending patterns with fiscal year support and savings opportunities',
            'year_over_year': 'Year-over-year comparison with top gainers, decliners, and variance analysis',
            'tail_spend': 'Tail vendor analysis with consolidation opportunities and action plans',
            'custom': 'Custom report with user-defined parameters',
            # P2P Report descriptions
            'p2p_pr_status': 'Purchase requisition workflow analysis with approval metrics and department breakdown',
            'p2p_po_compliance': 'Contract coverage, maverick spend analysis, and PO compliance metrics',
            'p2p_ap_aging': 'Accounts payable aging buckets, DPO trends, and payment performance',
        }
        return descriptions.get(report_type, '')
