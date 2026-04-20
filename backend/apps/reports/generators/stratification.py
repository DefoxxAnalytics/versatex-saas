"""
Spend Stratification Report Generator.
Provides Kraljic matrix analysis with strategic, leverage, routine, and tactical segments.
"""
from .base import BaseReportGenerator


class StratificationReportGenerator(BaseReportGenerator):
    """
    Generates spend stratification reports showing Kraljic matrix analysis
    with segment classifications and strategic recommendations.
    """

    @property
    def report_type(self) -> str:
        return 'stratification'

    @property
    def report_title(self) -> str:
        return 'Spend Stratification Report'

    def generate(self) -> dict:
        """Generate spend stratification analysis data."""
        # Get detailed stratification from analytics service
        stratification = self.analytics.get_detailed_stratification()

        # Get strategic segment drilldown for top suppliers
        strategic_drilldown = None
        try:
            strategic_drilldown = self.analytics.get_stratification_segment_drilldown('Strategic')
        except Exception:
            # Strategic segment may not have data
            pass

        summary = stratification.get('summary', {})
        segments = stratification.get('segments', [])
        spend_bands = stratification.get('spend_bands', [])

        # Extract key metrics
        total_spend = summary.get('total_spend', 0)
        active_bands = summary.get('active_spend_bands', 0)
        strategic_bands = summary.get('strategic_bands', 0)
        high_risk_bands = summary.get('high_risk_bands', 0)

        # Get strategic suppliers from drilldown if available
        strategic_suppliers = []
        if strategic_drilldown and 'suppliers' in strategic_drilldown:
            strategic_suppliers = strategic_drilldown['suppliers'][:20]

        # Calculate segment distributions for charts
        segment_distribution = []
        for seg in segments:
            segment_distribution.append({
                'name': seg.get('segment', ''),
                'spend': seg.get('total_spend', 0),
                'percentage': seg.get('percent_of_total', 0),
                'suppliers': seg.get('suppliers', 0),
                'transactions': seg.get('transactions', 0),
                'strategy': seg.get('strategy', ''),
                'spend_range': seg.get('spend_range', '')
            })

        # Calculate band distributions for charts
        band_distribution = []
        for band in spend_bands:
            if band.get('suppliers', 0) > 0:  # Only include active bands
                band_distribution.append({
                    'band': band.get('band', ''),
                    'label': band.get('label', ''),
                    'spend': band.get('total_spend', 0),
                    'percentage': band.get('percent_of_total', 0),
                    'suppliers': band.get('suppliers', 0),
                    'transactions': band.get('transactions', 0),
                    'strategic_importance': band.get('strategic_importance', ''),
                    'risk_level': band.get('risk_level', '')
                })

        # Generate strategic recommendations
        recommendations = self._generate_recommendations(
            summary, segments, spend_bands, total_spend
        )

        # Calculate risk assessment
        risk_assessment = self._assess_risk(segments, summary)

        return {
            'metadata': self.get_metadata(),
            'summary': {
                'total_spend': total_spend,
                'active_spend_bands': active_bands,
                'strategic_bands': strategic_bands,
                'high_risk_bands': high_risk_bands,
                'highest_impact_band': summary.get('highest_impact_band', 'N/A'),
                'highest_impact_percent': summary.get('highest_impact_percent', 0),
                'most_fragmented_band': summary.get('most_fragmented_band', 'N/A'),
                'most_fragmented_suppliers': summary.get('most_fragmented_suppliers', 0),
                'avg_suppliers_per_band': summary.get('avg_suppliers_per_band', 0),
                'overall_risk': summary.get('overall_risk', 'Unknown'),
            },
            'segments': segment_distribution,
            'spend_bands': band_distribution,
            'strategic_suppliers': strategic_suppliers,
            'risk_assessment': risk_assessment,
            'recommendations': recommendations,
        }

    def _generate_recommendations(self, summary, segments, spend_bands, total_spend):
        """Generate strategic recommendations based on stratification data."""
        recommendations = []

        # Check for concentration risk
        strategic_segment = next((s for s in segments if s.get('segment') == 'Strategic'), None)
        if strategic_segment:
            strategic_pct = strategic_segment.get('percent_of_total', 0)
            if strategic_pct > 60:
                recommendations.append({
                    'type': 'warning',
                    'priority': 'High',
                    'title': 'High Strategic Concentration',
                    'description': f'{strategic_pct:.1f}% of spend is with strategic suppliers. '
                                   'Consider diversification to reduce supply chain risk.',
                    'action': 'Develop secondary supplier relationships for critical categories'
                })
            elif strategic_pct > 40:
                recommendations.append({
                    'type': 'info',
                    'priority': 'Medium',
                    'title': 'Moderate Strategic Concentration',
                    'description': f'{strategic_pct:.1f}% of spend is with strategic suppliers. '
                                   'Monitor supplier performance closely.',
                    'action': 'Implement quarterly supplier performance reviews'
                })

        # Check for tactical segment consolidation opportunity
        tactical_segment = next((s for s in segments if s.get('segment') == 'Tactical'), None)
        if tactical_segment:
            tactical_suppliers = tactical_segment.get('suppliers', 0)
            tactical_spend = tactical_segment.get('total_spend', 0)
            if tactical_suppliers > 50:
                savings_potential = tactical_spend * 0.15  # 15% consolidation savings
                recommendations.append({
                    'type': 'opportunity',
                    'priority': 'High',
                    'title': 'Tactical Supplier Consolidation',
                    'description': f'{tactical_suppliers} suppliers in tactical segment. '
                                   'Consolidation could yield significant savings.',
                    'action': f'Target consolidation for ${savings_potential:,.0f} potential savings'
                })

        # Check for fragmentation in specific bands
        for band in spend_bands:
            suppliers = band.get('suppliers', 0)
            band_label = band.get('label', band.get('band', ''))
            band_spend = band.get('total_spend', 0)

            if suppliers > 100 and band_spend > 0:
                recommendations.append({
                    'type': 'opportunity',
                    'priority': 'Medium',
                    'title': f'Fragmentation in {band_label} Band',
                    'description': f'{suppliers} suppliers in {band_label} band. '
                                   'Consider supplier rationalization.',
                    'action': 'Review supplier performance and consolidate to top performers'
                })

        # Check for high-risk bands
        high_risk_count = summary.get('high_risk_bands', 0)
        if high_risk_count > 2:
            recommendations.append({
                'type': 'warning',
                'priority': 'High',
                'title': 'Multiple High-Risk Spend Bands',
                'description': f'{high_risk_count} spend bands identified as high-risk. '
                               'Requires immediate attention.',
                'action': 'Conduct detailed risk assessment for high-risk categories'
            })

        # Add general recommendations from summary
        summary_recs = summary.get('recommendations', [])
        for rec in summary_recs[:3]:  # Limit to 3
            recommendations.append({
                'type': 'info',
                'priority': 'Medium',
                'title': 'Strategic Opportunity',
                'description': rec,
                'action': 'Review and implement as part of category strategy'
            })

        return recommendations[:8]  # Limit total recommendations

    def _assess_risk(self, segments, summary):
        """Generate risk assessment summary."""
        risk_factors = []

        # Supplier concentration risk
        strategic_segment = next((s for s in segments if s.get('segment') == 'Strategic'), None)
        if strategic_segment:
            strategic_pct = strategic_segment.get('percent_of_total', 0)
            strategic_suppliers = strategic_segment.get('suppliers', 0)

            if strategic_pct > 50 and strategic_suppliers < 5:
                risk_factors.append({
                    'factor': 'Supplier Concentration',
                    'level': 'High',
                    'description': 'Heavy reliance on few strategic suppliers'
                })
            elif strategic_pct > 30 and strategic_suppliers < 10:
                risk_factors.append({
                    'factor': 'Supplier Concentration',
                    'level': 'Medium',
                    'description': 'Moderate concentration with strategic suppliers'
                })
            else:
                risk_factors.append({
                    'factor': 'Supplier Concentration',
                    'level': 'Low',
                    'description': 'Well-diversified supplier base'
                })

        # Fragmentation risk
        avg_suppliers = summary.get('avg_suppliers_per_band', 0)
        if avg_suppliers > 50:
            risk_factors.append({
                'factor': 'Supplier Fragmentation',
                'level': 'High',
                'description': 'High supplier fragmentation increases complexity and costs'
            })
        elif avg_suppliers > 25:
            risk_factors.append({
                'factor': 'Supplier Fragmentation',
                'level': 'Medium',
                'description': 'Moderate supplier fragmentation'
            })
        else:
            risk_factors.append({
                'factor': 'Supplier Fragmentation',
                'level': 'Low',
                'description': 'Manageable number of suppliers'
            })

        # Overall risk determination
        high_risk_count = len([r for r in risk_factors if r['level'] == 'High'])
        medium_risk_count = len([r for r in risk_factors if r['level'] == 'Medium'])

        if high_risk_count >= 2:
            overall = 'High'
        elif high_risk_count == 1 or medium_risk_count >= 2:
            overall = 'Medium'
        else:
            overall = 'Low'

        return {
            'overall_level': overall,
            'factors': risk_factors
        }
