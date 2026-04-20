"""
Spend analytics service.

Provides category and supplier spend analysis including breakdowns,
HHI calculations, and supplier drilldowns.
"""
from django.db.models import Sum, Count, Min, Max
from apps.procurement.models import Supplier, Category
from .base import BaseAnalyticsService


class SpendAnalyticsService(BaseAnalyticsService):
    """
    Service for spend-related analytics.

    Methods:
        get_spend_by_category: Basic category spend breakdown
        get_spend_by_supplier: Basic supplier spend breakdown
        get_detailed_category_analysis: Category analysis with subcategories and risk
        get_detailed_supplier_analysis: Supplier analysis with HHI scores
        get_supplier_drilldown: Detailed drill-down for a specific supplier
    """

    def get_spend_by_category(self):
        """
        Get spend breakdown by category.

        Returns:
            list: Category spend data with amount, count, and category_id
        """
        data = self.transactions.values(
            'category__name',
            'category_id'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')

        return [
            {
                'category': item['category__name'],
                'category_id': item['category_id'],
                'amount': float(item['total']),
                'count': item['count']
            }
            for item in data
        ]

    def get_spend_by_supplier(self):
        """
        Get spend breakdown by supplier.

        Returns:
            list: Supplier spend data with amount, count, and supplier_id
        """
        data = self.transactions.values(
            'supplier__name',
            'supplier_id'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')

        return [
            {
                'supplier': item['supplier__name'],
                'supplier_id': item['supplier_id'],
                'amount': float(item['total']),
                'count': item['count']
            }
            for item in data
        ]

    def get_detailed_category_analysis(self):
        """
        Get detailed category analysis including subcategories, suppliers, and risk levels.
        Returns comprehensive data for the Categories dashboard page.

        Returns:
            list: Category data with subcategories, concentration, and risk levels
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

        Returns:
            dict: Summary metrics and supplier list with HHI analysis
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

        Args:
            supplier_id: ID of the supplier to drill into

        Returns:
            dict: Supplier details with category, subcategory, and location breakdowns
            None: If supplier not found
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

    def get_category_drilldown(self, category_id):
        """
        Get detailed drill-down data for a specific category.
        Used by Overview page when user clicks on a category in charts.
        Returns supplier/subcategory/location breakdowns with full aggregation.

        Args:
            category_id: ID of the category to drill into

        Returns:
            dict: Category details with supplier, subcategory, and location breakdowns
            None: If category not found
        """
        try:
            category = Category.objects.get(id=category_id, organization=self.organization)
            category_name = category.name
        except Category.DoesNotExist:
            return None

        category_transactions = self.transactions.filter(category_id=category_id)

        if not category_transactions.exists():
            return {
                'category_id': category_id,
                'category_name': category_name,
                'total_spend': 0,
                'transaction_count': 0,
                'avg_transaction': 0,
                'supplier_count': 0,
                'date_range': {'min': None, 'max': None},
                'suppliers': [],
                'subcategories': [],
                'locations': [],
                'recent_transactions': []
            }

        total_spend = float(category_transactions.aggregate(total=Sum('amount'))['total'] or 0)
        transaction_count = category_transactions.count()
        avg_transaction = total_spend / transaction_count if transaction_count > 0 else 0
        supplier_count = category_transactions.values('supplier_id').distinct().count()

        date_agg = category_transactions.aggregate(
            min_date=Min('date'),
            max_date=Max('date')
        )

        suppliers = list(category_transactions.values(
            'supplier__name',
            'supplier_id'
        ).annotate(
            spend=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-spend')[:10])

        supplier_data = [
            {
                'id': sup['supplier_id'],
                'name': sup['supplier__name'] or 'Unspecified',
                'spend': float(sup['spend'] or 0),
                'transaction_count': sup['transaction_count'] or 0,
                'percent_of_total': round((float(sup['spend'] or 0) / total_spend * 100) if total_spend > 0 else 0, 2)
            }
            for sup in suppliers
        ]

        subcategories = list(category_transactions.values(
            'subcategory'
        ).annotate(
            spend=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-spend'))

        subcategory_data = [
            {
                'name': sub['subcategory'] or 'Unspecified',
                'spend': float(sub['spend'] or 0),
                'transaction_count': sub['transaction_count'] or 0,
                'percent_of_total': round((float(sub['spend'] or 0) / total_spend * 100) if total_spend > 0 else 0, 2)
            }
            for sub in subcategories
        ]

        locations = list(category_transactions.values(
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

        recent_txns = list(category_transactions.select_related('supplier').order_by('-date')[:10])
        recent_transactions = [
            {
                'id': txn.id,
                'date': txn.date.isoformat() if txn.date else None,
                'amount': float(txn.amount),
                'supplier_name': txn.supplier.name if txn.supplier else 'Unknown',
                'description': txn.description or ''
            }
            for txn in recent_txns
        ]

        return {
            'category_id': category_id,
            'category_name': category_name,
            'total_spend': total_spend,
            'transaction_count': transaction_count,
            'avg_transaction': round(avg_transaction, 2),
            'supplier_count': supplier_count,
            'date_range': {
                'min': date_agg['min_date'].isoformat() if date_agg['min_date'] else None,
                'max': date_agg['max_date'].isoformat() if date_agg['max_date'] else None
            },
            'suppliers': supplier_data,
            'subcategories': subcategory_data,
            'locations': location_data,
            'recent_transactions': recent_transactions
        }
