"""
URL patterns for P2P (Procure-to-Pay) Analytics
"""
from django.urls import path
from . import p2p_views

urlpatterns = [
    # P2P Cycle Time Analysis
    path('p2p/cycle-overview/', p2p_views.p2p_cycle_overview, name='p2p-cycle-overview'),
    path('p2p/cycle-by-category/', p2p_views.p2p_cycle_by_category, name='p2p-cycle-by-category'),
    path('p2p/cycle-by-supplier/', p2p_views.p2p_cycle_by_supplier, name='p2p-cycle-by-supplier'),
    path('p2p/cycle-trends/', p2p_views.p2p_cycle_trends, name='p2p-cycle-trends'),
    path('p2p/bottlenecks/', p2p_views.p2p_bottlenecks, name='p2p-bottlenecks'),
    path('p2p/process-funnel/', p2p_views.p2p_process_funnel, name='p2p-process-funnel'),
    path('p2p/stage-drilldown/<str:stage>/', p2p_views.p2p_stage_drilldown, name='p2p-stage-drilldown'),

    # 3-Way Matching
    path('matching/overview/', p2p_views.matching_overview, name='matching-overview'),
    path('matching/exceptions/', p2p_views.matching_exceptions, name='matching-exceptions'),
    path('matching/exceptions-by-type/', p2p_views.exceptions_by_type, name='exceptions-by-type'),
    path('matching/exceptions-by-supplier/', p2p_views.exceptions_by_supplier, name='exceptions-by-supplier'),
    path('matching/price-variance/', p2p_views.price_variance_analysis, name='price-variance'),
    path('matching/quantity-variance/', p2p_views.quantity_variance_analysis, name='quantity-variance'),
    path('matching/invoice/<int:invoice_id>/', p2p_views.invoice_match_detail, name='invoice-match-detail'),
    path('matching/invoice/<int:invoice_id>/resolve/', p2p_views.resolve_exception, name='resolve-exception'),
    path('matching/exceptions/bulk-resolve/', p2p_views.bulk_resolve_exceptions, name='bulk-resolve-exceptions'),

    # Invoice Aging / AP Analysis
    path('aging/overview/', p2p_views.aging_overview, name='aging-overview'),
    path('aging/by-supplier/', p2p_views.aging_by_supplier, name='aging-by-supplier'),
    path('aging/payment-terms-compliance/', p2p_views.payment_terms_compliance, name='payment-terms-compliance'),
    path('aging/dpo-trends/', p2p_views.dpo_trends, name='dpo-trends'),
    path('aging/cash-forecast/', p2p_views.cash_flow_forecast, name='cash-forecast'),

    # Purchase Requisitions
    path('requisitions/overview/', p2p_views.pr_overview, name='pr-overview'),
    path('requisitions/approval-analysis/', p2p_views.pr_approval_analysis, name='pr-approval-analysis'),
    path('requisitions/by-department/', p2p_views.pr_by_department, name='pr-by-department'),
    path('requisitions/pending/', p2p_views.pr_pending, name='pr-pending'),
    path('requisitions/<int:pr_id>/', p2p_views.pr_detail, name='pr-detail'),

    # Purchase Orders
    path('purchase-orders/overview/', p2p_views.po_overview, name='po-overview'),
    path('purchase-orders/leakage/', p2p_views.po_leakage, name='po-leakage'),
    path('purchase-orders/amendments/', p2p_views.po_amendments, name='po-amendments'),
    path('purchase-orders/by-supplier/', p2p_views.po_by_supplier, name='po-by-supplier'),
    path('purchase-orders/<int:po_id>/', p2p_views.po_detail, name='po-detail'),

    # Supplier Payments
    path('supplier-payments/overview/', p2p_views.supplier_payments_overview, name='supplier-payments-overview'),
    path('supplier-payments/scorecard/', p2p_views.supplier_payments_scorecard, name='supplier-payments-scorecard'),
    path('supplier-payments/<int:supplier_id>/', p2p_views.supplier_payment_detail, name='supplier-payment-detail'),
    path('supplier-payments/<int:supplier_id>/history/', p2p_views.supplier_payment_history, name='supplier-payment-history'),
]
