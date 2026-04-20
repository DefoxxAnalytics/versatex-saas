"""
P2P (Procure-to-Pay) Analytics API views

Provides endpoints for P2P cycle analysis, 3-way matching, invoice aging,
purchase requisition/order analytics, and supplier payment performance.
"""
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework import status
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from apps.authentication.utils import log_action
from apps.authentication.permissions import (
    HasP2PAccess,
    CanResolveExceptions,
    CanViewPaymentData,
    CanApprovePO,
    CanApprovePR,
)
from apps.procurement.models import Invoice
from .views import get_target_organization, validate_int_param, parse_filter_params
from .p2p_services import P2PAnalyticsService


# =============================================================================
# Common OpenAPI Parameters
# =============================================================================
ORGANIZATION_ID_PARAM = OpenApiParameter(
    name='organization_id',
    type=OpenApiTypes.INT,
    location=OpenApiParameter.QUERY,
    description='Organization ID (superusers only)',
    required=False,
)

MONTHS_PARAM = OpenApiParameter(
    name='months',
    type=OpenApiTypes.INT,
    location=OpenApiParameter.QUERY,
    description='Number of months to analyze (default: 12, range: 1-36)',
    required=False,
)

LIMIT_PARAM = OpenApiParameter(
    name='limit',
    type=OpenApiTypes.INT,
    location=OpenApiParameter.QUERY,
    description='Maximum number of results to return',
    required=False,
)


class P2PAnalyticsThrottle(ScopedRateThrottle):
    """Throttle for P2P analytics endpoints."""
    scope = 'p2p_analytics'


class P2PWriteThrottle(ScopedRateThrottle):
    """Throttle for P2P write operations (more restrictive)."""
    scope = 'p2p_write'


# =============================================================================
# P2P Cycle Time Analysis Endpoints
# =============================================================================

