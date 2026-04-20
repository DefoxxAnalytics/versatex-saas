"""
Savings Opportunities Report Generator.
Identifies potential cost savings and optimization opportunities.
"""
from .base import BaseReportGenerator


class SavingsOpportunitiesGenerator(BaseReportGenerator):
    """
    Generates savings opportunity reports with price benchmarking,
    consolidation opportunities, and estimated savings.
    """

    @property
    def report_type(self) -> str:
        return 'savings_opportunities'

    @property
    def report_title(self) -> str:
        return 'Savings Opportunities Report'

    def generate(self) -> dict:
        """Generate savings opportunities data."""
        # Get overview stats
        overview = self.analytics.get_overview_stats()
        total_spend = overview.get('total_spend', 0)

        # Get supplier and category data
        suppliers = self.analytics.get_spend_by_supplier()
        categories = self.analytics.get_spend_by_category()

        # Get tail spend
        tail_spend = self.analytics.get_tail_spend_analysis(threshold_percentage=20)

        # Get stratification
        stratification = self.analytics.get_spend_stratification()

        # Calculate consolidation opportunities
        # Suppliers with low spend but multiple transactions = consolidation target
        consolidation_opportunities = []
        for s in suppliers:
            avg_transaction = s['amount'] / s['count'] if s['count'] > 0 else 0
            if s['count'] >= 3 and s['amount'] < total_spend * 0.01:  # Small supplier, multiple transactions
                estimated_savings = s['amount'] * 0.15  # Assume 15% savings through consolidation
                consolidation_opportunities.append({
                    'supplier': s['supplier'],
                    'current_spend': s['amount'],
                    'transaction_count': s['count'],
                    'avg_transaction': round(avg_transaction, 2),
                    'opportunity_type': 'Consolidation',
                    'estimated_savings': round(estimated_savings, 2),
                    'recommendation': 'Consider consolidating with preferred supplier',
                })

        # Sort by estimated savings
        consolidation_opportunities.sort(key=lambda x: x['estimated_savings'], reverse=True)

        # Calculate category-level opportunities
        category_opportunities = []
        for cat in categories:
            # Estimate potential savings based on spend tier
            if cat['amount'] > total_spend * 0.1:  # High spend category
                savings_rate = 0.08  # 8% potential through strategic sourcing
                opportunity_type = 'Strategic Sourcing'
            elif cat['amount'] > total_spend * 0.05:
                savings_rate = 0.05  # 5% through competitive bidding
                opportunity_type = 'Competitive Bidding'
            else:
                savings_rate = 0.03  # 3% through process improvement
                opportunity_type = 'Process Improvement'

            category_opportunities.append({
                'category': cat['category'],
                'current_spend': cat['amount'],
                'transaction_count': cat['count'],
                'opportunity_type': opportunity_type,
                'savings_rate': round(savings_rate * 100, 1),
                'estimated_savings': round(cat['amount'] * savings_rate, 2),
            })

        # Sort by estimated savings
        category_opportunities.sort(key=lambda x: x['estimated_savings'], reverse=True)

        # Calculate tail spend savings
        tail_savings = tail_spend.get('tail_spend', 0) * 0.12  # 12% savings on tail spend

        # Calculate total potential savings
        total_consolidation_savings = sum(c['estimated_savings'] for c in consolidation_opportunities[:20])
        total_category_savings = sum(c['estimated_savings'] for c in category_opportunities)

        # Build savings summary by type
        savings_by_type = [
            {
                'type': 'Supplier Consolidation',
                'target_spend': sum(c['current_spend'] for c in consolidation_opportunities[:20]),
                'estimated_savings': total_consolidation_savings,
                'opportunity_count': min(20, len(consolidation_opportunities)),
                'implementation': 'Medium',
            },
            {
                'type': 'Tail Spend Reduction',
                'target_spend': tail_spend.get('tail_spend', 0),
                'estimated_savings': tail_savings,
                'opportunity_count': tail_spend.get('tail_count', 0),
                'implementation': 'Easy',
            },
            {
                'type': 'Category Optimization',
                'target_spend': total_spend,
                'estimated_savings': total_category_savings,
                'opportunity_count': len(categories),
                'implementation': 'Complex',
            },
        ]

        total_potential_savings = total_consolidation_savings + tail_savings + total_category_savings

        return {
            'metadata': self.get_metadata(),
            'overview': {
                'total_spend': total_spend,
                'supplier_count': overview.get('supplier_count', 0),
                'category_count': overview.get('category_count', 0),
            },
            'savings_summary': {
                'total_potential_savings': round(total_potential_savings, 2),
                'savings_percentage': round((total_potential_savings / total_spend * 100) if total_spend > 0 else 0, 2),
                'quick_wins': round(tail_savings, 2),
                'strategic_savings': round(total_category_savings, 2),
            },
            'savings_by_type': savings_by_type,
            'consolidation_opportunities': consolidation_opportunities[:20],
            'category_opportunities': category_opportunities[:10],
            'action_plan': [
                {
                    'priority': 1,
                    'action': 'Address Tail Spend',
                    'description': f'Consolidate {tail_spend.get("tail_count", 0)} tail suppliers',
                    'estimated_savings': round(tail_savings, 2),
                    'timeline': 'Short-term (1-3 months)',
                },
                {
                    'priority': 2,
                    'action': 'Supplier Consolidation',
                    'description': 'Consolidate top 10 consolidation opportunities',
                    'estimated_savings': sum(c['estimated_savings'] for c in consolidation_opportunities[:10]),
                    'timeline': 'Medium-term (3-6 months)',
                },
                {
                    'priority': 3,
                    'action': 'Strategic Category Review',
                    'description': 'Conduct strategic sourcing for top categories',
                    'estimated_savings': category_opportunities[0]['estimated_savings'] if category_opportunities else 0,
                    'timeline': 'Long-term (6-12 months)',
                },
            ],
        }
