"""
Pareto and tail spend analytics service.

Provides 80/20 analysis, tail spend classification, and consolidation
opportunity identification.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth

from apps.procurement.models import Supplier, Category
from .base import BaseAnalyticsService


class ParetoTailAnalyticsService(BaseAnalyticsService):
    """
    Service for Pareto (80/20) and tail spend analytics.

    Methods:
        get_pareto_analysis: Basic Pareto analysis for suppliers
        get_tail_spend_analysis: Analyze bottom X% of suppliers
        get_detailed_tail_spend: Comprehensive tail spend with consolidation opportunities
        get_tail_spend_category_drilldown: Category-level tail spend drill-down
        get_tail_spend_vendor_drilldown: Vendor-level tail spend drill-down
    """

    def get_pareto_analysis(self):
        """
        Get Pareto analysis (80/20 rule) for suppliers.

        Returns:
            list: Suppliers with cumulative percentage for Pareto chart
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
        Analyze tail spend (bottom X% of suppliers).

        Args:
            threshold_percentage: Percentage of total spend to consider as tail

        Returns:
            dict: Tail spend summary with supplier list
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

    def get_detailed_tail_spend(self, threshold=50000):
        """
        Get detailed tail spend analysis using dollar threshold.
        Tail vendors are those with total spend below the threshold.

        Args:
            threshold: Dollar amount threshold for tail classification (default $50,000)

        Returns:
            dict: Comprehensive tail spend data including:
                - summary: Total vendors, tail count, tail spend, savings opportunity
                - segments: micro (<$10K), small ($10K-$50K), non-tail (>$50K)
                - pareto_data: Top 20 vendors with cumulative %
                - category_analysis: Tail metrics per category
                - consolidation_opportunities: Multi-category, category, geographic
        """
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

        Returns:
            dict: Category tail spend details with vendor list and recommendations
            None: If category not found
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

        Returns:
            dict: Vendor tail spend details with category, location, and monthly breakdowns
            None: If supplier not found
        """
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
