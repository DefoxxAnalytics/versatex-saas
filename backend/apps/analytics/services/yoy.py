"""
Year-over-year analytics service.

Provides year-over-year comparison analysis with fiscal year support,
category/supplier breakdowns, and growth metrics.
"""
from collections import defaultdict

from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncYear

from apps.procurement.models import Category, Supplier
from .base import BaseAnalyticsService


CALENDAR_MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
FISCAL_MONTH_NAMES = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
                      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']


def _yoy_change(y1_spend, y2_spend):
    """
    Compute YoY change percentage with explicit new/discontinued flags.

    Returns a tuple (change_pct, is_new, is_discontinued) where:
    - is_new = category existed only in year2 (y1 was zero). change_pct
      defaults to 100 for back-compat but callers should prefer the flag.
    - is_discontinued = category existed only in year1 (y2 is zero).
      change_pct is -100 (a real -100% drop is the same number but not
      flagged, which is intentional — -100 always means "lost everything").
    - Otherwise the standard (y2 - y1)/y1 * 100 formula.
    """
    is_new = y1_spend == 0 and y2_spend > 0
    is_discontinued = y1_spend > 0 and y2_spend == 0
    if y1_spend > 0:
        change_pct = (y2_spend - y1_spend) / y1_spend * 100
    elif y2_spend > 0:
        change_pct = 100  # Placeholder; UI should render "New" via is_new flag
    else:
        change_pct = 0
    return change_pct, is_new, is_discontinued


