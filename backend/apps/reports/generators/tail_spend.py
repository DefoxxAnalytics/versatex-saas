"""
Tail Spend Analysis Report Generator.
Provides tail vendor analysis with consolidation opportunities and action plans.
"""
from .base import BaseReportGenerator


class TailSpendReportGenerator(BaseReportGenerator):
    """
    Generates tail spend analysis reports showing vendor fragmentation,
    consolidation opportunities, and prioritized action plans.
    """

    @property
    def report_type(self) -> str:
        return 'tail_spend'

    @property
    def report_title(self) -> str:
        return 'Tail Spend Analysis Report'

    def generate(self) -> dict:
        """Generate tail spend analysis data."""
        # Get threshold parameter (default $50,000)
        threshold = self.parameters.get('threshold', 50000)

        # Get detailed tail spend data from analytics service
        tail_data = self.analytics.get_detailed_tail_spend(threshold=threshold)

        summary = tail_data.get('summary', {})
        segments = tail_data.get('segments', {})
        pareto_data = tail_data.get('pareto_data', [])
        category_analysis = tail_data.get('category_analysis', [])
        consolidation_opportunities = tail_data.get('consolidation_opportunities', {})

        # Build segment distribution for charts
        segment_distribution = self._build_segment_distribution(segments, summary)

        # Generate action plan
        action_plan = self._generate_action_plan(
            summary, category_analysis, consolidation_opportunities
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            summary, category_analysis, consolidation_opportunities
        )

        # Build executive summary
        executive_summary = self._build_executive_summary(
            summary, consolidation_opportunities, threshold
        )

        return {
            'metadata': self.get_metadata(),
            'threshold_used': threshold,
            'summary': {
                'total_vendors': summary.get('total_vendors', 0),
                'tail_vendor_count': summary.get('tail_vendor_count', 0),
                'tail_spend': summary.get('tail_spend', 0),
                'tail_percentage': summary.get('tail_percentage', 0),
                'total_spend': summary.get('total_spend', 0),
                'savings_opportunity': summary.get('savings_opportunity', 0),
                'vendor_ratio': summary.get('vendor_ratio', 0),
            },
            'executive_summary': executive_summary,
            'segment_distribution': segment_distribution,
            'pareto_data': pareto_data,
            'category_analysis': category_analysis[:15],
            'consolidation_opportunities': {
                'total_opportunities': consolidation_opportunities.get('total_opportunities', 0),
                'total_savings': consolidation_opportunities.get('total_savings', 0),
                'top_type': consolidation_opportunities.get('top_type', 'N/A'),
                'multi_category': consolidation_opportunities.get('multi_category', [])[:10],
                'category': consolidation_opportunities.get('category', [])[:10],
                'geographic': consolidation_opportunities.get('geographic', [])[:10],
            },
            'action_plan': action_plan,
            'recommendations': recommendations,
        }

    def _build_segment_distribution(self, segments, summary):
        """Build segment distribution data for charts."""
        total_spend = summary.get('total_spend', 0)
        total_vendors = summary.get('total_vendors', 0)

        distribution = []

        # Micro segment (<$10K)
        micro = segments.get('micro', {})
        if micro.get('count', 0) > 0:
            distribution.append({
                'segment': 'Micro',
                'label': '<$10K',
                'vendor_count': micro.get('count', 0),
                'spend': micro.get('spend', 0),
                'transactions': micro.get('transactions', 0),
                'avg_spend_per_vendor': micro.get('avg_spend_per_vendor', 0),
                'vendor_percentage': round((micro.get('count', 0) / total_vendors * 100) if total_vendors > 0 else 0, 2),
                'spend_percentage': round((micro.get('spend', 0) / total_spend * 100) if total_spend > 0 else 0, 2),
                'is_tail': True
            })

        # Small segment ($10K-$50K)
        small = segments.get('small', {})
        if small.get('count', 0) > 0:
            distribution.append({
                'segment': 'Small',
                'label': '$10K-$50K',
                'vendor_count': small.get('count', 0),
                'spend': small.get('spend', 0),
                'transactions': small.get('transactions', 0),
                'avg_spend_per_vendor': small.get('avg_spend_per_vendor', 0),
                'vendor_percentage': round((small.get('count', 0) / total_vendors * 100) if total_vendors > 0 else 0, 2),
                'spend_percentage': round((small.get('spend', 0) / total_spend * 100) if total_spend > 0 else 0, 2),
                'is_tail': True
            })

        # Non-tail segment (>$50K)
        non_tail = segments.get('non_tail', {})
        if non_tail.get('count', 0) > 0:
            distribution.append({
                'segment': 'Core',
                'label': '>$50K',
                'vendor_count': non_tail.get('count', 0),
                'spend': non_tail.get('spend', 0),
                'transactions': non_tail.get('transactions', 0),
                'avg_spend_per_vendor': non_tail.get('avg_spend_per_vendor', 0),
                'vendor_percentage': round((non_tail.get('count', 0) / total_vendors * 100) if total_vendors > 0 else 0, 2),
                'spend_percentage': round((non_tail.get('spend', 0) / total_spend * 100) if total_spend > 0 else 0, 2),
                'is_tail': False
            })

        return distribution

    def _build_executive_summary(self, summary, consolidation_opportunities, threshold):
        """Build executive summary highlights."""
        tail_count = summary.get('tail_vendor_count', 0)
        total_vendors = summary.get('total_vendors', 0)
        tail_spend = summary.get('tail_spend', 0)
        tail_pct = summary.get('tail_percentage', 0)
        savings = summary.get('savings_opportunity', 0)
        consol_savings = consolidation_opportunities.get('total_savings', 0)
        total_opps = consolidation_opportunities.get('total_opportunities', 0)

        highlights = []

        # Tail vendor concentration
        if total_vendors > 0:
            vendor_ratio = tail_count / total_vendors * 100
            highlights.append({
                'metric': 'Vendor Concentration',
                'value': f'{tail_count} of {total_vendors}',
                'description': f'{vendor_ratio:.0f}% of vendors are tail suppliers (<${threshold:,})',
                'impact': 'high' if vendor_ratio > 70 else ('medium' if vendor_ratio > 50 else 'low')
            })

        # Tail spend percentage
        highlights.append({
            'metric': 'Tail Spend',
            'value': f'${tail_spend:,.0f}',
            'description': f'{tail_pct:.1f}% of total spend is with tail vendors',
            'impact': 'high' if tail_pct > 20 else ('medium' if tail_pct > 10 else 'low')
        })

        # Direct savings opportunity
        highlights.append({
            'metric': 'Direct Savings',
            'value': f'${savings:,.0f}',
            'description': 'Estimated 8% savings from tail spend management',
            'impact': 'opportunity'
        })

        # Consolidation savings
        if total_opps > 0:
            highlights.append({
                'metric': 'Consolidation Savings',
                'value': f'${consol_savings:,.0f}',
                'description': f'{total_opps} consolidation opportunities identified',
                'impact': 'opportunity'
            })

        # Total potential
        total_potential = savings + consol_savings
        highlights.append({
            'metric': 'Total Potential',
            'value': f'${total_potential:,.0f}',
            'description': 'Combined savings from all initiatives',
            'impact': 'opportunity'
        })

        return highlights

    def _generate_action_plan(self, summary, category_analysis, consolidation_opportunities):
        """Generate prioritized action plan."""
        actions = []

        # Phase 1: Quick wins (micro vendors)
        tail_count = summary.get('tail_vendor_count', 0)
        micro_count = 0
        for cat in category_analysis:
            if cat.get('vendor_percentage', 0) > 80:
                micro_count += 1

        if tail_count > 20:
            actions.append({
                'phase': 1,
                'title': 'Quick Wins - Micro Vendor Elimination',
                'priority': 'High',
                'timeline': '0-3 months',
                'description': 'Redirect purchases from micro vendors (<$10K) to existing '
                               'preferred suppliers or procurement card programs.',
                'estimated_savings': round(summary.get('savings_opportunity', 0) * 0.3, 2),
                'effort': 'Low',
                'actions': [
                    'Identify top 20 micro vendors by transaction count',
                    'Map spending to alternative approved suppliers',
                    'Implement procurement card for low-value purchases',
                    'Communicate changes to requisitioners'
                ]
            })

        # Phase 2: Category consolidation
        cat_opps = consolidation_opportunities.get('category', [])
        if len(cat_opps) > 0:
            top_cats = [c.get('category', '') for c in cat_opps[:3]]
            cat_savings = sum(c.get('savings_potential', 0) for c in cat_opps)

            actions.append({
                'phase': 2,
                'title': 'Category Consolidation',
                'priority': 'High',
                'timeline': '3-6 months',
                'description': f"Consolidate tail vendors in fragmented categories: "
                               f"{', '.join(top_cats)}.",
                'estimated_savings': round(cat_savings, 2),
                'effort': 'Medium',
                'actions': [
                    'Conduct spend analysis by category',
                    'Issue RFQs to top performers for consolidated volume',
                    'Negotiate volume-based pricing agreements',
                    'Transition spend to consolidated suppliers'
                ]
            })

        # Phase 3: Multi-category vendors
        multi_opps = consolidation_opportunities.get('multi_category', [])
        if len(multi_opps) > 0:
            multi_savings = sum(m.get('savings_potential', 0) for m in multi_opps)

            actions.append({
                'phase': 3,
                'title': 'Multi-Category Vendor Review',
                'priority': 'Medium',
                'timeline': '6-9 months',
                'description': 'Evaluate tail vendors serving multiple categories for '
                               'consolidation or strategic partnership.',
                'estimated_savings': round(multi_savings, 2),
                'effort': 'Medium',
                'actions': [
                    'Identify vendors serving 3+ categories',
                    'Evaluate capabilities for expanded scope',
                    'Negotiate enterprise agreements where appropriate',
                    'Standardize pricing across categories'
                ]
            })

        # Phase 4: Geographic consolidation
        geo_opps = consolidation_opportunities.get('geographic', [])
        if len(geo_opps) > 0:
            top_locs = [g.get('location', '') for g in geo_opps[:3]]
            geo_savings = sum(g.get('savings_potential', 0) for g in geo_opps)

            actions.append({
                'phase': 4,
                'title': 'Geographic Consolidation',
                'priority': 'Medium',
                'timeline': '9-12 months',
                'description': f"Consolidate tail vendors in key locations: "
                               f"{', '.join(top_locs)}.",
                'estimated_savings': round(geo_savings, 2),
                'effort': 'High',
                'actions': [
                    'Map vendor presence by location',
                    'Identify regional preferred suppliers',
                    'Negotiate location-based pricing',
                    'Implement regional sourcing strategies'
                ]
            })

        # Phase 5: Ongoing governance
        actions.append({
            'phase': 5,
            'title': 'Tail Spend Governance',
            'priority': 'Low',
            'timeline': 'Ongoing',
            'description': 'Establish governance to prevent tail spend creep.',
            'estimated_savings': 0,
            'effort': 'Low',
            'actions': [
                'Set tail spend KPIs and targets',
                'Implement new vendor approval process',
                'Quarterly tail spend reviews',
                'Requisitioner training on preferred suppliers'
            ]
        })

        return actions

    def _generate_recommendations(self, summary, category_analysis, consolidation_opportunities):
        """Generate strategic recommendations."""
        recommendations = []

        # Tail vendor concentration
        vendor_ratio = summary.get('vendor_ratio', 0)
        if vendor_ratio > 70:
            recommendations.append({
                'type': 'warning',
                'priority': 'High',
                'title': 'Severe Vendor Fragmentation',
                'description': f'{vendor_ratio:.0f}% of vendors are tail suppliers. '
                               f'Significant consolidation opportunity.',
                'action': 'Implement vendor rationalization program'
            })
        elif vendor_ratio > 50:
            recommendations.append({
                'type': 'warning',
                'priority': 'Medium',
                'title': 'High Vendor Fragmentation',
                'description': f'{vendor_ratio:.0f}% of vendors are tail suppliers.',
                'action': 'Target top fragmented categories for consolidation'
            })

        # Tail spend percentage
        tail_pct = summary.get('tail_percentage', 0)
        if tail_pct > 15:
            recommendations.append({
                'type': 'opportunity',
                'priority': 'High',
                'title': 'High Tail Spend Ratio',
                'description': f'{tail_pct:.1f}% of spend is with tail vendors. '
                               f'Significant savings opportunity.',
                'action': 'Develop tail spend reduction strategy'
            })

        # Consolidation opportunity type
        top_type = consolidation_opportunities.get('top_type', 'N/A')
        total_savings = consolidation_opportunities.get('total_savings', 0)
        if total_savings > 0:
            recommendations.append({
                'type': 'opportunity',
                'priority': 'High',
                'title': f'Top Opportunity: {top_type}',
                'description': f'${total_savings:,.0f} potential savings from consolidation.',
                'action': f'Prioritize {top_type.lower()} initiatives'
            })

        # Category-specific recommendations
        high_tail_cats = [c for c in category_analysis if c.get('tail_percentage', 0) > 50]
        if high_tail_cats:
            cat_names = ', '.join([c.get('category', '') for c in high_tail_cats[:3]])
            recommendations.append({
                'type': 'info',
                'priority': 'Medium',
                'title': 'Categories with High Tail Concentration',
                'description': f'Categories with >50% tail spend: {cat_names}.',
                'action': 'Conduct category-specific sourcing events'
            })

        # Multi-category vendors
        multi_cat = consolidation_opportunities.get('multi_category', [])
        if len(multi_cat) > 5:
            recommendations.append({
                'type': 'info',
                'priority': 'Medium',
                'title': 'Multi-Category Tail Vendors',
                'description': f'{len(multi_cat)} tail vendors serve multiple categories.',
                'action': 'Evaluate for strategic supplier development or elimination'
            })

        # Procurement card opportunity
        micro_spend = 0
        for cat in category_analysis:
            # Estimate micro spend as portion of tail
            if cat.get('tail_spend', 0) > 0:
                micro_spend += cat.get('tail_spend', 0) * 0.3  # Estimate 30% is micro

        if micro_spend > 50000:
            recommendations.append({
                'type': 'opportunity',
                'priority': 'Medium',
                'title': 'Procurement Card Opportunity',
                'description': f'Estimated ${micro_spend:,.0f} in micro purchases '
                               f'suitable for p-card program.',
                'action': 'Expand procurement card usage for low-value purchases'
            })

        return recommendations[:6]
