"""
Report API views.
Provides endpoints for report generation, retrieval, download, and scheduling.
"""
import logging
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework import status

from apps.authentication.utils import log_action
from apps.authentication.models import Organization
from apps.authentication.organization_utils import (
    get_target_organization as get_user_organization
)
from .models import Report
from .serializers import (
    ReportListSerializer,
    ReportDetailSerializer,
    ReportGenerateSerializer,
    ReportScheduleSerializer,
    ReportShareSerializer,
    ReportTemplateSerializer,
    ReportStatusSerializer,
)
from .services import ReportingService

logger = logging.getLogger(__name__)
User = get_user_model()


# Report templates (predefined configurations)
REPORT_TEMPLATES = [
    {
        'id': 'executive_summary',
        'name': 'Executive Summary',
        'description': 'High-level KPIs, trends, and strategic insights for leadership',
        'report_type': 'executive_summary',
        'icon': 'file-text',
        'default_parameters': {},
    },
    {
        'id': 'spend_analysis',
        'name': 'Spend Analysis',
        'description': 'Detailed breakdown by category, supplier, and time period',
        'report_type': 'spend_analysis',
        'icon': 'pie-chart',
        'default_parameters': {'include_monthly_trend': True},
    },
    {
        'id': 'supplier_performance',
        'name': 'Supplier Performance',
        'description': 'Top suppliers, concentration analysis, and risk assessment',
        'report_type': 'supplier_performance',
        'icon': 'users',
        'default_parameters': {'top_n': 20},
    },
    {
        'id': 'pareto_analysis',
        'name': 'Pareto Analysis',
        'description': '80/20 analysis with strategic supplier classifications',
        'report_type': 'pareto_analysis',
        'icon': 'bar-chart-2',
        'default_parameters': {'threshold': 80},
    },
    {
        'id': 'contract_compliance',
        'name': 'Compliance Report',
        'description': 'Maverick spend analysis and policy violation summary',
        'report_type': 'contract_compliance',
        'icon': 'shield',
        'default_parameters': {},
    },
    {
        'id': 'savings_opportunities',
        'name': 'Savings Opportunities',
        'description': 'Consolidation opportunities and estimated savings potential',
        'report_type': 'savings_opportunities',
        'icon': 'trending-down',
        'default_parameters': {},
    },
    {
        'id': 'stratification',
        'name': 'Spend Stratification',
        'description': 'Kraljic matrix analysis with strategic, leverage, routine, and tactical segments',
        'report_type': 'stratification',
        'icon': 'layers',
        'default_parameters': {},
    },
    {
        'id': 'seasonality',
        'name': 'Seasonality & Trends',
        'description': 'Monthly spending patterns with fiscal year support and savings opportunities',
        'report_type': 'seasonality',
        'icon': 'calendar-days',
        'default_parameters': {'use_fiscal_year': True},
    },
    {
        'id': 'year_over_year',
        'name': 'Year-over-Year Analysis',
        'description': 'Year-over-year comparison with top gainers, decliners, and variance analysis',
        'report_type': 'year_over_year',
        'icon': 'trending-up',
        'default_parameters': {'use_fiscal_year': True},
    },
    {
        'id': 'tail_spend',
        'name': 'Tail Spend Analysis',
        'description': 'Tail vendor analysis with consolidation opportunities and action plans',
        'report_type': 'tail_spend',
        'icon': 'scissors',
        'default_parameters': {'threshold': 50000},
    },
    # P2P Report Templates
    {
        'id': 'p2p_pr_status',
        'name': 'PR Status Report',
        'description': 'Purchase requisition workflow analysis with approval metrics and department breakdown',
        'report_type': 'p2p_pr_status',
        'icon': 'file-check',
        'default_parameters': {},
    },
    {
        'id': 'p2p_po_compliance',
        'name': 'PO Compliance Report',
        'description': 'Contract coverage, maverick spend analysis, and PO compliance metrics',
        'report_type': 'p2p_po_compliance',
        'icon': 'shield-check',
        'default_parameters': {},
    },
    {
        'id': 'p2p_ap_aging',
        'name': 'AP Aging Report',
        'description': 'Accounts payable aging buckets, DPO trends, and payment performance',
        'report_type': 'p2p_ap_aging',
        'icon': 'clock',
        'default_parameters': {},
    },
]


