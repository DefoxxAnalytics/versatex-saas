"""
Stratification analytics service.

Provides spend stratification using Kraljic matrix segments and spend bands
for strategic purchasing analysis.
"""
from django.db.models import Sum, Count
from .base import BaseAnalyticsService
from .constants import SPEND_BANDS, SEGMENTS


class StratificationAnalyticsService(BaseAnalyticsService):
    """
    Service for spend stratification analytics.

    Methods:
        get_spend_stratification: Basic Kraljic matrix classification
        get_detailed_stratification: Comprehensive band and segment analysis
        get_stratification_segment_drilldown: Drill into Strategic/Leverage/Routine/Tactical
        get_stratification_band_drilldown: Drill into specific spend bands
    """

    def get_spend_stratification(self):
        """
        Categorize spend into strategic, leverage, bottleneck, and tactical.
        Based on spend value and supplier count using median thresholds.

        Returns:
            dict: Categories grouped by Kraljic quadrant
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

    def get_detailed_stratification(self):
        """
        Get detailed spend stratification analysis by spend bands.
        Returns comprehensive data for the SpendStratification dashboard page.

        Groups transactions by their spend_band field and calculates metrics.

        Returns:
            dict: Summary, spend_bands, and segments with full metrics
        """
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

        Args:
            segment_name: One of 'Strategic', 'Leverage', 'Routine', 'Tactical'

        Returns:
            dict: Segment details with suppliers, subcategories, and locations
            None: If segment name is invalid
        """
        # Define segments
        SEGMENT_DEFS = {
            'Strategic': {'min': 1000000, 'max': float('inf')},
            'Leverage': {'min': 100000, 'max': 1000000},
            'Routine': {'min': 10000, 'max': 100000},
            'Tactical': {'min': 0, 'max': 10000},
        }

        # Define spend bands for each segment
        BAND_DEFS = [
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

        if segment_name not in SEGMENT_DEFS:
            return None

        seg_def = SEGMENT_DEFS[segment_name]

        # Find spend band names that belong to this segment
        segment_band_names = [
            band['name'] for band in BAND_DEFS
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

        Args:
            band_name: One of the valid spend band names (e.g., '0 - 1K', '1M and Above')

        Returns:
            dict: Band details with suppliers, subcategories, and locations
            None: If band name is invalid
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
