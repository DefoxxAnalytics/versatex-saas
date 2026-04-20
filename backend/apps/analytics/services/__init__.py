"""
Analytics services package.

This module provides the AnalyticsService facade class that maintains backwards
compatibility while delegating to domain-specific services internally.

Usage:
    from apps.analytics.services import AnalyticsService

    service = AnalyticsService(organization, filters)
    stats = service.get_overview_stats()

For new code, you can also import domain-specific services directly:
    from apps.analytics.services.spend import SpendAnalyticsService
    from apps.analytics.services.pareto import ParetoTailAnalyticsService
"""

from .base import BaseAnalyticsService
from .overview import OverviewAnalyticsService
from .spend import SpendAnalyticsService
from .pareto import ParetoTailAnalyticsService
from .stratification import StratificationAnalyticsService
from .seasonality import SeasonalityAnalyticsService
from .yoy import YearOverYearAnalyticsService
from .trend import TrendConsolidationAnalyticsService
from .constants import SPEND_BANDS, SEGMENTS


class AnalyticsService:
    """
    Facade class maintaining backwards compatibility.

    Delegates to domain-specific services internally. All existing code using
    AnalyticsService will continue to work without modification.

    For new code, consider using domain-specific services directly for better
    organization and testability:
    - OverviewAnalyticsService: get_overview_stats
    - SpendAnalyticsService: spend by category/supplier, drilldowns
    - ParetoTailAnalyticsService: pareto analysis, tail spend
    - StratificationAnalyticsService: spend stratification
    - SeasonalityAnalyticsService: seasonal patterns
    - YearOverYearAnalyticsService: YoY comparisons
    - TrendConsolidationAnalyticsService: trends, consolidation
    """

    def __init__(self, organization, filters=None):
        """
        Initialize analytics service with optional filters.

        Args:
            organization: Organization instance
            filters: Optional dict with filter parameters:
                - date_from: Start date (str 'YYYY-MM-DD' or date)
                - date_to: End date (str 'YYYY-MM-DD' or date)
                - supplier_ids: List of supplier IDs to include
                - category_ids: List of category IDs to include
                - subcategories: List of subcategory names to include
                - locations: List of location names to include
                - years: List of fiscal years to include
                - min_amount: Minimum transaction amount
                - max_amount: Maximum transaction amount
        """
        self.organization = organization
        self.filters = filters or {}

        # Initialize all sub-services
        self._overview = OverviewAnalyticsService(organization, filters)
        self._spend = SpendAnalyticsService(organization, filters)
        self._pareto = ParetoTailAnalyticsService(organization, filters)
        self._stratification = StratificationAnalyticsService(organization, filters)
        self._seasonality = SeasonalityAnalyticsService(organization, filters)
        self._yoy = YearOverYearAnalyticsService(organization, filters)
        self._trend = TrendConsolidationAnalyticsService(organization, filters)

        # Expose transactions queryset for backwards compatibility
        # (some consumers access service.transactions directly)
        self.transactions = self._overview.transactions

    # =========================================================================
    # Overview methods (delegated to OverviewAnalyticsService)
    # =========================================================================

    def get_overview_stats(self):
        """Get overview statistics."""
        return self._overview.get_overview_stats()

    # =========================================================================
    # Spend methods (delegated to SpendAnalyticsService)
    # =========================================================================

    def get_spend_by_category(self):
        """Get spend breakdown by category."""
        return self._spend.get_spend_by_category()

    def get_spend_by_supplier(self):
        """Get spend breakdown by supplier."""
        return self._spend.get_spend_by_supplier()

    def get_detailed_category_analysis(self):
        """Get detailed category analysis."""
        return self._spend.get_detailed_category_analysis()

    def get_detailed_supplier_analysis(self):
        """Get detailed supplier analysis with HHI."""
        return self._spend.get_detailed_supplier_analysis()

    def get_supplier_drilldown(self, supplier_id):
        """Get supplier drill-down data."""
        return self._spend.get_supplier_drilldown(supplier_id)

    def get_category_drilldown(self, category_id):
        """Get category drill-down data for Overview page."""
        return self._spend.get_category_drilldown(category_id)

    # =========================================================================
    # Pareto and Tail Spend methods (delegated to ParetoTailAnalyticsService)
    # =========================================================================

    def get_pareto_analysis(self):
        """Get Pareto analysis (80/20 rule)."""
        return self._pareto.get_pareto_analysis()

    def get_tail_spend_analysis(self, threshold_percentage=20):
        """Analyze tail spend (bottom X% of suppliers)."""
        return self._pareto.get_tail_spend_analysis(threshold_percentage)

    def get_detailed_tail_spend(self, threshold=50000):
        """Get detailed tail spend analysis."""
        return self._pareto.get_detailed_tail_spend(threshold)

    def get_tail_spend_category_drilldown(self, category_id, threshold=50000):
        """Get tail spend drill-down for a category."""
        return self._pareto.get_tail_spend_category_drilldown(category_id, threshold)

    def get_tail_spend_vendor_drilldown(self, supplier_id, threshold=50000):
        """Get tail spend drill-down for a vendor."""
        return self._pareto.get_tail_spend_vendor_drilldown(supplier_id, threshold)

    # =========================================================================
    # Stratification methods (delegated to StratificationAnalyticsService)
    # =========================================================================

    def get_spend_stratification(self):
        """Get Kraljic matrix stratification."""
        return self._stratification.get_spend_stratification()

    def get_detailed_stratification(self):
        """Get detailed stratification analysis."""
        return self._stratification.get_detailed_stratification()

    def get_stratification_segment_drilldown(self, segment_name):
        """Get drill-down for a stratification segment."""
        return self._stratification.get_stratification_segment_drilldown(segment_name)

    def get_stratification_band_drilldown(self, band_name):
        """Get drill-down for a spend band."""
        return self._stratification.get_stratification_band_drilldown(band_name)

    # =========================================================================
    # Seasonality methods (delegated to SeasonalityAnalyticsService)
    # =========================================================================

    def get_seasonality_analysis(self):
        """Get basic seasonality analysis."""
        return self._seasonality.get_seasonality_analysis()

    def get_detailed_seasonality_analysis(self, use_fiscal_year=True):
        """Get detailed seasonality with fiscal year support."""
        return self._seasonality.get_detailed_seasonality_analysis(use_fiscal_year)

    def get_seasonality_category_drilldown(self, category_id, use_fiscal_year=True):
        """Get seasonality drill-down for a category."""
        return self._seasonality.get_seasonality_category_drilldown(category_id, use_fiscal_year)

    # =========================================================================
    # Year-over-Year methods (delegated to YearOverYearAnalyticsService)
    # =========================================================================

    def get_year_over_year_comparison(self):
        """Get basic YoY comparison."""
        return self._yoy.get_year_over_year_comparison()

    def get_detailed_year_over_year(self, year1=None, year2=None, use_fiscal_year=True):
        """Get detailed YoY comparison."""
        return self._yoy.get_detailed_year_over_year(year1, year2, use_fiscal_year)

    def get_yoy_category_drilldown(self, category_id, year1=None, year2=None, use_fiscal_year=True):
        """Get YoY drill-down for a category."""
        return self._yoy.get_yoy_category_drilldown(category_id, year1, year2, use_fiscal_year)

    def get_yoy_supplier_drilldown(self, supplier_id, year1=None, year2=None, use_fiscal_year=True):
        """Get YoY drill-down for a supplier."""
        return self._yoy.get_yoy_supplier_drilldown(supplier_id, year1, year2, use_fiscal_year)

    # =========================================================================
    # Trend and Consolidation methods (delegated to TrendConsolidationAnalyticsService)
    # =========================================================================

    def get_monthly_trend(self, months=12):
        """Get monthly spend trend."""
        return self._trend.get_monthly_trend(months)

    def get_supplier_consolidation_opportunities(self):
        """Identify supplier consolidation opportunities."""
        return self._trend.get_supplier_consolidation_opportunities()

    # =========================================================================
    # Helper methods (for backwards compatibility)
    # =========================================================================

    def _build_filtered_queryset(self):
        """Build filtered queryset (exposed for backwards compatibility)."""
        return self._overview._build_filtered_queryset()

    def _get_fiscal_year(self, date, use_fiscal_year=True):
        """Get fiscal year for a date."""
        return self._overview._get_fiscal_year(date, use_fiscal_year)

    def _get_fiscal_month(self, date):
        """Get fiscal month number."""
        return self._overview._get_fiscal_month(date)


# Export commonly used items
__all__ = [
    'AnalyticsService',
    'BaseAnalyticsService',
    'OverviewAnalyticsService',
    'SpendAnalyticsService',
    'ParetoTailAnalyticsService',
    'StratificationAnalyticsService',
    'SeasonalityAnalyticsService',
    'YearOverYearAnalyticsService',
    'TrendConsolidationAnalyticsService',
    'SPEND_BANDS',
    'SEGMENTS',
]
