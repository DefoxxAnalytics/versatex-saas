"""
Seasonality & Trends Report Generator.
Provides monthly spending patterns with fiscal year support and savings opportunities.
"""
from .base import BaseReportGenerator


class SeasonalityReportGenerator(BaseReportGenerator):
    """
    Generates seasonality analysis reports showing monthly spending patterns,
    seasonal indices, and savings opportunities from timing optimization.
    """

    @property
    def report_type(self) -> str:
        return 'seasonality'

    @property
    def report_title(self) -> str:
        return 'Seasonality & Trends Report'

    def generate(self) -> dict:
        """Generate seasonality analysis data."""
        # Get use_fiscal_year parameter (default True)
        use_fiscal = self.parameters.get('use_fiscal_year', True)

        # Get detailed seasonality from analytics service
        seasonality = self.analytics.get_detailed_seasonality_analysis(
            use_fiscal_year=use_fiscal
        )

        summary = seasonality.get('summary', {})
        monthly_data = seasonality.get('monthly_data', [])
        category_seasonality = seasonality.get('category_seasonality', [])

        # Calculate seasonal indices (normalized to 100)
        seasonal_indices = self._calculate_seasonal_indices(monthly_data)

        # Find peak and trough months
        peak_analysis = self._analyze_peak_trough(monthly_data, seasonal_indices)

        # Generate savings opportunities
        savings_opportunities = self._identify_savings_opportunities(
            category_seasonality, summary
        )

        # Build monthly trend data for charts
        monthly_trend = []
        for month in monthly_data:
            month_entry = {
                'month': month.get('month', ''),
                'fiscal_month': month.get('fiscal_month', 0),
                'average': month.get('average', 0),
            }
            # Add year-by-year data
            years = month.get('years', {})
            for year_key, spend in years.items():
                month_entry[year_key] = spend
            monthly_trend.append(month_entry)

        # Build category analysis (top 15)
        category_analysis = []
        for cat in category_seasonality[:15]:
            category_analysis.append({
                'category': cat.get('category', ''),
                'category_id': cat.get('category_id'),
                'total_spend': cat.get('total_spend', 0),
                'peak_month': cat.get('peak_month', ''),
                'low_month': cat.get('low_month', ''),
                'seasonality_strength': cat.get('seasonality_strength', 0),
                'impact_level': cat.get('impact_level', 'Low'),
                'savings_potential': cat.get('savings_potential', 0),
                'yoy_growth': cat.get('yoy_growth', 0),
                'seasonal_indices': cat.get('seasonal_indices', []),
                'monthly_spend': cat.get('monthly_spend', [])
            })

        # Generate recommendations
        recommendations = self._generate_recommendations(
            summary, category_analysis, peak_analysis
        )

        return {
            'metadata': self.get_metadata(),
            'summary': {
                'categories_analyzed': summary.get('categories_analyzed', 0),
                'opportunities_found': summary.get('opportunities_found', 0),
                'high_impact_count': summary.get('high_impact_count', 0),
                'total_savings_potential': summary.get('total_savings_potential', 0),
                'avg_yoy_growth': summary.get('avg_yoy_growth', 0),
                'available_years': summary.get('available_years', []),
                'use_fiscal_year': use_fiscal,
            },
            'monthly_trend': monthly_trend,
            'seasonal_indices': seasonal_indices,
            'peak_analysis': peak_analysis,
            'category_analysis': category_analysis,
            'savings_opportunities': savings_opportunities,
            'recommendations': recommendations,
        }

    def _calculate_seasonal_indices(self, monthly_data):
        """Calculate normalized seasonal indices (average = 100)."""
        if not monthly_data:
            return []

        # Get average spend for each month
        monthly_averages = [m.get('average', 0) for m in monthly_data]
        overall_average = sum(monthly_averages) / len(monthly_averages) if monthly_averages else 0

        indices = []
        for i, month in enumerate(monthly_data):
            avg = month.get('average', 0)
            index = (avg / overall_average * 100) if overall_average > 0 else 100
            indices.append({
                'month': month.get('month', ''),
                'fiscal_month': month.get('fiscal_month', i + 1),
                'average_spend': avg,
                'index': round(index, 2),
                'variance_from_average': round(index - 100, 2)
            })

        return indices

    def _analyze_peak_trough(self, monthly_data, seasonal_indices):
        """Identify peak and trough spending months."""
        if not seasonal_indices:
            return {
                'peak_months': [],
                'trough_months': [],
                'volatility': 0,
                'peak_to_trough_ratio': 0
            }

        # Sort by index to find peaks and troughs
        sorted_indices = sorted(seasonal_indices, key=lambda x: x['index'], reverse=True)

        # Peak months (index > 115)
        peak_months = [m for m in sorted_indices if m['index'] > 115][:3]

        # Trough months (index < 85)
        trough_months = [m for m in sorted_indices if m['index'] < 85][:3]
        trough_months.reverse()  # Show lowest first

        # Calculate volatility (standard deviation of indices)
        indices_values = [m['index'] for m in seasonal_indices]
        mean_index = sum(indices_values) / len(indices_values)
        variance = sum((idx - mean_index) ** 2 for idx in indices_values) / len(indices_values)
        volatility = variance ** 0.5

        # Peak to trough ratio
        max_index = max(indices_values) if indices_values else 100
        min_index = min(indices_values) if indices_values else 100
        ratio = max_index / min_index if min_index > 0 else 1

        return {
            'peak_months': peak_months,
            'trough_months': trough_months,
            'volatility': round(volatility, 2),
            'peak_to_trough_ratio': round(ratio, 2),
            'max_index': round(max_index, 2),
            'min_index': round(min_index, 2)
        }

    def _identify_savings_opportunities(self, category_seasonality, summary):
        """Identify and prioritize savings opportunities from timing optimization."""
        opportunities = []

        for cat in category_seasonality:
            if cat.get('savings_potential', 0) > 0:
                savings = cat.get('savings_potential', 0)
                strength = cat.get('seasonality_strength', 0)
                impact = cat.get('impact_level', 'Low')

                # Determine opportunity type
                if strength > 30:
                    opp_type = 'timing_shift'
                    description = f"Shift purchases from {cat.get('peak_month', '')} to {cat.get('low_month', '')} to capture volume discounts"
                elif strength > 20:
                    opp_type = 'demand_smoothing'
                    description = f"Negotiate fixed pricing to avoid seasonal premiums"
                else:
                    opp_type = 'contract_terms'
                    description = f"Lock in annual pricing to reduce seasonal volatility"

                opportunities.append({
                    'category': cat.get('category', ''),
                    'category_id': cat.get('category_id'),
                    'savings_potential': savings,
                    'seasonality_strength': strength,
                    'impact_level': impact,
                    'opportunity_type': opp_type,
                    'description': description,
                    'peak_month': cat.get('peak_month', ''),
                    'low_month': cat.get('low_month', ''),
                    'priority': 'High' if impact == 'High' else ('Medium' if impact == 'Medium' else 'Low')
                })

        # Sort by savings potential
        opportunities.sort(key=lambda x: x['savings_potential'], reverse=True)
        return opportunities[:10]

    def _generate_recommendations(self, summary, category_analysis, peak_analysis):
        """Generate strategic recommendations based on seasonality data."""
        recommendations = []

        # High seasonality categories
        high_impact = [c for c in category_analysis if c.get('impact_level') == 'High']
        if high_impact:
            total_high_savings = sum(c.get('savings_potential', 0) for c in high_impact)
            recommendations.append({
                'type': 'opportunity',
                'priority': 'High',
                'title': 'High-Impact Seasonal Categories',
                'description': f'{len(high_impact)} categories show strong seasonal patterns '
                               f'with ${total_high_savings:,.0f} total savings potential.',
                'action': 'Implement timing-based purchasing strategies for these categories'
            })

        # Peak concentration
        if peak_analysis.get('peak_to_trough_ratio', 1) > 2:
            recommendations.append({
                'type': 'warning',
                'priority': 'High',
                'title': 'Significant Seasonal Volatility',
                'description': f"Peak spending is {peak_analysis['peak_to_trough_ratio']:.1f}x higher "
                               f"than trough periods.",
                'action': 'Review demand patterns and negotiate flexible pricing'
            })

        # Year-over-year growth
        avg_growth = summary.get('avg_yoy_growth', 0)
        if avg_growth > 10:
            recommendations.append({
                'type': 'warning',
                'priority': 'Medium',
                'title': 'Rising Seasonal Costs',
                'description': f'Average year-over-year growth of {avg_growth:.1f}% '
                               f'across seasonal categories.',
                'action': 'Negotiate multi-year contracts to lock in pricing'
            })
        elif avg_growth < -10:
            recommendations.append({
                'type': 'info',
                'priority': 'Low',
                'title': 'Declining Spend Trend',
                'description': f'Average year-over-year decline of {abs(avg_growth):.1f}%. '
                               f'Review if volume reductions are intentional.',
                'action': 'Validate demand planning assumptions'
            })

        # Volatility recommendation
        volatility = peak_analysis.get('volatility', 0)
        if volatility > 25:
            recommendations.append({
                'type': 'opportunity',
                'priority': 'Medium',
                'title': 'High Spending Volatility',
                'description': f'Monthly spending volatility of {volatility:.1f}% suggests '
                               f'opportunities for demand smoothing.',
                'action': 'Consider inventory buffers or blanket purchase orders'
            })

        # Peak month concentration
        peak_months = peak_analysis.get('peak_months', [])
        if len(peak_months) >= 2:
            peak_names = [p['month'] for p in peak_months[:2]]
            recommendations.append({
                'type': 'info',
                'priority': 'Medium',
                'title': 'Peak Spending Periods',
                'description': f'Highest spending occurs in {" and ".join(peak_names)}. '
                               f'Plan procurement activities accordingly.',
                'action': 'Pre-negotiate rates before peak periods'
            })

        return recommendations[:6]