@extend_schema(
    tags=['P2P Analytics - Cycle Time'],
    summary='Get P2P cycle overview',
    description='''
Get end-to-end P2P cycle time metrics.

Returns average days for each stage:
- **PR to PO**: Average days from requisition creation to PO approval
- **PO to GR**: Average days from PO sent to goods received
- **GR to Invoice**: Average days from receipt to invoice received
- **Invoice to Payment**: Average days from invoice to payment
- **Total Cycle**: End-to-end average cycle time
    ''',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def p2p_cycle_overview(request):
    """
    Get end-to-end P2P cycle time metrics.

    Returns average days for each stage:
    - PR to PO conversion time
    - PO to GR receipt time
    - GR to Invoice time
    - Invoice to Payment time
    - Total P2P cycle time

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_p2p_cycle_overview()

    log_action(
        user=request.user,
        action='view',
        resource='p2p_cycle_overview',
        request=request,
        details={'organization_id': organization.id} if request.user.is_superuser else {}
    )

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Cycle Time'],
    summary='Get P2P cycle times by category',
    description='Returns P2P cycle time metrics broken down by spend category.',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def p2p_cycle_by_category(request):
    """
    Get P2P cycle times broken down by spend category.

    Returns cycle time metrics per category including:
    - Average days for each stage
    - Total transactions processed
    - Category spend totals

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_cycle_time_by_category()

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Cycle Time'],
    summary='Get P2P cycle times by supplier',
    description='Returns P2P cycle time metrics broken down by supplier.',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def p2p_cycle_by_supplier(request):
    """
    Get P2P cycle times broken down by supplier.

    Returns cycle time metrics per supplier including:
    - Average days for each stage
    - Total transactions processed
    - On-time delivery rates

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_cycle_time_by_supplier()

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Cycle Time'],
    summary='Get P2P cycle time trends',
    description='Returns monthly trend of P2P cycle times over the specified period.',
    parameters=[MONTHS_PARAM, ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def p2p_cycle_trends(request):
    """
    Get monthly trend of P2P cycle times.

    Query params:
    - months: Number of months to analyze (default: 12, range: 1-36)
    - organization_id: View data for a specific organization (superusers only)
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    months = validate_int_param(request, 'months', 12, min_val=1, max_val=36)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_cycle_time_trends(months=months)

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Cycle Time'],
    summary='Get P2P process bottlenecks',
    description='Identifies bottlenecks in the P2P process with variance analysis and recommendations.',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def p2p_bottlenecks(request):
    """
    Identify bottlenecks in the P2P process.

    Returns analysis of where delays occur including:
    - Stage-by-stage variance from target
    - Top bottleneck categories
    - Recommendations for improvement

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_bottleneck_analysis()

    log_action(
        user=request.user,
        action='view',
        resource='p2p_bottlenecks',
        request=request,
        details={'organization_id': organization.id} if request.user.is_superuser else {}
    )

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Cycle Time'],
    summary='Get P2P process funnel',
    description='Returns process funnel visualization data showing document flow (PRs → POs → GRs → Paid).',
    parameters=[MONTHS_PARAM, ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def p2p_process_funnel(request):
    """
    Get P2P process funnel visualization data.

    Shows document flow through the P2P process:
    PRs Created → Approved → Converted to PO → Received → Paid

    Query params:
    - months: Number of months to analyze (default: 12)
    - organization_id: View data for a specific organization (superusers only)
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    months = validate_int_param(request, 'months', 12, min_val=1, max_val=36)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_process_funnel(months=months)

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Cycle Time'],
    summary='Get P2P stage drilldown',
    description='Returns detailed breakdown for a specific P2P stage with the top 10 slowest items.',
    parameters=[
        OpenApiParameter(
            name='stage',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='Stage: pr_to_po, po_to_gr, gr_to_invoice, or invoice_to_payment',
            enum=['pr_to_po', 'po_to_gr', 'gr_to_invoice', 'invoice_to_payment'],
        ),
        ORGANIZATION_ID_PARAM,
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def p2p_stage_drilldown(request, stage):
    """
    Get detailed breakdown for a specific P2P stage.

    Args:
        stage: One of 'pr_to_po', 'po_to_gr', 'gr_to_invoice', 'invoice_to_payment'

    Returns top 10 slowest items in the specified stage.

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    valid_stages = ['pr_to_po', 'po_to_gr', 'gr_to_invoice', 'invoice_to_payment']
    if stage not in valid_stages:
        return Response({
            'error': f"Invalid stage: {stage}. Must be one of: {', '.join(valid_stages)}"
        }, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_stage_drilldown(stage)

    return Response(data)


# =============================================================================
# 3-Way Matching Analysis Endpoints
# =============================================================================

@extend_schema(
    tags=['P2P Analytics - 3-Way Matching'],
    summary='Get matching overview',
    description='''
Get 3-way match rates and exception metrics.

Returns:
- Total invoices processed
- 3-way matched percentage
- 2-way matched percentage
- Exception rate and amount
- Average resolution time
    ''',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def matching_overview(request):
    """
    Get 3-way match rates and exception metrics.

    Returns:
    - Total invoices processed
    - 3-way matched percentage
    - 2-way matched percentage
    - Exception rate and amount
    - Average resolution time

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_matching_overview()

    log_action(
        user=request.user,
        action='view',
        resource='matching_overview',
        request=request,
        details={'organization_id': organization.id} if request.user.is_superuser else {}
    )

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - 3-Way Matching'],
    summary='Get invoice exceptions',
    description='Returns list of invoice exceptions with filtering options.',
    parameters=[
        OpenApiParameter(
            name='status',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter by status (default: open)',
            enum=['open', 'resolved', 'all'],
            required=False,
        ),
        OpenApiParameter(
            name='exception_type',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter by exception type',
            enum=['price_variance', 'quantity_variance', 'no_po', 'duplicate', 'missing_gr', 'other'],
            required=False,
        ),
        OpenApiParameter(
            name='limit',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Maximum results (default: 100, max: 500)',
            required=False,
        ),
        ORGANIZATION_ID_PARAM,
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def matching_exceptions(request):
    """
    Get list of invoice exceptions with filtering.

    Query params:
    - status: Filter by status (open/resolved) - default: open
    - exception_type: Filter by type (price_variance/quantity_variance/no_po/duplicate/missing_gr)
    - limit: Maximum results (default: 100, max: 500)
    - organization_id: View data for a specific organization (superusers only)
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    # Parse filters
    status_filter = request.query_params.get('status', 'open')
    if status_filter not in ['open', 'resolved', 'all']:
        status_filter = 'open'

    exception_type = request.query_params.get('exception_type')
    valid_types = ['price_variance', 'quantity_variance', 'no_po', 'duplicate', 'missing_gr', 'other']
    if exception_type and exception_type not in valid_types:
        exception_type = None

    limit = validate_int_param(request, 'limit', 100, min_val=1, max_val=500)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_matching_exceptions(
        status=status_filter,
        exception_type=exception_type,
        limit=limit
    )

    return Response({
        'exceptions': data,
        'count': len(data),
        'filters': {
            'status': status_filter,
            'exception_type': exception_type
        }
    })


@extend_schema(
    tags=['P2P Analytics - 3-Way Matching'],
    summary='Get exceptions by type',
    description='Returns breakdown of exceptions by type with count and amount.',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def exceptions_by_type(request):
    """
    Get breakdown of exceptions by type.

    Returns count and amount for each exception type:
    - Price variance
    - Quantity variance
    - No PO
    - Duplicate
    - Missing GR

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_exceptions_by_type()

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - 3-Way Matching'],
    summary='Get exceptions by supplier',
    description='Returns suppliers ranked by exception rate with detailed metrics.',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def exceptions_by_supplier(request):
    """
    Get suppliers ranked by exception rate.

    Returns suppliers with:
    - Total invoice count
    - Exception count and rate
    - Exception amount
    - Primary exception types

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_exceptions_by_supplier()

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - 3-Way Matching'],
    summary='Get price variance analysis',
    description='Analyzes PO price vs Invoice price variances with trends.',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def price_variance_analysis(request):
    """
    Analyze PO price vs Invoice price variances.

    Returns:
    - Invoices with price differences
    - Variance amounts and percentages
    - Trends over time

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_price_variance_analysis()

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - 3-Way Matching'],
    summary='Get quantity variance analysis',
    description='Analyzes PO qty vs GR qty vs Invoice qty variances with supplier metrics.',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def quantity_variance_analysis(request):
    """
    Analyze PO qty vs GR qty vs Invoice qty variances.

    Returns:
    - Orders with quantity mismatches
    - Over/under shipment analysis
    - Supplier performance metrics

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_quantity_variance_analysis()

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - 3-Way Matching'],
    summary='Get invoice match detail',
    description='Returns detailed match information for a specific invoice.',
    parameters=[
        OpenApiParameter(
            name='invoice_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='Invoice ID',
        ),
        ORGANIZATION_ID_PARAM,
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def invoice_match_detail(request, invoice_id):
    """
    Get detailed match information for a specific invoice.

    Returns:
    - Invoice details
    - Linked PO and GR details
    - Variance breakdown
    - Exception history

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_invoice_match_detail(invoice_id)

    if data is None:
        return Response({'error': 'Invoice not found'}, status=404)

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - 3-Way Matching'],
    summary='Resolve invoice exception',
    description='Resolves an invoice exception. Only managers and admins can resolve exceptions.',
    parameters=[
        OpenApiParameter(
            name='invoice_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='Invoice ID',
        ),
        ORGANIZATION_ID_PARAM,
    ],
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'resolution_notes': {
                    'type': 'string',
                    'description': 'Notes explaining the resolution (required, max 2000 chars)',
                },
            },
            'required': ['resolution_notes'],
        }
    },
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, CanResolveExceptions])
@throttle_classes([P2PWriteThrottle])
def resolve_exception(request, invoice_id):
    """
    Resolve an invoice exception.

    Request body:
    - resolution_notes: Notes explaining the resolution (required)

    Only managers and admins can resolve exceptions.

    Query params (superusers only):
    - organization_id: Resolve exception for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    resolution_notes = request.data.get('resolution_notes', '')
    if not resolution_notes or not resolution_notes.strip():
        return Response({'error': 'resolution_notes is required'}, status=400)

    # Validate resolution_notes length
    if len(resolution_notes) > 2000:
        return Response({'error': 'resolution_notes must be 2000 characters or less'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.resolve_exception(
        invoice_id=invoice_id,
        user=request.user,
        resolution_notes=resolution_notes.strip()
    )

    if data is None:
        return Response({'error': 'Invoice not found or no exception to resolve'}, status=404)

    log_action(
        user=request.user,
        action='resolve',
        resource='invoice_exception',
        resource_id=invoice_id,
        request=request,
        details={
            'resolution_notes': resolution_notes[:200],  # Truncate for log
            'organization_id': organization.id
        } if request.user.is_superuser else {'resolution_notes': resolution_notes[:200]}
    )

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - 3-Way Matching'],
    summary='Bulk resolve exceptions',
    description='Resolves multiple invoice exceptions at once. Only managers and admins can resolve exceptions.',
    parameters=[ORGANIZATION_ID_PARAM],
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'invoice_ids': {
                    'type': 'array',
                    'items': {'type': 'integer'},
                    'description': 'List of invoice IDs to resolve (max 50)',
                },
                'resolution_notes': {
                    'type': 'string',
                    'description': 'Notes explaining the resolution (required, max 2000 chars)',
                },
            },
            'required': ['invoice_ids', 'resolution_notes'],
        }
    },
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, CanResolveExceptions])
@throttle_classes([P2PWriteThrottle])
def bulk_resolve_exceptions(request):
    """
    Resolve multiple invoice exceptions at once.

    Request body:
    - invoice_ids: List of invoice IDs to resolve (required, max 50)
    - resolution_notes: Notes explaining the resolution (required)

    Only managers and admins can resolve exceptions.

    Query params (superusers only):
    - organization_id: Resolve exceptions for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    invoice_ids = request.data.get('invoice_ids', [])
    resolution_notes = request.data.get('resolution_notes', '')

    # Validate inputs
    if not invoice_ids:
        return Response({'error': 'invoice_ids is required'}, status=400)

    if not isinstance(invoice_ids, list):
        return Response({'error': 'invoice_ids must be a list'}, status=400)

    if len(invoice_ids) > 50:
        return Response({'error': 'Maximum 50 invoices can be resolved at once'}, status=400)

    if not resolution_notes or not resolution_notes.strip():
        return Response({'error': 'resolution_notes is required'}, status=400)

    if len(resolution_notes) > 2000:
        return Response({'error': 'resolution_notes must be 2000 characters or less'}, status=400)

    # Validate all IDs are integers
    try:
        invoice_ids = [int(id) for id in invoice_ids]
    except (ValueError, TypeError):
        return Response({'error': 'All invoice_ids must be integers'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.bulk_resolve_exceptions(
        invoice_ids=invoice_ids,
        user=request.user,
        resolution_notes=resolution_notes.strip()
    )

    log_action(
        user=request.user,
        action='bulk_resolve',
        resource='invoice_exceptions',
        request=request,
        details={
            'invoice_count': len(invoice_ids),
            'resolved_count': data.get('resolved_count', 0),
            'organization_id': organization.id
        } if request.user.is_superuser else {
            'invoice_count': len(invoice_ids),
            'resolved_count': data.get('resolved_count', 0)
        }
    )

    return Response(data)


# =============================================================================
# Invoice Aging / AP Analysis Endpoints
# =============================================================================

@extend_schema(
    tags=['P2P Analytics - Invoice Aging'],
    summary='Get invoice aging overview',
    description='''
Get invoice aging overview with bucket totals.

Aging buckets:
- **Current (0-30 days)**: Not yet due
- **31-60 days**: Coming due soon
- **61-90 days**: Overdue
- **90+ days**: Significantly overdue

Plus total AP, overdue amount, and DPO.
    ''',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def aging_overview(request):
    """
    Get invoice aging overview with bucket totals.

    Returns aging buckets:
    - Current (0-30 days)
    - 31-60 days
    - 61-90 days
    - 90+ days

    Plus total AP, overdue amount, and DPO.

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_aging_overview()

    log_action(
        user=request.user,
        action='view',
        resource='aging_overview',
        request=request,
        details={'organization_id': organization.id} if request.user.is_superuser else {}
    )

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Invoice Aging'],
    summary='Get aging by supplier',
    description='Returns invoice aging breakdown by supplier with AP balances and payment metrics.',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def aging_by_supplier(request):
    """
    Get aging breakdown by supplier.

    Returns suppliers with:
    - Total AP balance
    - Aging bucket distribution
    - Average days outstanding
    - On-time payment percentage

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_aging_by_supplier()

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Invoice Aging'],
    summary='Get payment terms compliance',
    description='Analyzes payment terms compliance. **Manager/Admin access required.**',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess, CanViewPaymentData])
@throttle_classes([P2PAnalyticsThrottle])
def payment_terms_compliance(request):
    """
    Get payment terms compliance analysis.

    Returns:
    - On-time vs late payment rates
    - Early payment discount capture rate
    - Payment terms distribution
    - Compliance by supplier

    Only managers and admins can view payment data.

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_payment_terms_compliance()

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Invoice Aging'],
    summary='Get DPO trends',
    description='Returns Days Payable Outstanding trends over time.',
    parameters=[MONTHS_PARAM, ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def dpo_trends(request):
    """
    Get Days Payable Outstanding trends.

    Query params:
    - months: Number of months to analyze (default: 12, range: 1-36)
    - organization_id: View data for a specific organization (superusers only)
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    months = validate_int_param(request, 'months', 12, min_val=1, max_val=36)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_dpo_trends(months=months)

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Invoice Aging'],
    summary='Get cash flow forecast',
    description='Returns projected payments by week/month. **Manager/Admin access required.**',
    parameters=[
        OpenApiParameter(
            name='weeks',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Number of weeks to forecast (default: 4, range: 1-12)',
            required=False,
        ),
        ORGANIZATION_ID_PARAM,
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess, CanViewPaymentData])
@throttle_classes([P2PAnalyticsThrottle])
def cash_flow_forecast(request):
    """
    Get projected payments by week/month.

    Only managers and admins can view cash flow data.

    Query params:
    - weeks: Number of weeks to forecast (default: 4, range: 1-12)
    - organization_id: View data for a specific organization (superusers only)
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    weeks = validate_int_param(request, 'weeks', 4, min_val=1, max_val=12)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_cash_flow_forecast(weeks=weeks)

    log_action(
        user=request.user,
        action='view',
        resource='cash_flow_forecast',
        request=request,
        details={
            'weeks': weeks,
            'organization_id': organization.id
        } if request.user.is_superuser else {'weeks': weeks}
    )

    return Response(data)


# =============================================================================
# Purchase Requisition Analysis Endpoints
# =============================================================================

@extend_schema(
    tags=['P2P Analytics - Requisitions'],
    summary='Get PR overview',
    description='''
Get Purchase Requisition overview metrics.

Returns:
- Total PRs count
- Conversion rate (PR to PO)
- Average approval time
- Rejection rate
    ''',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def pr_overview(request):
    """
    Get Purchase Requisition overview metrics.

    Returns:
    - Total PRs
    - Conversion rate (PR to PO)
    - Average approval time
    - Rejection rate

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_pr_overview()

    log_action(
        user=request.user,
        action='view',
        resource='pr_overview',
        request=request,
        details={'organization_id': organization.id} if request.user.is_superuser else {}
    )

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Requisitions'],
    summary='Get PR approval analysis',
    description='Analyzes PR approval bottlenecks and patterns.',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def pr_approval_analysis(request):
    """
    Analyze PR approval bottlenecks and patterns.

    Returns:
    - Average approval time
    - Approval time distribution
    - Top approvers and their metrics
    - Bottleneck identification

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_pr_approval_analysis()

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Requisitions'],
    summary='Get PRs by department',
    description='Returns requisition patterns grouped by department.',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def pr_by_department(request):
    """
    Get requisition patterns by department.

    Returns departments with:
    - PR count and total value
    - Approval rate
    - Average processing time

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_pr_by_department()

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Requisitions'],
    summary='Get pending PRs',
    description='Returns PRs pending approval sorted by age.',
    parameters=[LIMIT_PARAM, ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def pr_pending(request):
    """
    Get pending PR approvals (aged items).

    Returns PRs pending approval sorted by age.

    Query params:
    - limit: Maximum results (default: 50, max: 200)
    - organization_id: View data for a specific organization (superusers only)
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    limit = validate_int_param(request, 'limit', 50, min_val=1, max_val=200)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_pr_pending(limit=limit)

    return Response({
        'pending_prs': data,
        'count': len(data)
    })


@extend_schema(
    tags=['P2P Analytics - Requisitions'],
    summary='Get PR detail',
    description='Returns detailed information for a specific purchase requisition.',
    parameters=[
        OpenApiParameter(
            name='pr_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='Purchase Requisition ID',
        ),
        ORGANIZATION_ID_PARAM,
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def pr_detail(request, pr_id):
    """
    Get detailed information for a specific PR.

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_pr_detail(pr_id)

    if data is None:
        return Response({'error': 'Purchase Requisition not found'}, status=404)

    return Response(data)


# =============================================================================
# Purchase Order Analysis Endpoints
# =============================================================================

@extend_schema(
    tags=['P2P Analytics - Purchase Orders'],
    summary='Get PO overview',
    description='''
Get Purchase Order overview metrics.

Returns:
- Total POs count and value
- Contract coverage percentage
- Amendment rate
- Average PO value
    ''',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def po_overview(request):
    """
    Get Purchase Order overview metrics.

    Returns:
    - Total POs and value
    - Contract coverage percentage
    - Amendment rate
    - Average PO value

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_po_overview()

    log_action(
        user=request.user,
        action='view',
        resource='po_overview',
        request=request,
        details={'organization_id': organization.id} if request.user.is_superuser else {}
    )

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Purchase Orders'],
    summary='Get PO leakage analysis',
    description='Identifies off-contract PO spending (maverick spend) with consolidation recommendations.',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def po_leakage(request):
    """
    Identify off-contract PO spending (leakage).

    Returns:
    - Maverick PO summary
    - Leakage by category
    - Top maverick suppliers
    - Consolidation recommendations

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_po_leakage()

    log_action(
        user=request.user,
        action='view',
        resource='po_leakage',
        request=request,
        details={'organization_id': organization.id} if request.user.is_superuser else {}
    )

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Purchase Orders'],
    summary='Get PO amendments analysis',
    description='Analyzes PO amendment/change order patterns.',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def po_amendments(request):
    """
    Analyze PO amendment/change order patterns.

    Returns:
    - Amendment rate
    - Average value change percentage
    - Top reasons for amendments
    - Suppliers with high amendment rates

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_po_amendment_analysis()

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Purchase Orders'],
    summary='Get POs by supplier',
    description='Returns PO metrics grouped by supplier.',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def po_by_supplier(request):
    """
    Get PO metrics by supplier.

    Returns suppliers with:
    - PO count and value
    - Contract status
    - On-time delivery rate
    - Amendment rate

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_po_by_supplier()

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Purchase Orders'],
    summary='Get PO detail',
    description='Returns detailed information for a specific purchase order.',
    parameters=[
        OpenApiParameter(
            name='po_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='Purchase Order ID',
        ),
        ORGANIZATION_ID_PARAM,
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess])
@throttle_classes([P2PAnalyticsThrottle])
def po_detail(request, po_id):
    """
    Get detailed information for a specific PO.

    Returns:
    - PO details
    - Line items
    - Linked PRs, GRs, and Invoices
    - Amendment history

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_po_detail(po_id)

    if data is None:
        return Response({'error': 'Purchase Order not found'}, status=404)

    return Response(data)


# =============================================================================
# Supplier Payment Performance Endpoints
# =============================================================================

@extend_schema(
    tags=['P2P Analytics - Supplier Payments'],
    summary='Get supplier payments overview',
    description='''
Get supplier payment performance overview. **Admin access required.**

Returns:
- Total suppliers with AP
- Overall on-time payment rate
- Average DPO by supplier
- Exception rate overview
    ''',
    parameters=[ORGANIZATION_ID_PARAM],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess, CanViewPaymentData])
@throttle_classes([P2PAnalyticsThrottle])
def supplier_payments_overview(request):
    """
    Get supplier payment performance overview.

    Only managers and admins can view payment data.

    Returns:
    - Total suppliers with AP
    - Overall on-time payment rate
    - Average DPO by supplier
    - Exception rate overview

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_supplier_payments_overview()

    log_action(
        user=request.user,
        action='view',
        resource='supplier_payments_overview',
        request=request,
        details={'organization_id': organization.id} if request.user.is_superuser else {}
    )

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Supplier Payments'],
    summary='Get supplier payments scorecard',
    description='Returns suppliers ranked by payment performance score. **Admin access required.**',
    parameters=[
        OpenApiParameter(
            name='limit',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Maximum results (default: 50, max: 200)',
            required=False,
        ),
        ORGANIZATION_ID_PARAM,
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess, CanViewPaymentData])
@throttle_classes([P2PAnalyticsThrottle])
def supplier_payments_scorecard(request):
    """
    Get supplier payment scorecard with rankings.

    Only managers and admins can view payment data.

    Returns suppliers ranked by payment performance score including:
    - AP balance
    - DPO
    - On-time payment percentage
    - Exception rate
    - Overall score (0-100)

    Query params:
    - limit: Maximum results (default: 50, max: 200)
    - organization_id: View data for a specific organization (superusers only)
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    limit = validate_int_param(request, 'limit', 50, min_val=1, max_val=200)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_supplier_payments_scorecard(limit=limit)

    return Response({
        'suppliers': data,
        'count': len(data)
    })


@extend_schema(
    tags=['P2P Analytics - Supplier Payments'],
    summary='Get supplier payment detail',
    description='Returns detailed payment information for a specific supplier. **Admin access required.**',
    parameters=[
        OpenApiParameter(
            name='supplier_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='Supplier ID',
        ),
        ORGANIZATION_ID_PARAM,
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess, CanViewPaymentData])
@throttle_classes([P2PAnalyticsThrottle])
def supplier_payment_detail(request, supplier_id):
    """
    Get detailed payment information for a specific supplier.

    Only managers and admins can view payment data.

    Returns:
    - Basic supplier info
    - Payment metrics (DPO, on-time rate)
    - Exception breakdown
    - Aging buckets

    Query params (superusers only):
    - organization_id: View data for a specific organization
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_supplier_payment_detail(supplier_id)

    if data is None:
        return Response({'error': 'Supplier not found'}, status=404)

    return Response(data)


@extend_schema(
    tags=['P2P Analytics - Supplier Payments'],
    summary='Get supplier payment history',
    description='Returns payment history for a specific supplier. **Admin access required.**',
    parameters=[
        OpenApiParameter(
            name='supplier_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='Supplier ID',
        ),
        MONTHS_PARAM,
        ORGANIZATION_ID_PARAM,
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasP2PAccess, CanViewPaymentData])
@throttle_classes([P2PAnalyticsThrottle])
def supplier_payment_history(request, supplier_id):
    """
    Get payment history for a specific supplier.

    Only managers and admins can view payment data.

    Returns:
    - Monthly payment trend
    - Recent invoices with payment status
    - Exception history

    Query params:
    - months: Number of months of history (default: 12, max: 36)
    - organization_id: View data for a specific organization (superusers only)
    """
    organization = get_target_organization(request)
    if organization is None:
        return Response({'error': 'User profile not found'}, status=400)

    months = validate_int_param(request, 'months', 12, min_val=1, max_val=36)

    filters = parse_filter_params(request)
    service = P2PAnalyticsService(organization, filters=filters)
    data = service.get_supplier_payment_history(supplier_id, months=months)

    if data is None:
        return Response({'error': 'Supplier not found'}, status=404)

    return Response(data)