class ReportGenerateThrottle(ScopedRateThrottle):
    """Throttle for report generation (expensive operation)."""
    scope = 'report_generate'


class ReportDownloadThrottle(ScopedRateThrottle):
    """Throttle for report downloads."""
    scope = 'report_download'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_templates(request):
    """
    List available report templates.

    Returns predefined report configurations that users can generate.
    """
    serializer = ReportTemplateSerializer(REPORT_TEMPLATES, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_template_detail(request, template_id):
    """
    Get details of a specific report template.
    """
    template = next((t for t in REPORT_TEMPLATES if t['id'] == template_id), None)
    if not template:
        return Response(
            {'error': 'Template not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    serializer = ReportTemplateSerializer(template)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ReportGenerateThrottle])
def generate_report(request):
    """
    Generate a new report.

    Request body:
    - report_type: Type of report (required)
    - report_format: Output format (pdf, xlsx, csv) - default: pdf
    - name: Report name (optional, auto-generated if not provided)
    - description: Report description (optional)
    - period_start: Start date for data (optional)
    - period_end: End date for data (optional)
    - filters: Additional filters as JSON (optional)
    - parameters: Report-specific parameters as JSON (optional)
    - async_generation: Whether to generate asynchronously (default: false)
    """
    organization = get_user_organization(request)
    if organization is None:
        return Response(
            {'error': 'User profile not found'},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = ReportGenerateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    async_generation = data.pop('async_generation', False)

    # Create report service
    service = ReportingService(organization, request.user)

    try:
        if async_generation:
            # Create report record and queue for async generation
            report = service.create_report(
                report_type=data['report_type'],
                report_format=data.get('report_format', 'pdf'),
                name=data.get('name'),
                description=data.get('description', ''),
                period_start=data.get('period_start'),
                period_end=data.get('period_end'),
                filters=data.get('filters', {}),
                parameters=data.get('parameters', {}),
            )
            # Queue async task
            from .tasks import generate_report_async
            generate_report_async.delay(str(report.id))

            log_action(
                user=request.user,
                action='create',
                resource='report',
                resource_id=str(report.id),
                request=request,
                details={'report_type': data['report_type'], 'async': True}
            )

            return Response(
                {
                    'id': str(report.id),
                    'status': report.status,
                    'message': 'Report generation started'
                },
                status=status.HTTP_202_ACCEPTED
            )
        else:
            # Generate synchronously
            report = service.generate_report(
                report_type=data['report_type'],
                report_format=data.get('report_format', 'pdf'),
                name=data.get('name'),
                description=data.get('description', ''),
                period_start=data.get('period_start'),
                period_end=data.get('period_end'),
                filters=data.get('filters', {}),
                parameters=data.get('parameters', {}),
            )

            log_action(
                user=request.user,
                action='create',
                resource='report',
                resource_id=str(report.id),
                request=request,
                details={'report_type': data['report_type'], 'async': False}
            )

            return Response(
                ReportDetailSerializer(report).data,
                status=status.HTTP_201_CREATED
            )

    except Exception as e:
        logger.exception(f"Error generating report: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_preview(request):
    """
    Generate a lightweight preview of report data without creating a Report record.

    Returns JSON summary data for client-side preview rendering.
    The preview is limited to first 5-10 items per section for performance.

    Request body (same as generate_report):
    - report_type: Type of report (required)
    - period_start: Start date for data (optional)
    - period_end: End date for data (optional)
    - filters: Additional filters as JSON (optional)
    - parameters: Report-specific parameters as JSON (optional)
    """
    organization = get_user_organization(request)
    if organization is None:
        return Response(
            {'error': 'User profile not found'},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = ReportGenerateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Create report service
    service = ReportingService(organization, request.user)

    try:
        # Generate preview data (using the same generation logic)
        preview_data = service._generate_data(
            report_type=data['report_type'],
            period_start=data.get('period_start'),
            period_end=data.get('period_end'),
            filters=data.get('filters', {}),
            parameters=data.get('parameters', {}),
        )

        # Truncate lists to max 5 items for preview
        def truncate_lists(obj, max_items=5):
            if isinstance(obj, dict):
                return {k: truncate_lists(v, max_items) for k, v in obj.items()}
            elif isinstance(obj, list):
                return obj[:max_items]
            return obj

        preview_data = truncate_lists(preview_data)

        # Add preview metadata
        preview_data['_preview'] = True
        preview_data['_truncated'] = True

        return Response(preview_data)

    except Exception as e:
        logger.exception(f"Error generating preview: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_list(request):
    """
    List reports for the current user/organization.

    Query params:
    - status: Filter by status (draft, generating, completed, failed, scheduled)
    - report_type: Filter by report type
    - limit: Number of results (default: 50, max: 100)
    - offset: Pagination offset
    """
    organization = get_user_organization(request)
    if organization is None:
        return Response(
            {'error': 'User profile not found'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Build queryset
    queryset = Report.objects.filter(organization=organization)

    # Apply filters
    status_filter = request.query_params.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    report_type = request.query_params.get('report_type')
    if report_type:
        queryset = queryset.filter(report_type=report_type)

    # Pagination
    try:
        limit = min(int(request.query_params.get('limit', 50)), 100)
        offset = int(request.query_params.get('offset', 0))
    except ValueError:
        limit, offset = 50, 0

    # Get total count before slicing
    total = queryset.count()

    # Order and slice
    reports = queryset.order_by('-created_at')[offset:offset + limit]

    serializer = ReportListSerializer(reports, many=True)
    return Response({
        'results': serializer.data,
        'total': total,
        'limit': limit,
        'offset': offset
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_detail(request, report_id):
    """
    Get details of a specific report.

    Note: Uses report's own organization rather than current context,
    allowing access to reports from any organization user has access to.
    """
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return Response(
            {'error': 'Report not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check access - user must have access to the report's organization
    if not report.can_access(request.user):
        return Response(
            {'error': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = ReportDetailSerializer(report)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_status(request, report_id):
    """
    Get the generation status of a report.
    Used for polling during async generation.

    Note: Uses report's own organization rather than current context.
    """
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return Response(
            {'error': 'Report not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check access
    if not report.can_access(request.user):
        return Response(
            {'error': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = ReportStatusSerializer(report)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def report_delete(request, report_id):
    """
    Delete a report.

    Note: Uses report's own organization rather than current context.
    """
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return Response(
            {'error': 'Report not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check basic access first
    if not report.can_access(request.user):
        return Response(
            {'error': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Only creator or admin can delete
    if report.created_by != request.user and not request.user.is_superuser:
        if not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

    report_name = report.name
    report.delete()

    log_action(
        user=request.user,
        action='delete',
        resource='report',
        resource_id=str(report_id),
        request=request,
        details={'name': report_name}
    )

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([ReportDownloadThrottle])
def report_download(request, report_id):
    """
    Download a generated report file.

    Query params:
    - format: Override output format (pdf, xlsx, csv)

    Note: Unlike list endpoints, download uses the report's own organization
    rather than the current organization context. This allows downloading
    reports created in any organization the user has access to.
    """
    # Get the report first (without org filter)
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return Response(
            {'error': 'Report not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check access - user must have access to the report's organization
    if not report.can_access(request.user):
        logger.warning(f"Download access denied for report {report_id} to user {request.user.id}")
        return Response(
            {'error': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Check if report is completed
    if report.status != 'completed':
        return Response(
            {'error': f'Report is not ready. Status: {report.status}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get export format (allow override)
    # NOTE: Use 'output_format' not 'format' to avoid conflict with DRF content negotiation
    export_format = request.query_params.get('output_format', report.report_format)
    if export_format not in ['pdf', 'xlsx', 'csv']:
        export_format = report.report_format

    # Generate file from summary_data using report's organization
    service = ReportingService(report.organization, request.user)

    try:
        file_buffer, content_type, filename = service.render_report(
            report,
            export_format
        )

        log_action(
            user=request.user,
            action='download',
            resource='report',
            resource_id=str(report_id),
            request=request,
            details={'format': export_format}
        )

        response = HttpResponse(
            file_buffer.getvalue(),
            content_type=content_type
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        logger.exception(f"Error downloading report: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def report_schedules(request):
    """
    List or create scheduled reports.

    GET: List all scheduled reports
    POST: Create a new scheduled report
    """
    organization = get_user_organization(request)
    if organization is None:
        return Response(
            {'error': 'User profile not found'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if request.method == 'GET':
        schedules = Report.objects.filter(
            organization=organization,
            is_scheduled=True
        ).order_by('next_run')

        serializer = ReportListSerializer(schedules, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = ReportScheduleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        report = serializer.save(
            organization=organization,
            created_by=request.user,
            status='scheduled'
        )
        report.calculate_next_run()
        report.save()

        log_action(
            user=request.user,
            action='create',
            resource='report_schedule',
            resource_id=str(report.id),
            request=request,
            details={'frequency': report.schedule_frequency}
        )

        return Response(
            ReportListSerializer(report).data,
            status=status.HTTP_201_CREATED
        )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def report_schedule_detail(request, schedule_id):
    """
    Get, update, or delete a scheduled report.
    """
    organization = get_user_organization(request)
    if organization is None:
        return Response(
            {'error': 'User profile not found'},
            status=status.HTTP_400_BAD_REQUEST
        )

    schedule = get_object_or_404(
        Report,
        id=schedule_id,
        organization=organization,
        is_scheduled=True
    )

    if request.method == 'GET':
        serializer = ReportDetailSerializer(schedule)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = ReportScheduleSerializer(schedule, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        schedule = serializer.save()
        if schedule.is_scheduled:
            schedule.calculate_next_run()
            schedule.save()

        log_action(
            user=request.user,
            action='update',
            resource='report_schedule',
            resource_id=str(schedule.id),
            request=request,
        )

        return Response(ReportDetailSerializer(schedule).data)

    elif request.method == 'DELETE':
        schedule.delete()

        log_action(
            user=request.user,
            action='delete',
            resource='report_schedule',
            resource_id=str(schedule_id),
            request=request,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ReportGenerateThrottle])
def schedule_run_now(request, schedule_id):
    """
    Trigger immediate execution of a scheduled report.
    """
    organization = get_user_organization(request)
    if organization is None:
        return Response(
            {'error': 'User profile not found'},
            status=status.HTTP_400_BAD_REQUEST
        )

    schedule = get_object_or_404(
        Report,
        id=schedule_id,
        organization=organization,
        is_scheduled=True
    )

    # Queue async generation
    from .tasks import generate_report_async
    generate_report_async.delay(str(schedule.id))

    log_action(
        user=request.user,
        action='execute',
        resource='report_schedule',
        resource_id=str(schedule.id),
        request=request,
    )

    return Response({
        'message': 'Report generation triggered',
        'id': str(schedule.id)
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_share(request, report_id):
    """
    Share a report with other users.
    """
    organization = get_user_organization(request)
    if organization is None:
        return Response(
            {'error': 'User profile not found'},
            status=status.HTTP_400_BAD_REQUEST
        )

    report = get_object_or_404(Report, id=report_id, organization=organization)

    # Only creator can share
    if report.created_by != request.user and not request.user.is_superuser:
        return Response(
            {'error': 'Only the report creator can share'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = ReportShareSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Update public flag
    if 'is_public' in data:
        report.is_public = data['is_public']

    # Update shared users
    if 'user_ids' in data:
        # Get users in same organization
        users = User.objects.filter(
            id__in=data['user_ids'],
            profile__organization=organization
        )
        report.shared_with.set(users)

    report.save()

    log_action(
        user=request.user,
        action='share',
        resource='report',
        resource_id=str(report.id),
        request=request,
        details={'is_public': report.is_public, 'shared_count': report.shared_with.count()}
    )

    return Response(ReportDetailSerializer(report).data)
