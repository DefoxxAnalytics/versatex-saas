"""
Compliance Report Generator.
Provides contract compliance and maverick spend analysis.
"""
from .base import BaseReportGenerator


class ComplianceReportGenerator(BaseReportGenerator):
    """
    Generates compliance reports with maverick spend analysis,
    policy violations, and compliance metrics.
    """

    @property
    def report_type(self) -> str:
        return 'contract_compliance'

    @property
    def report_title(self) -> str:
        return 'Contract Compliance Report'

    def generate(self) -> dict:
        """Generate compliance data."""
        # Get overview stats
        overview = self.analytics.get_overview_stats()
        total_spend = overview.get('total_spend', 0)
        transaction_count = overview.get('transaction_count', 0)

        # Get supplier data for analysis
        suppliers = self.analytics.get_spend_by_supplier()

        # Get tail spend (often non-compliant)
        tail_spend = self.analytics.get_tail_spend_analysis(threshold_percentage=20)

        # Estimate compliance metrics
        # In a real implementation, this would come from contract data
        # For now, we estimate based on supplier concentration
        pareto = self.analytics.get_pareto_analysis()

        # Calculate metrics
        # Assume top suppliers (80% spend) are compliant, tail is maverick
        compliant_suppliers = 0
        compliant_spend = 0
        for p in pareto:
            if p.get('cumulative_percentage', 0) <= 80:
                compliant_suppliers += 1
                compliant_spend += p.get('amount', 0)

        maverick_spend = total_spend - compliant_spend
        compliance_rate = (compliant_spend / total_spend * 100) if total_spend > 0 else 100

        # Identify potential violations (tail spend suppliers with high transaction counts)
        potential_violations = []
        tail_suppliers = tail_spend.get('tail_suppliers', [])
        for ts in tail_suppliers:
            if ts.get('transaction_count', 0) > 3:  # Multiple transactions with tail supplier
                potential_violations.append({
                    'supplier': ts.get('supplier'),
                    'violation_type': 'Unauthorized Supplier',
                    'spend': ts.get('amount', 0),
                    'transaction_count': ts.get('transaction_count', 0),
                    'severity': 'Medium' if ts.get('amount', 0) < 5000 else 'High',
                    'recommendation': 'Review and potentially add to approved supplier list or consolidate',
                })

        # Build compliance by category (estimate)
        categories = self.analytics.get_spend_by_category()
        category_compliance = []
        for cat in categories[:10]:
            # Estimate compliance based on spend concentration
            cat_compliance_rate = min(95, 70 + (cat['count'] / 10))  # Higher transaction count = better compliance
            category_compliance.append({
                'category': cat['category'],
                'total_spend': cat['amount'],
                'compliant_spend': cat['amount'] * (cat_compliance_rate / 100),
                'maverick_spend': cat['amount'] * (1 - cat_compliance_rate / 100),
                'compliance_rate': round(cat_compliance_rate, 1),
            })

        return {
            'metadata': self.get_metadata(),
            'overview': {
                'total_spend': total_spend,
                'transaction_count': transaction_count,
                'supplier_count': overview.get('supplier_count', 0),
            },
            'compliance_summary': {
                'overall_compliance_rate': round(compliance_rate, 1),
                'compliant_spend': compliant_spend,
                'maverick_spend': maverick_spend,
                'maverick_percentage': round(100 - compliance_rate, 1),
                'compliant_supplier_count': compliant_suppliers,
                'total_violations': len(potential_violations),
            },
            'violations': potential_violations[:20],
            'compliance_by_category': category_compliance,
            'tail_spend_analysis': {
                'tail_spend': tail_spend.get('tail_spend', 0),
                'tail_percentage': tail_spend.get('tail_percentage', 0),
                'tail_supplier_count': tail_spend.get('tail_count', 0),
            },
            'recommendations': [
                {
                    'priority': 'High',
                    'action': 'Supplier Consolidation',
                    'description': f'Review {len(tail_suppliers)} tail suppliers for potential consolidation.',
                    'potential_savings': maverick_spend * 0.1,  # Estimate 10% savings
                },
                {
                    'priority': 'Medium',
                    'action': 'Contract Coverage',
                    'description': 'Expand contract coverage to high-volume tail suppliers.',
                    'potential_savings': maverick_spend * 0.05,
                },
            ],
        }
