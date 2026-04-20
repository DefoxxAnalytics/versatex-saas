"""
Year-over-Year Analysis Report Generator.
Provides comprehensive year-over-year comparison with category and supplier breakdowns.
"""
from .base import BaseReportGenerator


class YearOverYearReportGenerator(BaseReportGenerator):
    """
    Generates year-over-year comparison reports showing spending changes,
    top gainers/decliners, and variance analysis by category and supplier.
    """

    @property
    def report_type(self) -> str:
        return 'year_over_year'

    @property
    def report_title(self) -> str:
        return 'Year-over-Year Analysis Report'

    def generate(self) -> dict:
        """Generate year-over-year comparison data."""
        # Get parameters
        year1 = self.parameters.get('year1')
        year2 = self.parameters.get('year2')
        use_fiscal = self.parameters.get('use_fiscal_year', True)

        # Get detailed YoY data from analytics service
        yoy_data = self.analytics.get_detailed_year_over_year(
            year1=year1,
            year2=year2,
            use_fiscal_year=use_fiscal
        )

        summary = yoy_data.get('summary', {})
        monthly_comparison = yoy_data.get('monthly_comparison', [])
        category_comparison = yoy_data.get('category_comparison', [])
        supplier_comparison = yoy_data.get('supplier_comparison', [])
        top_gainers = yoy_data.get('top_gainers', [])
        top_decliners = yoy_data.get('top_decliners', [])
        available_years = yoy_data.get('available_years', [])

        # Calculate variance analysis
        variance_analysis = self._analyze_variance(
            category_comparison, summary
        )

        # Build insights
        insights = self._generate_insights(
            summary, top_gainers, top_decliners, variance_analysis
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            summary, top_gainers, top_decliners, category_comparison
        )

        return {
            'metadata': self.get_metadata(),
            'summary': {
                'year1': summary.get('year1', ''),
                'year2': summary.get('year2', ''),
                'year1_total_spend': summary.get('year1_total_spend', 0),
                'year2_total_spend': summary.get('year2_total_spend', 0),
                'spend_change': summary.get('spend_change', 0),
                'spend_change_pct': summary.get('spend_change_pct', 0),
                'year1_transactions': summary.get('year1_transactions', 0),
                'year2_transactions': summary.get('year2_transactions', 0),
                'year1_suppliers': summary.get('year1_suppliers', 0),
                'year2_suppliers': summary.get('year2_suppliers', 0),
                'year1_avg_transaction': summary.get('year1_avg_transaction', 0),
                'year2_avg_transaction': summary.get('year2_avg_transaction', 0),
                'use_fiscal_year': use_fiscal,
                'available_years': available_years,
            },
            'monthly_comparison': monthly_comparison,
            'category_comparison': category_comparison[:20],
            'supplier_comparison': supplier_comparison[:20],
            'top_gainers': top_gainers[:5],
            'top_decliners': top_decliners[:5],
            'variance_analysis': variance_analysis,
            'insights': insights,
            'recommendations': recommendations,
        }

    def _analyze_variance(self, category_comparison, summary):
        """Analyze spending variance patterns."""
        if not category_comparison:
            return {
                'total_categories': 0,
                'categories_increased': 0,
                'categories_decreased': 0,
                'categories_new': 0,
                'categories_discontinued': 0,
                'largest_increase': None,
                'largest_decrease': None,
                'avg_change_pct': 0
            }

        categories_increased = []
        categories_decreased = []
        categories_new = []
        categories_discontinued = []

        for cat in category_comparison:
            y1 = cat.get('year1_spend', 0)
            y2 = cat.get('year2_spend', 0)
            change = cat.get('change', 0)

            if y1 == 0 and y2 > 0:
                categories_new.append(cat)
            elif y1 > 0 and y2 == 0:
                categories_discontinued.append(cat)
            elif change > 0:
                categories_increased.append(cat)
            elif change < 0:
                categories_decreased.append(cat)

        # Find largest movements
        largest_increase = None
        largest_decrease = None

        if categories_increased:
            largest_increase = max(categories_increased, key=lambda x: x.get('change', 0))
        if categories_decreased:
            largest_decrease = min(categories_decreased, key=lambda x: x.get('change', 0))

        # Calculate average change percentage (excluding new/discontinued)
        comparable = [c for c in category_comparison if c.get('year1_spend', 0) > 0 and c.get('year2_spend', 0) > 0]
        avg_change = sum(c.get('change_pct', 0) for c in comparable) / len(comparable) if comparable else 0

        return {
            'total_categories': len(category_comparison),
            'categories_increased': len(categories_increased),
            'categories_decreased': len(categories_decreased),
            'categories_new': len(categories_new),
            'categories_discontinued': len(categories_discontinued),
            'largest_increase': {
                'category': largest_increase.get('category', ''),
                'change': largest_increase.get('change', 0),
                'change_pct': largest_increase.get('change_pct', 0)
            } if largest_increase else None,
            'largest_decrease': {
                'category': largest_decrease.get('category', ''),
                'change': largest_decrease.get('change', 0),
                'change_pct': largest_decrease.get('change_pct', 0)
            } if largest_decrease else None,
            'avg_change_pct': round(avg_change, 2),
            'new_categories': [c.get('category', '') for c in categories_new[:5]],
            'discontinued_categories': [c.get('category', '') for c in categories_discontinued[:5]]
        }

    def _generate_insights(self, summary, top_gainers, top_decliners, variance_analysis):
        """Generate key insights from YoY data."""
        insights = []

        # Overall spend trend
        change_pct = summary.get('spend_change_pct', 0)
        change_amt = summary.get('spend_change', 0)

        if abs(change_pct) > 0:
            direction = 'increased' if change_pct > 0 else 'decreased'
            insights.append({
                'type': 'trend',
                'title': f'Overall Spend {direction.capitalize()}',
                'description': f"Total spend {direction} by ${abs(change_amt):,.0f} ({abs(change_pct):.1f}%) "
                               f"from {summary.get('year1', '')} to {summary.get('year2', '')}.",
                'impact': 'positive' if change_pct < 0 else 'neutral'
            })

        # Transaction volume changes
        y1_txns = summary.get('year1_transactions', 0)
        y2_txns = summary.get('year2_transactions', 0)
        txn_change = ((y2_txns - y1_txns) / y1_txns * 100) if y1_txns > 0 else 0

        if abs(txn_change) > 10:
            direction = 'increased' if txn_change > 0 else 'decreased'
            insights.append({
                'type': 'volume',
                'title': f'Transaction Volume {direction.capitalize()}',
                'description': f"Transaction count {direction} by {abs(txn_change):.1f}% "
                               f"({y1_txns:,} to {y2_txns:,}).",
                'impact': 'neutral'
            })

        # Supplier changes
        y1_sups = summary.get('year1_suppliers', 0)
        y2_sups = summary.get('year2_suppliers', 0)
        sup_change = y2_sups - y1_sups

        if abs(sup_change) > 0:
            direction = 'added' if sup_change > 0 else 'reduced'
            insights.append({
                'type': 'suppliers',
                'title': f'Supplier Base {direction.capitalize()}',
                'description': f"Net {abs(sup_change)} suppliers {direction} "
                               f"({y1_sups} to {y2_sups}).",
                'impact': 'positive' if sup_change < 0 else 'neutral'
            })

        # Top gainer insight
        if top_gainers:
            top = top_gainers[0]
            insights.append({
                'type': 'gainer',
                'title': 'Largest Category Growth',
                'description': f"'{top.get('category', '')}' increased by "
                               f"${top.get('change', 0):,.0f} ({top.get('change_pct', 0):.1f}%).",
                'impact': 'neutral'
            })

        # Top decliner insight
        if top_decliners:
            top = top_decliners[0]
            insights.append({
                'type': 'decliner',
                'title': 'Largest Category Reduction',
                'description': f"'{top.get('category', '')}' decreased by "
                               f"${abs(top.get('change', 0)):,.0f} ({abs(top.get('change_pct', 0)):.1f}%).",
                'impact': 'positive'
            })

        # New categories
        new_count = variance_analysis.get('categories_new', 0)
        if new_count > 0:
            insights.append({
                'type': 'new',
                'title': 'New Spending Categories',
                'description': f"{new_count} new categories added in {summary.get('year2', '')}.",
                'impact': 'neutral'
            })

        return insights[:6]

    def _generate_recommendations(self, summary, top_gainers, top_decliners, category_comparison):
        """Generate strategic recommendations based on YoY data."""
        recommendations = []

        # High growth recommendation
        change_pct = summary.get('spend_change_pct', 0)
        if change_pct > 15:
            recommendations.append({
                'type': 'warning',
                'priority': 'High',
                'title': 'Significant Spend Increase',
                'description': f'Overall spend increased {change_pct:.1f}% year-over-year. '
                               f'Review cost drivers and validate demand.',
                'action': 'Conduct category-level cost analysis'
            })
        elif change_pct < -15:
            recommendations.append({
                'type': 'info',
                'priority': 'Medium',
                'title': 'Significant Spend Reduction',
                'description': f'Overall spend decreased {abs(change_pct):.1f}% year-over-year. '
                               f'Validate if reductions are sustainable.',
                'action': 'Review service level impacts'
            })

        # Top gainers recommendation
        if top_gainers:
            high_growth_cats = [g for g in top_gainers if g.get('change_pct', 0) > 25]
            if high_growth_cats:
                cat_names = ', '.join([c.get('category', '') for c in high_growth_cats[:3]])
                total_increase = sum(c.get('change', 0) for c in high_growth_cats)
                recommendations.append({
                    'type': 'opportunity',
                    'priority': 'High',
                    'title': 'High-Growth Categories',
                    'description': f"Categories with >25% growth: {cat_names}. "
                                   f"Total increase: ${total_increase:,.0f}.",
                    'action': 'Negotiate volume-based pricing for growing categories'
                })

        # Top decliners recommendation
        if top_decliners:
            high_decline_cats = [d for d in top_decliners if d.get('change_pct', 0) < -25]
            if high_decline_cats:
                cat_names = ', '.join([c.get('category', '') for c in high_decline_cats[:3]])
                recommendations.append({
                    'type': 'info',
                    'priority': 'Medium',
                    'title': 'Declining Categories',
                    'description': f"Categories with >25% decline: {cat_names}. "
                                   f"Verify service quality maintained.",
                    'action': 'Review contracts and supplier performance'
                })

        # Supplier base changes
        y1_sups = summary.get('year1_suppliers', 0)
        y2_sups = summary.get('year2_suppliers', 0)
        if y2_sups > y1_sups * 1.2:  # >20% increase in suppliers
            recommendations.append({
                'type': 'warning',
                'priority': 'Medium',
                'title': 'Supplier Base Growth',
                'description': f'Supplier count increased from {y1_sups} to {y2_sups}. '
                               f'Review for fragmentation.',
                'action': 'Evaluate supplier consolidation opportunities'
            })

        # Transaction volume vs spend mismatch
        y1_txns = summary.get('year1_transactions', 0)
        y2_txns = summary.get('year2_transactions', 0)
        txn_change_pct = ((y2_txns - y1_txns) / y1_txns * 100) if y1_txns > 0 else 0

        if abs(change_pct - txn_change_pct) > 15:
            if change_pct > txn_change_pct:
                recommendations.append({
                    'type': 'warning',
                    'priority': 'Medium',
                    'title': 'Rising Average Transaction Value',
                    'description': f'Spend increased {change_pct:.1f}% but transactions only '
                                   f'changed {txn_change_pct:.1f}%. Unit costs may be rising.',
                    'action': 'Analyze pricing trends by category'
                })
            else:
                recommendations.append({
                    'type': 'opportunity',
                    'priority': 'Medium',
                    'title': 'Lower Average Transaction Value',
                    'description': f'Transactions changed {txn_change_pct:.1f}% but spend only '
                                   f'changed {change_pct:.1f}%. Unit costs may be falling.',
                    'action': 'Lock in favorable pricing through contracts'
                })

        # Average transaction value
        y1_avg = summary.get('year1_avg_transaction', 0)
        y2_avg = summary.get('year2_avg_transaction', 0)
        avg_change = ((y2_avg - y1_avg) / y1_avg * 100) if y1_avg > 0 else 0

        if avg_change > 20:
            recommendations.append({
                'type': 'warning',
                'priority': 'Medium',
                'title': 'Increasing Transaction Size',
                'description': f'Average transaction value increased {avg_change:.1f}% '
                               f'(${y1_avg:,.0f} to ${y2_avg:,.0f}).',
                'action': 'Review purchase consolidation or price increases'
            })

        return recommendations[:6]
