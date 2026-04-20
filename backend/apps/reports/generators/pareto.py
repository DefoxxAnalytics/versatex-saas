"""
Pareto Analysis Report Generator.
Provides 80/20 rule analysis with strategic recommendations.
"""
from .base import BaseReportGenerator


class ParetoReportGenerator(BaseReportGenerator):
    """
    Generates Pareto analysis reports showing the 80/20 rule
    with supplier classifications and recommendations.
    """

    @property
    def report_type(self) -> str:
        return 'pareto_analysis'

    @property
    def report_title(self) -> str:
        return 'Pareto Analysis Report'

    def generate(self) -> dict:
        """Generate Pareto analysis data."""
        # Get overview stats
        overview = self.analytics.get_overview_stats()

        # Get Pareto analysis from analytics service
        pareto_data = self.analytics.get_pareto_analysis()

        total_spend = overview.get('total_spend', 0)
        total_suppliers = len(pareto_data)

        # Classify suppliers into groups
        critical_suppliers = []  # 80% spend
        important_suppliers = []  # 80-95% spend
        standard_suppliers = []  # 95%+ spend

        suppliers_for_80 = 0
        suppliers_for_90 = 0
        suppliers_for_95 = 0

        for item in pareto_data:
            cumulative = item.get('cumulative_percentage', 0)

            # Determine classification and recommendations
            if cumulative <= 80:
                classification = 'Critical (80%)'
                priority = 'Strategic'
                recommended_action = 'Partnership Development'
                critical_suppliers.append(item)
                suppliers_for_80 += 1
                suppliers_for_90 += 1
                suppliers_for_95 += 1
            elif cumulative <= 90:
                classification = 'Important (90%)'
                priority = 'Tactical'
                recommended_action = 'Performance Monitoring'
                important_suppliers.append(item)
                suppliers_for_90 += 1
                suppliers_for_95 += 1
            elif cumulative <= 95:
                classification = 'Standard'
                priority = 'Operational'
                recommended_action = 'Regular Review'
                standard_suppliers.append(item)
                suppliers_for_95 += 1
            else:
                classification = 'Low Impact'
                priority = 'Minimal'
                recommended_action = 'Consolidation Review'

            item['classification'] = classification
            item['priority'] = priority
            item['recommended_action'] = recommended_action

        # Calculate efficiency ratio
        efficiency_ratio = (suppliers_for_80 / total_suppliers * 100) if total_suppliers > 0 else 0

        # Calculate spend by classification
        critical_spend = sum(s['amount'] for s in critical_suppliers)
        important_spend = sum(s['amount'] for s in important_suppliers)
        standard_spend = sum(s['amount'] for s in standard_suppliers)
        tail_spend = total_spend - critical_spend - important_spend - standard_spend

        # Generate strategic recommendations
        recommendations = []
        if efficiency_ratio < 10:
            recommendations.append({
                'type': 'opportunity',
                'title': 'Strong Supplier Concentration',
                'description': f'Only {suppliers_for_80} suppliers account for 80% of spend. Focus on strengthening these partnerships.',
            })
        if efficiency_ratio > 30:
            recommendations.append({
                'type': 'warning',
                'title': 'High Supplier Fragmentation',
                'description': f'{suppliers_for_80} suppliers needed for 80% of spend. Consider consolidation opportunities.',
            })
        if total_suppliers - suppliers_for_95 > 10:
            recommendations.append({
                'type': 'opportunity',
                'title': 'Tail Spend Opportunity',
                'description': f'{total_suppliers - suppliers_for_95} suppliers in tail spend. Review for consolidation or elimination.',
            })

        return {
            'metadata': self.get_metadata(),
            'overview': {
                'total_spend': total_spend,
                'total_suppliers': total_suppliers,
                'transaction_count': overview.get('transaction_count', 0),
            },
            'pareto_metrics': {
                'suppliers_for_80_percent': suppliers_for_80,
                'suppliers_for_90_percent': suppliers_for_90,
                'suppliers_for_95_percent': suppliers_for_95,
                'efficiency_ratio': round(efficiency_ratio, 2),
            },
            'spend_by_classification': {
                'critical': {
                    'supplier_count': len(critical_suppliers),
                    'spend': critical_spend,
                    'percentage': round((critical_spend / total_spend * 100) if total_spend > 0 else 0, 2),
                },
                'important': {
                    'supplier_count': len(important_suppliers),
                    'spend': important_spend,
                    'percentage': round((important_spend / total_spend * 100) if total_spend > 0 else 0, 2),
                },
                'standard': {
                    'supplier_count': len(standard_suppliers),
                    'spend': standard_spend,
                    'percentage': round((standard_spend / total_spend * 100) if total_spend > 0 else 0, 2),
                },
                'tail': {
                    'supplier_count': total_suppliers - suppliers_for_95,
                    'spend': tail_spend,
                    'percentage': round((tail_spend / total_spend * 100) if total_spend > 0 else 0, 2),
                },
            },
            'supplier_ranking': pareto_data[:30],  # Top 30 with classifications
            'recommendations': recommendations,
        }
