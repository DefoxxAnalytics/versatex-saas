"""
Analytics business logic and calculations
"""
from decimal import Decimal
from django.db.models import Sum, Count, Avg, Q, F, Min, Max
from django.db.models.functions import TruncMonth, TruncYear
from datetime import datetime, timedelta
from apps.procurement.models import Transaction, Supplier, Category


class AnalyticsService:
    """
    Service class for analytics calculations
    """

    def __init__(self, organization, filters=None):
        """
        Initialize analytics service with optional filters.

        Args:
            organization: Organization instance
            filters: Optional dict with filter parameters:
                - date_from: Start date (str 'YYYY-MM-DD' or date)
                - date_to: End date (str 'YYYY-MM-DD' or date)
                - supplier_ids: List of supplier IDs to include
                - category_ids: List of category IDs to include
                - min_amount: Minimum transaction amount
                - max_amount: Maximum transaction amount
        """
        self.organization = organization
        self.filters = filters or {}
        self.transactions = self._build_filtered_queryset()

    def _build_filtered_queryset(self):
        """Build transaction queryset with applied filters."""
        qs = Transaction.objects.filter(organization=self.organization)

        # Date range filters
        if date_from := self.filters.get('date_from'):
            if isinstance(date_from, str):
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            qs = qs.filter(date__gte=date_from)

        if date_to := self.filters.get('date_to'):
            if isinstance(date_to, str):
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            qs = qs.filter(date__lte=date_to)

        # Supplier filter
        if supplier_ids := self.filters.get('supplier_ids'):
            if isinstance(supplier_ids, list) and supplier_ids:
                qs = qs.filter(supplier_id__in=supplier_ids)

        # Category filter
        if category_ids := self.filters.get('category_ids'):
            if isinstance(category_ids, list) and category_ids:
                qs = qs.filter(category_id__in=category_ids)

        # Amount range filters
        if min_amount := self.filters.get('min_amount'):
            qs = qs.filter(amount__gte=min_amount)

        if max_amount := self.filters.get('max_amount'):
            qs = qs.filter(amount__lte=max_amount)

        return qs
    
    def get_overview_stats(self):
        """
        Get overview statistics
        """
        stats = self.transactions.aggregate(
            total_spend=Sum('amount'),
            transaction_count=Count('id'),
            supplier_count=Count('supplier', distinct=True),
            category_count=Count('category', distinct=True),
            avg_transaction=Avg('amount')
        )
        
        return {
            'total_spend': float(stats['total_spend'] or 0),
            'transaction_count': stats['transaction_count'] or 0,
            'supplier_count': stats['supplier_count'] or 0,
            'category_count': stats['category_count'] or 0,
            'avg_transaction': float(stats['avg_transaction'] or 0)
        }
    
    def get_spend_by_category(self):
        """
        Get spend breakdown by category
        """
        data = self.transactions.values(
            'category__name'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        return [
            {
                'category': item['category__name'],
                'amount': float(item['total']),
                'count': item['count']
            }
            for item in data
        ]
    
    def get_spend_by_supplier(self):
        """
        Get spend breakdown by supplier
        """
        data = self.transactions.values(
            'supplier__name'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        return [
            {
                'supplier': item['supplier__name'],
                'amount': float(item['total']),
                'count': item['count']
            }
            for item in data
        ]
    
    def get_monthly_trend(self, months=12):
        """
        Get monthly spend trend
        """
        cutoff_date = datetime.now().date() - timedelta(days=months*30)
        
        data = self.transactions.filter(
            date__gte=cutoff_date
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('month')
        
        return [
            {
                'month': item['month'].strftime('%Y-%m'),
                'amount': float(item['total']),
                'count': item['count']
            }
            for item in data
        ]
    
    def get_pareto_analysis(self):
        """
        Get Pareto analysis (80/20 rule) for suppliers
        """
        suppliers = self.transactions.values(
            'supplier__name',
            'supplier_id'
        ).annotate(
            total=Sum('amount')
        ).order_by('-total')

        total_spend = sum(s['total'] for s in suppliers)
        cumulative = 0
        result = []

        for supplier in suppliers:
            cumulative += supplier['total']
            percentage = (cumulative / total_spend * 100) if total_spend > 0 else 0

            result.append({
                'supplier': supplier['supplier__name'],
                'supplier_id': supplier['supplier_id'],
                'amount': float(supplier['total']),
                'cumulative_percentage': round(percentage, 2)
            })

        return result
    
    def get_tail_spend_analysis(self, threshold_percentage=20):
        """
        Analyze tail spend (bottom X% of suppliers)
        """
        suppliers = list(self.transactions.values(
            'supplier__name',
            'supplier_id'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total'))
        
        total_spend = sum(s['total'] for s in suppliers) or Decimal('0')
        threshold_amount = total_spend * Decimal(str(threshold_percentage)) / Decimal('100')
        
        cumulative = 0
        tail_suppliers = []
        
        # Find tail suppliers (from bottom)
        for supplier in reversed(suppliers):
            if cumulative >= threshold_amount:
                break
            cumulative += supplier['total']
            tail_suppliers.append({
                'supplier': supplier['supplier__name'],
                'supplier_id': supplier['supplier_id'],
                'amount': float(supplier['total']),
                'transaction_count': supplier['count']
            })
        
        return {
            'tail_suppliers': tail_suppliers,
            'tail_count': len(tail_suppliers),
            'tail_spend': float(cumulative),
            'tail_percentage': round((cumulative / total_spend * 100) if total_spend > 0 else 0, 2)
        }
    
    def get_spend_stratification(self):
        """
        Categorize spend into strategic, leverage, bottleneck, and tactical
        Based on spend value and supplier count
        """
        categories = self.transactions.values(
            'category__name',
            'category_id'
        ).annotate(
            total_spend=Sum('amount'),
            supplier_count=Count('supplier', distinct=True),
            transaction_count=Count('id')
        )
        
        # Calculate medians for classification
        spends = [c['total_spend'] for c in categories]
        supplier_counts = [c['supplier_count'] for c in categories]
        
        median_spend = sorted(spends)[len(spends)//2] if spends else 0
        median_suppliers = sorted(supplier_counts)[len(supplier_counts)//2] if supplier_counts else 0
        
        result = {
            'strategic': [],  # High spend, few suppliers
            'leverage': [],   # High spend, many suppliers
            'bottleneck': [], # Low spend, few suppliers
            'tactical': []    # Low spend, many suppliers
        }
        
        for cat in categories:
            item = {
                'category': cat['category__name'],
                'spend': float(cat['total_spend']),
                'supplier_count': cat['supplier_count'],
                'transaction_count': cat['transaction_count']
            }
            
            if cat['total_spend'] >= median_spend:
                if cat['supplier_count'] <= median_suppliers:
                    result['strategic'].append(item)
                else:
                    result['leverage'].append(item)
            else:
                if cat['supplier_count'] <= median_suppliers:
                    result['bottleneck'].append(item)
                else:
                    result['tactical'].append(item)
        
        return result
    
    def get_seasonality_analysis(self):
        """
        Analyze spending patterns by month across years
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

        Returns comprehensive data for the Seasonality dashboard page.
        """
        import math
        from collections import defaultdict

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

            # Savings = Total Spend × Peak Month % × Savings Rate
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
        """
        import math
        from collections import defaultdict

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

    def get_year_over_year_comparison(self):
        """
        Compare spending year over year
        """
        data = self.transactions.annotate(
            year=TruncYear('date')
        ).values('year').annotate(
            total=Sum('amount'),
            count=Count('id'),
            avg=Avg('amount')
        ).order_by('year')
        
        result = []
        for i, item in enumerate(data):
            year_data = {
                'year': item['year'].year,
                'total_spend': float(item['total']),
                'transaction_count': item['count'],
                'avg_transaction': float(item['avg'])
            }
            
            # Calculate growth if previous year exists
            if i > 0:
                prev_total = float(data[i-1]['total'])
                growth = ((float(item['total']) - prev_total) / prev_total * 100) if prev_total > 0 else 0
                year_data['growth_percentage'] = round(growth, 2)
            
            result.append(year_data)
        
        return result
    
    def get_supplier_consolidation_opportunities(self):
        """
        Identify opportunities for supplier consolidation
        """
        # Find categories with multiple suppliers
        categories_with_multiple = self.transactions.values(
            'category__name',
            'category_id'
        ).annotate(
            supplier_count=Count('supplier', distinct=True),
            total_spend=Sum('amount')
        ).filter(supplier_count__gt=2).order_by('-supplier_count')

        opportunities = []
        for cat in categories_with_multiple:
            # Get suppliers in this category
            suppliers = self.transactions.filter(
                category_id=cat['category_id']
            ).values('supplier__name').annotate(
                spend=Sum('amount')
            ).order_by('-spend')

            opportunities.append({
                'category': cat['category__name'],
                'supplier_count': cat['supplier_count'],
                'total_spend': float(cat['total_spend']),
                'suppliers': [
                    {
                        'name': s['supplier__name'],
                        'spend': float(s['spend'])
                    }
                    for s in suppliers
                ],
                'potential_savings': float(cat['total_spend'] * Decimal('0.10'))  # Estimate 10% savings
            })

        return opportunities

    def get_detailed_category_analysis(self):
        """
        Get detailed category analysis including subcategories, suppliers, and risk levels.
        Returns comprehensive data for the Categories dashboard page.
        """
        # Get category-level aggregations
        categories = list(self.transactions.values(
            'category__name',
            'category_id'
        ).annotate(
            total_spend=Sum('amount'),
            transaction_count=Count('id'),
            supplier_count=Count('supplier', distinct=True),
            subcategory_count=Count('subcategory', distinct=True)
        ).order_by('-total_spend'))

        result = []
        total_all_spend = float(sum(c['total_spend'] or 0 for c in categories))

        for cat in categories:
            category_id = cat['category_id']
            category_name = cat['category__name']
            total_spend = float(cat['total_spend'] or 0)
            supplier_count = cat['supplier_count'] or 0

            # Get subcategory breakdown for this category
            subcategories = list(self.transactions.filter(
                category_id=category_id
            ).values('subcategory').annotate(
                spend=Sum('amount'),
                transaction_count=Count('id'),
                supplier_count=Count('supplier', distinct=True)
            ).order_by('-spend'))

            # Find top subcategory
            top_subcategory = subcategories[0] if subcategories else None
            top_subcategory_name = top_subcategory['subcategory'] if top_subcategory else 'N/A'
            top_subcategory_spend = float(top_subcategory['spend']) if top_subcategory else 0

            # Calculate concentration (top subcategory spend as % of category total)
            concentration = (top_subcategory_spend / total_spend * 100) if total_spend > 0 else 0

            # Calculate risk level based on concentration and supplier diversity
            if concentration > 70 or supplier_count < 3:
                risk_level = 'high'
            elif concentration > 50 or supplier_count < 5:
                risk_level = 'medium'
            else:
                risk_level = 'low'

            result.append({
                'category': category_name,
                'category_id': category_id,
                'total_spend': total_spend,
                'percent_of_total': round((total_spend / total_all_spend * 100) if total_all_spend > 0 else 0, 2),
                'transaction_count': cat['transaction_count'] or 0,
                'subcategory_count': cat['subcategory_count'] or 0,
                'supplier_count': supplier_count,
                'avg_spend_per_supplier': round(total_spend / supplier_count, 2) if supplier_count > 0 else 0,
                'top_subcategory': top_subcategory_name,
                'top_subcategory_spend': top_subcategory_spend,
                'concentration': round(concentration, 2),
                'risk_level': risk_level,
                'subcategories': [
                    {
                        'name': sub['subcategory'] or 'Unspecified',
                        'spend': float(sub['spend'] or 0),
                        'transaction_count': sub['transaction_count'] or 0,
                        'supplier_count': sub['supplier_count'] or 0,
                        'percent_of_category': round((float(sub['spend'] or 0) / total_spend * 100) if total_spend > 0 else 0, 2)
                    }
                    for sub in subcategories
                ]
            })

        return result

    def get_detailed_supplier_analysis(self):
        """
        Get detailed supplier analysis including HHI score, concentration metrics, and category diversity.
        Returns comprehensive data for the Suppliers dashboard page.
        """
        # Get supplier-level aggregations
        suppliers = list(self.transactions.values(
            'supplier__name',
            'supplier_id'
        ).annotate(
            total_spend=Sum('amount'),
            transaction_count=Count('id'),
            category_count=Count('category', distinct=True)
        ).order_by('-total_spend'))

        if not suppliers:
            return {
                'summary': {
                    'total_suppliers': 0,
                    'total_spend': 0,
                    'hhi_score': 0,
                    'hhi_risk_level': 'low',
                    'top3_concentration': 0,
                    'top_supplier': None,
                    'top_supplier_spend': 0
                },
                'suppliers': []
            }

        total_spend = float(sum(s['total_spend'] or 0 for s in suppliers))
        total_suppliers = len(suppliers)

        # Calculate HHI (Herfindahl-Hirschman Index)
        # HHI = Σ(market share%)²
        # Range: 0-10,000
        hhi_score = 0
        supplier_list = []

        for rank, sup in enumerate(suppliers, 1):
            spend = float(sup['total_spend'] or 0)
            percent_of_total = (spend / total_spend * 100) if total_spend > 0 else 0
            hhi_score += percent_of_total ** 2

            supplier_list.append({
                'supplier': sup['supplier__name'],
                'supplier_id': sup['supplier_id'],
                'total_spend': spend,
                'percent_of_total': round(percent_of_total, 2),
                'transaction_count': sup['transaction_count'] or 0,
                'avg_transaction': round(spend / sup['transaction_count'], 2) if sup['transaction_count'] else 0,
                'category_count': sup['category_count'] or 0,
                'rank': rank
            })

        # HHI Risk Level
        # < 1,500 = Low concentration (competitive)
        # 1,500-2,500 = Moderate concentration
        # > 2,500 = High concentration (risk)
        if hhi_score < 1500:
            hhi_risk_level = 'low'
        elif hhi_score < 2500:
            hhi_risk_level = 'moderate'
        else:
            hhi_risk_level = 'high'

        # Top 3 concentration
        top3_spend = sum(s['total_spend'] for s in supplier_list[:3])
        top3_concentration = (top3_spend / total_spend * 100) if total_spend > 0 else 0

        # Top supplier
        top_supplier = supplier_list[0] if supplier_list else None

        return {
            'summary': {
                'total_suppliers': total_suppliers,
                'total_spend': total_spend,
                'hhi_score': round(hhi_score, 2),
                'hhi_risk_level': hhi_risk_level,
                'top3_concentration': round(top3_concentration, 2),
                'top_supplier': top_supplier['supplier'] if top_supplier else None,
                'top_supplier_spend': top_supplier['total_spend'] if top_supplier else 0
            },
            'suppliers': supplier_list
        }

    def get_supplier_drilldown(self, supplier_id):
        """
        Get detailed drill-down data for a specific supplier.
        Used by Pareto Analysis page when user clicks on a supplier.
        Returns category/subcategory/location breakdowns with full aggregation.
        """
        # Get supplier name
        try:
            supplier = Supplier.objects.get(id=supplier_id, organization=self.organization)
            supplier_name = supplier.name
        except Supplier.DoesNotExist:
            return None

        # Filter transactions for this supplier
        supplier_transactions = self.transactions.filter(supplier_id=supplier_id)

        if not supplier_transactions.exists():
            return {
                'supplier_id': supplier_id,
                'supplier_name': supplier_name,
                'total_spend': 0,
                'transaction_count': 0,
                'avg_transaction': 0,
                'date_range': {'min': None, 'max': None},
                'categories': [],
                'subcategories': [],
                'locations': []
            }

        # Basic metrics
        total_spend = float(supplier_transactions.aggregate(total=Sum('amount'))['total'] or 0)
        transaction_count = supplier_transactions.count()
        avg_transaction = total_spend / transaction_count if transaction_count > 0 else 0

        # Date range
        date_agg = supplier_transactions.aggregate(
            min_date=Min('date'),
            max_date=Max('date')
        )

        # Category breakdown
        categories = list(supplier_transactions.values(
            'category__name'
        ).annotate(
            spend=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-spend'))

        category_data = [
            {
                'name': cat['category__name'] or 'Unspecified',
                'spend': float(cat['spend'] or 0),
                'transaction_count': cat['transaction_count'] or 0,
                'percent_of_total': round((float(cat['spend'] or 0) / total_spend * 100) if total_spend > 0 else 0, 2)
            }
            for cat in categories
        ]

        # Subcategory breakdown (top 10)
        subcategories = list(supplier_transactions.values(
            'subcategory'
        ).annotate(
            spend=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-spend')[:10])

        subcategory_data = [
            {
                'name': sub['subcategory'] or 'Unspecified',
                'spend': float(sub['spend'] or 0),
                'transaction_count': sub['transaction_count'] or 0,
                'percent_of_total': round((float(sub['spend'] or 0) / total_spend * 100) if total_spend > 0 else 0, 2)
            }
            for sub in subcategories
        ]

        # Location breakdown (top 10)
        locations = list(supplier_transactions.values(
            'location'
        ).annotate(
            spend=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-spend')[:10])

        location_data = [
            {
                'name': loc['location'] or 'Unspecified',
                'spend': float(loc['spend'] or 0),
                'transaction_count': loc['transaction_count'] or 0,
                'percent_of_total': round((float(loc['spend'] or 0) / total_spend * 100) if total_spend > 0 else 0, 2)
            }
            for loc in locations
        ]

        return {
            'supplier_id': supplier_id,
            'supplier_name': supplier_name,
            'total_spend': total_spend,
            'transaction_count': transaction_count,
            'avg_transaction': round(avg_transaction, 2),
            'date_range': {
                'min': date_agg['min_date'].isoformat() if date_agg['min_date'] else None,
                'max': date_agg['max_date'].isoformat() if date_agg['max_date'] else None
            },
            'categories': category_data,
            'subcategories': subcategory_data,
            'locations': location_data
        }

    def get_detailed_stratification(self):
        """
        Get detailed spend stratification analysis by spend bands.
        Returns comprehensive data for the SpendStratification dashboard page.
        Groups transactions by their spend_band field and calculates metrics.
        """
        # Define spend bands (must match frontend definitions)
        SPEND_BANDS = [
            {'name': '0 - 1K', 'label': '0-1K', 'min': 0, 'max': 1000},
            {'name': '1K - 2K', 'label': '1K-2K', 'min': 1000, 'max': 2000},
            {'name': '2K - 5K', 'label': '2K-5K', 'min': 2000, 'max': 5000},
            {'name': '5K - 10K', 'label': '5K-10K', 'min': 5000, 'max': 10000},
            {'name': '10K - 25K', 'label': '10K-25K', 'min': 10000, 'max': 25000},
            {'name': '25K - 50K', 'label': '25K-50K', 'min': 25000, 'max': 50000},
            {'name': '50K - 100K', 'label': '50K-100K', 'min': 50000, 'max': 100000},
            {'name': '100K - 500K', 'label': '100K-500K', 'min': 100000, 'max': 500000},
            {'name': '500K - 1M', 'label': '500K-1M', 'min': 500000, 'max': 1000000},
            {'name': '1M and Above', 'label': '1M+', 'min': 1000000, 'max': float('inf')},
        ]

        # Define segments (Strategic/Leverage/Routine/Tactical)
        SEGMENTS = [
            {'name': 'Strategic', 'min': 1000000, 'max': float('inf'), 'strategy': 'Partnership & Innovation'},
            {'name': 'Leverage', 'min': 100000, 'max': 1000000, 'strategy': 'Competitive Bidding'},
            {'name': 'Routine', 'min': 10000, 'max': 100000, 'strategy': 'Efficiency & Automation'},
            {'name': 'Tactical', 'min': 0, 'max': 10000, 'strategy': 'Consolidation'},
        ]

        # Group by spend_band field from transactions
        band_data = list(self.transactions.values('spend_band').annotate(
            total_spend=Sum('amount'),
            transaction_count=Count('id'),
            supplier_count=Count('supplier', distinct=True)
        ))

        # Create a map for quick lookup
        band_map = {b['spend_band']: b for b in band_data}

        # Calculate total spend across all bands
        total_spend = float(sum(b['total_spend'] or 0 for b in band_data))

        # Build spend bands result
        spend_bands = []
        for band_def in SPEND_BANDS:
            band_name = band_def['name']
            band_info = band_map.get(band_name, {
                'total_spend': 0,
                'transaction_count': 0,
                'supplier_count': 0
            })

            band_spend = float(band_info.get('total_spend') or 0)
            suppliers = band_info.get('supplier_count') or 0
            transactions = band_info.get('transaction_count') or 0
            percent_of_total = (band_spend / total_spend * 100) if total_spend > 0 else 0
            avg_spend_per_supplier = band_spend / suppliers if suppliers > 0 else 0

            # Determine strategic importance and risk level
            if percent_of_total > 30:
                strategic_importance = 'Critical'
                risk_level = 'High'
            elif percent_of_total > 15:
                strategic_importance = 'Strategic'
                risk_level = 'Medium'
            else:
                strategic_importance = 'Tactical'
                risk_level = 'Low'

            spend_bands.append({
                'band': band_name,
                'label': band_def['label'],
                'min': band_def['min'],
                'max': band_def['max'] if band_def['max'] != float('inf') else None,
                'total_spend': band_spend,
                'percent_of_total': round(percent_of_total, 2),
                'suppliers': suppliers,
                'transactions': transactions,
                'avg_spend_per_supplier': round(avg_spend_per_supplier, 2),
                'strategic_importance': strategic_importance,
                'risk_level': risk_level
            })

        # Build segments result
        segments = []
        for seg_def in SEGMENTS:
            # Find spend bands that fall within this segment
            segment_spend = 0
            segment_suppliers = 0
            segment_transactions = 0

            for band in spend_bands:
                band_min = band['min']
                if band_min >= seg_def['min'] and band_min < seg_def['max']:
                    segment_spend += band['total_spend']
                    segment_suppliers += band['suppliers']
                    segment_transactions += band['transactions']

            percent_of_total = (segment_spend / total_spend * 100) if total_spend > 0 else 0

            # Format spend range label
            if seg_def['min'] == 0:
                spend_range = f"<${int(seg_def['max'] / 1000)}K"
            elif seg_def['max'] == float('inf'):
                spend_range = f">${int(seg_def['min'] / 1000000)}M"
            else:
                spend_range = f"${int(seg_def['min'] / 1000)}K-${int(seg_def['max'] / 1000)}K"

            segments.append({
                'segment': seg_def['name'],
                'spend_range': spend_range,
                'min': seg_def['min'],
                'max': seg_def['max'] if seg_def['max'] != float('inf') else None,
                'total_spend': segment_spend,
                'percent_of_total': round(percent_of_total, 2),
                'suppliers': segment_suppliers,
                'transactions': segment_transactions,
                'strategy': seg_def['strategy']
            })

        # Calculate summary metrics
        active_spend_bands = len([b for b in spend_bands if b['suppliers'] > 0])
        strategic_bands = len([b for b in spend_bands if b['strategic_importance'] in ['Strategic', 'Critical'] and b['suppliers'] > 0])
        high_risk_bands = len([b for b in spend_bands if b['risk_level'] == 'High' and b['suppliers'] > 0])
        complex_bands = len([b for b in spend_bands if b['suppliers'] >= 50])

        # Find highest impact band
        highest_impact = max(spend_bands, key=lambda b: b['percent_of_total']) if spend_bands else None

        # Find most fragmented band
        most_fragmented = max(spend_bands, key=lambda b: b['suppliers']) if spend_bands else None

        # Average suppliers per band
        total_suppliers_in_bands = sum(b['suppliers'] for b in spend_bands)
        avg_suppliers_per_band = total_suppliers_in_bands / len(spend_bands) if spend_bands else 0

        # Strategic segment for risk assessment
        strategic_segment = next((s for s in segments if s['segment'] == 'Strategic'), None)
        strategic_concentration = strategic_segment['percent_of_total'] if strategic_segment else 0

        # Overall risk assessment
        if strategic_concentration > 60:
            overall_risk = 'HIGH - CONCENTRATION RISK REQUIRES IMMEDIATE ATTENTION'
        elif strategic_concentration > 40:
            overall_risk = 'MEDIUM - MONITOR CONCENTRATION'
        else:
            overall_risk = 'LOW'

        # Generate recommendations
        recommendations = []
        if highest_impact and highest_impact['percent_of_total'] > 50:
            recommendations.append(f"Implement supplier diversification strategy within the {highest_impact['label']} band")
            recommendations.append("Evaluate supplier consolidation opportunities to reduce administrative burden")

        for band in spend_bands:
            if band['suppliers'] > 100 and 'K' in band['label'] and 'M' not in band['label']:
                recommendations.append(f"{band['label']}: Consider supplier consolidation to improve efficiency")
            if band['percent_of_total'] > 10 and band['suppliers'] < 5 and band['suppliers'] > 0:
                recommendations.append(f"{band['label']}: High concentration with few suppliers - diversification recommended")

        return {
            'summary': {
                'total_spend': total_spend,
                'active_spend_bands': active_spend_bands,
                'strategic_bands': strategic_bands,
                'high_risk_bands': high_risk_bands,
                'complex_bands': complex_bands,
                'highest_impact_band': highest_impact['label'] if highest_impact else 'N/A',
                'highest_impact_percent': highest_impact['percent_of_total'] if highest_impact else 0,
                'most_fragmented_band': most_fragmented['label'] if most_fragmented else 'N/A',
                'most_fragmented_suppliers': most_fragmented['suppliers'] if most_fragmented else 0,
                'avg_suppliers_per_band': round(avg_suppliers_per_band),
                'overall_risk': overall_risk,
                'recommendations': recommendations[:5]  # Limit to 5
            },
            'spend_bands': spend_bands,
            'segments': segments
        }

    def get_stratification_segment_drilldown(self, segment_name):
        """
        Get detailed drill-down data for a specific segment (Strategic/Leverage/Routine/Tactical).
        Returns supplier list, subcategory breakdown, and location breakdown.
        """
        # Define segments
        SEGMENTS = {
            'Strategic': {'min': 1000000, 'max': float('inf')},
            'Leverage': {'min': 100000, 'max': 1000000},
            'Routine': {'min': 10000, 'max': 100000},
            'Tactical': {'min': 0, 'max': 10000},
        }

        # Define spend bands for each segment
        SPEND_BANDS = [
            {'name': '0 - 1K', 'min': 0},
            {'name': '1K - 2K', 'min': 1000},
            {'name': '2K - 5K', 'min': 2000},
            {'name': '5K - 10K', 'min': 5000},
            {'name': '10K - 25K', 'min': 10000},
            {'name': '25K - 50K', 'min': 25000},
            {'name': '50K - 100K', 'min': 50000},
            {'name': '100K - 500K', 'min': 100000},
            {'name': '500K - 1M', 'min': 500000},
            {'name': '1M and Above', 'min': 1000000},
        ]

        if segment_name not in SEGMENTS:
            return None

        seg_def = SEGMENTS[segment_name]

        # Find spend band names that belong to this segment
        segment_band_names = [
            band['name'] for band in SPEND_BANDS
            if band['min'] >= seg_def['min'] and band['min'] < seg_def['max']
        ]

        if not segment_band_names:
            return {
                'segment': segment_name,
                'total_spend': 0,
                'supplier_count': 0,
                'transaction_count': 0,
                'avg_spend_per_supplier': 0,
                'suppliers': [],
                'subcategories': [],
                'locations': []
            }

        # Filter transactions by spend_band
        segment_transactions = self.transactions.filter(spend_band__in=segment_band_names)

        if not segment_transactions.exists():
            return {
                'segment': segment_name,
                'total_spend': 0,
                'supplier_count': 0,
                'transaction_count': 0,
                'avg_spend_per_supplier': 0,
                'suppliers': [],
                'subcategories': [],
                'locations': []
            }

        # Calculate totals
        total_spend = float(segment_transactions.aggregate(total=Sum('amount'))['total'] or 0)
        transaction_count = segment_transactions.count()

        # Get supplier breakdown
        suppliers_data = list(segment_transactions.values(
            'supplier__name',
            'supplier_id'
        ).annotate(
            total_spend=Sum('amount'),
            transaction_count=Count('id'),
            subcategory_count=Count('subcategory', distinct=True),
            location_count=Count('location', distinct=True)
        ).order_by('-total_spend'))

        supplier_count = len(suppliers_data)
        avg_spend_per_supplier = total_spend / supplier_count if supplier_count > 0 else 0

        suppliers = [
            {
                'name': s['supplier__name'],
                'supplier_id': s['supplier_id'],
                'total_spend': float(s['total_spend'] or 0),
                'percent_of_segment': round((float(s['total_spend'] or 0) / total_spend * 100) if total_spend > 0 else 0, 2),
                'transactions': s['transaction_count'] or 0,
                'subcategory_count': s['subcategory_count'] or 0,
                'location_count': s['location_count'] or 0
            }
            for s in suppliers_data
        ]

        # Get subcategory breakdown (top 10)
        subcategories_data = list(segment_transactions.values('subcategory').annotate(
            spend=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-spend')[:10])

        subcategories = [
            {
                'name': sub['subcategory'] or 'Unspecified',
                'spend': float(sub['spend'] or 0),
                'percent_of_segment': round((float(sub['spend'] or 0) / total_spend * 100) if total_spend > 0 else 0, 2),
                'transactions': sub['transaction_count'] or 0
            }
            for sub in subcategories_data
        ]

        # Get location breakdown (top 10)
        locations_data = list(segment_transactions.values('location').annotate(
            spend=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-spend')[:10])

        locations = [
            {
                'name': loc['location'] or 'Unspecified',
                'spend': float(loc['spend'] or 0),
                'percent_of_segment': round((float(loc['spend'] or 0) / total_spend * 100) if total_spend > 0 else 0, 2),
                'transactions': loc['transaction_count'] or 0
            }
            for loc in locations_data
        ]

        return {
            'segment': segment_name,
            'total_spend': total_spend,
            'supplier_count': supplier_count,
            'transaction_count': transaction_count,
            'avg_spend_per_supplier': round(avg_spend_per_supplier, 2),
            'suppliers': suppliers,
            'subcategories': subcategories,
            'locations': locations
        }

    def get_stratification_band_drilldown(self, band_name):
        """
        Get detailed drill-down data for a specific spend band.
        Returns supplier list, subcategory breakdown, and location breakdown.
        """
        # Define valid spend bands
        VALID_BANDS = [
            '0 - 1K', '1K - 2K', '2K - 5K', '5K - 10K', '10K - 25K',
            '25K - 50K', '50K - 100K', '100K - 500K', '500K - 1M', '1M and Above'
        ]

        if band_name not in VALID_BANDS:
            return None

        # Filter transactions by spend_band
        band_transactions = self.transactions.filter(spend_band=band_name)

        if not band_transactions.exists():
            return {
                'band': band_name,
                'total_spend': 0,
                'supplier_count': 0,
                'transaction_count': 0,
                'avg_spend_per_supplier': 0,
                'suppliers': [],
                'subcategories': [],
                'locations': []
            }

        # Calculate totals
        total_spend = float(band_transactions.aggregate(total=Sum('amount'))['total'] or 0)
        transaction_count = band_transactions.count()

        # Get supplier breakdown
        suppliers_data = list(band_transactions.values(
            'supplier__name',
            'supplier_id'
        ).annotate(
            total_spend=Sum('amount'),
            transaction_count=Count('id'),
            subcategory_count=Count('subcategory', distinct=True),
            location_count=Count('location', distinct=True)
        ).order_by('-total_spend'))

        supplier_count = len(suppliers_data)
        avg_spend_per_supplier = total_spend / supplier_count if supplier_count > 0 else 0

        suppliers = [
            {
                'name': s['supplier__name'],
                'supplier_id': s['supplier_id'],
                'total_spend': float(s['total_spend'] or 0),
                'percent_of_band': round((float(s['total_spend'] or 0) / total_spend * 100) if total_spend > 0 else 0, 2),
                'transactions': s['transaction_count'] or 0,
                'subcategory_count': s['subcategory_count'] or 0,
                'location_count': s['location_count'] or 0
            }
            for s in suppliers_data
        ]

        # Get subcategory breakdown (top 10)
        subcategories_data = list(band_transactions.values('subcategory').annotate(
            spend=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-spend')[:10])

        subcategories = [
            {
                'name': sub['subcategory'] or 'Unspecified',
                'spend': float(sub['spend'] or 0),
                'percent_of_band': round((float(sub['spend'] or 0) / total_spend * 100) if total_spend > 0 else 0, 2),
                'transactions': sub['transaction_count'] or 0
            }
            for sub in subcategories_data
        ]

        # Get location breakdown (top 10)
        locations_data = list(band_transactions.values('location').annotate(
            spend=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-spend')[:10])

        locations = [
            {
                'name': loc['location'] or 'Unspecified',
                'spend': float(loc['spend'] or 0),
                'percent_of_band': round((float(loc['spend'] or 0) / total_spend * 100) if total_spend > 0 else 0, 2),
                'transactions': loc['transaction_count'] or 0
            }
            for loc in locations_data
        ]

        return {
            'band': band_name,
            'total_spend': total_spend,
            'supplier_count': supplier_count,
            'transaction_count': transaction_count,
            'avg_spend_per_supplier': round(avg_spend_per_supplier, 2),
            'suppliers': suppliers,
            'subcategories': subcategories,
            'locations': locations
        }

    def _get_fiscal_year(self, date, use_fiscal_year=True):
        """
        Get fiscal year for a date.
        Fiscal year runs Jul-Jun, so Jul 2024 = FY2025.
        """
        if not use_fiscal_year:
            return date.year
        # If month >= 7 (July), it's the next fiscal year
        if date.month >= 7:
            return date.year + 1
        return date.year

    def _get_fiscal_month(self, date):
        """
        Get fiscal month number (1-12, where 1 = July, 12 = June).
        """
        month = date.month
        if month >= 7:
            return month - 6  # Jul=1, Aug=2, ..., Dec=6
        return month + 6  # Jan=7, Feb=8, ..., Jun=12

    def get_detailed_year_over_year(self, year1=None, year2=None, use_fiscal_year=True):
        """
        Get detailed year-over-year comparison with category and supplier breakdowns.
        Returns comprehensive data for the Year-over-Year dashboard page.

        Args:
            year1: First fiscal year to compare (optional, defaults to previous FY)
            year2: Second fiscal year to compare (optional, defaults to current FY)
            use_fiscal_year: Whether to use fiscal year (Jul-Jun) or calendar year
        """
        from collections import defaultdict

        # Get all transactions with dates
        all_transactions = list(self.transactions.select_related('category', 'supplier').values(
            'id', 'amount', 'date', 'category__name', 'category_id', 'supplier__name', 'supplier_id'
        ))

        if not all_transactions:
            return {
                'summary': {
                    'year1': 'FY2024' if use_fiscal_year else '2024',
                    'year2': 'FY2025' if use_fiscal_year else '2025',
                    'year1_total_spend': 0,
                    'year2_total_spend': 0,
                    'spend_change': 0,
                    'spend_change_pct': 0,
                    'year1_transactions': 0,
                    'year2_transactions': 0,
                    'year1_suppliers': 0,
                    'year2_suppliers': 0,
                    'year1_avg_transaction': 0,
                    'year2_avg_transaction': 0
                },
                'monthly_comparison': [],
                'category_comparison': [],
                'supplier_comparison': [],
                'top_gainers': [],
                'top_decliners': [],
                'available_years': []
            }

        # Calculate fiscal years for all transactions
        for t in all_transactions:
            t['fiscal_year'] = self._get_fiscal_year(t['date'], use_fiscal_year)
            t['fiscal_month'] = self._get_fiscal_month(t['date'])

        # Find available fiscal years
        available_years = sorted(set(t['fiscal_year'] for t in all_transactions))

        # Default years if not specified
        if year1 is None or year2 is None:
            if len(available_years) >= 2:
                year1 = year1 or available_years[-2]
                year2 = year2 or available_years[-1]
            elif len(available_years) == 1:
                year1 = year1 or available_years[0]
                year2 = year2 or available_years[0]
            else:
                year1, year2 = 2024, 2025

        year_prefix = 'FY' if use_fiscal_year else ''

        # Filter transactions by year
        year1_txns = [t for t in all_transactions if t['fiscal_year'] == year1]
        year2_txns = [t for t in all_transactions if t['fiscal_year'] == year2]

        # Calculate summary stats
        year1_total = sum(float(t['amount'] or 0) for t in year1_txns)
        year2_total = sum(float(t['amount'] or 0) for t in year2_txns)
        year1_count = len(year1_txns)
        year2_count = len(year2_txns)
        year1_suppliers = len(set(t['supplier_id'] for t in year1_txns if t['supplier_id']))
        year2_suppliers = len(set(t['supplier_id'] for t in year2_txns if t['supplier_id']))

        spend_change = year2_total - year1_total
        spend_change_pct = ((year2_total - year1_total) / year1_total * 100) if year1_total > 0 else 0

        # Monthly comparison
        fiscal_month_names = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']

        monthly_year1 = defaultdict(float)
        monthly_year2 = defaultdict(float)
        for t in year1_txns:
            monthly_year1[t['fiscal_month']] += float(t['amount'] or 0)
        for t in year2_txns:
            monthly_year2[t['fiscal_month']] += float(t['amount'] or 0)

        monthly_comparison = []
        for i in range(1, 13):
            y1_spend = monthly_year1.get(i, 0)
            y2_spend = monthly_year2.get(i, 0)
            change_pct = ((y2_spend - y1_spend) / y1_spend * 100) if y1_spend > 0 else (100 if y2_spend > 0 else 0)
            monthly_comparison.append({
                'month': fiscal_month_names[i - 1],
                'fiscal_month': i,
                'year1_spend': round(y1_spend, 2),
                'year2_spend': round(y2_spend, 2),
                'change_pct': round(change_pct, 2)
            })

        # Category comparison
        cat_year1 = defaultdict(lambda: {'spend': 0, 'id': None, 'name': ''})
        cat_year2 = defaultdict(lambda: {'spend': 0, 'id': None, 'name': ''})
        for t in year1_txns:
            cat_name = t['category__name'] or 'Uncategorized'
            cat_year1[cat_name]['spend'] += float(t['amount'] or 0)
            cat_year1[cat_name]['id'] = t['category_id']
            cat_year1[cat_name]['name'] = cat_name
        for t in year2_txns:
            cat_name = t['category__name'] or 'Uncategorized'
            cat_year2[cat_name]['spend'] += float(t['amount'] or 0)
            cat_year2[cat_name]['id'] = t['category_id']
            cat_year2[cat_name]['name'] = cat_name

        all_categories = set(cat_year1.keys()) | set(cat_year2.keys())
        category_comparison = []
        for cat_name in all_categories:
            y1_data = cat_year1.get(cat_name, {'spend': 0, 'id': None, 'name': cat_name})
            y2_data = cat_year2.get(cat_name, {'spend': 0, 'id': None, 'name': cat_name})
            y1_spend = y1_data['spend']
            y2_spend = y2_data['spend']
            change = y2_spend - y1_spend
            change_pct = ((y2_spend - y1_spend) / y1_spend * 100) if y1_spend > 0 else (100 if y2_spend > 0 else 0)
            category_comparison.append({
                'category': cat_name,
                'category_id': y1_data['id'] or y2_data['id'],
                'year1_spend': round(y1_spend, 2),
                'year2_spend': round(y2_spend, 2),
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'year1_pct_of_total': round((y1_spend / year1_total * 100) if year1_total > 0 else 0, 2),
                'year2_pct_of_total': round((y2_spend / year2_total * 100) if year2_total > 0 else 0, 2)
            })

        # Sort by absolute year2 spend descending
        category_comparison.sort(key=lambda x: x['year2_spend'], reverse=True)

        # Top gainers and decliners (categories with data in both years)
        comparable_cats = [c for c in category_comparison if c['year1_spend'] > 0]
        top_gainers = sorted(comparable_cats, key=lambda x: x['change_pct'], reverse=True)[:5]
        top_decliners = sorted(comparable_cats, key=lambda x: x['change_pct'])[:5]

        # Supplier comparison
        sup_year1 = defaultdict(lambda: {'spend': 0, 'id': None, 'name': '', 'count': 0})
        sup_year2 = defaultdict(lambda: {'spend': 0, 'id': None, 'name': '', 'count': 0})
        for t in year1_txns:
            sup_name = t['supplier__name'] or 'Unknown'
            sup_year1[sup_name]['spend'] += float(t['amount'] or 0)
            sup_year1[sup_name]['id'] = t['supplier_id']
            sup_year1[sup_name]['name'] = sup_name
            sup_year1[sup_name]['count'] += 1
        for t in year2_txns:
            sup_name = t['supplier__name'] or 'Unknown'
            sup_year2[sup_name]['spend'] += float(t['amount'] or 0)
            sup_year2[sup_name]['id'] = t['supplier_id']
            sup_year2[sup_name]['name'] = sup_name
            sup_year2[sup_name]['count'] += 1

        all_suppliers = set(sup_year1.keys()) | set(sup_year2.keys())
        supplier_comparison = []
        for sup_name in all_suppliers:
            y1_data = sup_year1.get(sup_name, {'spend': 0, 'id': None, 'name': sup_name, 'count': 0})
            y2_data = sup_year2.get(sup_name, {'spend': 0, 'id': None, 'name': sup_name, 'count': 0})
            y1_spend = y1_data['spend']
            y2_spend = y2_data['spend']
            change = y2_spend - y1_spend
            change_pct = ((y2_spend - y1_spend) / y1_spend * 100) if y1_spend > 0 else (100 if y2_spend > 0 else 0)
            supplier_comparison.append({
                'supplier': sup_name,
                'supplier_id': y1_data['id'] or y2_data['id'],
                'year1_spend': round(y1_spend, 2),
                'year2_spend': round(y2_spend, 2),
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'year1_transactions': y1_data['count'],
                'year2_transactions': y2_data['count']
            })

        # Sort by combined spend descending
        supplier_comparison.sort(key=lambda x: x['year1_spend'] + x['year2_spend'], reverse=True)
        # Limit to top 50 suppliers
        supplier_comparison = supplier_comparison[:50]

        return {
            'summary': {
                'year1': f'{year_prefix}{year1}',
                'year2': f'{year_prefix}{year2}',
                'year1_total_spend': round(year1_total, 2),
                'year2_total_spend': round(year2_total, 2),
                'spend_change': round(spend_change, 2),
                'spend_change_pct': round(spend_change_pct, 2),
                'year1_transactions': year1_count,
                'year2_transactions': year2_count,
                'year1_suppliers': year1_suppliers,
                'year2_suppliers': year2_suppliers,
                'year1_avg_transaction': round(year1_total / year1_count, 2) if year1_count > 0 else 0,
                'year2_avg_transaction': round(year2_total / year2_count, 2) if year2_count > 0 else 0
            },
            'monthly_comparison': monthly_comparison,
            'category_comparison': category_comparison,
            'supplier_comparison': supplier_comparison,
            'top_gainers': top_gainers,
            'top_decliners': top_decliners,
            'available_years': available_years
        }

    def get_yoy_category_drilldown(self, category_id, year1=None, year2=None, use_fiscal_year=True):
        """
        Get detailed YoY comparison for a specific category.
        Returns supplier-level breakdowns within the category.
        """
        from collections import defaultdict

        # Verify category exists
        try:
            category = Category.objects.get(id=category_id, organization=self.organization)
            category_name = category.name
        except Category.DoesNotExist:
            return None

        # Get transactions for this category
        cat_transactions = list(self.transactions.filter(category_id=category_id).select_related('supplier').values(
            'id', 'amount', 'date', 'supplier__name', 'supplier_id'
        ))

        if not cat_transactions:
            return {
                'category': category_name,
                'category_id': category_id,
                'year1': 'FY2024' if use_fiscal_year else '2024',
                'year2': 'FY2025' if use_fiscal_year else '2025',
                'year1_total': 0,
                'year2_total': 0,
                'change_pct': 0,
                'suppliers': [],
                'monthly_breakdown': []
            }

        # Calculate fiscal years
        for t in cat_transactions:
            t['fiscal_year'] = self._get_fiscal_year(t['date'], use_fiscal_year)
            t['fiscal_month'] = self._get_fiscal_month(t['date'])

        # Determine years
        available_years = sorted(set(t['fiscal_year'] for t in cat_transactions))
        if year1 is None or year2 is None:
            if len(available_years) >= 2:
                year1 = year1 or available_years[-2]
                year2 = year2 or available_years[-1]
            else:
                year1 = year1 or (available_years[0] if available_years else 2024)
                year2 = year2 or (available_years[0] if available_years else 2025)

        year_prefix = 'FY' if use_fiscal_year else ''

        year1_txns = [t for t in cat_transactions if t['fiscal_year'] == year1]
        year2_txns = [t for t in cat_transactions if t['fiscal_year'] == year2]

        year1_total = sum(float(t['amount'] or 0) for t in year1_txns)
        year2_total = sum(float(t['amount'] or 0) for t in year2_txns)
        change_pct = ((year2_total - year1_total) / year1_total * 100) if year1_total > 0 else (100 if year2_total > 0 else 0)

        # Supplier breakdown
        sup_year1 = defaultdict(lambda: {'spend': 0, 'id': None, 'name': ''})
        sup_year2 = defaultdict(lambda: {'spend': 0, 'id': None, 'name': ''})
        for t in year1_txns:
            sup_name = t['supplier__name'] or 'Unknown'
            sup_year1[sup_name]['spend'] += float(t['amount'] or 0)
            sup_year1[sup_name]['id'] = t['supplier_id']
            sup_year1[sup_name]['name'] = sup_name
        for t in year2_txns:
            sup_name = t['supplier__name'] or 'Unknown'
            sup_year2[sup_name]['spend'] += float(t['amount'] or 0)
            sup_year2[sup_name]['id'] = t['supplier_id']
            sup_year2[sup_name]['name'] = sup_name

        all_suppliers = set(sup_year1.keys()) | set(sup_year2.keys())
        suppliers = []
        for sup_name in all_suppliers:
            y1_data = sup_year1.get(sup_name, {'spend': 0, 'id': None, 'name': sup_name})
            y2_data = sup_year2.get(sup_name, {'spend': 0, 'id': None, 'name': sup_name})
            y1_spend = y1_data['spend']
            y2_spend = y2_data['spend']
            change = y2_spend - y1_spend
            sup_change_pct = ((y2_spend - y1_spend) / y1_spend * 100) if y1_spend > 0 else (100 if y2_spend > 0 else 0)
            suppliers.append({
                'name': sup_name,
                'supplier_id': y1_data['id'] or y2_data['id'],
                'year1_spend': round(y1_spend, 2),
                'year2_spend': round(y2_spend, 2),
                'change': round(change, 2),
                'change_pct': round(sup_change_pct, 2)
            })

        suppliers.sort(key=lambda x: x['year1_spend'] + x['year2_spend'], reverse=True)

        # Monthly breakdown
        fiscal_month_names = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        monthly_year1 = defaultdict(float)
        monthly_year2 = defaultdict(float)
        for t in year1_txns:
            monthly_year1[t['fiscal_month']] += float(t['amount'] or 0)
        for t in year2_txns:
            monthly_year2[t['fiscal_month']] += float(t['amount'] or 0)

        monthly_breakdown = []
        for i in range(1, 13):
            monthly_breakdown.append({
                'month': fiscal_month_names[i - 1],
                'year1_spend': round(monthly_year1.get(i, 0), 2),
                'year2_spend': round(monthly_year2.get(i, 0), 2)
            })

        return {
            'category': category_name,
            'category_id': category_id,
            'year1': f'{year_prefix}{year1}',
            'year2': f'{year_prefix}{year2}',
            'year1_total': round(year1_total, 2),
            'year2_total': round(year2_total, 2),
            'change_pct': round(change_pct, 2),
            'suppliers': suppliers,
            'monthly_breakdown': monthly_breakdown
        }

    def get_yoy_supplier_drilldown(self, supplier_id, year1=None, year2=None, use_fiscal_year=True):
        """
        Get detailed YoY comparison for a specific supplier.
        Returns category-level breakdowns for the supplier.
        """
        from collections import defaultdict

        # Verify supplier exists
        try:
            supplier = Supplier.objects.get(id=supplier_id, organization=self.organization)
            supplier_name = supplier.name
        except Supplier.DoesNotExist:
            return None

        # Get transactions for this supplier
        sup_transactions = list(self.transactions.filter(supplier_id=supplier_id).select_related('category').values(
            'id', 'amount', 'date', 'category__name', 'category_id'
        ))

        if not sup_transactions:
            return {
                'supplier': supplier_name,
                'supplier_id': supplier_id,
                'year1': 'FY2024' if use_fiscal_year else '2024',
                'year2': 'FY2025' if use_fiscal_year else '2025',
                'year1_total': 0,
                'year2_total': 0,
                'change_pct': 0,
                'categories': [],
                'monthly_breakdown': []
            }

        # Calculate fiscal years
        for t in sup_transactions:
            t['fiscal_year'] = self._get_fiscal_year(t['date'], use_fiscal_year)
            t['fiscal_month'] = self._get_fiscal_month(t['date'])

        # Determine years
        available_years = sorted(set(t['fiscal_year'] for t in sup_transactions))
        if year1 is None or year2 is None:
            if len(available_years) >= 2:
                year1 = year1 or available_years[-2]
                year2 = year2 or available_years[-1]
            else:
                year1 = year1 or (available_years[0] if available_years else 2024)
                year2 = year2 or (available_years[0] if available_years else 2025)

        year_prefix = 'FY' if use_fiscal_year else ''

        year1_txns = [t for t in sup_transactions if t['fiscal_year'] == year1]
        year2_txns = [t for t in sup_transactions if t['fiscal_year'] == year2]

        year1_total = sum(float(t['amount'] or 0) for t in year1_txns)
        year2_total = sum(float(t['amount'] or 0) for t in year2_txns)
        change_pct = ((year2_total - year1_total) / year1_total * 100) if year1_total > 0 else (100 if year2_total > 0 else 0)

        # Category breakdown
        cat_year1 = defaultdict(lambda: {'spend': 0, 'id': None, 'name': ''})
        cat_year2 = defaultdict(lambda: {'spend': 0, 'id': None, 'name': ''})
        for t in year1_txns:
            cat_name = t['category__name'] or 'Uncategorized'
            cat_year1[cat_name]['spend'] += float(t['amount'] or 0)
            cat_year1[cat_name]['id'] = t['category_id']
            cat_year1[cat_name]['name'] = cat_name
        for t in year2_txns:
            cat_name = t['category__name'] or 'Uncategorized'
            cat_year2[cat_name]['spend'] += float(t['amount'] or 0)
            cat_year2[cat_name]['id'] = t['category_id']
            cat_year2[cat_name]['name'] = cat_name

        all_categories = set(cat_year1.keys()) | set(cat_year2.keys())
        categories = []
        for cat_name in all_categories:
            y1_data = cat_year1.get(cat_name, {'spend': 0, 'id': None, 'name': cat_name})
            y2_data = cat_year2.get(cat_name, {'spend': 0, 'id': None, 'name': cat_name})
            y1_spend = y1_data['spend']
            y2_spend = y2_data['spend']
            change = y2_spend - y1_spend
            cat_change_pct = ((y2_spend - y1_spend) / y1_spend * 100) if y1_spend > 0 else (100 if y2_spend > 0 else 0)
            categories.append({
                'name': cat_name,
                'category_id': y1_data['id'] or y2_data['id'],
                'year1_spend': round(y1_spend, 2),
                'year2_spend': round(y2_spend, 2),
                'change': round(change, 2),
                'change_pct': round(cat_change_pct, 2)
            })

        categories.sort(key=lambda x: x['year1_spend'] + x['year2_spend'], reverse=True)

        # Monthly breakdown
        fiscal_month_names = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        monthly_year1 = defaultdict(float)
        monthly_year2 = defaultdict(float)
        for t in year1_txns:
            monthly_year1[t['fiscal_month']] += float(t['amount'] or 0)
        for t in year2_txns:
            monthly_year2[t['fiscal_month']] += float(t['amount'] or 0)

        monthly_breakdown = []
        for i in range(1, 13):
            monthly_breakdown.append({
                'month': fiscal_month_names[i - 1],
                'year1_spend': round(monthly_year1.get(i, 0), 2),
                'year2_spend': round(monthly_year2.get(i, 0), 2)
            })

        return {
            'supplier': supplier_name,
            'supplier_id': supplier_id,
            'year1': f'{year_prefix}{year1}',
            'year2': f'{year_prefix}{year2}',
            'year1_total': round(year1_total, 2),
            'year2_total': round(year2_total, 2),
            'change_pct': round(change_pct, 2),
            'categories': categories,
            'monthly_breakdown': monthly_breakdown
        }

    def get_detailed_tail_spend(self, threshold=50000):
        """
        Get detailed tail spend analysis using dollar threshold.
        Tail vendors are those with total spend below the threshold.

        Args:
            threshold: Dollar amount threshold for tail classification (default $50,000)

        Returns comprehensive data for the Tail Spend dashboard page including:
        - Summary stats (total vendors, tail count, tail spend, savings opportunity)
        - Segments (micro <$10K, small $10K-$50K, non-tail >$50K)
        - Pareto data (top 20 vendors with cumulative %)
        - Category analysis (tail metrics per category)
        - Consolidation opportunities
        """
        from collections import defaultdict

        # Segment thresholds
        MICRO_THRESHOLD = 10000
        SMALL_THRESHOLD = threshold  # Default $50K

        # Get supplier-level aggregations
        suppliers = list(self.transactions.values(
            'supplier__name',
            'supplier_id'
        ).annotate(
            total_spend=Sum('amount'),
            transaction_count=Count('id'),
            category_count=Count('category', distinct=True),
            location_count=Count('location', distinct=True)
        ).order_by('-total_spend'))

        if not suppliers:
            return {
                'summary': {
                    'total_vendors': 0,
                    'tail_vendor_count': 0,
                    'tail_spend': 0,
                    'tail_percentage': 0,
                    'total_spend': 0,
                    'savings_opportunity': 0,
                    'vendor_ratio': 0
                },
                'segments': {
                    'micro': {'count': 0, 'spend': 0, 'transactions': 0, 'avg_spend_per_vendor': 0},
                    'small': {'count': 0, 'spend': 0, 'transactions': 0, 'avg_spend_per_vendor': 0},
                    'non_tail': {'count': 0, 'spend': 0, 'transactions': 0, 'avg_spend_per_vendor': 0}
                },
                'pareto_data': [],
                'category_analysis': [],
                'consolidation_opportunities': {
                    'total_opportunities': 0,
                    'total_savings': 0,
                    'top_type': 'N/A',
                    'multi_category': [],
                    'category': [],
                    'geographic': []
                }
            }

        total_spend = float(sum(s['total_spend'] or 0 for s in suppliers))
        total_vendors = len(suppliers)

        # Classify suppliers into segments
        micro_suppliers = []
        small_suppliers = []
        non_tail_suppliers = []

        for sup in suppliers:
            spend = float(sup['total_spend'] or 0)
            if spend < MICRO_THRESHOLD:
                micro_suppliers.append(sup)
            elif spend < SMALL_THRESHOLD:
                small_suppliers.append(sup)
            else:
                non_tail_suppliers.append(sup)

        # Calculate segment metrics
        def calc_segment_metrics(supplier_list):
            count = len(supplier_list)
            spend = sum(float(s['total_spend'] or 0) for s in supplier_list)
            transactions = sum(s['transaction_count'] or 0 for s in supplier_list)
            avg = spend / count if count > 0 else 0
            return {
                'count': count,
                'spend': round(spend, 2),
                'transactions': transactions,
                'avg_spend_per_vendor': round(avg, 2)
            }

        segments = {
            'micro': calc_segment_metrics(micro_suppliers),
            'small': calc_segment_metrics(small_suppliers),
            'non_tail': calc_segment_metrics(non_tail_suppliers)
        }

        # Tail spend summary
        tail_suppliers = micro_suppliers + small_suppliers
        tail_count = len(tail_suppliers)
        tail_spend = segments['micro']['spend'] + segments['small']['spend']
        tail_percentage = (tail_spend / total_spend * 100) if total_spend > 0 else 0
        vendor_ratio = (tail_count / total_vendors * 100) if total_vendors > 0 else 0
        savings_opportunity = tail_spend * 0.08  # 8% savings potential

        # Pareto data (top 20 vendors with cumulative %)
        cumulative = 0
        pareto_data = []
        for sup in suppliers[:20]:
            spend = float(sup['total_spend'] or 0)
            cumulative += spend
            cumulative_pct = (cumulative / total_spend * 100) if total_spend > 0 else 0
            is_tail = spend < SMALL_THRESHOLD

            pareto_data.append({
                'supplier': sup['supplier__name'],
                'supplier_id': sup['supplier_id'],
                'spend': round(spend, 2),
                'cumulative_pct': round(cumulative_pct, 2),
                'is_tail': is_tail
            })

        # Category analysis
        category_data = defaultdict(lambda: {
            'tail_spend': 0, 'tail_vendors': set(), 'total_spend': 0, 'total_vendors': set(),
            'category_id': None, 'category_name': ''
        })

        # Get transaction-level data for category analysis
        cat_transactions = list(self.transactions.values(
            'supplier_id', 'category_id', 'category__name'
        ).annotate(
            spend=Sum('amount')
        ))

        # Build supplier spend lookup
        supplier_spend = {s['supplier_id']: float(s['total_spend'] or 0) for s in suppliers}

        for t in cat_transactions:
            cat_name = t['category__name'] or 'Uncategorized'
            cat_id = t['category_id']
            sup_id = t['supplier_id']
            spend = float(t['spend'] or 0)
            sup_total = supplier_spend.get(sup_id, 0)

            category_data[cat_name]['category_id'] = cat_id
            category_data[cat_name]['category_name'] = cat_name
            category_data[cat_name]['total_spend'] += spend
            category_data[cat_name]['total_vendors'].add(sup_id)

            if sup_total < SMALL_THRESHOLD:
                category_data[cat_name]['tail_spend'] += spend
                category_data[cat_name]['tail_vendors'].add(sup_id)

        category_analysis = []
        for cat_name, data in category_data.items():
            total_cat_spend = data['total_spend']
            tail_cat_spend = data['tail_spend']
            total_vendors_count = len(data['total_vendors'])
            tail_vendors_count = len(data['tail_vendors'])

            category_analysis.append({
                'category': cat_name,
                'category_id': data['category_id'],
                'tail_spend': round(tail_cat_spend, 2),
                'tail_vendors': tail_vendors_count,
                'total_spend': round(total_cat_spend, 2),
                'total_vendors': total_vendors_count,
                'tail_percentage': round((tail_cat_spend / total_cat_spend * 100) if total_cat_spend > 0 else 0, 2),
                'vendor_percentage': round((tail_vendors_count / total_vendors_count * 100) if total_vendors_count > 0 else 0, 2)
            })

        category_analysis.sort(key=lambda x: x['tail_spend'], reverse=True)

        # Consolidation opportunities
        # 1. Multi-category vendors (tail vendors serving multiple categories)
        multi_category = []
        for sup in tail_suppliers:
            if sup['category_count'] > 1:
                # Get categories for this supplier
                sup_cats = list(self.transactions.filter(
                    supplier_id=sup['supplier_id']
                ).values_list('category__name', flat=True).distinct())

                multi_category.append({
                    'supplier': sup['supplier__name'],
                    'supplier_id': sup['supplier_id'],
                    'categories': sup_cats,
                    'category_count': sup['category_count'],
                    'total_spend': round(float(sup['total_spend'] or 0), 2),
                    'savings_potential': round(float(sup['total_spend'] or 0) * 0.15, 2)  # 15% consolidation savings
                })

        multi_category.sort(key=lambda x: x['total_spend'], reverse=True)
        multi_category = multi_category[:10]

        # 2. Category consolidation (categories with 3+ tail vendors)
        category_consolidation = []
        for cat in category_analysis:
            if cat['tail_vendors'] >= 3:
                # Get top vendor in this category
                top_vendor = self.transactions.filter(
                    category_id=cat['category_id']
                ).values('supplier__name').annotate(
                    spend=Sum('amount')
                ).order_by('-spend').first()

                category_consolidation.append({
                    'category': cat['category'],
                    'category_id': cat['category_id'],
                    'tail_vendors': cat['tail_vendors'],
                    'total_vendors': cat['total_vendors'],
                    'tail_spend': cat['tail_spend'],
                    'top_vendor': top_vendor['supplier__name'] if top_vendor else 'N/A',
                    'savings_potential': round(cat['tail_spend'] * 0.10, 2)  # 10% consolidation savings
                })

        category_consolidation.sort(key=lambda x: x['tail_spend'], reverse=True)
        category_consolidation = category_consolidation[:10]

        # 3. Geographic consolidation (locations with 3+ tail vendors)
        location_data = defaultdict(lambda: {'tail_vendors': set(), 'total_vendors': set(), 'tail_spend': 0})

        loc_transactions = list(self.transactions.values(
            'supplier_id', 'location'
        ).annotate(
            spend=Sum('amount')
        ))

        for t in loc_transactions:
            loc = t['location'] or 'Unspecified'
            sup_id = t['supplier_id']
            spend = float(t['spend'] or 0)
            sup_total = supplier_spend.get(sup_id, 0)

            location_data[loc]['total_vendors'].add(sup_id)
            if sup_total < SMALL_THRESHOLD:
                location_data[loc]['tail_vendors'].add(sup_id)
                location_data[loc]['tail_spend'] += spend

        geographic_consolidation = []
        for loc, data in location_data.items():
            if len(data['tail_vendors']) >= 3:
                # Get top vendor in this location
                top_vendor = self.transactions.filter(
                    location=loc
                ).values('supplier__name').annotate(
                    spend=Sum('amount')
                ).order_by('-spend').first()

                geographic_consolidation.append({
                    'location': loc,
                    'tail_vendors': len(data['tail_vendors']),
                    'total_vendors': len(data['total_vendors']),
                    'tail_spend': round(data['tail_spend'], 2),
                    'top_vendor': top_vendor['supplier__name'] if top_vendor else 'N/A',
                    'savings_potential': round(data['tail_spend'] * 0.10, 2)
                })

        geographic_consolidation.sort(key=lambda x: x['tail_spend'], reverse=True)
        geographic_consolidation = geographic_consolidation[:10]

        # Calculate total consolidation opportunities
        total_opportunities = len(multi_category) + len(category_consolidation) + len(geographic_consolidation)
        total_consol_savings = (
            sum(m['savings_potential'] for m in multi_category) +
            sum(c['savings_potential'] for c in category_consolidation) +
            sum(g['savings_potential'] for g in geographic_consolidation)
        )

        # Determine top opportunity type
        savings_by_type = {
            'Multi-Category Vendors': sum(m['savings_potential'] for m in multi_category),
            'Category Consolidation': sum(c['savings_potential'] for c in category_consolidation),
            'Geographic Consolidation': sum(g['savings_potential'] for g in geographic_consolidation)
        }
        top_type = max(savings_by_type, key=savings_by_type.get) if savings_by_type else 'N/A'

        return {
            'summary': {
                'total_vendors': total_vendors,
                'tail_vendor_count': tail_count,
                'tail_spend': round(tail_spend, 2),
                'tail_percentage': round(tail_percentage, 2),
                'total_spend': round(total_spend, 2),
                'savings_opportunity': round(savings_opportunity, 2),
                'vendor_ratio': round(vendor_ratio, 2)
            },
            'segments': segments,
            'pareto_data': pareto_data,
            'category_analysis': category_analysis,
            'consolidation_opportunities': {
                'total_opportunities': total_opportunities,
                'total_savings': round(total_consol_savings, 2),
                'top_type': top_type,
                'multi_category': multi_category,
                'category': category_consolidation,
                'geographic': geographic_consolidation
            }
        }

    def get_tail_spend_category_drilldown(self, category_id, threshold=50000):
        """
        Get detailed tail spend drill-down for a specific category.
        Returns vendor-level breakdown within the category.

        Args:
            category_id: The category ID to drill down into
            threshold: Dollar amount threshold for tail classification
        """
        # Verify category exists
        try:
            category = Category.objects.get(id=category_id, organization=self.organization)
            category_name = category.name
        except Category.DoesNotExist:
            return None

        # Get supplier-level aggregations for this category
        suppliers = list(self.transactions.filter(category_id=category_id).values(
            'supplier__name',
            'supplier_id'
        ).annotate(
            spend=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-spend'))

        if not suppliers:
            return {
                'category': category_name,
                'category_id': category_id,
                'total_spend': 0,
                'tail_spend': 0,
                'tail_percentage': 0,
                'vendors': [],
                'recommendations': []
            }

        # Get global supplier spend to determine tail status
        global_supplier_spend = dict(self.transactions.values(
            'supplier_id'
        ).annotate(
            total=Sum('amount')
        ).values_list('supplier_id', 'total'))

        total_spend = sum(float(s['spend'] or 0) for s in suppliers)
        tail_spend = 0
        vendors = []

        for sup in suppliers:
            spend = float(sup['spend'] or 0)
            global_spend = float(global_supplier_spend.get(sup['supplier_id'], 0))
            is_tail = global_spend < threshold

            if is_tail:
                tail_spend += spend

            vendors.append({
                'name': sup['supplier__name'],
                'supplier_id': sup['supplier_id'],
                'spend': round(spend, 2),
                'transaction_count': sup['transaction_count'],
                'is_tail': is_tail,
                'percent_of_category': round((spend / total_spend * 100) if total_spend > 0 else 0, 2)
            })

        tail_percentage = (tail_spend / total_spend * 100) if total_spend > 0 else 0

        # Generate recommendations
        recommendations = []
        tail_vendor_count = sum(1 for v in vendors if v['is_tail'])

        if tail_vendor_count >= 5:
            recommendations.append(f"Consider consolidating {tail_vendor_count} tail vendors into fewer strategic suppliers")
        if tail_percentage > 30:
            recommendations.append(f"High tail spend ({tail_percentage:.1f}%) suggests opportunity for preferred vendor program")
        if any(v['is_tail'] and v['percent_of_category'] > 10 for v in vendors):
            recommendations.append("Some tail vendors have significant category share - evaluate for strategic partnership")

        return {
            'category': category_name,
            'category_id': category_id,
            'total_spend': round(total_spend, 2),
            'tail_spend': round(tail_spend, 2),
            'tail_percentage': round(tail_percentage, 2),
            'vendors': vendors,
            'recommendations': recommendations
        }

    def get_tail_spend_vendor_drilldown(self, supplier_id, threshold=50000):
        """
        Get detailed tail spend drill-down for a specific vendor.
        Returns category breakdown, locations, and monthly spend.

        Args:
            supplier_id: The supplier ID to drill down into
            threshold: Dollar amount threshold for tail classification
        """
        from collections import defaultdict
        from datetime import datetime, timedelta

        # Verify supplier exists
        try:
            supplier = Supplier.objects.get(id=supplier_id, organization=self.organization)
            supplier_name = supplier.name
        except Supplier.DoesNotExist:
            return None

        # Get total spend for this supplier
        total_agg = self.transactions.filter(supplier_id=supplier_id).aggregate(
            total_spend=Sum('amount'),
            transaction_count=Count('id')
        )

        total_spend = float(total_agg['total_spend'] or 0)
        transaction_count = total_agg['transaction_count'] or 0
        is_tail = total_spend < threshold

        if transaction_count == 0:
            return {
                'supplier': supplier_name,
                'supplier_id': supplier_id,
                'total_spend': 0,
                'transaction_count': 0,
                'is_tail': True,
                'categories': [],
                'locations': [],
                'monthly_spend': []
            }

        # Category breakdown
        categories = list(self.transactions.filter(supplier_id=supplier_id).values(
            'category__name',
            'category_id'
        ).annotate(
            spend=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-spend'))

        category_data = [
            {
                'name': cat['category__name'] or 'Uncategorized',
                'category_id': cat['category_id'],
                'spend': round(float(cat['spend'] or 0), 2),
                'transaction_count': cat['transaction_count'],
                'percent_of_vendor': round((float(cat['spend'] or 0) / total_spend * 100) if total_spend > 0 else 0, 2)
            }
            for cat in categories
        ]

        # Location breakdown
        locations = list(self.transactions.filter(supplier_id=supplier_id).values(
            'location'
        ).annotate(
            spend=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-spend'))

        location_data = [
            {
                'name': loc['location'] or 'Unspecified',
                'spend': round(float(loc['spend'] or 0), 2),
                'transaction_count': loc['transaction_count']
            }
            for loc in locations
        ]

        # Monthly spend (last 12 months)
        twelve_months_ago = datetime.now().date() - timedelta(days=365)
        monthly_txns = self.transactions.filter(
            supplier_id=supplier_id,
            date__gte=twelve_months_ago
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            spend=Sum('amount')
        ).order_by('month')

        # Build monthly spend array
        monthly_spend = []
        for m in monthly_txns:
            monthly_spend.append({
                'month': m['month'].strftime('%Y-%m'),
                'spend': round(float(m['spend'] or 0), 2)
            })

        return {
            'supplier': supplier_name,
            'supplier_id': supplier_id,
            'total_spend': round(total_spend, 2),
            'transaction_count': transaction_count,
            'is_tail': is_tail,
            'categories': category_data,
            'locations': location_data,
            'monthly_spend': monthly_spend
        }