class YearOverYearAnalyticsService(BaseAnalyticsService):
    """
    Service for year-over-year comparison analytics.

    Methods:
        get_year_over_year_comparison: Basic YoY spend comparison
        get_detailed_year_over_year: Comprehensive YoY with category/supplier breakdowns
        get_yoy_category_drilldown: Category-level YoY drill-down
        get_yoy_supplier_drilldown: Supplier-level YoY drill-down
    """

    def get_year_over_year_comparison(self):
        """
        Compare spending year over year.

        Returns:
            list: Yearly spend with growth percentages
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

    def get_detailed_year_over_year(self, year1=None, year2=None, use_fiscal_year=True):
        """
        Get detailed year-over-year comparison with category and supplier breakdowns.
        Returns comprehensive data for the Year-over-Year dashboard page.

        Args:
            year1: First fiscal year to compare (optional, defaults to previous FY)
            year2: Second fiscal year to compare (optional, defaults to current FY)
            use_fiscal_year: Whether to use fiscal year (Jul-Jun) or calendar year

        Returns:
            dict: Comprehensive YoY comparison with summary, monthly, category, supplier data
        """
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
                    'year2_avg_transaction': 0,
                    'insufficient_data_for_yoy': True,
                },
                'monthly_comparison': [],
                'category_comparison': [],
                'supplier_comparison': [],
                'top_gainers': [],
                'top_decliners': [],
                'available_years': []
            }

        # Calculate fiscal years for all transactions; honor the use_fiscal_year
        # toggle on month too (earlier versions always returned fiscal months,
        # which mislabeled the monthly axis when calendar year was selected).
        for t in all_transactions:
            t['fiscal_year'] = self._get_fiscal_year(t['date'], use_fiscal_year)
            t['fiscal_month'] = self._get_fiscal_month(t['date'], use_fiscal_year)

        # Find available fiscal years
        available_years = sorted(set(t['fiscal_year'] for t in all_transactions))

        # Default years if not specified. If only one year's data exists, the
        # insufficient_data_for_yoy flag tells the frontend to render a clear
        # "need more data" state rather than showing a misleading 0% change.
        insufficient_data_for_yoy = False
        if year1 is None or year2 is None:
            if len(available_years) >= 2:
                year1 = year1 or available_years[-2]
                year2 = year2 or available_years[-1]
            elif len(available_years) == 1:
                year1 = year1 or available_years[0]
                year2 = year2 or available_years[0]
                insufficient_data_for_yoy = True
            else:
                year1, year2 = 2024, 2025
                insufficient_data_for_yoy = True

        year_prefix = 'FY' if use_fiscal_year else ''
        month_names = FISCAL_MONTH_NAMES if use_fiscal_year else CALENDAR_MONTH_NAMES

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
            change_pct, is_new, is_discontinued = _yoy_change(y1_spend, y2_spend)
            monthly_comparison.append({
                'month': month_names[i - 1],
                'fiscal_month': i,
                'year1_spend': round(y1_spend, 2),
                'year2_spend': round(y2_spend, 2),
                'change_pct': round(change_pct, 2),
                'is_new': is_new,
                'is_discontinued': is_discontinued,
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
            change_pct, is_new, is_discontinued = _yoy_change(y1_spend, y2_spend)
            category_comparison.append({
                'category': cat_name,
                'category_id': y1_data['id'] or y2_data['id'],
                'year1_spend': round(y1_spend, 2),
                'year2_spend': round(y2_spend, 2),
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'is_new': is_new,
                'is_discontinued': is_discontinued,
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
            change_pct, is_new, is_discontinued = _yoy_change(y1_spend, y2_spend)
            supplier_comparison.append({
                'supplier': sup_name,
                'supplier_id': y1_data['id'] or y2_data['id'],
                'year1_spend': round(y1_spend, 2),
                'year2_spend': round(y2_spend, 2),
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'is_new': is_new,
                'is_discontinued': is_discontinued,
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
                'year2_avg_transaction': round(year2_total / year2_count, 2) if year2_count > 0 else 0,
                'insufficient_data_for_yoy': insufficient_data_for_yoy,
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

        Args:
            category_id: The category ID to drill into
            year1: First fiscal year to compare
            year2: Second fiscal year to compare
            use_fiscal_year: Whether to use fiscal year (Jul-Jun) or calendar year

        Returns:
            dict: Category YoY with supplier breakdowns and monthly data
            None: If category not found
        """
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

        # Calculate fiscal years (month honors the calendar toggle post-Cluster 2)
        for t in cat_transactions:
            t['fiscal_year'] = self._get_fiscal_year(t['date'], use_fiscal_year)
            t['fiscal_month'] = self._get_fiscal_month(t['date'], use_fiscal_year)

        # Determine years
        insufficient_data_for_yoy = False
        available_years = sorted(set(t['fiscal_year'] for t in cat_transactions))
        if year1 is None or year2 is None:
            if len(available_years) >= 2:
                year1 = year1 or available_years[-2]
                year2 = year2 or available_years[-1]
            else:
                year1 = year1 or (available_years[0] if available_years else 2024)
                year2 = year2 or (available_years[0] if available_years else 2025)
                insufficient_data_for_yoy = True

        year_prefix = 'FY' if use_fiscal_year else ''
        month_names = FISCAL_MONTH_NAMES if use_fiscal_year else CALENDAR_MONTH_NAMES

        year1_txns = [t for t in cat_transactions if t['fiscal_year'] == year1]
        year2_txns = [t for t in cat_transactions if t['fiscal_year'] == year2]

        year1_total = sum(float(t['amount'] or 0) for t in year1_txns)
        year2_total = sum(float(t['amount'] or 0) for t in year2_txns)
        change_pct, _is_new, _is_discontinued = _yoy_change(year1_total, year2_total)

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
            sup_change_pct, sup_is_new, sup_is_discontinued = _yoy_change(y1_spend, y2_spend)
            suppliers.append({
                'name': sup_name,
                'supplier_id': y1_data['id'] or y2_data['id'],
                'year1_spend': round(y1_spend, 2),
                'year2_spend': round(y2_spend, 2),
                'change': round(change, 2),
                'change_pct': round(sup_change_pct, 2),
                'is_new': sup_is_new,
                'is_discontinued': sup_is_discontinued,
            })

        suppliers.sort(key=lambda x: x['year1_spend'] + x['year2_spend'], reverse=True)

        # Monthly breakdown (month_names already honors use_fiscal_year)
        monthly_year1 = defaultdict(float)
        monthly_year2 = defaultdict(float)
        for t in year1_txns:
            monthly_year1[t['fiscal_month']] += float(t['amount'] or 0)
        for t in year2_txns:
            monthly_year2[t['fiscal_month']] += float(t['amount'] or 0)

        monthly_breakdown = []
        for i in range(1, 13):
            monthly_breakdown.append({
                'month': month_names[i - 1],
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
            'insufficient_data_for_yoy': insufficient_data_for_yoy,
            'suppliers': suppliers,
            'monthly_breakdown': monthly_breakdown
        }

    def get_yoy_supplier_drilldown(self, supplier_id, year1=None, year2=None, use_fiscal_year=True):
        """
        Get detailed YoY comparison for a specific supplier.
        Returns category-level breakdowns for the supplier.

        Args:
            supplier_id: The supplier ID to drill into
            year1: First fiscal year to compare
            year2: Second fiscal year to compare
            use_fiscal_year: Whether to use fiscal year (Jul-Jun) or calendar year

        Returns:
            dict: Supplier YoY with category breakdowns and monthly data
            None: If supplier not found
        """
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

        # Calculate fiscal years (month honors the calendar toggle post-Cluster 2)
        for t in sup_transactions:
            t['fiscal_year'] = self._get_fiscal_year(t['date'], use_fiscal_year)
            t['fiscal_month'] = self._get_fiscal_month(t['date'], use_fiscal_year)

        # Determine years
        insufficient_data_for_yoy = False
        available_years = sorted(set(t['fiscal_year'] for t in sup_transactions))
        if year1 is None or year2 is None:
            if len(available_years) >= 2:
                year1 = year1 or available_years[-2]
                year2 = year2 or available_years[-1]
            else:
                year1 = year1 or (available_years[0] if available_years else 2024)
                year2 = year2 or (available_years[0] if available_years else 2025)
                insufficient_data_for_yoy = True

        year_prefix = 'FY' if use_fiscal_year else ''
        month_names = FISCAL_MONTH_NAMES if use_fiscal_year else CALENDAR_MONTH_NAMES

        year1_txns = [t for t in sup_transactions if t['fiscal_year'] == year1]
        year2_txns = [t for t in sup_transactions if t['fiscal_year'] == year2]

        year1_total = sum(float(t['amount'] or 0) for t in year1_txns)
        year2_total = sum(float(t['amount'] or 0) for t in year2_txns)
        change_pct, _is_new, _is_discontinued = _yoy_change(year1_total, year2_total)

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
            cat_change_pct, cat_is_new, cat_is_discontinued = _yoy_change(y1_spend, y2_spend)
            categories.append({
                'name': cat_name,
                'category_id': y1_data['id'] or y2_data['id'],
                'year1_spend': round(y1_spend, 2),
                'year2_spend': round(y2_spend, 2),
                'change': round(change, 2),
                'change_pct': round(cat_change_pct, 2),
                'is_new': cat_is_new,
                'is_discontinued': cat_is_discontinued,
            })

        categories.sort(key=lambda x: x['year1_spend'] + x['year2_spend'], reverse=True)

        # Monthly breakdown (month_names already honors use_fiscal_year)
        monthly_year1 = defaultdict(float)
        monthly_year2 = defaultdict(float)
        for t in year1_txns:
            monthly_year1[t['fiscal_month']] += float(t['amount'] or 0)
        for t in year2_txns:
            monthly_year2[t['fiscal_month']] += float(t['amount'] or 0)

        monthly_breakdown = []
        for i in range(1, 13):
            monthly_breakdown.append({
                'month': month_names[i - 1],
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
            'insufficient_data_for_yoy': insufficient_data_for_yoy,
            'categories': categories,
            'monthly_breakdown': monthly_breakdown
        }
