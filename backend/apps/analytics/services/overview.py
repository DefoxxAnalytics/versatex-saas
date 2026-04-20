"""
Overview analytics service.

Provides high-level statistics and summary metrics for the analytics dashboard.
"""
from django.db.models import Sum, Count, Avg
from .base import BaseAnalyticsService


class OverviewAnalyticsService(BaseAnalyticsService):
    """
    Service for overview/summary analytics.

    Methods:
        get_overview_stats: Get high-level dashboard statistics
    """

    def get_overview_stats(self):
        """
        Get overview statistics for the dashboard.

        Returns:
            dict: Overview statistics including:
                - total_spend: Total spend amount
                - transaction_count: Number of transactions
                - supplier_count: Number of unique suppliers
                - category_count: Number of unique categories
                - avg_transaction: Average transaction amount
        """
        stats = self.transactions.aggregate(
            total_spend=Sum('amount'),
            transaction_count=Count('id'),
            supplier_count=Count('supplier', distinct=True),
            category_count=Count('category', distinct=True),
            avg_transaction=Avg('amount')
        )

        return {
            'total_spend': float(stats['total_spend'] or 0),
            'transaction_count': stats['transaction_count'] or 0,
            'supplier_count': stats['supplier_count'] or 0,
            'category_count': stats['category_count'] or 0,
            'avg_transaction': float(stats['avg_transaction'] or 0)
        }
