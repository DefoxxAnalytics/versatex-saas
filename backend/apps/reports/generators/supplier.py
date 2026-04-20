"""
Supplier Performance Report Generator.
Provides supplier analysis, concentration, and risk metrics.
"""
from .base import BaseReportGenerator


class SupplierPerformanceGenerator(BaseReportGenerator):
    """
    Generates supplier performance reports with rankings,
    concentration analysis, and risk assessment.
    """

    @property
    def report_type(self) -> str:
        return 'supplier_performance'

    @property
    def report_title(self) -> str:
        return 'Supplier Performance Report'

    def generate(self) -> dict:
        """Generate supplier performance data."""
        # Get overview stats
        overview = self.analytics.get_overview_stats()

        # Get supplier breakdown
        suppliers = self.analytics.get_spend_by_supplier()

        # Get Pareto analysis
        pareto = self.analytics.get_pareto_analysis()

        # Get tail spend analysis
        tail_spend = self.analytics.get_tail_spend_analysis(threshold_percentage=20)

        total_spend = overview.get('total_spend', 0)
        supplier_count = overview.get('supplier_count', 0)

        # Calculate concentration metrics
        top_5_spend = sum(s['amount'] for s in suppliers[:5])
        top_10_spend = sum(s['amount'] for s in suppliers[:10])
        top_5_concentration = (top_5_spend / total_spend * 100) if total_spend > 0 else 0
        top_10_concentration = (top_10_spend / total_spend * 100) if total_spend > 0 else 0

        # Calculate HHI (Herfindahl-Hirschman Index)
        hhi = 0
        if total_spend > 0:
            for s in suppliers:
                market_share = (s['amount'] / total_spend) * 100
                hhi += market_share ** 2

        # Classify concentration level
        if hhi < 1500:
            concentration_level = 'Low'
            concentration_risk = 'Healthy supplier diversity'
        elif hhi < 2500:
            concentration_level = 'Moderate'
            concentration_risk = 'Some concentration risk'
        else:
            concentration_level = 'High'
            concentration_risk = 'High dependency on few suppliers'

        # Find suppliers for 80% spend
        suppliers_for_80 = 0
        cumulative = 0
        for p in pareto:
            suppliers_for_80 += 1
            cumulative = p.get('cumulative_percentage', 0)
            if cumulative >= 80:
                break

        # Build detailed supplier list
        supplier_details = []
        for i, s in enumerate(suppliers):
            percentage = (s['amount'] / total_spend * 100) if total_spend > 0 else 0
            # Find cumulative from pareto
            cumulative_pct = pareto[i]['cumulative_percentage'] if i < len(pareto) else 100

            # Classify supplier
            if cumulative_pct <= 80:
                tier = 'Strategic'
            elif cumulative_pct <= 95:
                tier = 'Leverage'
            else:
                tier = 'Tail'

            supplier_details.append({
                'rank': i + 1,
                'supplier': s['supplier'],
                'amount': s['amount'],
                'count': s['count'],
                'percentage': round(percentage, 2),
                'cumulative_percentage': round(cumulative_pct, 2),
                'tier': tier,
            })

        return {
            'metadata': self.get_metadata(),
            'overview': {
                'total_spend': total_spend,
                'supplier_count': supplier_count,
                'transaction_count': overview.get('transaction_count', 0),
            },
            'concentration': {
                'hhi': round(hhi, 2),
                'concentration_level': concentration_level,
                'concentration_risk': concentration_risk,
                'top_5_concentration': round(top_5_concentration, 2),
                'top_10_concentration': round(top_10_concentration, 2),
                'suppliers_for_80_percent': suppliers_for_80,
            },
            'suppliers': supplier_details[:30],  # Top 30 suppliers
            'tail_spend': {
                'tail_supplier_count': tail_spend.get('tail_count', 0),
                'tail_spend_amount': tail_spend.get('tail_spend', 0),
                'tail_spend_percentage': tail_spend.get('tail_percentage', 0),
                'tail_suppliers': tail_spend.get('tail_suppliers', [])[:10],
            },
        }
