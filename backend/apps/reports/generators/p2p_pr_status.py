"""
PR Status Report Generator.
Provides comprehensive Purchase Requisition workflow analysis.
"""
from .base import BaseReportGenerator
from apps.analytics.p2p_services import P2PAnalyticsService


class PRStatusReportGenerator(BaseReportGenerator):
    """
    Generates PR Status reports showing requisition workflow metrics,
    approval patterns, department analysis, and pending approvals.
    """

    def __init__(self, organization, filters=None, parameters=None):
        """Initialize with P2P analytics service."""
        super().__init__(organization, filters, parameters)
        # Use P2P analytics service instead of standard analytics
        self.p2p_analytics = P2PAnalyticsService(organization, filters=self.filters)

    @property
    def report_type(self) -> str:
        return 'p2p_pr_status'

    @property
    def report_title(self) -> str:
        return 'PR Status Report'

    def generate(self) -> dict:
        """Generate PR status analysis data."""
        # Get PR overview metrics
        pr_overview = self.p2p_analytics.get_pr_overview()

        # Get PR breakdown by department
        pr_by_department = self.p2p_analytics.get_pr_by_department()

        # Get pending approvals
        pending_approvals = self.p2p_analytics.get_pr_pending(limit=20)

        # Get approval analysis
        approval_analysis = self.p2p_analytics.get_pr_approval_analysis()

        # Build summary KPIs
        summary = {
            'total_prs': pr_overview.get('total_prs', 0),
            'total_value': pr_overview.get('total_value', 0),
            'conversion_rate': pr_overview.get('conversion_rate', 0),
            'rejection_rate': pr_overview.get('rejection_rate', 0),
            'pending_count': pr_overview.get('pending_count', 0),
            'avg_approval_days': pr_overview.get('avg_approval_days', 0),
        }

        # Build status breakdown
        status_breakdown = pr_overview.get('by_status', [])

        # Build approval time distribution
        approval_distribution = approval_analysis.get('time_distribution', {})

        # Generate insights
        insights = self._generate_insights(
            summary, pr_by_department, approval_analysis
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            summary, pr_by_department, pending_approvals, approval_analysis
        )

        return {
            'metadata': self.get_metadata(),
            'summary': summary,
            'status_breakdown': status_breakdown,
            'department_analysis': pr_by_department[:15],
            'pending_approvals': pending_approvals[:20],
            'approval_distribution': approval_distribution,
            'oldest_pending': approval_analysis.get('oldest_pending', [])[:10],
            'insights': insights,
            'recommendations': recommendations,
        }

    def _generate_insights(self, summary, departments, approval_analysis):
        """Generate key insights from PR data."""
        insights = []

        # Conversion rate insight
        conversion_rate = summary.get('conversion_rate', 0)
        if conversion_rate < 80:
            insights.append({
                'type': 'warning',
                'title': 'Low PR Conversion Rate',
                'description': f'Only {conversion_rate:.1f}% of PRs are converted to POs. '
                               f'Review rejection reasons and approval bottlenecks.',
                'impact': 'negative'
            })
        elif conversion_rate >= 95:
            insights.append({
                'type': 'success',
                'title': 'High PR Conversion Rate',
                'description': f'{conversion_rate:.1f}% of PRs successfully convert to POs.',
                'impact': 'positive'
            })

        # Rejection rate insight
        rejection_rate = summary.get('rejection_rate', 0)
        if rejection_rate > 15:
            insights.append({
                'type': 'warning',
                'title': 'High Rejection Rate',
                'description': f'{rejection_rate:.1f}% of PRs are rejected. '
                               f'Consider requisitioner training or clearer policies.',
                'impact': 'negative'
            })

        # Approval time insight
        avg_approval = summary.get('avg_approval_days', 0)
        if avg_approval > 5:
            insights.append({
                'type': 'warning',
                'title': 'Slow Approval Process',
                'description': f'Average approval time is {avg_approval:.1f} days. '
                               f'Target: 2-3 days.',
                'impact': 'negative'
            })
        elif avg_approval <= 2:
            insights.append({
                'type': 'success',
                'title': 'Efficient Approval Process',
                'description': f'PRs are approved in {avg_approval:.1f} days on average.',
                'impact': 'positive'
            })

        # Pending backlog insight
        pending_count = summary.get('pending_count', 0)
        if pending_count > 20:
            insights.append({
                'type': 'warning',
                'title': 'Pending PR Backlog',
                'description': f'{pending_count} PRs awaiting approval. '
                               f'Review approval workflow capacity.',
                'impact': 'negative'
            })

        # Department variation insight
        if departments:
            approval_rates = [d.get('approval_rate', 0) for d in departments if d.get('pr_count', 0) >= 5]
            if approval_rates:
                max_rate = max(approval_rates)
                min_rate = min(approval_rates)
                if max_rate - min_rate > 20:
                    insights.append({
                        'type': 'info',
                        'title': 'Department Variation',
                        'description': f'Approval rates vary from {min_rate:.0f}% to {max_rate:.0f}% '
                                       f'across departments.',
                        'impact': 'neutral'
                    })

        return insights[:6]

    def _generate_recommendations(self, summary, departments, pending, approval_analysis):
        """Generate actionable recommendations."""
        recommendations = []

        # High rejection rate
        rejection_rate = summary.get('rejection_rate', 0)
        if rejection_rate > 10:
            recommendations.append({
                'type': 'opportunity',
                'priority': 'High',
                'title': 'Reduce PR Rejections',
                'description': f'{rejection_rate:.1f}% rejection rate indicates process issues.',
                'action': 'Analyze common rejection reasons and provide requisitioner training'
            })

        # Slow approvals
        avg_approval = summary.get('avg_approval_days', 0)
        if avg_approval > 3:
            recommendations.append({
                'type': 'opportunity',
                'priority': 'High',
                'title': 'Accelerate Approval Process',
                'description': f'Average {avg_approval:.1f} day approval cycle delays procurement.',
                'action': 'Implement escalation rules and mobile approval capabilities'
            })

        # Pending backlog
        pending_count = summary.get('pending_count', 0)
        if pending_count > 10:
            oldest = approval_analysis.get('oldest_pending', [])
            old_count = len([p for p in oldest if p.get('days_pending', 0) > 5])
            if old_count > 0:
                recommendations.append({
                    'type': 'warning',
                    'priority': 'High',
                    'title': 'Address Stale Approvals',
                    'description': f'{old_count} PRs pending >5 days require attention.',
                    'action': 'Review and resolve oldest pending approvals immediately'
                })

        # Low-performing departments
        low_approval_depts = [d for d in departments if d.get('approval_rate', 100) < 75 and d.get('pr_count', 0) >= 3]
        if low_approval_depts:
            dept_names = ', '.join([d.get('department', 'Unknown') for d in low_approval_depts[:3]])
            recommendations.append({
                'type': 'info',
                'priority': 'Medium',
                'title': 'Department-Specific Training',
                'description': f'Low approval rates in: {dept_names}.',
                'action': 'Provide targeted training on PR requirements and policies'
            })

        # High-value pending PRs
        high_value_pending = [p for p in pending if p.get('estimated_amount', 0) > 50000]
        if high_value_pending:
            total_pending_value = sum(p.get('estimated_amount', 0) for p in high_value_pending)
            recommendations.append({
                'type': 'warning',
                'priority': 'High',
                'title': 'High-Value PRs Awaiting Approval',
                'description': f'{len(high_value_pending)} PRs totaling ${total_pending_value:,.0f} pending.',
                'action': 'Prioritize review of high-value requisitions'
            })

        # Approval time distribution
        time_dist = approval_analysis.get('time_distribution', {})
        slow_approvals = time_dist.get('>5 days', 0)
        if slow_approvals > 10:
            recommendations.append({
                'type': 'opportunity',
                'priority': 'Medium',
                'title': 'Reduce Extended Approval Times',
                'description': f'{slow_approvals} PRs took >5 days to approve.',
                'action': 'Implement automatic escalation for PRs pending >3 days'
            })

        return recommendations[:6]
