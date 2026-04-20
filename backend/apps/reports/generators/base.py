"""
Base report generator class.
All report generators inherit from this class.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from django.utils import timezone
from apps.analytics.services import AnalyticsService


class BaseReportGenerator(ABC):
    """
    Abstract base class for all report generators.
    Provides common functionality and defines interface.
    """

    def __init__(self, organization, filters=None, parameters=None):
        """
        Initialize generator with organization and optional filters.

        Args:
            organization: Organization instance
            filters: Dict of filter parameters:
                - date_from/date_to: Date range for transactions
                - supplier_ids: List of supplier IDs to include
                - category_ids: List of category IDs to include
                - min_amount/max_amount: Amount range filter
            parameters: Dict of additional parameters (include_charts, sections, etc.)
        """
        self.organization = organization
        self.filters = filters or {}
        self.parameters = parameters or {}
        # Pass filters to analytics service for filtered queries
        self.analytics = AnalyticsService(organization, filters=self.filters)

    @property
    @abstractmethod
    def report_type(self) -> str:
        """Return the report type identifier."""
        pass

    @property
    @abstractmethod
    def report_title(self) -> str:
        """Return human-readable report title."""
        pass

    @abstractmethod
    def generate(self) -> dict:
        """
        Generate the report data.

        Returns:
            dict: Report data to be stored in summary_data
        """
        pass

    def get_date_range(self):
        """
        Get date range from filters or default to last 30 days.

        Returns:
            tuple: (start_date, end_date)
        """
        date_range = self.filters.get('date_range', {})
        end_date = date_range.get('end')
        start_date = date_range.get('start')

        if not end_date:
            end_date = timezone.now().date()
        elif isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        if not start_date:
            start_date = end_date - timedelta(days=30)
        elif isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

        return start_date, end_date

    def get_metadata(self) -> dict:
        """
        Get common metadata for the report.

        Returns:
            dict: Report metadata
        """
        start_date, end_date = self.get_date_range()
        return {
            'report_type': self.report_type,
            'report_title': self.report_title,
            'organization': self.organization.name,
            'period_start': str(start_date),
            'period_end': str(end_date),
            'generated_at': timezone.now().isoformat(),
            'filters_applied': self.filters,
        }
