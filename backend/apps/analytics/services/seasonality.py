"""
Seasonality analytics service.

Provides seasonal pattern analysis with fiscal year support, category breakdowns,
seasonal indices, and savings potential calculations.
"""
import math
from collections import defaultdict

from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth

from apps.procurement.models import Category
from .base import BaseAnalyticsService


class SeasonalityAnalyticsService(BaseAnalyticsService):
    """
    Service for seasonality analytics.

    Methods:
        get_seasonality_analysis: Basic monthly spending patterns
        get_detailed_seasonality_analysis: Comprehensive seasonal analysis with fiscal year
        get_seasonality_category_drilldown: Category-level seasonal drill-down
    """

    def get_seasonality_analysis(self):
        """
        Analyze spending patterns by month across years.

        Returns:
            list: Monthly averages with occurrence counts
        """
        data = self.transactions.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('month')

        # Group by month number
        monthly_avg = {}
        for item in data:
            month_num = item['month'].month
            if month_num not in monthly_avg:
                monthly_avg[month_num] = []
            monthly_avg[month_num].append(float(item['total']))

        # Calculate averages
        result = []
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        for month_num in range(1, 13):
            values = monthly_avg.get(month_num, [0])
            result.append({
                'month': month_names[month_num-1],
                'average_spend': round(sum(values) / len(values), 2),
                'occurrences': len(values)
            })

        return result

    def get_detailed_seasonality_analysis(self, use_fiscal_year=True):
        """
        Get detailed seasonality analysis with fiscal year support, category breakdowns,
        seasonal indices, and savings potential calculations.

        Args:
            use_fiscal_year: If True, use fiscal year (Jul-Jun); else calendar year

        Returns:
            dict: Comprehensive seasonality data with summary, monthly_data, category_seasonality
        """
        # Month names for calendar and fiscal year
        CALENDAR_MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        FISCAL_MONTH_NAMES = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
                              'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']

        month_names = FISCAL_MONTH_NAMES if use_fiscal_year else CALENDAR_MONTH_NAMES

        def get_fiscal_year(date):
            """Get fiscal year (Jul-Jun) from date"""
            if use_fiscal_year:
                return date.year + 1 if date.month >= 7 else date.year
            return date.year

        def calendar_to_fiscal_month(calendar_month):
            """Convert calendar month (1-12) to fiscal month (1-12)"""
            if not use_fiscal_year:
                return calendar_month
            return calendar_month - 6 if calendar_month >= 7 else calendar_month + 6

        # Get all transactions with date info
        transactions = list(self.transactions.values(
            'id', 'date', 'amount', 'category__name', 'category_id'
        ))

        if not transactions:
            return {
                'summary': {
                    'categories_analyzed': 0,
                    'opportunities_found': 0,
                    'high_impact_count': 0,
                    'total_savings_potential': 0,
                    'avg_yoy_growth': 0,
                    'available_years': []
                },
                'monthly_data': [],
                'category_seasonality': []
            }

        # Extract unique fiscal years
        available_years = sorted(set(get_fiscal_year(t['date']) for t in transactions))

        # Build monthly data by fiscal year
        # Structure: {fiscal_month: {fiscal_year: total_spend}}
        monthly_by_year = defaultdict(lambda: defaultdict(float))

        for t in transactions:
            fiscal_year = get_fiscal_year(t['date'])
            calendar_month = t['date'].month
            fiscal_month = calendar_to_fiscal_month(calendar_month)
            monthly_by_year[fiscal_month][fiscal_year] += float(t['amount'])

        # Build monthly_data response
        monthly_data = []
        for fiscal_month in range(1, 13):
            month_entry = {
                'month': month_names[fiscal_month - 1],
                'fiscal_month': fiscal_month,
                'years': {}
            }
            year_values = []
            for year in available_years:
                spend = monthly_by_year[fiscal_month].get(year, 0)
                month_entry['years'][f'FY{year}'] = round(spend, 2)
                year_values.append(spend)

            month_entry['average'] = round(sum(year_values) / len(year_values), 2) if year_values else 0
            monthly_data.append(month_entry)

        # Calculate category seasonality
        # Group transactions by category
        category_data = defaultdict(list)
        for t in transactions:
            category_data[t['category__name']].append(t)

        category_seasonality = []

        for category_name, cat_transactions in category_data.items():
            # Calculate monthly spend for this category
            cat_monthly_spend = [0.0] * 12  # Index 0-11 for fiscal months 1-12
            cat_yearly_totals = defaultdict(float)

            for t in cat_transactions:
                fiscal_year = get_fiscal_year(t['date'])
                calendar_month = t['date'].month
                fiscal_month = calendar_to_fiscal_month(calendar_month)
                cat_monthly_spend[fiscal_month - 1] += float(t['amount'])
                cat_yearly_totals[fiscal_year] += float(t['amount'])

            total_spend = sum(cat_monthly_spend)
            if total_spend == 0:
                continue

            avg_monthly_spend = total_spend / 12

            # Find peak and low months
            max_spend = max(cat_monthly_spend)
            non_zero_spends = [s for s in cat_monthly_spend if s > 0]
            min_spend = min(non_zero_spends) if non_zero_spends else 0

            peak_month_index = cat_monthly_spend.index(max_spend)
            low_month_index = cat_monthly_spend.index(min_spend) if min_spend > 0 else 0

            # Calculate seasonal indices (normalized where average = 100)
            seasonal_indices = []
            for spend in cat_monthly_spend:
                index = (spend / avg_monthly_spend * 100) if avg_monthly_spend > 0 else 100
                seasonal_indices.append(round(index, 2))

            # Calculate peak spend percentage
            peak_spend_percentage = (max_spend / total_spend * 100) if total_spend > 0 else 0

            # Calculate seasonality strength (coefficient of variation)
            mean_index = sum(seasonal_indices) / len(seasonal_indices)
            variance = sum((idx - mean_index) ** 2 for idx in seasonal_indices) / len(seasonal_indices)
            std_dev = math.sqrt(variance)
            seasonality_strength = (std_dev / mean_index * 100) if mean_index > 0 else 0

            # Determine savings rate based on seasonality strength
            if seasonality_strength > 30:
                savings_rate = 0.25  # High seasonality: 25%
                impact_level = 'High'
            elif seasonality_strength > 20:
                savings_rate = 0.20  # Medium seasonality: 20%
                impact_level = 'Medium'
            else:
                savings_rate = 0.10  # Low seasonality: 10%
                impact_level = 'Low'

            # Only include categories with meaningful seasonality (>15%)
            if seasonality_strength <= 15:
                continue

            # Savings = Total Spend x Peak Month % x Savings Rate
            savings_potential = total_spend * (peak_spend_percentage / 100) * savings_rate

            # Calculate YoY growth (comparing two most recent fiscal years)
            yoy_growth = 0
            fy_totals = {}
            if len(available_years) >= 2:
                recent_years = sorted(available_years)[-2:]
                fy_prev = cat_yearly_totals.get(recent_years[0], 0)
                fy_curr = cat_yearly_totals.get(recent_years[1], 0)
                if fy_prev > 0:
                    yoy_growth = ((fy_curr - fy_prev) / fy_prev * 100)
                fy_totals = {
                    f'FY{recent_years[0]}': round(fy_prev, 2),
                    f'FY{recent_years[1]}': round(fy_curr, 2)
                }
            else:
                for year in available_years:
                    fy_totals[f'FY{year}'] = round(cat_yearly_totals.get(year, 0), 2)

            category_seasonality.append({
                'category': category_name,
                'category_id': cat_transactions[0]['category_id'] if cat_transactions else None,
                'total_spend': round(total_spend, 2),
                'peak_month': month_names[peak_month_index],
                'low_month': month_names[low_month_index],
                'seasonality_strength': round(seasonality_strength, 2),
                'impact_level': impact_level,
                'savings_potential': round(savings_potential, 2),
                'yoy_growth': round(yoy_growth, 2),
                'fy_totals': fy_totals,
                'monthly_spend': [round(s, 2) for s in cat_monthly_spend],
                'seasonal_indices': seasonal_indices
            })

        # Sort by savings potential descending
        category_seasonality.sort(key=lambda x: x['savings_potential'], reverse=True)

        # Calculate summary metrics
        categories_analyzed = len(category_seasonality)
        opportunities_found = len([c for c in category_seasonality if c['seasonality_strength'] > 15])
        high_impact_count = len([c for c in category_seasonality if c['impact_level'] == 'High'])
        total_savings_potential = sum(c['savings_potential'] for c in category_seasonality)
        avg_yoy_growth = (
            sum(c['yoy_growth'] for c in category_seasonality) / len(category_seasonality)
            if category_seasonality else 0
        )

        return {
            'summary': {
                'categories_analyzed': categories_analyzed,
                'opportunities_found': opportunities_found,
                'high_impact_count': high_impact_count,
                'total_savings_potential': round(total_savings_potential, 2),
                'avg_yoy_growth': round(avg_yoy_growth, 2),
                'available_years': available_years
            },
            'monthly_data': monthly_data,
            'category_seasonality': category_seasonality
        }

    def get_seasonality_category_drilldown(self, category_id, use_fiscal_year=True):
        """
        Get detailed seasonality drill-down for a specific category.
        Returns supplier-level seasonal patterns.

        Args:
            category_id: The category ID to drill into
            use_fiscal_year: If True, use fiscal year (Jul-Jun); else calendar year

        Returns:
            dict: Category seasonality with supplier breakdowns
            None: If category not found
        """
        # Month names for calendar and fiscal year
        CALENDAR_MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        FISCAL_MONTH_NAMES = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
                              'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']

        month_names = FISCAL_MONTH_NAMES if use_fiscal_year else CALENDAR_MONTH_NAMES

        def calendar_to_fiscal_month(calendar_month):
            """Convert calendar month (1-12) to fiscal month (1-12)"""
            if not use_fiscal_year:
                return calendar_month
            return calendar_month - 6 if calendar_month >= 7 else calendar_month + 6

        # Get category info
        try:
            category = Category.objects.get(id=category_id, organization=self.organization)
            category_name = category.name
        except Category.DoesNotExist:
            return None

        # Get transactions for this category
        cat_transactions = list(self.transactions.filter(category_id=category_id).values(
            'id', 'date', 'amount', 'supplier__name', 'supplier_id'
        ))

        if not cat_transactions:
            return {
                'category': category_name,
                'category_id': category_id,
                'total_spend': 0,
                'supplier_count': 0,
                'suppliers': [],
                'monthly_totals': [{'month': m, 'spend': 0} for m in month_names]
            }

        # Calculate monthly totals for category
        monthly_totals = [0.0] * 12
        for t in cat_transactions:
            calendar_month = t['date'].month
            fiscal_month = calendar_to_fiscal_month(calendar_month)
            monthly_totals[fiscal_month - 1] += float(t['amount'])

        total_spend = sum(monthly_totals)

        # Group transactions by supplier
        supplier_data = defaultdict(list)
        for t in cat_transactions:
            supplier_data[(t['supplier_id'], t['supplier__name'])].append(t)

        # Calculate supplier-level seasonality
        suppliers = []
        for (supplier_id, supplier_name), transactions in supplier_data.items():
            sup_monthly_spend = [0.0] * 12

            for t in transactions:
                calendar_month = t['date'].month
                fiscal_month = calendar_to_fiscal_month(calendar_month)
                sup_monthly_spend[fiscal_month - 1] += float(t['amount'])

            sup_total = sum(sup_monthly_spend)
            if sup_total == 0:
                continue

            avg_monthly = sup_total / 12

            # Find peak and low months
            max_spend = max(sup_monthly_spend)
            non_zero = [s for s in sup_monthly_spend if s > 0]
            min_spend = min(non_zero) if non_zero else 0

            peak_idx = sup_monthly_spend.index(max_spend)
            low_idx = sup_monthly_spend.index(min_spend) if min_spend > 0 else 0

            # Calculate seasonality strength (coefficient of variation)
            if avg_monthly > 0:
                variance = sum((s - avg_monthly) ** 2 for s in sup_monthly_spend) / 12
                std_dev = math.sqrt(variance)
                seasonality_strength = (std_dev / avg_monthly * 100)
            else:
                seasonality_strength = 0

            suppliers.append({
                'name': supplier_name,
                'supplier_id': supplier_id,
                'total_spend': round(sup_total, 2),
                'percent_of_category': round((sup_total / total_spend * 100) if total_spend > 0 else 0, 2),
                'monthly_spend': [round(s, 2) for s in sup_monthly_spend],
                'peak_month': month_names[peak_idx],
                'low_month': month_names[low_idx],
                'seasonality_strength': round(seasonality_strength, 2)
            })

        # Sort suppliers by total spend descending
        suppliers.sort(key=lambda x: x['total_spend'], reverse=True)

        # Build monthly totals response
        monthly_totals_response = [
            {'month': month_names[i], 'spend': round(monthly_totals[i], 2)}
            for i in range(12)
        ]

        return {
            'category': category_name,
            'category_id': category_id,
            'total_spend': round(total_spend, 2),
            'supplier_count': len(suppliers),
            'suppliers': suppliers,
            'monthly_totals': monthly_totals_response
        }
