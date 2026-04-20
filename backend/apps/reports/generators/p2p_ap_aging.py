"""
AP Aging Report Generator.
Provides Accounts Payable aging analysis and payment performance metrics.
"""
from .base import BaseReportGenerator
from apps.analytics.p2p_services import P2PAnalyticsService


class APAgingReportGenerator(BaseReportGenerator):
    """
    Generates AP Aging reports showing aging buckets, DPO trends,
    supplier aging analysis, and cash flow forecasts.
    """

    def __init__(self, organization, filters=None, parameters=None):
        """Initialize with P2P analytics service."""
        super().__init__(organization, filters, parameters)
        self.p2p_analytics = P2PAnalyticsService(organization, filters=self.filters)

    @property
    def report_type(self) -> str:
        return 'p2p_ap_aging'

    @property
    def report_title(self) -> str:
        return 'AP Aging Report'

    def generate(self) -> dict:
        """Generate AP aging analysis data."""
        # Get aging overview
        aging_overview = self.p2p_analytics.get_aging_overview()

        # Get aging by supplier
        aging_by_supplier = self.p2p_analytics.get_aging_by_supplier(limit=25)

        # Get payment terms compliance
        terms_compliance = self.p2p_analytics.get_payment_terms_compliance()

        # Get cash flow forecast
        cash_flow = self.p2p_analytics.get_cash_flow_forecast(weeks=8)

        # Get DPO trends
        dpo_trends = self.p2p_analytics.get_dpo_trends(months=12)

        # Get supplier payment overview
        payment_overview = self.p2p_analytics.get_supplier_payments_overview()

        # Build summary KPIs
        summary = {
            'total_ap': aging_overview.get('total_ap', 0),
            'overdue_amount': aging_overview.get('total_overdue', 0),
            'current_dpo': aging_overview.get('avg_dpo', 0),
            'on_time_rate': aging_overview.get('on_time_rate', 0),
            'suppliers_with_ap': payment_overview.get('suppliers_with_ap', 0),
            'exception_rate': payment_overview.get('exception_rate', 0),
        }

        # Calculate overdue percentage
        total_ap = summary['total_ap']
        overdue = summary['overdue_amount']
        summary['overdue_pct'] = round((overdue / total_ap * 100) if total_ap > 0 else 0, 1)

        # Get aging buckets
        aging_buckets = aging_overview.get('buckets', [])

        # Get DPO trend from aging overview
        dpo_trend = aging_overview.get('trend', [])

        # Generate risk assessment
        risk_assessment = self._assess_ap_risk(summary, aging_buckets, aging_by_supplier)

        # Generate insights
        insights = self._generate_insights(
            summary, aging_buckets, aging_by_supplier, terms_compliance
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            summary, aging_buckets, aging_by_supplier, cash_flow
        )

        return {
            'metadata': self.get_metadata(),
            'summary': summary,
            'aging_buckets': aging_buckets,
            'dpo_trend': dpo_trend if dpo_trend else dpo_trends[:6],
            'supplier_aging': aging_by_supplier[:20],
            'terms_compliance': terms_compliance,
            'cash_flow_forecast': cash_flow,
            'risk_assessment': risk_assessment,
            'insights': insights,
            'recommendations': recommendations,
        }

    def _assess_ap_risk(self, summary, buckets, suppliers):
        """Assess overall AP risk profile."""
        risk_factors = []

        # Overdue concentration risk
        overdue_pct = summary.get('overdue_pct', 0)
        if overdue_pct > 30:
            risk_factors.append({
                'factor': 'Overdue Concentration',
                'level': 'High',
                'description': f'{overdue_pct:.1f}% of AP is overdue',
                'impact': f"${summary.get('overdue_amount', 0):,.0f} at risk"
            })
        elif overdue_pct > 15:
            risk_factors.append({
                'factor': 'Overdue Concentration',
                'level': 'Medium',
                'description': f'{overdue_pct:.1f}% of AP is overdue',
                'impact': 'Monitor closely'
            })
        else:
            risk_factors.append({
                'factor': 'Overdue Concentration',
                'level': 'Low',
                'description': f'{overdue_pct:.1f}% of AP is overdue',
                'impact': 'Within acceptable range'
            })

        # DPO risk
        current_dpo = summary.get('current_dpo', 0)
        if current_dpo > 45:
            risk_factors.append({
                'factor': 'Extended Payment Terms',
                'level': 'Medium',
                'description': f'DPO of {current_dpo:.1f} days may strain supplier relationships',
                'impact': 'Potential supply chain risk'
            })
        elif current_dpo < 15:
            risk_factors.append({
                'factor': 'Early Payment',
                'level': 'Low',
                'description': f'DPO of {current_dpo:.1f} days indicates fast payments',
                'impact': 'Strong supplier relationships'
            })

        # Supplier concentration risk
        if suppliers:
            top_5_value = sum(s.get('total_ap', 0) for s in suppliers[:5])
            total_ap = summary.get('total_ap', 0)
            concentration = (top_5_value / total_ap * 100) if total_ap > 0 else 0

            if concentration > 70:
                risk_factors.append({
                    'factor': 'Supplier Concentration',
                    'level': 'High',
                    'description': f'Top 5 suppliers represent {concentration:.1f}% of AP',
                    'impact': 'High dependency on few suppliers'
                })
            elif concentration > 50:
                risk_factors.append({
                    'factor': 'Supplier Concentration',
                    'level': 'Medium',
                    'description': f'Top 5 suppliers represent {concentration:.1f}% of AP',
                    'impact': 'Moderate concentration'
                })

        # 90+ days bucket risk
        bucket_90_plus = next((b for b in buckets if '90' in b.get('bucket', '')), None)
        if bucket_90_plus:
            pct_90_plus = bucket_90_plus.get('percentage', 0)
            if pct_90_plus > 10:
                risk_factors.append({
                    'factor': 'Severely Overdue',
                    'level': 'High',
                    'description': f'{pct_90_plus:.1f}% of AP is 90+ days overdue',
                    'impact': 'Potential bad debt or disputes'
                })

        # Determine overall risk
        high_count = len([r for r in risk_factors if r['level'] == 'High'])
        medium_count = len([r for r in risk_factors if r['level'] == 'Medium'])

        if high_count >= 2:
            overall = 'High'
        elif high_count == 1 or medium_count >= 2:
            overall = 'Medium'
        else:
            overall = 'Low'

        return {
            'overall_level': overall,
            'factors': risk_factors
        }

    def _generate_insights(self, summary, buckets, suppliers, terms_compliance):
        """Generate key insights from AP data."""
        insights = []

        # DPO insight
        current_dpo = summary.get('current_dpo', 0)
        if current_dpo > 45:
            insights.append({
                'type': 'warning',
                'title': 'Extended DPO',
                'description': f'Current DPO is {current_dpo:.1f} days. '
                               f'May impact supplier relationships.',
                'impact': 'negative'
            })
        elif current_dpo <= 30:
            insights.append({
                'type': 'success',
                'title': 'Healthy Payment Cycle',
                'description': f'DPO of {current_dpo:.1f} days indicates timely payments.',
                'impact': 'positive'
            })

        # On-time rate insight
        on_time_rate = summary.get('on_time_rate', 0)
        if on_time_rate < 80:
            insights.append({
                'type': 'warning',
                'title': 'Low On-Time Payment Rate',
                'description': f'Only {on_time_rate:.1f}% of invoices paid on time.',
                'impact': 'negative'
            })
        elif on_time_rate >= 95:
            insights.append({
                'type': 'success',
                'title': 'Excellent Payment Performance',
                'description': f'{on_time_rate:.1f}% on-time payment rate.',
                'impact': 'positive'
            })

        # Overdue amount insight
        overdue = summary.get('overdue_amount', 0)
        overdue_pct = summary.get('overdue_pct', 0)
        if overdue > 0 and overdue_pct > 20:
            insights.append({
                'type': 'warning',
                'title': 'Significant Overdue Balance',
                'description': f'${overdue:,.0f} ({overdue_pct:.1f}%) is past due.',
                'impact': 'negative'
            })

        # 90+ days bucket
        bucket_90_plus = next((b for b in buckets if '90' in b.get('bucket', '')), None)
        if bucket_90_plus and bucket_90_plus.get('amount', 0) > 0:
            insights.append({
                'type': 'warning',
                'title': 'Severely Overdue Invoices',
                'description': f"${bucket_90_plus.get('amount', 0):,.0f} is 90+ days overdue.",
                'impact': 'negative'
            })

        # Supplier with high overdue
        high_overdue_suppliers = [s for s in suppliers if s.get('days_90_plus', 0) > 0]
        if high_overdue_suppliers:
            total_90_plus = sum(s.get('days_90_plus', 0) for s in high_overdue_suppliers)
            insights.append({
                'type': 'info',
                'title': 'Suppliers with Aged Payables',
                'description': f'{len(high_overdue_suppliers)} suppliers have 90+ day balances '
                               f'totaling ${total_90_plus:,.0f}.',
                'impact': 'neutral'
            })

        # Payment terms compliance
        if terms_compliance:
            low_compliance_terms = [t for t in terms_compliance if t.get('on_time_rate', 100) < 70]
            if low_compliance_terms:
                worst = min(low_compliance_terms, key=lambda x: x.get('on_time_rate', 100))
                insights.append({
                    'type': 'warning',
                    'title': 'Payment Terms Non-Compliance',
                    'description': f"'{worst.get('payment_terms', '')}' terms have "
                                   f"{worst.get('on_time_rate', 0):.1f}% on-time rate.",
                    'impact': 'negative'
                })

        return insights[:6]

    def _generate_recommendations(self, summary, buckets, suppliers, cash_flow):
        """Generate actionable recommendations."""
        recommendations = []

        # Overdue management
        overdue_pct = summary.get('overdue_pct', 0)
        overdue_amount = summary.get('overdue_amount', 0)
        if overdue_pct > 15:
            recommendations.append({
                'type': 'warning',
                'priority': 'High',
                'title': 'Reduce Overdue Balance',
                'description': f'${overdue_amount:,.0f} overdue requires immediate attention.',
                'action': 'Prioritize payment of oldest invoices and resolve disputes'
            })

        # 90+ days aging
        bucket_90_plus = next((b for b in buckets if '90' in b.get('bucket', '')), None)
        if bucket_90_plus and bucket_90_plus.get('amount', 0) > 10000:
            recommendations.append({
                'type': 'warning',
                'priority': 'High',
                'title': 'Address Severely Overdue Items',
                'description': f"${bucket_90_plus.get('amount', 0):,.0f} in 90+ day bucket.",
                'action': 'Investigate payment blocks, disputes, or authorization issues'
            })

        # On-time rate improvement
        on_time_rate = summary.get('on_time_rate', 0)
        if on_time_rate < 85:
            recommendations.append({
                'type': 'opportunity',
                'priority': 'Medium',
                'title': 'Improve On-Time Payments',
                'description': f'{on_time_rate:.1f}% on-time rate below target of 90%.',
                'action': 'Implement payment automation and early warning alerts'
            })

        # High-risk suppliers
        high_risk_suppliers = [s for s in suppliers if s.get('on_time_rate', 100) < 70 and s.get('total_ap', 0) > 50000]
        if high_risk_suppliers:
            supplier_names = ', '.join([s.get('supplier', '') for s in high_risk_suppliers[:3]])
            recommendations.append({
                'type': 'warning',
                'priority': 'High',
                'title': 'Critical Supplier Payment Issues',
                'description': f'Low on-time rates with key suppliers: {supplier_names}.',
                'action': 'Review payment processes for these suppliers immediately'
            })

        # Cash flow planning
        if cash_flow:
            upcoming_payments = sum(cf.get('amount', 0) for cf in cash_flow[:4])
            if upcoming_payments > summary.get('total_ap', 0) * 0.5:
                recommendations.append({
                    'type': 'info',
                    'priority': 'Medium',
                    'title': 'Upcoming Payment Volume',
                    'description': f'${upcoming_payments:,.0f} due in next 4 weeks.',
                    'action': 'Ensure adequate cash reserves for upcoming payments'
                })

        # DPO optimization
        current_dpo = summary.get('current_dpo', 0)
        if current_dpo < 25:
            recommendations.append({
                'type': 'opportunity',
                'priority': 'Low',
                'title': 'Optimize Payment Timing',
                'description': f'DPO of {current_dpo:.1f} days may be too aggressive.',
                'action': 'Consider extending payment terms to improve cash flow'
            })
        elif current_dpo > 50:
            recommendations.append({
                'type': 'warning',
                'priority': 'Medium',
                'title': 'High DPO Risk',
                'description': f'DPO of {current_dpo:.1f} days may strain supplier relationships.',
                'action': 'Accelerate payments to strategic suppliers'
            })

        # Supplier concentration
        if suppliers:
            top_3_value = sum(s.get('total_ap', 0) for s in suppliers[:3])
            total_ap = summary.get('total_ap', 0)
            concentration = (top_3_value / total_ap * 100) if total_ap > 0 else 0
            if concentration > 60:
                recommendations.append({
                    'type': 'info',
                    'priority': 'Medium',
                    'title': 'High AP Concentration',
                    'description': f'Top 3 suppliers represent {concentration:.1f}% of AP.',
                    'action': 'Prioritize relationship management with key suppliers'
                })

        return recommendations[:6]
