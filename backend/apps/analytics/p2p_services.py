"""
P2P (Procure-to-Pay) Analytics Service

Provides analytics for the complete procure-to-pay cycle including:
- Cycle time analysis (PR → PO → GR → Invoice → Payment)
- 3-Way matching (PO vs GR vs Invoice)
- Invoice aging / AP analysis
- Purchase requisition analysis
- Purchase order analysis
- Supplier payment performance
"""
from decimal import Decimal
from datetime import date, datetime, timedelta
from collections import defaultdict
from django.db.models import (
    Sum, Count, Avg, Q, F, Min, Max, Case, When, Value,
    DecimalField, IntegerField, CharField
)
from django.db.models.functions import TruncMonth, TruncWeek, Coalesce, ExtractMonth
from apps.procurement.models import (
    PurchaseRequisition, PurchaseOrder, GoodsReceipt, Invoice,
    Supplier, Category
)


class P2PAnalyticsService:
    """
    Analytics service for Procure-to-Pay process metrics.
    Handles PR, PO, GR, and Invoice analysis.
    """

    def __init__(self, organization, filters=None):
        """
        Initialize P2P analytics service.

        Args:
            organization: Organization instance
            filters: Optional dict with filter parameters:
                - date_from: Start date (str 'YYYY-MM-DD' or date)
                - date_to: End date (str 'YYYY-MM-DD' or date)
                - supplier_ids: List of supplier IDs
                - category_ids: List of category IDs
                - department: Department name filter
                - status: Status filter
        """
        self.organization = organization
        self.filters = filters or {}

    def _parse_date(self, date_val):
        """Parse date from string or return as-is if already a date."""
        if isinstance(date_val, str):
            return datetime.strptime(date_val, '%Y-%m-%d').date()
        return date_val

    def _apply_date_filters(self, qs, date_field='created_date'):
        """Apply date range filters to queryset."""
        if date_from := self.filters.get('date_from'):
            qs = qs.filter(**{f'{date_field}__gte': self._parse_date(date_from)})
        if date_to := self.filters.get('date_to'):
            qs = qs.filter(**{f'{date_field}__lte': self._parse_date(date_to)})
        return qs

    # =========================================================================
    # P2P CYCLE TIME ANALYSIS
    # =========================================================================

    def get_p2p_cycle_overview(self):
        """
        Get end-to-end P2P cycle time metrics.
        Returns average days for each stage and overall cycle.
        """
        # Get PRs with linked POs (PO.requisition -> PR, so PR.purchase_orders is reverse relation)
        prs_with_po = PurchaseRequisition.objects.filter(
            organization=self.organization,
            status='converted_to_po',
            purchase_orders__isnull=False,
            submitted_date__isnull=False
        ).prefetch_related('purchase_orders')

        prs_with_po = self._apply_date_filters(prs_with_po, 'created_date')

        # Calculate PR to PO time
        pr_to_po_days = []
        for pr in prs_with_po:
            po = pr.purchase_orders.first()  # Get the first linked PO
            if po and pr.approval_date:
                days = (po.created_date - pr.approval_date).days
                if days >= 0:
                    pr_to_po_days.append(days)

        # Get POs with linked GRs
        pos_with_gr = PurchaseOrder.objects.filter(
            organization=self.organization,
            goods_receipts__isnull=False
        ).prefetch_related('goods_receipts')

        pos_with_gr = self._apply_date_filters(pos_with_gr, 'created_date')

        # Calculate PO to GR time
        po_to_gr_days = []
        for po in pos_with_gr:
            gr = po.goods_receipts.first()
            if gr and po.sent_date:
                days = (gr.received_date - po.sent_date).days
                if days >= 0:
                    po_to_gr_days.append(days)

        # Get GRs with linked Invoices
        grs_with_invoice = GoodsReceipt.objects.filter(
            organization=self.organization,
            invoices__isnull=False
        ).prefetch_related('invoices')

        # Calculate GR to Invoice time
        gr_to_inv_days = []
        for gr in grs_with_invoice:
            inv = gr.invoices.first()
            if inv:
                days = (inv.invoice_date - gr.received_date).days
                if days >= 0:
                    gr_to_inv_days.append(days)

        # Get paid invoices for Invoice to Payment time
        paid_invoices = Invoice.objects.filter(
            organization=self.organization,
            status='paid',
            paid_date__isnull=False
        )

        paid_invoices = self._apply_date_filters(paid_invoices, 'invoice_date')

        # Calculate Invoice to Payment time
        inv_to_pay_days = []
        for inv in paid_invoices:
            days = (inv.paid_date - inv.invoice_date).days
            if days >= 0:
                inv_to_pay_days.append(days)

        # Calculate averages
        avg_pr_to_po = sum(pr_to_po_days) / len(pr_to_po_days) if pr_to_po_days else 0
        avg_po_to_gr = sum(po_to_gr_days) / len(po_to_gr_days) if po_to_gr_days else 0
        avg_gr_to_inv = sum(gr_to_inv_days) / len(gr_to_inv_days) if gr_to_inv_days else 0
        avg_inv_to_pay = sum(inv_to_pay_days) / len(inv_to_pay_days) if inv_to_pay_days else 0

        total_cycle = avg_pr_to_po + avg_po_to_gr + avg_gr_to_inv + avg_inv_to_pay

        def get_status(avg, target):
            variance = (avg - target) / target * 100 if target > 0 else 0
            if variance <= 0:
                return 'on_track'
            elif variance <= 25:
                return 'warning'
            return 'critical'

        return {
            'stages': {
                'pr_to_po': {
                    'avg_days': round(avg_pr_to_po, 1),
                    'target_days': 3,
                    'sample_size': len(pr_to_po_days),
                    'status': get_status(avg_pr_to_po, 3)
                },
                'po_to_gr': {
                    'avg_days': round(avg_po_to_gr, 1),
                    'target_days': 7,
                    'sample_size': len(po_to_gr_days),
                    'status': get_status(avg_po_to_gr, 7)
                },
                'gr_to_invoice': {
                    'avg_days': round(avg_gr_to_inv, 1),
                    'target_days': 3,
                    'sample_size': len(gr_to_inv_days),
                    'status': get_status(avg_gr_to_inv, 3)
                },
                'invoice_to_payment': {
                    'avg_days': round(avg_inv_to_pay, 1),
                    'target_days': 30,
                    'sample_size': len(inv_to_pay_days),
                    'status': get_status(avg_inv_to_pay, 30)
                }
            },
            'total_cycle': {
                'avg_days': round(total_cycle, 1),
                'target_days': 43,
                'status': get_status(total_cycle, 43)
            }
        }

    def get_cycle_time_trends(self, months=12):
        """Get monthly trend of cycle times."""
        cutoff_date = date.today() - timedelta(days=months * 30)

        # Get monthly invoice to payment times
        paid_invoices = Invoice.objects.filter(
            organization=self.organization,
            status='paid',
            paid_date__isnull=False,
            invoice_date__gte=cutoff_date
        ).annotate(
            month=TruncMonth('invoice_date')
        ).values('month').annotate(
            avg_days=Avg(F('paid_date') - F('invoice_date')),
            count=Count('id')
        ).order_by('month')

        return [
            {
                'month': item['month'].strftime('%Y-%m'),
                'avg_days': item['avg_days'].days if item['avg_days'] else 0,
                'invoice_count': item['count']
            }
            for item in paid_invoices
        ]

    def get_cycle_time_by_category(self):
        """Cycle times broken down by spend category."""
        # Get invoices with linked POs for cycle time calculation
        invoices = Invoice.objects.filter(
            organization=self.organization,
            status='paid',
            paid_date__isnull=False,
            purchase_order__isnull=False
        ).select_related('purchase_order', 'purchase_order__category')

        invoices = self._apply_date_filters(invoices, 'invoice_date')

        # Group by category
        category_data = defaultdict(lambda: {
            'cycle_days': [],
            'spend': Decimal('0'),
            'count': 0
        })

        for inv in invoices:
            cat_name = (inv.purchase_order.category.name
                        if inv.purchase_order and inv.purchase_order.category
                        else 'Uncategorized')
            days = (inv.paid_date - inv.invoice_date).days
            if days >= 0:
                category_data[cat_name]['cycle_days'].append(days)
            category_data[cat_name]['spend'] += inv.invoice_amount
            category_data[cat_name]['count'] += 1

        result = []
        for cat_name, data in category_data.items():
            avg_days = sum(data['cycle_days']) / len(data['cycle_days']) if data['cycle_days'] else 0
            result.append({
                'category': cat_name,
                'total_days': round(avg_days, 1),
                'total_spend': float(data['spend']),
                'transaction_count': data['count']
            })

        return sorted(result, key=lambda x: x['total_spend'], reverse=True)

    def get_cycle_time_by_supplier(self):
        """Cycle times broken down by supplier."""
        invoices = Invoice.objects.filter(
            organization=self.organization,
            status='paid',
            paid_date__isnull=False
        ).select_related('supplier')

        invoices = self._apply_date_filters(invoices, 'invoice_date')

        # Group by supplier
        supplier_data = defaultdict(lambda: {
            'cycle_days': [],
            'spend': Decimal('0'),
            'count': 0,
            'on_time': 0
        })

        for inv in invoices:
            supplier_name = inv.supplier.name if inv.supplier else 'Unknown'
            days = (inv.paid_date - inv.invoice_date).days
            if days >= 0:
                supplier_data[supplier_name]['cycle_days'].append(days)
            supplier_data[supplier_name]['spend'] += inv.invoice_amount
            supplier_data[supplier_name]['count'] += 1
            if inv.days_overdue == 0:
                supplier_data[supplier_name]['on_time'] += 1

        result = []
        for supplier_name, data in supplier_data.items():
            avg_days = sum(data['cycle_days']) / len(data['cycle_days']) if data['cycle_days'] else 0
            on_time_rate = data['on_time'] / data['count'] * 100 if data['count'] > 0 else 0
            result.append({
                'supplier': supplier_name,
                'total_days': round(avg_days, 1),
                'total_spend': float(data['spend']),
                'transaction_count': data['count'],
                'on_time_rate': round(on_time_rate, 1)
            })

        return sorted(result, key=lambda x: x['total_spend'], reverse=True)

    def get_stage_drilldown(self, stage):
        """Get detailed breakdown for a specific P2P stage."""
        slowest_docs = []
        avg_days = 0
        total_value = Decimal('0')
        doc_count = 0

        if stage == 'pr_to_po':
            prs = PurchaseRequisition.objects.filter(
                organization=self.organization,
                status='converted_to_po',
                approval_date__isnull=False,
                purchase_orders__isnull=False
            ).select_related('supplier_suggested').prefetch_related('purchase_orders')[:100]

            days_list = []
            for pr in prs:
                po = pr.purchase_orders.first()
                if po and pr.approval_date:
                    days = (po.created_date - pr.approval_date).days
                    if days >= 0:
                        days_list.append((pr, days, pr.estimated_amount))
                        total_value += pr.estimated_amount

            days_list.sort(key=lambda x: x[1], reverse=True)
            doc_count = len(days_list)
            avg_days = sum(d[1] for d in days_list) / len(days_list) if days_list else 0

            for pr, days, amt in days_list[:10]:
                slowest_docs.append({
                    'document_number': pr.pr_number,
                    'supplier_name': pr.supplier_suggested.name if pr.supplier_suggested else 'N/A',
                    'days_in_stage': days,
                    'amount': float(amt)
                })

        elif stage == 'po_to_gr':
            pos = PurchaseOrder.objects.filter(
                organization=self.organization,
                sent_date__isnull=False,
                goods_receipts__isnull=False
            ).select_related('supplier').prefetch_related('goods_receipts')[:100]

            days_list = []
            for po in pos:
                gr = po.goods_receipts.first()
                if gr:
                    days = (gr.received_date - po.sent_date).days
                    if days >= 0:
                        days_list.append((po, days, po.total_amount))
                        total_value += po.total_amount

            days_list.sort(key=lambda x: x[1], reverse=True)
            doc_count = len(days_list)
            avg_days = sum(d[1] for d in days_list) / len(days_list) if days_list else 0

            for po, days, amt in days_list[:10]:
                slowest_docs.append({
                    'document_number': po.po_number,
                    'supplier_name': po.supplier.name if po.supplier else 'N/A',
                    'days_in_stage': days,
                    'amount': float(amt)
                })

        elif stage == 'gr_to_invoice':
            grs = GoodsReceipt.objects.filter(
                organization=self.organization,
                invoices__isnull=False
            ).select_related('purchase_order', 'purchase_order__supplier').prefetch_related('invoices')[:100]

            days_list = []
            for gr in grs:
                inv = gr.invoices.first()
                if inv:
                    days = (inv.invoice_date - gr.received_date).days
                    if days >= 0:
                        days_list.append((gr, inv, days, inv.invoice_amount))
                        total_value += inv.invoice_amount

            days_list.sort(key=lambda x: x[2], reverse=True)
            doc_count = len(days_list)
            avg_days = sum(d[2] for d in days_list) / len(days_list) if days_list else 0

            for gr, inv, days, amt in days_list[:10]:
                slowest_docs.append({
                    'document_number': gr.gr_number,
                    'supplier_name': gr.purchase_order.supplier.name if gr.purchase_order and gr.purchase_order.supplier else 'N/A',
                    'days_in_stage': days,
                    'amount': float(amt)
                })

        elif stage == 'invoice_to_payment':
            invoices = Invoice.objects.filter(
                organization=self.organization,
                status='paid',
                paid_date__isnull=False
            ).select_related('supplier')[:100]

            days_list = []
            for inv in invoices:
                days = (inv.paid_date - inv.invoice_date).days
                if days >= 0:
                    days_list.append((inv, days, inv.invoice_amount))
                    total_value += inv.invoice_amount

            days_list.sort(key=lambda x: x[1], reverse=True)
            doc_count = len(days_list)
            avg_days = sum(d[1] for d in days_list) / len(days_list) if days_list else 0

            for inv, days, amt in days_list[:10]:
                slowest_docs.append({
                    'document_number': inv.invoice_number,
                    'supplier_name': inv.supplier.name if inv.supplier else 'N/A',
                    'days_in_stage': days,
                    'amount': float(amt)
                })

        return {
            'stage': stage,
            'avg_days': round(avg_days, 1),
            'documents_count': doc_count,
            'total_value': float(total_value),
            'slowest_documents': slowest_docs
        }

    def get_bottleneck_analysis(self):
        """Identify where delays occur in the P2P process."""
        cycle = self.get_p2p_cycle_overview()
        stages = cycle['stages']

        bottlenecks = []
        for stage_name, stage_data in stages.items():
            variance = ((stage_data['avg_days'] - stage_data['target_days'])
                        / stage_data['target_days'] * 100) if stage_data['target_days'] > 0 else 0

            status = 'on_track'
            if variance > 50:
                status = 'critical'
            elif variance > 20:
                status = 'warning'

            bottlenecks.append({
                'stage': stage_name.replace('_', ' ').title(),
                'avg_days': stage_data['avg_days'],
                'target_days': stage_data['target_days'],
                'variance_percent': round(variance, 1),
                'status': status,
                'sample_size': stage_data['sample_size']
            })

        # Sort by variance (worst first)
        bottlenecks.sort(key=lambda x: x['variance_percent'], reverse=True)

        return bottlenecks

    def get_process_funnel(self, months=12):
        """Get document flow funnel (PRs → POs → GRs → Invoices → Paid)."""
        filters = Q(organization=self.organization)

        # Apply date filters (use months if no explicit date filter)
        if date_from := self.filters.get('date_from'):
            parsed_date = self._parse_date(date_from)
            filters &= Q(created_date__gte=parsed_date)
        elif months:
            cutoff_date = date.today() - timedelta(days=months * 30)
            filters &= Q(created_date__gte=cutoff_date)

        if date_to := self.filters.get('date_to'):
            parsed_date = self._parse_date(date_to)
            filters &= Q(created_date__lte=parsed_date)

        # Count documents at each stage
        pr_count = PurchaseRequisition.objects.filter(filters).count()
        pr_approved = PurchaseRequisition.objects.filter(
            filters,
            status__in=['approved', 'converted_to_po']
        ).count()

        po_count = PurchaseOrder.objects.filter(
            organization=self.organization
        ).count()

        gr_count = GoodsReceipt.objects.filter(
            organization=self.organization
        ).count()

        inv_count = Invoice.objects.filter(
            organization=self.organization
        ).count()

        inv_paid = Invoice.objects.filter(
            organization=self.organization,
            status='paid'
        ).count()

        return {
            'stages': [
                {'name': 'PRs Created', 'count': pr_count},
                {'name': 'PRs Approved', 'count': pr_approved},
                {'name': 'POs Created', 'count': po_count},
                {'name': 'GRs Received', 'count': gr_count},
                {'name': 'Invoices', 'count': inv_count},
                {'name': 'Paid', 'count': inv_paid}
            ]
        }

    # =========================================================================
    # 3-WAY MATCHING ANALYSIS
    # =========================================================================

    def get_matching_overview(self):
        """Get 3-way match rates and exception metrics."""
        invoices = Invoice.objects.filter(organization=self.organization)
        invoices = self._apply_date_filters(invoices, 'invoice_date')

        total_count = invoices.count()
        total_amount = invoices.aggregate(total=Sum('invoice_amount'))['total'] or Decimal('0')

        # Match status breakdown
        match_stats = invoices.values('match_status').annotate(
            count=Count('id'),
            amount=Sum('invoice_amount')
        )

        match_breakdown = {stat['match_status']: {
            'count': stat['count'],
            'amount': float(stat['amount'] or 0)
        } for stat in match_stats}

        # Exception metrics
        exceptions = invoices.filter(has_exception=True)
        exception_count = exceptions.count()
        exception_amount = exceptions.aggregate(total=Sum('invoice_amount'))['total'] or Decimal('0')

        # Open vs resolved exceptions
        open_exceptions = exceptions.filter(exception_resolved=False).count()
        resolved_exceptions = exceptions.filter(exception_resolved=True).count()

        # Calculate average resolution time for resolved exceptions
        resolved = invoices.filter(
            has_exception=True,
            exception_resolved=True,
            exception_resolved_at__isnull=False
        )
        avg_resolution_days = 0
        if resolved.exists():
            # Calculate average days between invoice date and resolution date
            resolution_times = []
            for inv in resolved:
                if inv.exception_resolved_at and inv.invoice_date:
                    # exception_resolved_at is datetime, invoice_date is date
                    resolved_date = inv.exception_resolved_at.date()
                    days = (resolved_date - inv.invoice_date).days
                    if days >= 0:
                        resolution_times.append(days)
            if resolution_times:
                avg_resolution_days = sum(resolution_times) / len(resolution_times)

        # Get counts and amounts for each match status
        three_way = match_breakdown.get('3way_matched', {'count': 0, 'amount': 0})
        two_way = match_breakdown.get('2way_matched', {'count': 0, 'amount': 0})

        # Calculate percentages
        three_way_pct = round(three_way['count'] / total_count * 100, 1) if total_count > 0 else 0
        two_way_pct = round(two_way['count'] / total_count * 100, 1) if total_count > 0 else 0
        exception_pct = round(exception_count / total_count * 100, 1) if total_count > 0 else 0

        # Return in nested structure expected by frontend
        return {
            'total_invoices': total_count,
            'total_amount': float(total_amount),
            'three_way_matched': {
                'count': three_way['count'],
                'amount': three_way['amount'],
                'percentage': three_way_pct
            },
            'two_way_matched': {
                'count': two_way['count'],
                'amount': two_way['amount'],
                'percentage': two_way_pct
            },
            'exceptions': {
                'count': open_exceptions,  # Open exceptions count
                'amount': float(exception_amount),
                'percentage': exception_pct,
                'total_count': exception_count,  # All exceptions (open + resolved)
                'resolved_count': resolved_exceptions
            },
            'avg_resolution_days': round(avg_resolution_days, 1),
            # Keep legacy fields for backwards compatibility
            'match_rate_3way': three_way_pct,
            'match_rate_2way': two_way_pct,
            'exception_rate': exception_pct,
            'exception_count': exception_count,
            'exception_amount': float(exception_amount),
            'open_exceptions': open_exceptions,
            'resolved_exceptions': resolved_exceptions,
            'match_breakdown': match_breakdown
        }

    def get_exceptions_by_type(self):
        """Breakdown of exceptions by type."""
        exceptions = Invoice.objects.filter(
            organization=self.organization,
            has_exception=True
        )
        exceptions = self._apply_date_filters(exceptions, 'invoice_date')

        by_type = exceptions.values('exception_type').annotate(
            count=Count('id'),
            amount=Sum('invoice_amount'),
            open_count=Count(Case(
                When(exception_resolved=False, then=1),
                output_field=IntegerField()
            ))
        ).order_by('-amount')

        return [
            {
                'exception_type': item['exception_type'],
                'display_name': dict(Invoice.EXCEPTION_TYPE_CHOICES).get(
                    item['exception_type'], item['exception_type']
                ),
                'count': item['count'],
                'amount': float(item['amount'] or 0),
                'open_count': item['open_count']
            }
            for item in by_type
        ]

    def get_exceptions_by_supplier(self, limit=20):
        """Which suppliers have most exceptions."""
        from django.db.models import Subquery, OuterRef

        exceptions = Invoice.objects.filter(
            organization=self.organization,
            has_exception=True
        ).select_related('supplier')

        exceptions = self._apply_date_filters(exceptions, 'invoice_date')

        # Get primary exception type per supplier (most common)
        primary_type_subquery = Invoice.objects.filter(
            organization=self.organization,
            has_exception=True,
            supplier_id=OuterRef('supplier__id')
        ).values('exception_type').annotate(
            type_count=Count('id')
        ).order_by('-type_count').values('exception_type')[:1]

        by_supplier = exceptions.values(
            'supplier__id', 'supplier__name'
        ).annotate(
            exception_count=Count('id'),
            exception_amount=Sum('invoice_amount'),
            open_count=Count(Case(
                When(exception_resolved=False, then=1),
                output_field=IntegerField()
            ))
        ).order_by('-exception_amount')[:limit]

        # Get total invoices per supplier for exception rate calculation
        supplier_totals = {}
        supplier_ids = [item['supplier__id'] for item in by_supplier if item['supplier__id']]
        if supplier_ids:
            totals = Invoice.objects.filter(
                organization=self.organization,
                supplier_id__in=supplier_ids
            ).values('supplier_id').annotate(total=Count('id'))
            supplier_totals = {t['supplier_id']: t['total'] for t in totals}

        # Get primary exception type per supplier
        primary_types = {}
        if supplier_ids:
            for supplier_id in supplier_ids:
                primary = Invoice.objects.filter(
                    organization=self.organization,
                    has_exception=True,
                    supplier_id=supplier_id
                ).values('exception_type').annotate(
                    type_count=Count('id')
                ).order_by('-type_count').first()
                if primary:
                    primary_types[supplier_id] = primary['exception_type']

        result = []
        for item in by_supplier:
            supplier_id = item['supplier__id']
            total_invoices = supplier_totals.get(supplier_id, 0)
            exception_count = item['exception_count']
            exception_rate = (exception_count / total_invoices * 100) if total_invoices > 0 else 0

            result.append({
                'supplier': item['supplier__name'],
                'supplier_id': supplier_id,
                'total_invoices': total_invoices,
                'exception_count': exception_count,
                'exception_rate': round(exception_rate, 1),
                'exception_amount': float(item['exception_amount'] or 0),
                'primary_exception_type': primary_types.get(supplier_id),
                'open_count': item['open_count']
            })

        return result

    def get_price_variance_analysis(self):
        """PO price vs Invoice price variances."""
        invoices = Invoice.objects.filter(
            organization=self.organization,
            purchase_order__isnull=False,
            has_exception=True,
            exception_type='price_variance'
        ).select_related('purchase_order', 'supplier')

        invoices = self._apply_date_filters(invoices, 'invoice_date')

        variances = []
        for inv in invoices[:50]:  # Limit for performance
            if inv.purchase_order and inv.purchase_order.total_amount > 0:
                variance_pct = ((inv.invoice_amount - inv.purchase_order.total_amount)
                                / inv.purchase_order.total_amount * 100)
                variance_amt = inv.invoice_amount - inv.purchase_order.total_amount

                variances.append({
                    'invoice_id': inv.id,
                    'invoice_number': inv.invoice_number,
                    'supplier_name': inv.supplier.name,
                    'po_number': inv.purchase_order.po_number,
                    'po_amount': float(inv.purchase_order.total_amount),
                    'invoice_amount': float(inv.invoice_amount),
                    'variance_amount': float(variance_amt),
                    'variance_percent': round(float(variance_pct), 1),
                    'resolved': inv.exception_resolved
                })

        return sorted(variances, key=lambda x: abs(x['variance_percent']), reverse=True)

    def get_quantity_variance_analysis(self):
        """PO qty vs GR qty vs Invoice qty variances."""
        grs = GoodsReceipt.objects.filter(
            organization=self.organization,
            quantity_ordered__isnull=False
        ).select_related('purchase_order', 'purchase_order__supplier')

        variances = []
        for gr in grs[:50]:  # Limit for performance
            if gr.quantity_ordered > 0:
                variance_pct = ((gr.quantity_received - gr.quantity_ordered)
                                / gr.quantity_ordered * 100)
                variance_qty = gr.quantity_received - gr.quantity_ordered

                variances.append({
                    'gr_id': gr.id,
                    'gr_number': gr.gr_number,
                    'po_number': gr.purchase_order.po_number if gr.purchase_order else None,
                    'supplier_name': gr.purchase_order.supplier.name if gr.purchase_order and gr.purchase_order.supplier else 'N/A',
                    'quantity_ordered': float(gr.quantity_ordered),
                    'quantity_received': float(gr.quantity_received),
                    'quantity_accepted': float(gr.quantity_accepted) if gr.quantity_accepted else None,
                    'variance_quantity': float(variance_qty),
                    'variance_percent': round(float(variance_pct), 1),
                    'status': gr.status
                })

        return sorted(variances, key=lambda x: abs(x['variance_percent']), reverse=True)

    def get_matching_exceptions(self, status='open', exception_type=None, limit=100):
        """Get list of invoice exceptions with filtering."""
        exceptions = Invoice.objects.filter(
            organization=self.organization,
            has_exception=True
        ).select_related('supplier', 'purchase_order', 'goods_receipt')

        # Apply status filter
        if status == 'open':
            exceptions = exceptions.filter(exception_resolved=False)
        elif status == 'resolved':
            exceptions = exceptions.filter(exception_resolved=True)
        # 'all' returns both

        # Apply exception type filter
        if exception_type:
            exceptions = exceptions.filter(exception_type=exception_type)

        exceptions = exceptions.order_by('-invoice_date')[:limit]

        # Calculate days_open (days since exception was created / invoice received)
        today = date.today()

        return [
            {
                'invoice_id': inv.id,
                'invoice_number': inv.invoice_number,
                'supplier': inv.supplier.name if inv.supplier else 'Unknown',
                'supplier_id': inv.supplier_id,
                'invoice_amount': float(inv.invoice_amount),
                'exception_type': inv.exception_type,
                'exception_amount': float(inv.exception_amount) if inv.exception_amount else None,
                'days_open': (today - inv.received_date).days if inv.received_date else (today - inv.invoice_date).days,
                'po_number': inv.purchase_order.po_number if inv.purchase_order else None,
                'invoice_date': inv.invoice_date.isoformat(),
                'status': inv.status,
                'exception_notes': inv.exception_notes or ''
            }
            for inv in exceptions
        ]

    def get_invoice_match_detail(self, invoice_id):
        """Get detailed match information for a specific invoice."""
        try:
            inv = Invoice.objects.select_related(
                'supplier', 'purchase_order', 'goods_receipt'
            ).get(id=invoice_id, organization=self.organization)
        except Invoice.DoesNotExist:
            return None

        # Build variance detail
        variance_detail = None
        if inv.purchase_order:
            po = inv.purchase_order
            variance_detail = {
                'po_amount': float(po.total_amount),
                'invoice_amount': float(inv.invoice_amount),
                'variance_amount': float(inv.invoice_amount - po.total_amount),
                'variance_percent': round(
                    float((inv.invoice_amount - po.total_amount) / po.total_amount * 100), 1
                ) if po.total_amount > 0 else 0
            }

        return {
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'supplier': {
                'id': inv.supplier_id,
                'name': inv.supplier.name if inv.supplier else None
            },
            'invoice_date': inv.invoice_date.isoformat(),
            'due_date': inv.due_date.isoformat(),
            'invoice_amount': float(inv.invoice_amount),
            'tax_amount': float(inv.tax_amount),
            'net_amount': float(inv.net_amount),
            'status': inv.status,
            'match_status': inv.match_status,
            'has_exception': inv.has_exception,
            'exception_type': inv.exception_type,
            'exception_type_display': dict(Invoice.EXCEPTION_TYPE_CHOICES).get(
                inv.exception_type, inv.exception_type
            ) if inv.exception_type else None,
            'exception_amount': float(inv.exception_amount) if inv.exception_amount else None,
            'exception_notes': inv.exception_notes,
            'exception_resolved': inv.exception_resolved,
            'purchase_order': {
                'id': inv.purchase_order.id,
                'po_number': inv.purchase_order.po_number,
                'total_amount': float(inv.purchase_order.total_amount),
                'status': inv.purchase_order.status
            } if inv.purchase_order else None,
            'goods_receipt': {
                'id': inv.goods_receipt.id,
                'gr_number': inv.goods_receipt.gr_number,
                'received_date': inv.goods_receipt.received_date.isoformat(),
                'status': inv.goods_receipt.status
            } if inv.goods_receipt else None,
            'variance_detail': variance_detail,
            'days_outstanding': inv.days_outstanding,
            'is_overdue': inv.is_overdue
        }

    def resolve_exception(self, invoice_id, user, resolution_notes):
        """Resolve a single invoice exception."""
        try:
            inv = Invoice.objects.get(
                id=invoice_id,
                organization=self.organization,
                has_exception=True,
                exception_resolved=False
            )
        except Invoice.DoesNotExist:
            return None

        inv.exception_resolved = True
        inv.exception_notes = (inv.exception_notes or '') + f'\n\nResolved: {resolution_notes}'
        inv.save(update_fields=['exception_resolved', 'exception_notes', 'updated_at'])

        return {
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'resolved': True,
            'message': 'Exception resolved successfully'
        }

    def bulk_resolve_exceptions(self, invoice_ids, user, resolution_notes):
        """Resolve multiple invoice exceptions at once."""
        invoices = Invoice.objects.filter(
            id__in=invoice_ids,
            organization=self.organization,
            has_exception=True,
            exception_resolved=False
        )

        resolved_count = 0
        failed_ids = []

        for inv in invoices:
            try:
                inv.exception_resolved = True
                inv.exception_notes = (inv.exception_notes or '') + f'\n\nResolved: {resolution_notes}'
                inv.save(update_fields=['exception_resolved', 'exception_notes', 'updated_at'])
                resolved_count += 1
            except Exception:
                failed_ids.append(inv.id)

        return {
            'resolved_count': resolved_count,
            'failed_count': len(failed_ids),
            'failed_ids': failed_ids,
            'message': f'Successfully resolved {resolved_count} exceptions'
        }

    # =========================================================================
    # INVOICE AGING / AP ANALYSIS
    # =========================================================================

    def get_aging_overview(self):
        """Invoice aging buckets: Current, 1-30, 31-60, 61-90, 90+"""
        today = date.today()

        invoices = Invoice.objects.filter(
            organization=self.organization,
            status__in=['received', 'pending_match', 'matched', 'approved', 'on_hold']
        )

        # Calculate aging buckets with display names matching frontend expectations
        bucket_definitions = [
            {'name': 'Current', 'display': 'Current', 'min': 0, 'max': 30},
            {'name': '31-60 Days', 'display': '31-60 Days', 'min': 31, 'max': 60},
            {'name': '61-90 Days', 'display': '61-90 Days', 'min': 61, 'max': 90},
            {'name': '90+ Days', 'display': '90+ Days', 'min': 91, 'max': 9999}
        ]

        buckets_list = []
        total_ap = Decimal('0')
        total_overdue = Decimal('0')

        # First pass: calculate totals
        for bucket_def in bucket_definitions:
            bucket_invoices = [
                inv for inv in invoices
                if bucket_def['min'] <= inv.days_outstanding <= bucket_def['max']
            ]

            bucket_amount = sum(inv.invoice_amount for inv in bucket_invoices)
            total_ap += bucket_amount

            if bucket_def['name'] != 'Current':
                total_overdue += bucket_amount

            buckets_list.append({
                'bucket': bucket_def['display'],
                'count': len(bucket_invoices),
                'amount': float(bucket_amount),
                'percentage': 0  # Will be calculated after we know total
            })

        # Second pass: calculate percentages
        for bucket in buckets_list:
            if total_ap > 0:
                bucket['percentage'] = round(bucket['amount'] / float(total_ap) * 100, 1)

        # Calculate DPO
        paid_invoices = Invoice.objects.filter(
            organization=self.organization,
            status='paid',
            paid_date__isnull=False
        )

        dpo_days = []
        for inv in paid_invoices:
            days = (inv.paid_date - inv.invoice_date).days
            if days >= 0:
                dpo_days.append(days)

        avg_dpo = sum(dpo_days) / len(dpo_days) if dpo_days else 0

        # On-time payment rate
        on_time = sum(1 for inv in paid_invoices if inv.days_overdue == 0)
        on_time_rate = on_time / len(dpo_days) * 100 if dpo_days else 0

        # Get DPO trend for past 6 months
        trend = []
        for i in range(5, -1, -1):
            month_start = date.today().replace(day=1) - timedelta(days=i * 30)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            month_paid = Invoice.objects.filter(
                organization=self.organization,
                status='paid',
                paid_date__isnull=False,
                paid_date__gte=month_start,
                paid_date__lte=month_end
            )

            month_dpo_days = []
            for inv in month_paid:
                days = (inv.paid_date - inv.invoice_date).days
                if days >= 0:
                    month_dpo_days.append(days)

            month_avg_dpo = sum(month_dpo_days) / len(month_dpo_days) if month_dpo_days else 0
            trend.append({
                'month': month_start.strftime('%Y-%m'),
                'dpo': round(month_avg_dpo, 1)
            })

        return {
            'total_ap': float(total_ap),
            'total_overdue': float(total_overdue),
            'overdue_amount': float(total_overdue),  # Added for frontend compatibility
            'avg_dpo': round(avg_dpo, 1),
            'current_dpo': round(avg_dpo, 1),  # Added for frontend compatibility
            'on_time_rate': round(on_time_rate, 1),
            'buckets': buckets_list,  # Now an array with bucket, count, amount, percentage
            'trend': trend  # Added for frontend compatibility
        }

    def get_aging_by_supplier(self, limit=20):
        """Aging breakdown by supplier with bucket details."""
        invoices = Invoice.objects.filter(
            organization=self.organization,
            status__in=['received', 'pending_match', 'matched', 'approved', 'on_hold']
        ).select_related('supplier')

        # Group by supplier with aging bucket breakdown
        supplier_aging = defaultdict(lambda: {
            'total_ap': Decimal('0'),
            'current': Decimal('0'),
            'days_31_60': Decimal('0'),
            'days_61_90': Decimal('0'),
            'days_90_plus': Decimal('0'),
            'count': 0,
            'days_outstanding_sum': 0,
            'on_time_count': 0
        })

        for inv in invoices:
            if not inv.supplier:
                continue
            supplier_name = inv.supplier.name
            supplier_id = inv.supplier_id
            key = (supplier_id, supplier_name)

            amount = inv.invoice_amount
            days = inv.days_outstanding

            supplier_aging[key]['total_ap'] += amount
            supplier_aging[key]['count'] += 1
            supplier_aging[key]['days_outstanding_sum'] += days

            # Categorize by aging bucket
            if days <= 30:
                supplier_aging[key]['current'] += amount
            elif days <= 60:
                supplier_aging[key]['days_31_60'] += amount
            elif days <= 90:
                supplier_aging[key]['days_61_90'] += amount
            else:
                supplier_aging[key]['days_90_plus'] += amount

        # Get on-time rate from paid invoices per supplier
        # On-time = paid_date <= due_date (paid on or before due date)
        from django.db.models import F
        paid_invoices = Invoice.objects.filter(
            organization=self.organization,
            status='paid',
            paid_date__isnull=False,
            due_date__isnull=False
        ).values('supplier_id').annotate(
            total_paid=Count('id'),
            on_time=Count(Case(
                When(paid_date__lte=F('due_date'), then=1),
                output_field=IntegerField()
            ))
        )
        on_time_rates = {p['supplier_id']: (p['on_time'] / p['total_paid'] * 100 if p['total_paid'] > 0 else 0) for p in paid_invoices}

        # Convert to list
        result = []
        for key, data in supplier_aging.items():
            supplier_id, supplier_name = key
            count = data['count']
            avg_days = data['days_outstanding_sum'] / count if count > 0 else 0

            result.append({
                'supplier': supplier_name,
                'supplier_id': supplier_id,
                'total_ap': float(data['total_ap']),
                'current': float(data['current']),
                'days_31_60': float(data['days_31_60']),
                'days_61_90': float(data['days_61_90']),
                'days_90_plus': float(data['days_90_plus']),
                'avg_days_outstanding': round(avg_days, 1),
                'on_time_rate': round(on_time_rates.get(supplier_id, 0), 1)
            })

        return sorted(result, key=lambda x: x['total_ap'], reverse=True)[:limit]

    def get_payment_terms_compliance(self):
        """On-time vs late payment rates by payment terms."""
        paid_invoices = Invoice.objects.filter(
            organization=self.organization,
            status='paid',
            paid_date__isnull=False,
            payment_terms__isnull=False
        ).exclude(payment_terms='')

        # Group by payment terms
        terms_stats = defaultdict(lambda: {'on_time': 0, 'late': 0, 'total': 0})

        for inv in paid_invoices:
            terms = inv.payment_terms
            terms_stats[terms]['total'] += 1

            if inv.days_overdue == 0:
                terms_stats[terms]['on_time'] += 1
            else:
                terms_stats[terms]['late'] += 1

        return [
            {
                'payment_terms': terms,
                'total': stats['total'],
                'on_time': stats['on_time'],
                'late': stats['late'],
                'on_time_rate': round(stats['on_time'] / stats['total'] * 100, 1) if stats['total'] > 0 else 0
            }
            for terms, stats in terms_stats.items()
        ]

    def get_cash_flow_forecast(self, weeks=4):
        """Projected payments by week."""
        today = date.today()
        forecasts = []

        for week in range(weeks):
            week_start = today + timedelta(weeks=week)
            week_end = week_start + timedelta(days=6)

            invoices = Invoice.objects.filter(
                organization=self.organization,
                status__in=['approved', 'matched'],
                due_date__gte=week_start,
                due_date__lte=week_end
            ).aggregate(
                amount=Sum('invoice_amount'),
                count=Count('id')
            )

            forecasts.append({
                'week': week + 1,
                'week_start': week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'amount': float(invoices['amount'] or 0),
                'invoice_count': invoices['count'] or 0
            })

        return forecasts

    # =========================================================================
    # PURCHASE REQUISITION ANALYSIS
    # =========================================================================

    def get_pr_overview(self):
        """PR metrics: volume, conversion rate, rejection rate."""
        prs = PurchaseRequisition.objects.filter(organization=self.organization)
        prs = self._apply_date_filters(prs, 'created_date')

        total = prs.count()
        converted = prs.filter(status='converted_to_po').count()
        rejected = prs.filter(status='rejected').count()
        pending = prs.filter(status='pending_approval').count()

        # Average approval time
        approved_prs = prs.filter(
            submitted_date__isnull=False,
            approval_date__isnull=False
        )

        approval_days = []
        for pr in approved_prs:
            days = (pr.approval_date - pr.submitted_date).days
            if days >= 0:
                approval_days.append(days)

        avg_approval = sum(approval_days) / len(approval_days) if approval_days else 0

        # Total value
        total_value = prs.aggregate(total=Sum('estimated_amount'))['total'] or Decimal('0')

        # Status breakdown for frontend
        status_counts = prs.values('status').annotate(
            count=Count('id'),
            value=Sum('estimated_amount')
        )
        by_status = [
            {
                'status': item['status'],
                'count': item['count'],
                'value': float(item['value'] or 0)
            }
            for item in status_counts
        ]

        # Status breakdown as dict for quick lookup
        status_breakdown = {item['status']: item['count'] for item in by_status}

        return {
            'total_prs': total,
            'total_count': total,  # Added for frontend compatibility
            'total_value': float(total_value),
            'conversion_rate': round(converted / total * 100, 1) if total > 0 else 0,
            'rejection_rate': round(rejected / total * 100, 1) if total > 0 else 0,
            'pending_count': pending,
            'avg_approval_days': round(avg_approval, 1),
            'by_status': by_status,  # Added for frontend compatibility
            'status_breakdown': status_breakdown  # Added for quick lookup
        }

    def get_pr_by_department(self):
        """Requisition patterns by department."""
        prs = PurchaseRequisition.objects.filter(organization=self.organization)
        prs = self._apply_date_filters(prs, 'created_date')

        by_dept = prs.values('department').annotate(
            count=Count('id'),
            total_value=Sum('estimated_amount'),
            approved=Count(Case(
                When(status__in=['approved', 'converted_to_po'], then=1),
                output_field=IntegerField()
            )),
            rejected=Count(Case(
                When(status='rejected', then=1),
                output_field=IntegerField()
            ))
        ).order_by('-total_value')

        return [
            {
                'department': item['department'] or 'Unassigned',
                'pr_count': item['count'],
                'total_value': float(item['total_value'] or 0),
                'approval_rate': round(item['approved'] / item['count'] * 100, 1) if item['count'] > 0 else 0,
                'rejection_rate': round(item['rejected'] / item['count'] * 100, 1) if item['count'] > 0 else 0
            }
            for item in by_dept
        ]

    def get_pr_pending(self, limit=50):
        """Get pending approval PRs."""
        pending = PurchaseRequisition.objects.filter(
            organization=self.organization,
            status='pending_approval'
        ).select_related('requested_by', 'category').order_by('-submitted_date')[:limit]

        today = date.today()

        return [
            {
                'id': pr.id,
                'pr_number': pr.pr_number,
                'requested_by': pr.requested_by.username if pr.requested_by else None,
                'department': pr.department,
                'estimated_amount': float(pr.estimated_amount),
                'category': pr.category.name if pr.category else None,
                'submitted_date': pr.submitted_date.isoformat() if pr.submitted_date else None,
                'days_pending': (today - pr.submitted_date).days if pr.submitted_date else 0,
                'priority': pr.priority
            }
            for pr in pending
        ]

    # =========================================================================
    # PURCHASE ORDER ANALYSIS
    # =========================================================================

    def get_po_overview(self):
        """PO metrics: volume, value, contract coverage."""
        pos = PurchaseOrder.objects.filter(organization=self.organization)
        pos = self._apply_date_filters(pos, 'created_date')

        total = pos.count()
        total_value = pos.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        contract_backed = pos.filter(is_contract_backed=True)
        contract_value = contract_backed.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        amended = pos.filter(amendment_count__gt=0).count()

        # Status breakdown
        by_status = pos.values('status').annotate(
            count=Count('id'),
            value=Sum('total_amount')
        )

        status_list = [
            {
                'status': item['status'],
                'count': item['count'],
                'value': float(item['value'] or 0)
            }
            for item in by_status
        ]

        # Calculate values for frontend
        off_contract_value = float(total_value - contract_value)
        contract_coverage_pct = round(float(contract_value / total_value * 100), 1) if total_value > 0 else 0
        avg_po_value = float(total_value / total) if total > 0 else 0

        return {
            'total_pos': total,
            'total_count': total,  # Added for frontend compatibility
            'total_value': float(total_value),
            'contract_coverage': contract_coverage_pct,
            'contract_coverage_pct': contract_coverage_pct,  # Added for frontend compatibility
            'on_contract_value': float(contract_value),  # Added for frontend compatibility
            'off_contract_value': off_contract_value,  # Added for frontend compatibility
            'maverick_rate': round((1 - float(contract_value / total_value)) * 100, 1) if total_value > 0 else 0,
            'amendment_rate': round(amended / total * 100, 1) if total > 0 else 0,
            'avg_po_value': avg_po_value,  # Added for frontend compatibility
            'by_status': status_list  # Changed from 'status_breakdown' to 'by_status'
        }

    def get_po_leakage(self, limit=20):
        """Off-contract PO identification by category."""
        maverick_pos = PurchaseOrder.objects.filter(
            organization=self.organization,
            is_contract_backed=False
        ).select_related('category', 'supplier')

        maverick_pos = self._apply_date_filters(maverick_pos, 'created_date')

        # Group by category
        by_category = defaultdict(lambda: {'maverick_amount': Decimal('0'), 'count': 0})

        for po in maverick_pos:
            cat_name = po.category.name if po.category else 'Uncategorized'
            by_category[cat_name]['maverick_amount'] += po.total_amount
            by_category[cat_name]['count'] += 1

        # Get total by category for percentage calculation
        all_pos = PurchaseOrder.objects.filter(organization=self.organization)
        all_pos = self._apply_date_filters(all_pos, 'created_date')

        category_totals = all_pos.values('category__name').annotate(
            total=Sum('total_amount')
        )

        cat_total_map = {
            item['category__name'] or 'Uncategorized': float(item['total'] or 0)
            for item in category_totals
        }

        result = []
        for cat_name, data in by_category.items():
            cat_total = cat_total_map.get(cat_name, 0)
            maverick_pct = float(data['maverick_amount']) / cat_total * 100 if cat_total > 0 else 0

            result.append({
                'category': cat_name,
                'maverick_amount': float(data['maverick_amount']),
                'maverick_count': data['count'],
                'category_total': cat_total,
                'maverick_percent': round(maverick_pct, 1)
            })

        return sorted(result, key=lambda x: x['maverick_amount'], reverse=True)[:limit]

    def get_po_amendment_analysis(self):
        """PO change order patterns."""
        amended_pos = PurchaseOrder.objects.filter(
            organization=self.organization,
            amendment_count__gt=0,
            original_amount__isnull=False
        )
        amended_pos = self._apply_date_filters(amended_pos, 'created_date')

        total_amended = amended_pos.count()
        all_pos = PurchaseOrder.objects.filter(organization=self.organization)
        all_pos = self._apply_date_filters(all_pos, 'created_date')
        total_pos = all_pos.count()

        # Calculate value changes
        value_increases = []
        value_decreases = []

        for po in amended_pos:
            if po.original_amount:
                change = float(po.total_amount - po.original_amount)
                if change > 0:
                    value_increases.append(change)
                else:
                    value_decreases.append(abs(change))

        avg_increase = sum(value_increases) / len(value_increases) if value_increases else 0
        avg_decrease = sum(value_decreases) / len(value_decreases) if value_decreases else 0

        return {
            'total_amended': total_amended,
            'amendment_rate': round(total_amended / total_pos * 100, 1) if total_pos > 0 else 0,
            'avg_amendments_per_po': round(
                sum(po.amendment_count for po in amended_pos) / total_amended, 1
            ) if total_amended > 0 else 0,
            'increase_count': len(value_increases),
            'decrease_count': len(value_decreases),
            'avg_increase_amount': round(avg_increase, 2),
            'avg_decrease_amount': round(avg_decrease, 2)
        }

    # =========================================================================
    # SUPPLIER PAYMENT PERFORMANCE
    # =========================================================================

    def get_supplier_payments_overview(self):
        """Overview of supplier payment metrics."""
        invoices = Invoice.objects.filter(organization=self.organization)

        # Suppliers with AP balance
        suppliers_with_ap = invoices.filter(
            status__in=['received', 'pending_match', 'matched', 'approved', 'on_hold']
        ).values('supplier').distinct().count()

        # Overall on-time rate
        paid_invoices = invoices.filter(status='paid', paid_date__isnull=False)
        on_time = sum(1 for inv in paid_invoices if inv.days_overdue == 0)
        on_time_rate = on_time / paid_invoices.count() * 100 if paid_invoices.count() > 0 else 0

        # Average DPO
        dpo_days = [
            (inv.paid_date - inv.invoice_date).days
            for inv in paid_invoices
            if (inv.paid_date - inv.invoice_date).days >= 0
        ]
        avg_dpo = sum(dpo_days) / len(dpo_days) if dpo_days else 0

        # Exception rate
        exception_count = invoices.filter(has_exception=True).count()
        total_count = invoices.count()
        exception_rate = exception_count / total_count * 100 if total_count > 0 else 0

        # Total AP balance
        total_ap_balance = invoices.filter(
            status__in=['received', 'pending_match', 'matched', 'approved', 'on_hold']
        ).aggregate(total=Sum('invoice_amount'))['total'] or Decimal('0')

        return {
            'total_suppliers_with_ap': suppliers_with_ap,  # Fixed field name
            'suppliers_with_ap': suppliers_with_ap,  # Keep for backward compatibility
            'overall_on_time_rate': round(on_time_rate, 1),  # Fixed field name
            'on_time_rate': round(on_time_rate, 1),  # Keep for backward compatibility
            'avg_dpo': round(avg_dpo, 1),
            'exception_rate': round(exception_rate, 1),
            'total_ap_balance': float(total_ap_balance)  # Added missing field
        }

    def get_supplier_payments_scorecard(self, limit=50):
        """Detailed supplier payment scorecard."""
        suppliers = Supplier.objects.filter(
            organization=self.organization,
            invoices__isnull=False
        ).distinct()

        scorecard = []

        for supplier in suppliers[:limit]:
            invoices = Invoice.objects.filter(
                organization=self.organization,
                supplier=supplier
            )

            # AP Balance
            ap_balance = invoices.filter(
                status__in=['received', 'pending_match', 'matched', 'approved', 'on_hold']
            ).aggregate(total=Sum('invoice_amount'))['total'] or Decimal('0')

            # DPO
            paid = invoices.filter(status='paid', paid_date__isnull=False)
            dpo_days = [
                (inv.paid_date - inv.invoice_date).days
                for inv in paid
                if (inv.paid_date - inv.invoice_date).days >= 0
            ]
            avg_dpo = sum(dpo_days) / len(dpo_days) if dpo_days else 0

            # On-time rate
            on_time = sum(1 for inv in paid if inv.days_overdue == 0)
            on_time_rate = on_time / len(dpo_days) * 100 if dpo_days else 0

            # Exception rate
            exception_count = invoices.filter(has_exception=True).count()
            total_count = invoices.count()
            exception_rate = exception_count / total_count * 100 if total_count > 0 else 0

            # Calculate score (weighted)
            score = (
                on_time_rate * 0.4 +
                (100 - min(exception_rate * 2, 100)) * 0.3 +
                min(100, max(0, 100 - abs(avg_dpo - 30) * 2)) * 0.3
            )

            # Determine risk level based on score
            if score >= 75:
                risk_level = 'low'
            elif score >= 50:
                risk_level = 'medium'
            else:
                risk_level = 'high'

            scorecard.append({
                'supplier_id': supplier.id,
                'supplier': supplier.name,  # Changed from 'supplier_name'
                'ap_balance': float(ap_balance),
                'dpo': round(avg_dpo, 1),  # Changed from 'avg_dpo'
                'on_time_rate': round(on_time_rate, 1),
                'exception_rate': round(exception_rate, 1),
                'invoice_count': total_count,
                'score': round(score, 0),
                'risk_level': risk_level  # Added for frontend compatibility
            })

        return sorted(scorecard, key=lambda x: x['score'], reverse=True)

    def get_supplier_payment_detail(self, supplier_id):
        """Detailed payment history for a specific supplier."""
        try:
            supplier = Supplier.objects.get(
                id=supplier_id,
                organization=self.organization
            )
        except Supplier.DoesNotExist:
            return None

        invoices = Invoice.objects.filter(
            organization=self.organization,
            supplier=supplier
        ).order_by('-invoice_date')

        # Summary stats
        total_invoices = invoices.count()
        total_amount = invoices.aggregate(total=Sum('invoice_amount'))['total'] or Decimal('0')

        paid = invoices.filter(status='paid', paid_date__isnull=False)
        avg_payment = paid.aggregate(avg=Avg('invoice_amount'))['avg'] or Decimal('0')

        # DPO
        dpo_days = [
            (inv.paid_date - inv.invoice_date).days
            for inv in paid
            if (inv.paid_date - inv.invoice_date).days >= 0
        ]
        avg_dpo = sum(dpo_days) / len(dpo_days) if dpo_days else 0

        # Exception breakdown
        exceptions = invoices.filter(has_exception=True).values('exception_type').annotate(
            count=Count('id')
        )

        # Recent invoices
        recent = [
            {
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'invoice_date': inv.invoice_date.isoformat(),
                'amount': float(inv.invoice_amount),
                'status': inv.status,
                'days_outstanding': inv.days_outstanding,
                'has_exception': inv.has_exception
            }
            for inv in invoices[:20]
        ]

        # Calculate additional metrics for frontend compatibility
        on_time = sum(1 for inv in paid if inv.days_overdue == 0)
        on_time_rate = on_time / len(dpo_days) * 100 if dpo_days else 0

        exception_count = invoices.filter(has_exception=True).count()
        exception_rate = exception_count / total_invoices * 100 if total_invoices > 0 else 0

        ap_balance = invoices.filter(
            status__in=['received', 'pending_match', 'matched', 'approved', 'on_hold']
        ).aggregate(total=Sum('invoice_amount'))['total'] or Decimal('0')

        # Aging buckets
        today = date.today()
        aging_buckets = []
        unpaid = invoices.filter(status__in=['received', 'pending_match', 'matched', 'approved', 'on_hold'])
        for bucket_name, min_days, max_days in [
            ('current', 0, 30), ('days_31_60', 31, 60), ('days_61_90', 61, 90), ('days_90_plus', 91, 9999)
        ]:
            bucket_invoices = [
                inv for inv in unpaid
                if min_days <= (today - inv.invoice_date).days <= max_days
            ]
            bucket_amount = sum(float(inv.invoice_amount) for inv in bucket_invoices)
            aging_buckets.append({'bucket': bucket_name, 'amount': bucket_amount, 'count': len(bucket_invoices)})

        return {
            'supplier_id': supplier.id,
            'supplier': supplier.name,  # Changed from 'supplier_name'
            'total_invoices': total_invoices,
            'total_amount': float(total_amount),
            'avg_payment': float(avg_payment),
            'dpo': round(avg_dpo, 1),  # Changed from 'avg_dpo'
            'on_time_rate': round(on_time_rate, 1),
            'exception_count': exception_count,
            'exception_rate': round(exception_rate, 1),
            'ap_balance': float(ap_balance),
            'aging_buckets': aging_buckets,
            'exception_breakdown': list(exceptions),
            'recent_invoices': recent
        }

    def get_supplier_payment_history(self, supplier_id, months=12):
        """Get payment history timeline for a specific supplier."""
        try:
            supplier = Supplier.objects.get(
                id=supplier_id,
                organization=self.organization
            )
        except Supplier.DoesNotExist:
            return None

        cutoff_date = date.today() - timedelta(days=months * 30)

        # Monthly payment trend
        invoices = Invoice.objects.filter(
            organization=self.organization,
            supplier=supplier,
            invoice_date__gte=cutoff_date
        ).annotate(
            month=TruncMonth('invoice_date')
        ).values('month').annotate(
            total=Sum('invoice_amount'),
            count=Count('id'),
            paid=Count(Case(
                When(status='paid', then=1),
                output_field=IntegerField()
            ))
        ).order_by('month')

        monthly_trend = [
            {
                'month': item['month'].strftime('%Y-%m'),
                'total_amount': float(item['total'] or 0),
                'invoice_count': item['count'],
                'paid_count': item['paid']
            }
            for item in invoices
        ]

        # Recent invoices with full detail
        recent_invoices = Invoice.objects.filter(
            organization=self.organization,
            supplier=supplier
        ).order_by('-invoice_date')[:20]

        recent = [
            {
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'invoice_date': inv.invoice_date.isoformat(),
                'due_date': inv.due_date.isoformat(),
                'paid_date': inv.paid_date.isoformat() if inv.paid_date else None,
                'amount': float(inv.invoice_amount),
                'status': inv.status,
                'days_outstanding': inv.days_outstanding,
                'days_overdue': inv.days_overdue,
                'has_exception': inv.has_exception,
                'exception_type': inv.exception_type
            }
            for inv in recent_invoices
        ]

        # Exception history
        exception_history = [
            {
                'invoice_id': inv.id,
                'invoice_number': inv.invoice_number,
                'exception_type': inv.exception_type,
                'amount': float(inv.exception_amount) if inv.exception_amount else float(inv.invoice_amount),
                'resolved': inv.status == 'paid',
                'date': inv.invoice_date.isoformat()
            }
            for inv in recent_invoices if inv.has_exception
        ]

        return {
            'supplier_id': supplier.id,
            'supplier': supplier.name,  # Changed from 'supplier_name'
            'monthly_trend': monthly_trend,
            'recent_invoices': recent,
            'exception_history': exception_history
        }

    def get_dpo_trends(self, months=12):
        """Get Days Payable Outstanding trends over time."""
        cutoff_date = date.today() - timedelta(days=months * 30)

        paid_invoices = Invoice.objects.filter(
            organization=self.organization,
            status='paid',
            paid_date__isnull=False,
            invoice_date__gte=cutoff_date
        )

        # Group by month
        monthly_data = defaultdict(lambda: {'days': [], 'count': 0, 'amount': Decimal('0')})

        for inv in paid_invoices:
            month_key = inv.invoice_date.strftime('%Y-%m')
            days = (inv.paid_date - inv.invoice_date).days
            if days >= 0:
                monthly_data[month_key]['days'].append(days)
            monthly_data[month_key]['count'] += 1
            monthly_data[month_key]['amount'] += inv.invoice_amount

        result = []
        for month, data in sorted(monthly_data.items()):
            avg_dpo = sum(data['days']) / len(data['days']) if data['days'] else 0
            result.append({
                'month': month,
                'avg_dpo': round(avg_dpo, 1),
                'invoice_count': data['count'],
                'total_amount': float(data['amount'])
            })

        return result

    def get_pr_approval_analysis(self):
        """Analyze PR approval bottlenecks and patterns."""
        prs = PurchaseRequisition.objects.filter(
            organization=self.organization,
            submitted_date__isnull=False
        )
        prs = self._apply_date_filters(prs, 'created_date')

        # Approval time distribution
        approved_prs = prs.filter(approval_date__isnull=False)
        time_buckets = {'<1 day': 0, '1-2 days': 0, '2-5 days': 0, '>5 days': 0}

        approval_days_list = []
        for pr in approved_prs:
            days = (pr.approval_date - pr.submitted_date).days
            if days >= 0:
                approval_days_list.append(days)
                if days < 1:
                    time_buckets['<1 day'] += 1
                elif days <= 2:
                    time_buckets['1-2 days'] += 1
                elif days <= 5:
                    time_buckets['2-5 days'] += 1
                else:
                    time_buckets['>5 days'] += 1

        avg_approval = sum(approval_days_list) / len(approval_days_list) if approval_days_list else 0

        # Pending by age
        pending = prs.filter(status='pending_approval')
        today = date.today()
        pending_age = []
        for pr in pending:
            if pr.submitted_date:
                days = (today - pr.submitted_date).days
                pending_age.append({
                    'id': pr.id,
                    'pr_number': pr.pr_number,
                    'days_pending': days,
                    'amount': float(pr.estimated_amount),
                    'priority': pr.priority
                })

        pending_age.sort(key=lambda x: x['days_pending'], reverse=True)

        return {
            'avg_approval_days': round(avg_approval, 1),
            'total_approved': len(approval_days_list),
            'time_distribution': time_buckets,
            'pending_count': len(pending_age),
            'oldest_pending': pending_age[:10]
        }

    def get_pr_detail(self, pr_id):
        """Get detailed information for a specific PR."""
        try:
            pr = PurchaseRequisition.objects.select_related(
                'requested_by', 'approved_by', 'category', 'supplier_suggested'
            ).prefetch_related('purchase_orders').get(id=pr_id, organization=self.organization)
        except PurchaseRequisition.DoesNotExist:
            return None

        # Get first linked PO if any
        first_po = pr.purchase_orders.first()

        return {
            'id': pr.id,
            'pr_number': pr.pr_number,
            'requested_by': pr.requested_by.username if pr.requested_by else None,
            'department': pr.department,
            'cost_center': pr.cost_center,
            'category': pr.category.name if pr.category else None,
            'description': pr.description,
            'estimated_amount': float(pr.estimated_amount),
            'currency': pr.currency,
            'budget_code': pr.budget_code,
            'status': pr.status,
            'priority': pr.priority,
            'created_date': pr.created_date.isoformat(),
            'submitted_date': pr.submitted_date.isoformat() if pr.submitted_date else None,
            'approval_date': pr.approval_date.isoformat() if pr.approval_date else None,
            'approved_by': pr.approved_by.username if pr.approved_by else None,
            'rejection_date': pr.rejection_date.isoformat() if pr.rejection_date else None,
            'rejection_reason': pr.rejection_reason,
            'supplier_suggested': {
                'id': pr.supplier_suggested.id,
                'name': pr.supplier_suggested.name
            } if pr.supplier_suggested else None,
            'purchase_order': {
                'id': first_po.id,
                'po_number': first_po.po_number
            } if first_po else None
        }

    def get_po_by_supplier(self, limit=20):
        """Get PO metrics by supplier."""
        pos = PurchaseOrder.objects.filter(organization=self.organization)
        pos = self._apply_date_filters(pos, 'created_date')

        by_supplier = pos.values(
            'supplier__id', 'supplier__name'
        ).annotate(
            po_count=Count('id'),
            total_value=Sum('total_amount'),
            contract_backed=Count(Case(
                When(is_contract_backed=True, then=1),
                output_field=IntegerField()
            )),
            amended=Count(Case(
                When(amendment_count__gt=0, then=1),
                output_field=IntegerField()
            )),
            on_time=Count(Case(
                When(
                    status__in=['fully_received', 'closed'],
                    goods_receipts__received_date__lte=F('required_date'),
                    then=1
                ),
                output_field=IntegerField()
            )),
            received_count=Count(Case(
                When(status__in=['fully_received', 'closed'], then=1),
                output_field=IntegerField()
            ))
        ).order_by('-total_value')[:limit]

        result = []
        for item in by_supplier:
            po_count = item['po_count']
            contract_backed = item['contract_backed']
            received_count = item['received_count']
            on_time = item['on_time']

            # Calculate contract coverage percentage
            contract_coverage = (contract_backed / po_count * 100) if po_count > 0 else 0

            # Determine contract status based on coverage
            if contract_coverage >= 80:
                contract_status = 'on_contract'
            elif contract_coverage >= 50:
                contract_status = 'preferred'
            else:
                contract_status = 'maverick'

            # Calculate on-time rate
            on_time_rate = round(on_time / received_count * 100, 1) if received_count > 0 else 100.0

            result.append({
                'supplier_id': item['supplier__id'],
                'supplier': item['supplier__name'],
                'po_count': po_count,
                'total_value': float(item['total_value'] or 0),
                'contract_status': contract_status,
                'on_contract_pct': round(contract_coverage, 1),  # Added for frontend compatibility
                'on_time_rate': on_time_rate,
                'amendment_rate': round(
                    item['amended'] / po_count * 100, 1
                ) if po_count > 0 else 0
            })

        return result

    def get_po_detail(self, po_id):
        """Get detailed information for a specific PO."""
        try:
            po = PurchaseOrder.objects.select_related(
                'supplier', 'contract', 'created_by', 'approved_by', 'category', 'requisition'
            ).prefetch_related(
                'goods_receipts', 'invoices'
            ).get(id=po_id, organization=self.organization)
        except PurchaseOrder.DoesNotExist:
            return None

        return {
            'id': po.id,
            'po_number': po.po_number,
            'supplier': {
                'id': po.supplier_id,
                'name': po.supplier.name
            } if po.supplier else None,
            'category': po.category.name if po.category else None,
            'total_amount': float(po.total_amount),
            'tax_amount': float(po.tax_amount),
            'freight_amount': float(po.freight_amount),
            'currency': po.currency,
            'status': po.status,
            'is_contract_backed': po.is_contract_backed,
            'contract': {
                'id': po.contract_id,
                'contract_number': po.contract.contract_number if po.contract else None
            } if po.contract else None,
            'created_date': po.created_date.isoformat(),
            'approval_date': po.approval_date.isoformat() if po.approval_date else None,
            'sent_date': po.sent_date.isoformat() if po.sent_date else None,
            'required_date': po.required_date.isoformat() if po.required_date else None,
            'promised_date': po.promised_date.isoformat() if po.promised_date else None,
            'created_by': po.created_by.username if po.created_by else None,
            'approved_by': po.approved_by.username if po.approved_by else None,
            'amendment_count': po.amendment_count,
            'original_amount': float(po.original_amount) if po.original_amount else None,
            'linked_pr': {
                'id': po.requisition.id,
                'pr_number': po.requisition.pr_number
            } if po.requisition else None,
            'goods_receipts': [
                {
                    'id': gr.id,
                    'gr_number': gr.gr_number,
                    'received_date': gr.received_date.isoformat(),
                    'status': gr.status
                }
                for gr in po.goods_receipts.all()[:5]
            ],
            'invoices': [
                {
                    'id': inv.id,
                    'invoice_number': inv.invoice_number,
                    'invoice_date': inv.invoice_date.isoformat(),
                    'amount': float(inv.invoice_amount),
                    'status': inv.status
                }
                for inv in po.invoices.all()[:5]
            ]
        }
