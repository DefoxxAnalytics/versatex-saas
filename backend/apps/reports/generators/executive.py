"""
Executive Summary Report Generator.
Provides high-level KPIs and strategic insights.
"""
from .base import BaseReportGenerator


class ExecutiveSummaryGenerator(BaseReportGenerator):
    """
    Generates executive summary reports with key KPIs,
    top suppliers, category breakdown, and trends.
    """

    @property
    def report_type(self) -> str:
        return 'executive_summary'

    @property
    def report_title(self) -> str:
        return 'Executive Summary Report'

    def generate(self) -> dict:
        """Generate executive summary data."""
        # Get overview stats
        overview = self.analytics.get_overview_stats()

        # Get category breakdown (top 10)
        categories = self.analytics.get_spend_by_category()[:10]

        # Get supplier breakdown (top 10)
        suppliers = self.analytics.get_spend_by_supplier()[:10]

        # Get monthly trend
        monthly_trend = self.analytics.get_monthly_trend(months=12)

        # Get Pareto summary (top 5 for 80% spend)
        pareto = self.analytics.get_pareto_analysis()
        pareto_summary = []
        for item in pareto:
            pareto_summary.append(item)
            if item.get('cumulative_percentage', 0) >= 80:
                break

        # Calculate key insights
        total_spend = overview.get('total_spend', 0)
        top_supplier_spend = suppliers[0]['amount'] if suppliers else 0
        top_supplier_concentration = (top_supplier_spend / total_spend * 100) if total_spend > 0 else 0

        return {
            'metadata': self.get_metadata(),
            'overview': {
                'total_spend': overview.get('total_spend', 0),
                'transaction_count': overview.get('transaction_count', 0),
                'supplier_count': overview.get('supplier_count', 0),
                'category_count': overview.get('category_count', 0),
                'avg_transaction': overview.get('avg_transaction', 0),
            },
            'spend_by_category': categories,
            'top_suppliers': suppliers,
            'monthly_trend': monthly_trend,
            'pareto_summary': pareto_summary[:5],
            'insights': {
                'top_supplier_concentration': round(top_supplier_concentration, 1),
                'suppliers_for_80_percent': len(pareto_summary),
                'avg_monthly_spend': sum(m['amount'] for m in monthly_trend) / len(monthly_trend) if monthly_trend else 0,
            },
        }
