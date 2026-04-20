"""
Trend and consolidation analytics service.

Provides monthly trend analysis and supplier consolidation opportunity identification.
"""
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth

from .base import BaseAnalyticsService


class TrendConsolidationAnalyticsService(BaseAnalyticsService):
    """
    Service for trend analysis and consolidation opportunities.

    Methods:
        get_monthly_trend: Monthly spend trend over time
        get_supplier_consolidation_opportunities: Identify consolidation opportunities
    """

    def get_monthly_trend(self, months=12):
        """
        Get monthly spend trend.

        Args:
            months: Number of months to include (default 12)

        Returns:
            list: Monthly spend data with amount and count
        """
        cutoff_date = datetime.now().date() - timedelta(days=months*30)

        data = self.transactions.filter(
            date__gte=cutoff_date
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('month')

        return [
            {
                'month': item['month'].strftime('%Y-%m'),
                'amount': float(item['total']),
                'count': item['count']
            }
            for item in data
        ]

    def get_supplier_consolidation_opportunities(self):
        """
        Identify opportunities for supplier consolidation.

        Finds categories with multiple suppliers where consolidation
        could yield savings.

        Returns:
            list: Consolidation opportunities with potential savings
        """
        # Find categories with multiple suppliers
        categories_with_multiple = self.transactions.values(
            'category__name',
            'category_id'
        ).annotate(
            supplier_count=Count('supplier', distinct=True),
            total_spend=Sum('amount')
        ).filter(supplier_count__gt=2).order_by('-supplier_count')

        opportunities = []
        for cat in categories_with_multiple:
            # Get suppliers in this category
            suppliers = self.transactions.filter(
                category_id=cat['category_id']
            ).values('supplier__name').annotate(
                spend=Sum('amount')
            ).order_by('-spend')

            opportunities.append({
                'category': cat['category__name'],
                'supplier_count': cat['supplier_count'],
                'total_spend': float(cat['total_spend']),
                'suppliers': [
                    {
                        'name': s['supplier__name'],
                        'spend': float(s['spend'])
                    }
                    for s in suppliers
                ],
                'potential_savings': float(cat['total_spend'] * Decimal('0.10'))  # Estimate 10% savings
            })

        return opportunities
