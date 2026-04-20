"""
Base analytics service with shared functionality.

This module provides the BaseAnalyticsService class that all domain-specific
analytics services inherit from. It contains:
- Organization and filter initialization
- Filtered queryset building
- Fiscal year/month utilities
"""
from datetime import datetime
from apps.procurement.models import Transaction


class BaseAnalyticsService:
    """
    Base class for all analytics services with shared query building.

    Provides common functionality:
    - Transaction queryset scoped to organization
    - Filter application (dates, suppliers, categories, amounts)
    - Fiscal year/month calculations

    All domain-specific analytics services should inherit from this class.
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
        self.transactions = self._build_filtered_queryset()

    def _build_filtered_queryset(self):
        """Build transaction queryset with applied filters."""
        qs = Transaction.objects.filter(organization=self.organization)

        # Date range filters
        if date_from := self.filters.get('date_from'):
            if isinstance(date_from, str):
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            qs = qs.filter(date__gte=date_from)

        if date_to := self.filters.get('date_to'):
            if isinstance(date_to, str):
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            qs = qs.filter(date__lte=date_to)

        # Supplier filter
        if supplier_ids := self.filters.get('supplier_ids'):
            if isinstance(supplier_ids, list) and supplier_ids:
                qs = qs.filter(supplier_id__in=supplier_ids)

        # Category filter
        if category_ids := self.filters.get('category_ids'):
            if isinstance(category_ids, list) and category_ids:
                qs = qs.filter(category_id__in=category_ids)

        # Subcategory filter (string names)
        if subcategories := self.filters.get('subcategories'):
            if isinstance(subcategories, list) and subcategories:
                qs = qs.filter(subcategory__in=subcategories)

        # Location filter (string names)
        if locations := self.filters.get('locations'):
            if isinstance(locations, list) and locations:
                qs = qs.filter(location__in=locations)

        # Fiscal year filter
        if years := self.filters.get('years'):
            if isinstance(years, list) and years:
                qs = qs.filter(fiscal_year__in=years)

        # Amount range filters
        if min_amount := self.filters.get('min_amount'):
            qs = qs.filter(amount__gte=min_amount)

        if max_amount := self.filters.get('max_amount'):
            qs = qs.filter(amount__lte=max_amount)

        return qs

    def _get_fiscal_year(self, date, use_fiscal_year=True):
        """
        Get fiscal year for a date.
        Fiscal year runs Jul-Jun, so Jul 2024 = FY2025.

        Args:
            date: The date to get fiscal year for
            use_fiscal_year: If False, returns calendar year instead

        Returns:
            int: The fiscal or calendar year
        """
        if not use_fiscal_year:
            return date.year
        # If month >= 7 (July), it's the next fiscal year
        if date.month >= 7:
            return date.year + 1
        return date.year

    def _get_fiscal_month(self, date):
        """
        Get fiscal month number (1-12, where 1 = July, 12 = June).

        Args:
            date: The date to get fiscal month for

        Returns:
            int: Fiscal month (1-12)
        """
        month = date.month
        if month >= 7:
            return month - 6  # Jul=1, Aug=2, ..., Dec=6
        return month + 6  # Jan=7, Feb=8, ..., Jun=12
