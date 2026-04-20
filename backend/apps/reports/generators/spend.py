"""
Spend Analysis Report Generator.
Provides detailed breakdown by category, supplier, and time period.
"""
from .base import BaseReportGenerator


class SpendAnalysisGenerator(BaseReportGenerator):
    """
    Generates spend analysis reports with detailed breakdowns
    by category, supplier, location, and time.
    """

    @property
    def report_type(self) -> str:
        return 'spend_analysis'

    @property
    def report_title(self) -> str:
        return 'Spend Analysis Report'

    def generate(self) -> dict:
        """Generate spend analysis data."""
        # Get overview stats
        overview = self.analytics.get_overview_stats()

        # Get all category data
        categories = self.analytics.get_spend_by_category()

        # Get all supplier data
        suppliers = self.analytics.get_spend_by_supplier()

        # Get monthly trend (full year)
        monthly_trend = self.analytics.get_monthly_trend(months=12)

        # Get stratification data
        stratification = self.analytics.get_spend_stratification()

        # Calculate category statistics
        total_spend = overview.get('total_spend', 0)
        category_stats = []
        for cat in categories:
            percentage = (cat['amount'] / total_spend * 100) if total_spend > 0 else 0
            category_stats.append({
                'category': cat['category'],
                'amount': cat['amount'],
                'count': cat['count'],
                'percentage': round(percentage, 2),
                'avg_transaction': round(cat['amount'] / cat['count'], 2) if cat['count'] > 0 else 0,
            })

        # Calculate supplier statistics
        supplier_stats = []
        for sup in suppliers[:20]:  # Top 20 suppliers
            percentage = (sup['amount'] / total_spend * 100) if total_spend > 0 else 0
            supplier_stats.append({
                'supplier': sup['supplier'],
                'amount': sup['amount'],
                'count': sup['count'],
                'percentage': round(percentage, 2),
                'avg_transaction': round(sup['amount'] / sup['count'], 2) if sup['count'] > 0 else 0,
            })

        # Calculate trend analysis
        trend_analysis = {
            'monthly_data': monthly_trend,
            'total_months': len(monthly_trend),
            'avg_monthly_spend': sum(m['amount'] for m in monthly_trend) / len(monthly_trend) if monthly_trend else 0,
            'highest_month': max(monthly_trend, key=lambda x: x['amount']) if monthly_trend else None,
            'lowest_month': min(monthly_trend, key=lambda x: x['amount']) if monthly_trend else None,
        }

        return {
            'metadata': self.get_metadata(),
            'overview': {
                'total_spend': total_spend,
                'transaction_count': overview.get('transaction_count', 0),
                'supplier_count': overview.get('supplier_count', 0),
                'category_count': overview.get('category_count', 0),
            },
            'spend_by_category': category_stats,
            'spend_by_supplier': supplier_stats,
            'trend_analysis': trend_analysis,
            'stratification': stratification,
        }
