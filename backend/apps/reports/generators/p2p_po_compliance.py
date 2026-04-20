"""
PO Compliance Report Generator.
Provides contract coverage, maverick spend, and PO compliance analysis.
"""
from .base import BaseReportGenerator
from apps.analytics.p2p_services import P2PAnalyticsService


class POComplianceReportGenerator(BaseReportGenerator):
    """
    Generates PO Compliance reports showing contract coverage,
    maverick spend analysis, amendment patterns, and supplier compliance.
    """

    def __init__(self, organization, filters=None, parameters=None):
        """Initialize with P2P analytics service."""
        super().__init__(organization, filters, parameters)
        self.p2p_analytics = P2PAnalyticsService(organization, filters=self.filters)

    @property
    def report_type(self) -> str:
        return 'p2p_po_compliance'

    @property
    def report_title(self) -> str:
        return 'PO Compliance Report'

    def generate(self) -> dict:
        """Generate PO compliance analysis data."""
        # Get PO overview metrics
        po_overview = self.p2p_analytics.get_po_overview()

        # Get maverick/leakage analysis by category
        po_leakage = self.p2p_analytics.get_po_leakage(limit=20)

        # Get PO amendment analysis
        amendment_analysis = self.p2p_analytics.get_po_amendment_analysis()

        # Get PO by supplier
        po_by_supplier = self.p2p_analytics.get_po_by_supplier(limit=20)

        # Build summary KPIs
        summary = {
            'total_pos': po_overview.get('total_pos', 0),
            'total_value': po_overview.get('total_value', 0),
            'contract_coverage_pct': po_overview.get('contract_coverage', 0),
            'on_contract_value': po_overview.get('on_contract_value', 0),
            'off_contract_value': po_overview.get('off_contract_value', 0),
            'maverick_rate': po_overview.get('maverick_rate', 0),
            'amendment_rate': po_overview.get('amendment_rate', 0),
            'avg_po_value': po_overview.get('avg_po_value', 0),
        }

        # Build status breakdown
        status_breakdown = po_overview.get('by_status', [])

        # Calculate compliance score
        compliance_score = self._calculate_compliance_score(summary, amendment_analysis)

        # Generate insights
        insights = self._generate_insights(
            summary, po_leakage, amendment_analysis, po_by_supplier
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            summary, po_leakage, amendment_analysis, po_by_supplier
        )

        return {
            'metadata': self.get_metadata(),
            'summary': summary,
            'compliance_score': compliance_score,
            'status_breakdown': status_breakdown,
            'maverick_by_category': po_leakage[:15],
            'amendment_analysis': amendment_analysis,
            'supplier_compliance': po_by_supplier[:20],
            'insights': insights,
            'recommendations': recommendations,
        }

    def _calculate_compliance_score(self, summary, amendment_analysis):
        """Calculate overall compliance score (0-100)."""
        # Contract coverage contributes 50%
        contract_score = min(summary.get('contract_coverage_pct', 0), 100) * 0.5

        # Maverick rate (inverse) contributes 30%
        maverick_rate = summary.get('maverick_rate', 0)
        maverick_score = max(0, 100 - maverick_rate * 2) * 0.3

        # Amendment rate (inverse) contributes 20%
        amendment_rate = summary.get('amendment_rate', 0)
        amendment_score = max(0, 100 - amendment_rate * 2) * 0.2

        total_score = contract_score + maverick_score + amendment_score

        # Determine grade
        if total_score >= 90:
            grade = 'A'
            status = 'Excellent'
        elif total_score >= 80:
            grade = 'B'
            status = 'Good'
        elif total_score >= 70:
            grade = 'C'
            status = 'Fair'
        elif total_score >= 60:
            grade = 'D'
            status = 'Needs Improvement'
        else:
            grade = 'F'
            status = 'Critical'

        return {
            'score': round(total_score, 1),
            'grade': grade,
            'status': status,
            'breakdown': {
                'contract_coverage': round(contract_score / 0.5, 1),
                'maverick_control': round(maverick_score / 0.3, 1),
                'change_management': round(amendment_score / 0.2, 1),
            }
        }

    def _generate_insights(self, summary, leakage, amendments, suppliers):
        """Generate key insights from compliance data."""
        insights = []

        # Contract coverage insight
        coverage = summary.get('contract_coverage_pct', 0)
        if coverage < 70:
            insights.append({
                'type': 'warning',
                'title': 'Low Contract Coverage',
                'description': f'Only {coverage:.1f}% of PO value is contract-backed. '
                               f'Target: >80%.',
                'impact': 'negative'
            })
        elif coverage >= 90:
            insights.append({
                'type': 'success',
                'title': 'Strong Contract Coverage',
                'description': f'{coverage:.1f}% of PO value is under contract.',
                'impact': 'positive'
            })

        # Maverick spend insight
        maverick_rate = summary.get('maverick_rate', 0)
        off_contract_value = summary.get('off_contract_value', 0)
        if maverick_rate > 20:
            insights.append({
                'type': 'warning',
                'title': 'High Maverick Spend',
                'description': f'${off_contract_value:,.0f} ({maverick_rate:.1f}%) spent off-contract.',
                'impact': 'negative'
            })

        # Amendment patterns insight
        amendment_rate = amendments.get('amendment_rate', 0)
        if amendment_rate > 25:
            insights.append({
                'type': 'warning',
                'title': 'Frequent PO Amendments',
                'description': f'{amendment_rate:.1f}% of POs are amended. '
                               f'Review scope and pricing accuracy.',
                'impact': 'negative'
            })

        # Category concentration insight
        if leakage:
            top_maverick_cat = leakage[0]
            if top_maverick_cat.get('maverick_percent', 0) > 50:
                insights.append({
                    'type': 'warning',
                    'title': 'Category Compliance Gap',
                    'description': f"'{top_maverick_cat.get('category', 'Unknown')}' has "
                                   f"{top_maverick_cat.get('maverick_percent', 0):.1f}% maverick spend.",
                    'impact': 'negative'
                })

        # Supplier compliance insight
        maverick_suppliers = [s for s in suppliers if s.get('contract_status') == 'maverick']
        if len(maverick_suppliers) > 5:
            total_maverick_value = sum(s.get('total_value', 0) for s in maverick_suppliers)
            insights.append({
                'type': 'info',
                'title': 'Off-Contract Suppliers',
                'description': f'{len(maverick_suppliers)} suppliers with ${total_maverick_value:,.0f} '
                               f'have no contract coverage.',
                'impact': 'neutral'
            })

        # Value increase amendments
        increase_count = amendments.get('increase_count', 0)
        avg_increase = amendments.get('avg_increase_amount', 0)
        if increase_count > 5 and avg_increase > 5000:
            insights.append({
                'type': 'warning',
                'title': 'PO Value Increases',
                'description': f'{increase_count} POs increased by avg ${avg_increase:,.0f}.',
                'impact': 'negative'
            })

        return insights[:6]

    def _generate_recommendations(self, summary, leakage, amendments, suppliers):
        """Generate actionable recommendations."""
        recommendations = []

        # Low contract coverage
        coverage = summary.get('contract_coverage_pct', 0)
        off_contract_value = summary.get('off_contract_value', 0)
        if coverage < 80:
            savings_potential = off_contract_value * 0.10  # 10% savings assumption
            recommendations.append({
                'type': 'opportunity',
                'priority': 'High',
                'title': 'Increase Contract Coverage',
                'description': f'${off_contract_value:,.0f} off-contract spend. '
                               f'Potential ${savings_potential:,.0f} savings.',
                'action': 'Negotiate contracts for top maverick categories'
            })

        # Top maverick categories
        if leakage:
            high_maverick_cats = [c for c in leakage if c.get('maverick_percent', 0) > 30]
            if high_maverick_cats:
                cat_names = ', '.join([c.get('category', '') for c in high_maverick_cats[:3]])
                total_maverick = sum(c.get('maverick_amount', 0) for c in high_maverick_cats)
                recommendations.append({
                    'type': 'opportunity',
                    'priority': 'High',
                    'title': 'Address Category Leakage',
                    'description': f'High maverick spend in: {cat_names}. '
                                   f'Total: ${total_maverick:,.0f}.',
                    'action': 'Establish preferred supplier agreements for these categories'
                })

        # High amendment rate
        amendment_rate = amendments.get('amendment_rate', 0)
        if amendment_rate > 15:
            recommendations.append({
                'type': 'opportunity',
                'priority': 'Medium',
                'title': 'Reduce PO Amendments',
                'description': f'{amendment_rate:.1f}% amendment rate indicates scope issues.',
                'action': 'Improve requirements gathering and PO accuracy at creation'
            })

        # Maverick suppliers
        maverick_suppliers = [s for s in suppliers if s.get('contract_status') == 'maverick']
        if maverick_suppliers:
            # Sort by value
            maverick_suppliers.sort(key=lambda x: x.get('total_value', 0), reverse=True)
            top_maverick = maverick_suppliers[:5]
            top_maverick_value = sum(s.get('total_value', 0) for s in top_maverick)
            recommendations.append({
                'type': 'opportunity',
                'priority': 'High',
                'title': 'Contract Top Maverick Suppliers',
                'description': f'Top 5 off-contract suppliers: ${top_maverick_value:,.0f}.',
                'action': 'Negotiate contracts or redirect spend to contracted alternatives'
            })

        # Amendment value increases
        increase_count = amendments.get('increase_count', 0)
        avg_increase = amendments.get('avg_increase_amount', 0)
        if increase_count > 3 and avg_increase > 10000:
            recommendations.append({
                'type': 'warning',
                'priority': 'Medium',
                'title': 'Control PO Value Increases',
                'description': f'{increase_count} POs with avg ${avg_increase:,.0f} increases.',
                'action': 'Implement stricter change order approval process'
            })

        # On-time delivery for contracted suppliers
        late_suppliers = [s for s in suppliers if s.get('on_time_rate', 100) < 80 and s.get('contract_status') == 'on_contract']
        if late_suppliers:
            recommendations.append({
                'type': 'warning',
                'priority': 'Medium',
                'title': 'Contracted Supplier Performance',
                'description': f'{len(late_suppliers)} contracted suppliers with <80% on-time delivery.',
                'action': 'Review SLAs and enforce contract terms'
            })

        return recommendations[:6]
