"""
Django admin configuration for procurement with CSV upload functionality.
Includes Data Upload Center with organization management and upload wizard.
"""
import json
import csv
import io
import uuid as uuid_lib
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.core.serializers.json import DjangoJSONEncoder

from .models import (
    Supplier, Category, Transaction, DataUpload,
    ColumnMappingTemplate, Contract, SpendingPolicy, PolicyViolation,
    PurchaseRequisition, PurchaseOrder, GoodsReceipt, Invoice
)
from .forms import CSVUploadForm, OrganizationResetForm, DeleteAllDataForm
from .services import CSVProcessor
from apps.authentication.models import Organization
from apps.authentication.utils import log_action

User = get_user_model()


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'code', 'is_active', 'created_at']
    list_filter = ['is_active', 'organization', 'created_at']
    search_fields = ['name', 'code', 'contact_email']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            return qs.filter(organization=request.user.profile.organization)
        return qs.none()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'organization', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            return qs.filter(organization=request.user.profile.organization)
        return qs.none()


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'supplier', 'category', 'amount', 'organization', 'uploaded_by']
    list_filter = ['organization', 'date', 'fiscal_year', 'supplier', 'category']
    search_fields = ['description', 'invoice_number', 'supplier__name', 'category__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            return qs.filter(organization=request.user.profile.organization)
        return qs.none()


@admin.register(DataUpload)
class DataUploadAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'organization', 'uploaded_by', 'status_badge', 'successful_rows', 'failed_rows', 'duplicate_rows', 'created_at']
    list_filter = ['status', 'organization', 'created_at', 'processing_mode']
    search_fields = ['file_name', 'batch_id']
    readonly_fields = ['file_name', 'file_size', 'batch_id', 'total_rows', 'successful_rows',
                       'failed_rows', 'duplicate_rows', 'status', 'error_log', 'uploaded_by',
                       'organization', 'created_at', 'completed_at', 'progress_percent',
                       'progress_message', 'processing_mode', 'celery_task_id']
    ordering = ['-created_at']
    change_list_template = 'admin/procurement/dataupload/change_list.html'

    def status_badge(self, obj):
        """Display status with color-coded badge"""
        colors = {
            'pending': '#6b7280',     # gray
            'processing': '#f59e0b',  # amber
            'completed': '#10b981',   # green
            'failed': '#ef4444',      # red
            'partial': '#6366f1',     # indigo
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 600;">{}</span>',
            color, obj.status.upper()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            # Legacy upload (still supported)
            path(
                'upload-csv/',
                self.admin_site.admin_view(self.upload_csv_view),
                name='procurement_dataupload_upload_csv'
            ),
            # Upload Wizard
            path(
                'upload-wizard/',
                self.admin_site.admin_view(self.upload_wizard_view),
                name='procurement_dataupload_upload_wizard'
            ),
            # AJAX API Endpoints for Upload Wizard
            path(
                'api/preview/',
                self.admin_site.admin_view(self.api_preview_file),
                name='procurement_dataupload_api_preview'
            ),
            path(
                'api/validate/',
                self.admin_site.admin_view(self.api_validate_mapping),
                name='procurement_dataupload_api_validate'
            ),
            path(
                'api/upload/',
                self.admin_site.admin_view(self.api_process_upload),
                name='procurement_dataupload_api_upload'
            ),
            path(
                'api/progress/<str:task_id>/',
                self.admin_site.admin_view(self.api_get_progress),
                name='procurement_dataupload_api_progress'
            ),
            path(
                'api/templates/',
                self.admin_site.admin_view(self.api_list_templates),
                name='procurement_dataupload_api_templates'
            ),
            path(
                'api/templates/save/',
                self.admin_site.admin_view(self.api_save_template),
                name='procurement_dataupload_api_save_template'
            ),
            # Organization Management
            path(
                'reset-organization/',
                self.admin_site.admin_view(self.reset_organization_view),
                name='procurement_dataupload_reset_organization'
            ),
            path(
                'delete-all-data/',
                self.admin_site.admin_view(self.delete_all_data_view),
                name='procurement_dataupload_delete_all_data'
            ),
            # Upload Detail View
            path(
                '<str:uuid>/detail/',
                self.admin_site.admin_view(self.upload_detail_view),
                name='procurement_dataupload_detail'
            ),
            path(
                '<str:uuid>/download-errors/',
                self.admin_site.admin_view(self.download_error_report),
                name='procurement_dataupload_download_errors'
            ),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            return qs.filter(organization=request.user.profile.organization)
        return qs.none()

    def has_add_permission(self, request):
        """Disable the default add - use the upload CSV view instead"""
        return False

    def has_change_permission(self, request, obj=None):
        """Uploads are read-only"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow superusers to delete uploads"""
        return request.user.is_superuser

    @method_decorator(staff_member_required)
    def upload_csv_view(self, request):
        """Custom view for CSV upload"""
        # Check permission - only admin/manager roles or superuser
        if not request.user.is_superuser:
            if not hasattr(request.user, 'profile'):
                messages.error(request, 'You do not have a user profile. Contact an administrator.')
                return redirect('..')
            if request.user.profile.role not in ['admin', 'manager']:
                messages.error(request, 'Only Admins and Managers can upload data.')
                return redirect('..')

        if request.method == 'POST':
            form = CSVUploadForm(request.POST, request.FILES, user=request.user)
            if form.is_valid():
                try:
                    organization = form.get_organization()
                    if not organization:
                        messages.error(request, 'Could not determine target organization.')
                        return redirect('.')

                    # Check if super admin is doing multi-org upload
                    is_super_admin = request.user.is_superuser

                    processor = CSVProcessor(
                        organization=organization,
                        user=request.user,
                        file=form.cleaned_data['file'],
                        skip_duplicates=form.cleaned_data.get('skip_duplicates', True),
                        allow_multi_org=is_super_admin
                    )

                    upload = processor.process()

                    # Build audit details
                    audit_details = {
                        'file_name': upload.file_name,
                        'successful': upload.successful_rows,
                        'failed': upload.failed_rows,
                        'duplicates': upload.duplicate_rows
                    }

                    # Include affected organizations for super admin multi-org uploads
                    if is_super_admin and len(processor.orgs_affected) > 0:
                        audit_details['organizations_affected'] = list(processor.orgs_affected)

                    log_action(
                        user=request.user,
                        action='upload',
                        resource='transactions',
                        resource_id=upload.batch_id,
                        details=audit_details,
                        request=request
                    )

                    # Success message with details
                    if upload.status == 'completed':
                        messages.success(
                            request,
                            f'Successfully uploaded {upload.successful_rows} transactions from "{upload.file_name}".'
                        )
                    elif upload.status == 'partial':
                        messages.warning(
                            request,
                            f'Uploaded {upload.successful_rows} transactions, '
                            f'{upload.failed_rows} failed, {upload.duplicate_rows} duplicates skipped.'
                        )
                    else:
                        messages.error(
                            request,
                            f'Upload failed. {upload.failed_rows} rows had errors.'
                        )

                    return redirect('..')

                except ValueError as e:
                    messages.error(request, f'Upload error: {str(e)}')
                except Exception as e:
                    messages.error(request, f'Unexpected error: {str(e)}')
        else:
            form = CSVUploadForm(user=request.user)

        context = {
            **self.admin_site.each_context(request),
            'title': 'Upload CSV Data',
            'form': form,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }

        return render(request, 'admin/procurement/dataupload/upload_csv.html', context)

    @method_decorator(staff_member_required)
    def reset_organization_view(self, request):
        """
        Super admin only: Complete database reset for an organization.
        Requires typing the exact organization name to confirm.
        """
        # Permission check - superuser only
        if not request.user.is_superuser:
            messages.error(request, 'Only super administrators can reset organizations.')
            return redirect('..')

        if request.method == 'POST':
            form = OrganizationResetForm(request.POST)
            if form.is_valid():
                organization = form.cleaned_data['organization']

                # Perform reset in correct order (respecting FK constraints)
                with transaction.atomic():
                    counts = {}

                    # 1. Delete policy violations first (FK to transactions)
                    counts['violations'] = PolicyViolation.objects.filter(
                        organization=organization
                    ).count()
                    PolicyViolation.objects.filter(organization=organization).delete()

                    # 2. Delete P2P data (must delete before suppliers due to FK constraints)
                    # Order: Invoices -> GoodsReceipts -> PurchaseOrders -> PurchaseRequisitions
                    counts['invoices'] = Invoice.objects.filter(
                        organization=organization
                    ).count()
                    Invoice.objects.filter(organization=organization).delete()

                    counts['goods_receipts'] = GoodsReceipt.objects.filter(
                        organization=organization
                    ).count()
                    GoodsReceipt.objects.filter(organization=organization).delete()

                    counts['purchase_orders'] = PurchaseOrder.objects.filter(
                        organization=organization
                    ).count()
                    PurchaseOrder.objects.filter(organization=organization).delete()

                    counts['purchase_requisitions'] = PurchaseRequisition.objects.filter(
                        organization=organization
                    ).count()
                    PurchaseRequisition.objects.filter(organization=organization).delete()

                    # 3. Delete transactions
                    counts['transactions'] = Transaction.objects.filter(
                        organization=organization
                    ).count()
                    Transaction.objects.filter(organization=organization).delete()

                    # 4. Delete uploads
                    counts['uploads'] = DataUpload.objects.filter(
                        organization=organization
                    ).count()
                    DataUpload.objects.filter(organization=organization).delete()

                    # 5. Delete mapping templates
                    counts['templates'] = ColumnMappingTemplate.objects.filter(
                        organization=organization
                    ).count()
                    ColumnMappingTemplate.objects.filter(organization=organization).delete()

                    # 6. Delete contracts (has FK to suppliers)
                    counts['contracts'] = Contract.objects.filter(
                        organization=organization
                    ).count()
                    Contract.objects.filter(organization=organization).delete()

                    # 7. Delete suppliers
                    counts['suppliers'] = Supplier.objects.filter(
                        organization=organization
                    ).count()
                    Supplier.objects.filter(organization=organization).delete()

                    # 8. Delete categories
                    counts['categories'] = Category.objects.filter(
                        organization=organization
                    ).count()
                    Category.objects.filter(organization=organization).delete()

                    # 9. Delete spending policies
                    counts['policies'] = SpendingPolicy.objects.filter(
                        organization=organization
                    ).count()
                    SpendingPolicy.objects.filter(organization=organization).delete()

                    # Log the action
                    log_action(
                        user=request.user,
                        action='reset',
                        resource='organization',
                        resource_id=str(organization.pk),
                        details={
                            'organization_name': organization.name,
                            'transactions_deleted': counts['transactions'],
                            'suppliers_deleted': counts['suppliers'],
                            'categories_deleted': counts['categories'],
                            'uploads_deleted': counts['uploads'],
                            'templates_deleted': counts['templates'],
                            'contracts_deleted': counts['contracts'],
                            'invoices_deleted': counts['invoices'],
                            'purchase_orders_deleted': counts['purchase_orders'],
                            'goods_receipts_deleted': counts['goods_receipts'],
                            'purchase_requisitions_deleted': counts['purchase_requisitions'],
                        },
                        request=request
                    )

                p2p_total = (counts['invoices'] + counts['purchase_orders'] +
                             counts['goods_receipts'] + counts['purchase_requisitions'])
                messages.success(
                    request,
                    f'Organization "{organization.name}" has been reset. '
                    f'Deleted: {counts["transactions"]} transactions, '
                    f'{counts["suppliers"]} suppliers, {counts["categories"]} categories, '
                    f'{counts["uploads"]} uploads, {counts["contracts"]} contracts, '
                    f'{p2p_total} P2P documents (PRs/POs/GRs/Invoices).'
                )
                return redirect('..')
        else:
            form = OrganizationResetForm()

        context = {
            **self.admin_site.each_context(request),
            'title': 'Reset Organization',
            'form': form,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }

        return render(request, 'admin/procurement/dataupload/reset_organization.html', context)

    @method_decorator(staff_member_required)
    def delete_all_data_view(self, request):
        """
        Org admin: Delete all transactions for the user's organization.
        Preserves master data (suppliers, categories).
        """
        # Permission check
        if not request.user.is_superuser:
            if not hasattr(request.user, 'profile'):
                messages.error(request, 'You do not have a user profile.')
                return redirect('..')
            if request.user.profile.role != 'admin':
                messages.error(request, 'Only organization administrators can delete data.')
                return redirect('..')

        # Get user's organization for non-superusers
        organization = None
        if not request.user.is_superuser and hasattr(request.user, 'profile'):
            organization = request.user.profile.organization

        if request.method == 'POST':
            form = DeleteAllDataForm(request.POST, user=request.user)
            if form.is_valid():
                target_org = form.get_organization()
                if not target_org:
                    messages.error(request, 'Could not determine target organization.')
                    return redirect('.')

                # Delete all transactions and uploads
                with transaction.atomic():
                    # Delete policy violations first
                    violation_count = PolicyViolation.objects.filter(
                        organization=target_org
                    ).count()
                    PolicyViolation.objects.filter(organization=target_org).delete()

                    # Delete transactions
                    transaction_count = Transaction.objects.filter(
                        organization=target_org
                    ).count()
                    Transaction.objects.filter(organization=target_org).delete()

                    # Delete upload records
                    upload_count = DataUpload.objects.filter(
                        organization=target_org
                    ).count()
                    DataUpload.objects.filter(organization=target_org).delete()

                    # Log the action
                    log_action(
                        user=request.user,
                        action='bulk_delete',
                        resource='transactions',
                        resource_id=str(target_org.pk),
                        details={
                            'organization_name': target_org.name,
                            'transactions_deleted': transaction_count,
                            'uploads_deleted': upload_count,
                        },
                        request=request
                    )

                messages.success(
                    request,
                    f'Deleted {transaction_count} transactions and {upload_count} upload records '
                    f'from "{target_org.name}". Master data (suppliers, categories) preserved.'
                )
                return redirect('..')
        else:
            form = DeleteAllDataForm(user=request.user)

        context = {
            **self.admin_site.each_context(request),
            'title': 'Delete All Data',
            'form': form,
            'organization': organization,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }

        return render(request, 'admin/procurement/dataupload/delete_all_data.html', context)

    # ==================== Upload Wizard Views ====================

    @method_decorator(staff_member_required)
    def upload_wizard_view(self, request):
        """Render the 5-step upload wizard interface."""
        # Permission check
        if not request.user.is_superuser:
            if not hasattr(request.user, 'profile'):
                messages.error(request, 'You do not have a user profile.')
                return redirect('..')
            if request.user.profile.role not in ['admin', 'manager']:
                messages.error(request, 'Only Admins and Managers can upload data.')
                return redirect('..')

        # Get organizations for superuser dropdown
        organizations = []
        if request.user.is_superuser:
            organizations = list(
                Organization.objects.filter(is_active=True)
                .order_by('name')
                .values('id', 'name')
            )

        # Get user's organization
        user_org = None
        if hasattr(request.user, 'profile') and request.user.profile.organization:
            user_org = {
                'id': request.user.profile.organization.id,
                'name': request.user.profile.organization.name,
            }

        context = {
            **self.admin_site.each_context(request),
            'title': 'Upload Wizard',
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
            'is_superuser': request.user.is_superuser,
            'organizations': json.dumps(organizations, default=str),
            'user_organization': json.dumps(user_org, default=str),
        }

        return render(request, 'admin/procurement/dataupload/upload_wizard.html', context)

    @method_decorator(staff_member_required)
    def api_preview_file(self, request):
        """
        API endpoint to preview CSV file contents.
        Returns headers and first 100 rows for preview.
        """
        if request.method != 'POST':
            return JsonResponse({'error': 'POST required'}, status=405)

        # Permission check
        if not self._check_upload_permission(request):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'error': 'No file provided'}, status=400)

        # Validate file
        if not file.name.lower().endswith('.csv'):
            return JsonResponse({'error': 'File must be a CSV'}, status=400)

        if file.size > 50 * 1024 * 1024:
            return JsonResponse({'error': 'File size must be less than 50MB'}, status=400)

        try:
            # Read CSV content
            content = file.read().decode('utf-8-sig')
            file.seek(0)  # Reset for later use

            reader = csv.DictReader(io.StringIO(content))
            headers = reader.fieldnames or []

            # Get first 100 rows for preview
            rows = []
            for i, row in enumerate(reader):
                if i >= 100:
                    break
                rows.append(row)

            # Count total rows
            file.seek(0)
            total_rows = sum(1 for _ in csv.reader(io.StringIO(content))) - 1  # Exclude header

            return JsonResponse({
                'success': True,
                'headers': headers,
                'preview_rows': rows,
                'total_rows': total_rows,
                'file_name': file.name,
                'file_size': file.size,
            })

        except UnicodeDecodeError:
            return JsonResponse({'error': 'File encoding not supported. Please use UTF-8.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Error reading file: {str(e)}'}, status=400)

    @method_decorator(staff_member_required)
    def api_validate_mapping(self, request):
        """
        API endpoint to validate column mappings before upload.
        Returns validation results with error details.
        """
        if request.method != 'POST':
            return JsonResponse({'error': 'POST required'}, status=405)

        if not self._check_upload_permission(request):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        file = request.FILES.get('file')
        mapping_json = request.POST.get('mapping', '{}')
        organization_id = request.POST.get('organization_id')
        skip_duplicates = request.POST.get('skip_duplicates', 'false').lower() == 'true'
        strict_duplicates = request.POST.get('strict_duplicates', 'false').lower() == 'true'

        if not file:
            return JsonResponse({'error': 'No file provided'}, status=400)

        try:
            mapping = json.loads(mapping_json)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid mapping JSON'}, status=400)

        # Get organization
        organization = self._get_target_organization(request, organization_id)
        if not organization:
            return JsonResponse({'error': 'Organization not found'}, status=400)

        # Required fields check
        required_fields = {'supplier', 'category', 'amount', 'date'}
        mapped_fields = set(mapping.values())
        missing_required = required_fields - mapped_fields

        if missing_required:
            return JsonResponse({
                'success': False,
                'error': f'Missing required mappings: {", ".join(missing_required)}',
                'missing_fields': list(missing_required)
            }, status=400)

        try:
            content = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(content))
            headers = reader.fieldnames or []

            # Validate each row
            errors = []
            valid_count = 0
            duplicate_count = 0

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                row_errors = self._validate_row(row, mapping, organization, row_num)
                if row_errors:
                    errors.extend(row_errors)
                else:
                    # Check for duplicates (unless skip_duplicates is enabled)
                    if not skip_duplicates and self._is_duplicate_row(row, mapping, organization, strict_mode=strict_duplicates):
                        duplicate_count += 1
                    else:
                        valid_count += 1

            return JsonResponse({
                'success': True,
                'valid_count': valid_count,
                'error_count': len(errors),
                'duplicate_count': duplicate_count,
                'errors': errors[:100],  # Limit to first 100 errors
                'total_errors': len(errors),
            })

        except Exception as e:
            return JsonResponse({'error': f'Validation error: {str(e)}'}, status=400)

    @method_decorator(staff_member_required)
    def api_process_upload(self, request):
        """
        API endpoint to process the CSV upload.
        Uses sync or async processing based on file size.
        """
        if request.method != 'POST':
            return JsonResponse({'error': 'POST required'}, status=405)

        if not self._check_upload_permission(request):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        file = request.FILES.get('file')
        mapping_json = request.POST.get('mapping', '{}')
        organization_id = request.POST.get('organization_id')
        skip_invalid = request.POST.get('skip_invalid', 'true').lower() == 'true'
        skip_duplicates = request.POST.get('skip_duplicates', 'false').lower() == 'true'
        strict_duplicates = request.POST.get('strict_duplicates', 'false').lower() == 'true'
        template_name = request.POST.get('template_name', '')

        if not file:
            return JsonResponse({'error': 'No file provided'}, status=400)

        try:
            mapping = json.loads(mapping_json)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid mapping JSON'}, status=400)

        organization = self._get_target_organization(request, organization_id)
        if not organization:
            return JsonResponse({'error': 'Organization not found'}, status=400)

        # Determine processing mode based on file size
        # Files >10MB use async processing
        use_async = file.size > 10 * 1024 * 1024

        try:
            # Create upload record
            batch_id = str(uuid_lib.uuid4())
            upload = DataUpload.objects.create(
                organization=organization,
                uploaded_by=request.user,
                file_name=file.name,
                file_size=file.size,
                batch_id=batch_id,
                status='pending',
                processing_mode='async' if use_async else 'sync',
                column_mapping_snapshot=mapping,
            )

            if use_async:
                # Save file for async processing
                from django.core.files.base import ContentFile
                content = file.read()
                upload.stored_file.save(file.name, ContentFile(content))
                upload.save()

                # Queue Celery task
                from .tasks import process_csv_upload
                task = process_csv_upload.delay(upload.id, mapping, skip_invalid, skip_duplicates, strict_duplicates)

                upload.celery_task_id = task.id
                upload.status = 'processing'
                upload.save()

                return JsonResponse({
                    'success': True,
                    'async': True,
                    'task_id': task.id,
                    'upload_id': str(upload.uuid),
                    'message': 'Upload queued for background processing'
                })
            else:
                # Sync processing for smaller files
                upload.status = 'processing'
                upload.save()

                result = self._process_csv_sync(file, mapping, organization, request.user, upload, skip_invalid, skip_duplicates, strict_duplicates)

                # Log the action
                log_action(
                    user=request.user,
                    action='upload',
                    resource='transactions',
                    resource_id=upload.batch_id,
                    details={
                        'file_name': upload.file_name,
                        'successful': upload.successful_rows,
                        'failed': upload.failed_rows,
                        'duplicates': upload.duplicate_rows,
                        'processing_mode': 'sync',
                    },
                    request=request
                )

                return JsonResponse({
                    'success': True,
                    'async': False,
                    'upload_id': str(upload.uuid),
                    'status': upload.status,
                    'successful_rows': upload.successful_rows,
                    'failed_rows': upload.failed_rows,
                    'duplicate_rows': upload.duplicate_rows,
                    'message': f'Processed {upload.successful_rows} transactions'
                })

        except Exception as e:
            return JsonResponse({'error': f'Upload error: {str(e)}'}, status=500)

    @method_decorator(staff_member_required)
    def api_get_progress(self, request, task_id):
        """API endpoint to get upload progress for async tasks."""
        try:
            upload = DataUpload.objects.get(celery_task_id=task_id)

            # Check organization access
            if not request.user.is_superuser:
                if hasattr(request.user, 'profile'):
                    if upload.organization != request.user.profile.organization:
                        return JsonResponse({'error': 'Access denied'}, status=403)
                else:
                    return JsonResponse({'error': 'Access denied'}, status=403)

            return JsonResponse({
                'success': True,
                'status': upload.status,
                'progress_percent': upload.progress_percent,
                'progress_message': upload.progress_message,
                'successful_rows': upload.successful_rows,
                'failed_rows': upload.failed_rows,
                'duplicate_rows': upload.duplicate_rows,
                'total_rows': upload.total_rows,
            })

        except DataUpload.DoesNotExist:
            return JsonResponse({'error': 'Upload not found'}, status=404)

    @method_decorator(staff_member_required)
    def api_list_templates(self, request):
        """API endpoint to list column mapping templates."""
        organization = self._get_target_organization(
            request,
            request.GET.get('organization_id')
        )

        if not organization:
            return JsonResponse({'error': 'Organization not found'}, status=400)

        templates = ColumnMappingTemplate.objects.filter(
            organization=organization
        ).order_by('-is_default', 'name').values(
            'id', 'uuid', 'name', 'description', 'mapping', 'is_default', 'created_at'
        )

        return JsonResponse({
            'success': True,
            'templates': list(templates)
        }, encoder=DjangoJSONEncoder)

    @method_decorator(staff_member_required)
    def api_save_template(self, request):
        """API endpoint to save a column mapping template."""
        if request.method != 'POST':
            return JsonResponse({'error': 'POST required'}, status=405)

        if not self._check_upload_permission(request):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        mapping = data.get('mapping', {})
        organization_id = data.get('organization_id')
        set_default = data.get('is_default', False)

        if not name:
            return JsonResponse({'error': 'Template name is required'}, status=400)

        if not mapping:
            return JsonResponse({'error': 'Mapping is required'}, status=400)

        organization = self._get_target_organization(request, organization_id)
        if not organization:
            return JsonResponse({'error': 'Organization not found'}, status=400)

        try:
            with transaction.atomic():
                # If setting as default, unset other defaults
                if set_default:
                    ColumnMappingTemplate.objects.filter(
                        organization=organization,
                        is_default=True
                    ).update(is_default=False)

                # Create or update template
                template, created = ColumnMappingTemplate.objects.update_or_create(
                    organization=organization,
                    name=name,
                    defaults={
                        'description': description,
                        'mapping': mapping,
                        'is_default': set_default,
                        'created_by': request.user,
                    }
                )

                # Log action
                log_action(
                    user=request.user,
                    action='create' if created else 'update',
                    resource='mapping_template',
                    resource_id=str(template.uuid),
                    details={
                        'template_name': name,
                        'organization_name': organization.name,
                    },
                    request=request
                )

                return JsonResponse({
                    'success': True,
                    'template_id': str(template.uuid),
                    'created': created,
                    'message': f'Template "{name}" {"created" if created else "updated"} successfully'
                })

        except Exception as e:
            return JsonResponse({'error': f'Error saving template: {str(e)}'}, status=500)

    # ==================== Upload Detail Views ====================

    @method_decorator(staff_member_required)
    def upload_detail_view(self, request, uuid):
        """Detailed view of an upload with logs and error information."""
        try:
            upload = DataUpload.objects.get(uuid=uuid)
        except DataUpload.DoesNotExist:
            messages.error(request, 'Upload not found.')
            return redirect('..')

        # Check organization access
        if not request.user.is_superuser:
            if hasattr(request.user, 'profile'):
                if upload.organization != request.user.profile.organization:
                    messages.error(request, 'Access denied.')
                    return redirect('..')
            else:
                messages.error(request, 'Access denied.')
                return redirect('..')

        # Parse error log
        error_entries = []
        if upload.error_log:
            try:
                error_entries = json.loads(upload.error_log)
            except json.JSONDecodeError:
                error_entries = [{'message': upload.error_log}]

        context = {
            **self.admin_site.each_context(request),
            'title': f'Upload Detail: {upload.file_name}',
            'upload': upload,
            'error_entries': error_entries[:100],  # Limit displayed errors
            'total_errors': len(error_entries),
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }

        return render(request, 'admin/procurement/dataupload/upload_detail.html', context)

    @method_decorator(staff_member_required)
    def download_error_report(self, request, uuid):
        """Download error log as CSV."""
        try:
            upload = DataUpload.objects.get(uuid=uuid)
        except DataUpload.DoesNotExist:
            return HttpResponse('Upload not found', status=404)

        # Check organization access
        if not request.user.is_superuser:
            if hasattr(request.user, 'profile'):
                if upload.organization != request.user.profile.organization:
                    return HttpResponse('Access denied', status=403)
            else:
                return HttpResponse('Access denied', status=403)

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="errors_{upload.file_name}"'

        writer = csv.writer(response)
        writer.writerow(['Row', 'Field', 'Error', 'Value'])

        if upload.error_log:
            try:
                errors = json.loads(upload.error_log)
                for error in errors:
                    writer.writerow([
                        error.get('row', ''),
                        error.get('field', ''),
                        error.get('message', ''),
                        error.get('value', '')
                    ])
            except json.JSONDecodeError:
                writer.writerow(['', '', upload.error_log, ''])

        return response

    # ==================== Helper Methods ====================

    def _check_upload_permission(self, request):
        """Check if user has permission to upload."""
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'profile'):
            return request.user.profile.role in ['admin', 'manager']
        return False

    def _get_target_organization(self, request, organization_id=None):
        """Get the target organization for an operation."""
        if organization_id and request.user.is_superuser:
            try:
                return Organization.objects.get(id=organization_id, is_active=True)
            except Organization.DoesNotExist:
                pass

        if hasattr(request.user, 'profile'):
            return request.user.profile.organization

        return None

    def _validate_row(self, row, mapping, organization, row_num):
        """Validate a single row and return list of errors."""
        errors = []

        # Get mapped values
        supplier_col = next((k for k, v in mapping.items() if v == 'supplier'), None)
        category_col = next((k for k, v in mapping.items() if v == 'category'), None)
        amount_col = next((k for k, v in mapping.items() if v == 'amount'), None)
        date_col = next((k for k, v in mapping.items() if v == 'date'), None)

        # Validate supplier
        if supplier_col:
            supplier_val = row.get(supplier_col, '').strip()
            if not supplier_val:
                errors.append({
                    'row': row_num,
                    'field': 'supplier',
                    'message': 'Supplier is required',
                    'value': ''
                })

        # Validate category
        if category_col:
            category_val = row.get(category_col, '').strip()
            if not category_val:
                errors.append({
                    'row': row_num,
                    'field': 'category',
                    'message': 'Category is required',
                    'value': ''
                })

        # Validate amount
        if amount_col:
            amount_val = row.get(amount_col, '').strip()
            if not amount_val:
                errors.append({
                    'row': row_num,
                    'field': 'amount',
                    'message': 'Amount is required',
                    'value': ''
                })
            else:
                try:
                    # Clean amount string
                    clean_amount = amount_val.replace('$', '').replace(',', '').strip()
                    Decimal(clean_amount)
                except (InvalidOperation, ValueError):
                    errors.append({
                        'row': row_num,
                        'field': 'amount',
                        'message': 'Invalid amount format',
                        'value': amount_val
                    })

        # Validate date
        if date_col:
            date_val = row.get(date_col, '').strip()
            if not date_val:
                errors.append({
                    'row': row_num,
                    'field': 'date',
                    'message': 'Date is required',
                    'value': ''
                })
            else:
                if not self._parse_date(date_val):
                    errors.append({
                        'row': row_num,
                        'field': 'date',
                        'message': 'Invalid date format (use YYYY-MM-DD, MM/DD/YYYY, or DD-MM-YYYY)',
                        'value': date_val
                    })

        return errors

    def _parse_date(self, date_str):
        """Try to parse a date string in various formats."""
        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%m-%d-%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        return None

    def _is_duplicate_row(self, row, mapping, organization, strict_mode=False):
        """Check if a row would create a duplicate transaction.

        Args:
            row: The CSV row data
            mapping: Column to field mapping
            organization: Target organization
            strict_mode: If True, use all mapped fields for duplicate detection.
                        If False (default), use only core fields (supplier, category, amount, date, invoice_number).
        """
        supplier_col = next((k for k, v in mapping.items() if v == 'supplier'), None)
        category_col = next((k for k, v in mapping.items() if v == 'category'), None)
        amount_col = next((k for k, v in mapping.items() if v == 'amount'), None)
        date_col = next((k for k, v in mapping.items() if v == 'date'), None)
        invoice_col = next((k for k, v in mapping.items() if v == 'invoice_number'), None)

        if not all([supplier_col, category_col, amount_col, date_col]):
            return False

        supplier_name = row.get(supplier_col, '').strip()
        category_name = row.get(category_col, '').strip()
        amount_str = row.get(amount_col, '').strip().replace('$', '').replace(',', '')
        date_str = row.get(date_col, '').strip()
        invoice_number = row.get(invoice_col, '').strip() if invoice_col else ''

        try:
            amount = Decimal(amount_str)
            date = self._parse_date(date_str)

            if not date:
                return False

            # Check for existing transaction - start with core fields
            query = Transaction.objects.filter(
                organization=organization,
                supplier__name__iexact=supplier_name,
                category__name__iexact=category_name,
                amount=amount,
                date=date
            )

            if invoice_number:
                query = query.filter(invoice_number=invoice_number)

            # In strict mode, also check all other mapped fields
            if strict_mode:
                description_col = next((k for k, v in mapping.items() if v == 'description'), None)
                fiscal_year_col = next((k for k, v in mapping.items() if v == 'fiscal_year'), None)
                subcategory_col = next((k for k, v in mapping.items() if v == 'subcategory'), None)
                location_col = next((k for k, v in mapping.items() if v == 'location'), None)
                spend_band_col = next((k for k, v in mapping.items() if v == 'spend_band'), None)
                payment_method_col = next((k for k, v in mapping.items() if v == 'payment_method'), None)

                if description_col:
                    description = row.get(description_col, '').strip()
                    query = query.filter(description=description)

                if fiscal_year_col:
                    fiscal_year = row.get(fiscal_year_col, '').strip()
                    if fiscal_year:
                        query = query.filter(fiscal_year=fiscal_year)

                if subcategory_col:
                    subcategory = row.get(subcategory_col, '').strip()
                    query = query.filter(subcategory=subcategory)

                if location_col:
                    location = row.get(location_col, '').strip()
                    query = query.filter(location=location)

                if spend_band_col:
                    spend_band = row.get(spend_band_col, '').strip()
                    query = query.filter(spend_band=spend_band)

                if payment_method_col:
                    payment_method = row.get(payment_method_col, '').strip()
                    query = query.filter(payment_method=payment_method)

            return query.exists()

        except (InvalidOperation, ValueError):
            return False

    def _process_csv_sync(self, file, mapping, organization, user, upload, skip_invalid=True, skip_duplicates=False, strict_duplicates=False):
        """Process CSV file synchronously."""
        content = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))

        successful = 0
        failed = 0
        duplicates = 0
        errors = []

        # Get column mappings
        supplier_col = next((k for k, v in mapping.items() if v == 'supplier'), None)
        category_col = next((k for k, v in mapping.items() if v == 'category'), None)
        amount_col = next((k for k, v in mapping.items() if v == 'amount'), None)
        date_col = next((k for k, v in mapping.items() if v == 'date'), None)
        description_col = next((k for k, v in mapping.items() if v == 'description'), None)
        invoice_col = next((k for k, v in mapping.items() if v == 'invoice_number'), None)
        fiscal_year_col = next((k for k, v in mapping.items() if v == 'fiscal_year'), None)
        subcategory_col = next((k for k, v in mapping.items() if v == 'subcategory'), None)
        location_col = next((k for k, v in mapping.items() if v == 'location'), None)
        spend_band_col = next((k for k, v in mapping.items() if v == 'spend_band'), None)
        payment_method_col = next((k for k, v in mapping.items() if v == 'payment_method'), None)

        with transaction.atomic():
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Validate row
                    row_errors = self._validate_row(row, mapping, organization, row_num)
                    if row_errors:
                        errors.extend(row_errors)
                        if not skip_invalid:
                            raise ValueError(f"Row {row_num} has validation errors")
                        failed += 1
                        continue

                    # Check for duplicates (unless skip_duplicates is enabled)
                    if not skip_duplicates and self._is_duplicate_row(row, mapping, organization, strict_mode=strict_duplicates):
                        duplicates += 1
                        continue

                    # Get or create supplier
                    supplier_name = row.get(supplier_col, '').strip()
                    supplier, _ = Supplier.objects.get_or_create(
                        organization=organization,
                        name__iexact=supplier_name,
                        defaults={'name': supplier_name}
                    )

                    # Get or create category
                    category_name = row.get(category_col, '').strip()
                    category, _ = Category.objects.get_or_create(
                        organization=organization,
                        name__iexact=category_name,
                        defaults={'name': category_name}
                    )

                    # Parse amount
                    amount_str = row.get(amount_col, '').strip().replace('$', '').replace(',', '')
                    amount = Decimal(amount_str)

                    # Parse date
                    date_str = row.get(date_col, '').strip()
                    date = self._parse_date(date_str)

                    # Create transaction
                    Transaction.objects.create(
                        organization=organization,
                        supplier=supplier,
                        category=category,
                        amount=amount,
                        date=date,
                        description=row.get(description_col, '').strip() if description_col else '',
                        invoice_number=row.get(invoice_col, '').strip() if invoice_col else '',
                        fiscal_year=row.get(fiscal_year_col, '').strip() if fiscal_year_col else str(date.year),
                        subcategory=row.get(subcategory_col, '').strip() if subcategory_col else '',
                        location=row.get(location_col, '').strip() if location_col else '',
                        spend_band=row.get(spend_band_col, '').strip() if spend_band_col else '',
                        payment_method=row.get(payment_method_col, '').strip() if payment_method_col else '',
                        uploaded_by=user,
                        upload_batch=upload.batch_id
                    )
                    successful += 1

                except Exception as e:
                    failed += 1
                    errors.append({
                        'row': row_num,
                        'field': 'general',
                        'message': str(e),
                        'value': ''
                    })
                    if not skip_invalid:
                        raise

        # Update upload record
        upload.successful_rows = successful
        upload.failed_rows = failed
        upload.duplicate_rows = duplicates
        upload.total_rows = successful + failed + duplicates
        upload.error_log = json.dumps(errors) if errors else ''
        upload.completed_at = timezone.now()

        if failed == 0 and duplicates == 0:
            upload.status = 'completed'
        elif successful > 0:
            upload.status = 'partial'
        else:
            upload.status = 'failed'

        upload.save()

        return {
            'successful': successful,
            'failed': failed,
            'duplicates': duplicates,
            'errors': errors
        }


# =============================================================================
# P2P (Procure-to-Pay) Model Admin Registrations
# =============================================================================

class P2PImportMixin:
    """Mixin to add CSV import functionality to P2P model admins."""

    p2p_doc_type = None  # Override in subclass: 'pr', 'po', 'gr', 'invoice'
    p2p_import_fields = []  # Override with expected CSV columns

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'import-csv/',
                self.admin_site.admin_view(self.import_csv_view),
                name=f'{self.model._meta.model_name}_import_csv'
            ),
            path(
                'download-template/',
                self.admin_site.admin_view(self.download_template_view),
                name=f'{self.model._meta.model_name}_download_template'
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_import_button'] = True
        extra_context['import_url'] = f'import-csv/'
        extra_context['template_url'] = f'download-template/'
        return super().changelist_view(request, extra_context=extra_context)

    @method_decorator(staff_member_required)
    def import_csv_view(self, request):
        """Handle CSV import for P2P documents."""
        if not self._check_import_permission(request):
            messages.error(request, 'You do not have permission to import data.')
            return redirect('..')

        if request.method == 'POST':
            file = request.FILES.get('file')
            if not file:
                messages.error(request, 'Please select a CSV file.')
                return redirect('.')

            if not file.name.lower().endswith('.csv'):
                messages.error(request, 'File must be a CSV.')
                return redirect('.')

            try:
                # Get organization
                organization = self._get_import_organization(request)
                if not organization:
                    messages.error(request, 'Could not determine target organization.')
                    return redirect('.')

                # Process the import
                content = file.read().decode('utf-8-sig')
                reader = csv.DictReader(io.StringIO(content))
                rows = list(reader)

                batch_id = str(uuid_lib.uuid4())
                stats = self._process_p2p_import(rows, organization, batch_id, request.user)

                # Log the action
                log_action(
                    user=request.user,
                    action='upload',
                    resource=self.p2p_doc_type,
                    resource_id=batch_id,
                    details={
                        'file_name': file.name,
                        'successful': stats['successful'],
                        'failed': stats['failed'],
                        'skipped': stats['skipped'],
                    },
                    request=request
                )

                if stats['failed'] == 0:
                    messages.success(
                        request,
                        f'Successfully imported {stats["successful"]} {self.p2p_doc_type.upper()}(s). '
                        f'{stats["skipped"]} skipped as duplicates.'
                    )
                else:
                    messages.warning(
                        request,
                        f'Imported {stats["successful"]} {self.p2p_doc_type.upper()}(s), '
                        f'{stats["failed"]} failed, {stats["skipped"]} skipped.'
                    )

                return redirect('..')

            except UnicodeDecodeError:
                messages.error(request, 'File encoding not supported. Please use UTF-8.')
            except Exception as e:
                messages.error(request, f'Import error: {str(e)}')
                return redirect('.')

        # GET request - show upload form
        # Get organizations for superuser dropdown
        organizations = []
        if request.user.is_superuser:
            organizations = list(
                Organization.objects.filter(is_active=True)
                .order_by('name')
                .values('id', 'name')
            )

        # Get user's current organization
        user_org = None
        if hasattr(request.user, 'profile') and request.user.profile.organization:
            user_org = {
                'id': request.user.profile.organization.id,
                'name': request.user.profile.organization.name,
            }

        context = {
            **self.admin_site.each_context(request),
            'title': f'Import {self.model._meta.verbose_name_plural}',
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
            'expected_columns': self.p2p_import_fields,
            'doc_type': self.p2p_doc_type,
            'is_superuser': request.user.is_superuser,
            'organizations': organizations,
            'user_organization': user_org,
        }
        return render(request, 'admin/procurement/p2p_import.html', context)

    @method_decorator(staff_member_required)
    def download_template_view(self, request):
        """Download CSV template for this P2P document type."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.p2p_doc_type}_template.csv"'

        writer = csv.writer(response)
        writer.writerow(self.p2p_import_fields)
        # Add example row
        writer.writerow(self._get_template_example_row())

        return response

    def _check_import_permission(self, request):
        """Check if user can import data."""
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'profile'):
            return request.user.profile.role in ['admin', 'manager']
        return False

    def _get_import_organization(self, request):
        """Get organization for import."""
        org_id = request.POST.get('organization_id')
        if org_id and request.user.is_superuser:
            try:
                return Organization.objects.get(id=org_id, is_active=True)
            except Organization.DoesNotExist:
                pass
        if hasattr(request.user, 'profile'):
            return request.user.profile.organization
        return None

    def _process_p2p_import(self, rows, organization, batch_id, user):
        """Override in subclass to process import."""
        raise NotImplementedError

    def _get_template_example_row(self):
        """Override in subclass to provide example data."""
        return [''] * len(self.p2p_import_fields)


@admin.register(PurchaseRequisition)
class PurchaseRequisitionAdmin(P2PImportMixin, admin.ModelAdmin):
    """Admin for Purchase Requisitions - P2P Cycle Analytics."""

    p2p_doc_type = 'pr'
    p2p_import_fields = [
        'pr_number', 'department', 'cost_center', 'description', 'estimated_amount',
        'currency', 'budget_code', 'status', 'priority', 'created_date',
        'submitted_date', 'approval_date', 'supplier_suggested', 'category'
    ]

    list_display = [
        'pr_number', 'organization', 'status', 'priority', 'estimated_amount',
        'department', 'requested_by', 'created_date', 'approval_status_badge'
    ]
    list_filter = ['status', 'priority', 'organization', 'department', 'created_date']
    search_fields = ['pr_number', 'description', 'department', 'cost_center']
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    date_hierarchy = 'created_date'
    raw_id_fields = ['supplier_suggested', 'category', 'requested_by', 'approved_by']
    ordering = ['-created_date', '-created_at']
    change_list_template = 'admin/procurement/p2p_change_list.html'

    fieldsets = (
        ('Identity', {
            'fields': ('organization', 'pr_number', 'uuid')
        }),
        ('Request Details', {
            'fields': ('requested_by', 'department', 'cost_center', 'description')
        }),
        ('Content', {
            'fields': ('supplier_suggested', 'category')
        }),
        ('Financial', {
            'fields': ('estimated_amount', 'currency', 'budget_code')
        }),
        ('Status & Workflow', {
            'fields': ('status', 'priority')
        }),
        ('Key Dates', {
            'fields': ('created_date', 'submitted_date', 'approval_date', 'rejection_date')
        }),
        ('Approval', {
            'fields': ('approved_by', 'rejection_reason')
        }),
        ('Metadata', {
            'fields': ('upload_batch', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def approval_status_badge(self, obj):
        """Display approval status with color-coded badge."""
        colors = {
            'draft': '#6b7280',
            'pending_approval': '#f59e0b',
            'approved': '#10b981',
            'rejected': '#ef4444',
            'converted_to_po': '#3b82f6',
            'cancelled': '#9ca3af',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 600;">{}</span>',
            color, obj.get_status_display()
        )
    approval_status_badge.short_description = 'Status'

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'organization', 'supplier_suggested', 'category', 'requested_by', 'approved_by'
        )
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            return qs.filter(organization=request.user.profile.organization)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter FK choices by organization to prevent IDOR."""
        if not request.user.is_superuser and hasattr(request.user, 'profile'):
            user_org = request.user.profile.organization
            if db_field.name == 'supplier_suggested':
                kwargs['queryset'] = Supplier.objects.filter(organization=user_org)
            elif db_field.name == 'category':
                kwargs['queryset'] = Category.objects.filter(organization=user_org)
            elif db_field.name in ['requested_by', 'approved_by']:
                kwargs['queryset'] = User.objects.filter(profile__organization=user_org)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def _process_p2p_import(self, rows, organization, batch_id, user):
        """Process PR import from CSV rows."""
        stats = {'successful': 0, 'failed': 0, 'skipped': 0, 'errors': []}

        for row_num, row in enumerate(rows, start=2):
            try:
                pr_number = row.get('pr_number', '').strip()
                if not pr_number:
                    stats['failed'] += 1
                    continue

                # Skip duplicates
                if PurchaseRequisition.objects.filter(
                    organization=organization, pr_number=pr_number
                ).exists():
                    stats['skipped'] += 1
                    continue

                estimated_amount = self._parse_decimal(row.get('estimated_amount', ''))
                if estimated_amount is None:
                    stats['failed'] += 1
                    continue

                with transaction.atomic():
                    supplier = self._get_or_create_supplier(
                        row.get('supplier_suggested', ''), organization
                    )
                    category = self._get_or_create_category(
                        row.get('category', ''), organization
                    )

                    PurchaseRequisition.objects.create(
                        organization=organization,
                        pr_number=pr_number,
                        department=row.get('department', '').strip(),
                        cost_center=row.get('cost_center', '').strip(),
                        description=row.get('description', '').strip(),
                        estimated_amount=estimated_amount,
                        currency=row.get('currency', 'USD').strip() or 'USD',
                        budget_code=row.get('budget_code', '').strip(),
                        status=row.get('status', 'draft').strip() or 'draft',
                        priority=row.get('priority', 'medium').strip() or 'medium',
                        created_date=self._parse_date(row.get('created_date', '')) or datetime.now().date(),
                        submitted_date=self._parse_date(row.get('submitted_date', '')),
                        approval_date=self._parse_date(row.get('approval_date', '')),
                        supplier_suggested=supplier,
                        category=category,
                        upload_batch=batch_id
                    )

                stats['successful'] += 1
            except Exception:
                stats['failed'] += 1

        return stats

    def _get_template_example_row(self):
        return [
            'PR-2024-001', 'Engineering', 'CC-1001', 'Office supplies', '5000.00',
            'USD', 'BUD-2024', 'pending_approval', 'medium', '2024-01-15',
            '2024-01-16', '', 'ABC Supplies', 'Office Equipment'
        ]

    def _parse_date(self, date_str):
        if not date_str or date_str.strip() == '':
            return None
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _parse_decimal(self, value_str):
        if not value_str or value_str.strip() == '':
            return Decimal('0')
        try:
            return Decimal(value_str.strip().replace('$', '').replace(',', ''))
        except InvalidOperation:
            return None

    def _get_or_create_supplier(self, name, organization):
        if not name or name.strip() == '':
            return None
        supplier, _ = Supplier.objects.get_or_create(
            organization=organization, name__iexact=name.strip(),
            defaults={'name': name.strip()}
        )
        return supplier

    def _get_or_create_category(self, name, organization):
        if not name or name.strip() == '':
            return None
        category, _ = Category.objects.get_or_create(
            organization=organization, name__iexact=name.strip(),
            defaults={'name': name.strip()}
        )
        return category


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(P2PImportMixin, admin.ModelAdmin):
    """Admin for Purchase Orders - P2P Cycle Analytics."""

    p2p_doc_type = 'po'
    p2p_import_fields = [
        'po_number', 'supplier_name', 'total_amount', 'currency', 'tax_amount',
        'freight_amount', 'status', 'category', 'created_date', 'approval_date',
        'sent_date', 'required_date', 'promised_date', 'pr_number', 'is_contract_backed'
    ]

    list_display = [
        'po_number', 'organization', 'supplier', 'status', 'total_amount',
        'is_contract_backed', 'created_date', 'po_status_badge'
    ]
    list_filter = ['status', 'is_contract_backed', 'organization', 'supplier', 'created_date']
    search_fields = ['po_number', 'supplier__name']
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    date_hierarchy = 'created_date'
    raw_id_fields = ['supplier', 'category', 'contract', 'requisition', 'created_by', 'approved_by']
    ordering = ['-created_date', '-created_at']
    change_list_template = 'admin/procurement/p2p_change_list.html'

    fieldsets = (
        ('Identity', {
            'fields': ('organization', 'po_number', 'uuid')
        }),
        ('Supplier & Category', {
            'fields': ('supplier', 'category')
        }),
        ('Financial', {
            'fields': ('total_amount', 'currency', 'tax_amount', 'freight_amount')
        }),
        ('Contract Linkage', {
            'fields': ('contract', 'is_contract_backed')
        }),
        ('Status & Workflow', {
            'fields': ('status',)
        }),
        ('Key Dates', {
            'fields': ('created_date', 'approval_date', 'sent_date', 'required_date', 'promised_date')
        }),
        ('Approvals', {
            'fields': ('created_by', 'approved_by')
        }),
        ('Amendment Tracking', {
            'fields': ('original_amount', 'amendment_count')
        }),
        ('PR Linkage', {
            'fields': ('requisition',)
        }),
        ('Metadata', {
            'fields': ('upload_batch', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def po_status_badge(self, obj):
        """Display PO status with color-coded badge."""
        colors = {
            'draft': '#6b7280',
            'pending_approval': '#f59e0b',
            'approved': '#10b981',
            'sent_to_supplier': '#3b82f6',
            'acknowledged': '#6366f1',
            'partially_received': '#8b5cf6',
            'fully_received': '#14b8a6',
            'closed': '#059669',
            'cancelled': '#9ca3af',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 600;">{}</span>',
            color, obj.get_status_display()
        )
    po_status_badge.short_description = 'Status'

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'organization', 'supplier', 'category', 'contract', 'requisition',
            'created_by', 'approved_by'
        )
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            return qs.filter(organization=request.user.profile.organization)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter FK choices by organization to prevent IDOR."""
        if not request.user.is_superuser and hasattr(request.user, 'profile'):
            user_org = request.user.profile.organization
            if db_field.name == 'supplier':
                kwargs['queryset'] = Supplier.objects.filter(organization=user_org)
            elif db_field.name == 'category':
                kwargs['queryset'] = Category.objects.filter(organization=user_org)
            elif db_field.name == 'contract':
                kwargs['queryset'] = Contract.objects.filter(organization=user_org)
            elif db_field.name == 'requisition':
                kwargs['queryset'] = PurchaseRequisition.objects.filter(organization=user_org)
            elif db_field.name in ['created_by', 'approved_by']:
                kwargs['queryset'] = User.objects.filter(profile__organization=user_org)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def _process_p2p_import(self, rows, organization, batch_id, user):
        """Process PO import from CSV rows."""
        stats = {'successful': 0, 'failed': 0, 'skipped': 0, 'errors': []}

        for row_num, row in enumerate(rows, start=2):
            try:
                po_number = row.get('po_number', '').strip()
                if not po_number:
                    stats['failed'] += 1
                    continue

                # Skip duplicates
                if PurchaseOrder.objects.filter(
                    organization=organization, po_number=po_number
                ).exists():
                    stats['skipped'] += 1
                    continue

                supplier_name = row.get('supplier_name', '').strip()
                if not supplier_name:
                    stats['failed'] += 1
                    continue

                total_amount = self._parse_decimal(row.get('total_amount', ''))
                if total_amount is None:
                    stats['failed'] += 1
                    continue

                with transaction.atomic():
                    supplier = self._get_or_create_supplier(supplier_name, organization)
                    category = self._get_or_create_category(
                        row.get('category', ''), organization
                    )

                    # Link to existing PR if provided
                    requisition = None
                    pr_number = row.get('pr_number', '').strip()
                    if pr_number:
                        requisition = PurchaseRequisition.objects.filter(
                            organization=organization, pr_number=pr_number
                        ).first()

                    is_contract_backed = row.get('is_contract_backed', '').strip().lower() in ('true', 'yes', '1')

                    PurchaseOrder.objects.create(
                        organization=organization,
                        po_number=po_number,
                        supplier=supplier,
                        category=category,
                        total_amount=total_amount,
                        currency=row.get('currency', 'USD').strip() or 'USD',
                        tax_amount=self._parse_decimal(row.get('tax_amount', '')) or Decimal('0'),
                        freight_amount=self._parse_decimal(row.get('freight_amount', '')) or Decimal('0'),
                        status=row.get('status', 'draft').strip() or 'draft',
                        created_date=self._parse_date(row.get('created_date', '')) or datetime.now().date(),
                        approval_date=self._parse_date(row.get('approval_date', '')),
                        sent_date=self._parse_date(row.get('sent_date', '')),
                        required_date=self._parse_date(row.get('required_date', '')),
                        promised_date=self._parse_date(row.get('promised_date', '')),
                        requisition=requisition,
                        is_contract_backed=is_contract_backed,
                        original_amount=total_amount,
                        upload_batch=batch_id
                    )

                stats['successful'] += 1
            except Exception:
                stats['failed'] += 1

        return stats

    def _get_template_example_row(self):
        return [
            'PO-2024-001', 'ABC Supplies', '25000.00', 'USD', '2000.00',
            '500.00', 'approved', 'Office Equipment', '2024-01-20', '2024-01-21',
            '2024-01-22', '2024-02-15', '2024-02-10', 'PR-2024-001', 'false'
        ]

    def _parse_date(self, date_str):
        if not date_str or date_str.strip() == '':
            return None
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _parse_decimal(self, value_str):
        if not value_str or value_str.strip() == '':
            return Decimal('0')
        try:
            return Decimal(value_str.strip().replace('$', '').replace(',', ''))
        except InvalidOperation:
            return None

    def _get_or_create_supplier(self, name, organization):
        if not name or name.strip() == '':
            return None
        supplier, _ = Supplier.objects.get_or_create(
            organization=organization, name__iexact=name.strip(),
            defaults={'name': name.strip()}
        )
        return supplier

    def _get_or_create_category(self, name, organization):
        if not name or name.strip() == '':
            return None
        category, _ = Category.objects.get_or_create(
            organization=organization, name__iexact=name.strip(),
            defaults={'name': name.strip()}
        )
        return category


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(P2PImportMixin, admin.ModelAdmin):
    """Admin for Goods Receipts - 3-Way Matching."""

    p2p_doc_type = 'gr'
    p2p_import_fields = [
        'gr_number', 'po_number', 'received_date', 'quantity_ordered',
        'quantity_received', 'quantity_accepted', 'amount_received', 'status', 'inspection_notes'
    ]

    list_display = [
        'gr_number', 'organization', 'purchase_order', 'status',
        'quantity_received', 'received_date', 'variance_badge'
    ]
    list_filter = ['status', 'organization', 'received_date']
    search_fields = ['gr_number', 'purchase_order__po_number']
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    date_hierarchy = 'received_date'
    raw_id_fields = ['purchase_order', 'received_by']
    ordering = ['-received_date', '-created_at']
    change_list_template = 'admin/procurement/p2p_change_list.html'

    fieldsets = (
        ('Identity', {
            'fields': ('organization', 'gr_number', 'uuid')
        }),
        ('PO Linkage', {
            'fields': ('purchase_order',)
        }),
        ('Receipt Details', {
            'fields': ('received_date', 'received_by')
        }),
        ('Quantities', {
            'fields': ('quantity_ordered', 'quantity_received', 'quantity_accepted', 'amount_received')
        }),
        ('Status', {
            'fields': ('status', 'inspection_notes')
        }),
        ('Metadata', {
            'fields': ('upload_batch', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def variance_badge(self, obj):
        """Display variance with color-coded badge."""
        variance = obj.quantity_variance
        if abs(variance) <= 1:
            color = '#10b981'  # Green - good
            text = 'OK'
        elif abs(variance) <= 5:
            color = '#f59e0b'  # Amber - warning
            text = f'{variance:+.1f}%'
        else:
            color = '#ef4444'  # Red - critical
            text = f'{variance:+.1f}%'

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 600;">{}</span>',
            color, text
        )
    variance_badge.short_description = 'Variance'

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'organization', 'purchase_order', 'purchase_order__supplier', 'received_by'
        )
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            return qs.filter(organization=request.user.profile.organization)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter FK choices by organization to prevent IDOR."""
        if not request.user.is_superuser and hasattr(request.user, 'profile'):
            user_org = request.user.profile.organization
            if db_field.name == 'purchase_order':
                kwargs['queryset'] = PurchaseOrder.objects.filter(organization=user_org)
            elif db_field.name == 'received_by':
                kwargs['queryset'] = User.objects.filter(profile__organization=user_org)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def _process_p2p_import(self, rows, organization, batch_id, user):
        """Process GR import from CSV rows."""
        stats = {'successful': 0, 'failed': 0, 'skipped': 0, 'errors': []}

        for row_num, row in enumerate(rows, start=2):
            try:
                gr_number = row.get('gr_number', '').strip()
                if not gr_number:
                    stats['failed'] += 1
                    continue

                # Skip duplicates
                if GoodsReceipt.objects.filter(
                    organization=organization, gr_number=gr_number
                ).exists():
                    stats['skipped'] += 1
                    continue

                # Find linked PO
                po_number = row.get('po_number', '').strip()
                if not po_number:
                    stats['failed'] += 1
                    continue

                purchase_order = PurchaseOrder.objects.filter(
                    organization=organization, po_number=po_number
                ).first()

                if not purchase_order:
                    stats['failed'] += 1
                    continue

                received_date = self._parse_date(row.get('received_date', ''))
                if not received_date:
                    stats['failed'] += 1
                    continue

                quantity_received = self._parse_decimal(row.get('quantity_received', ''))
                if quantity_received is None:
                    stats['failed'] += 1
                    continue

                with transaction.atomic():
                    GoodsReceipt.objects.create(
                        organization=organization,
                        gr_number=gr_number,
                        purchase_order=purchase_order,
                        received_date=received_date,
                        quantity_ordered=self._parse_decimal(row.get('quantity_ordered', '')) or quantity_received,
                        quantity_received=quantity_received,
                        quantity_accepted=self._parse_decimal(row.get('quantity_accepted', '')) or quantity_received,
                        amount_received=self._parse_decimal(row.get('amount_received', '')) or Decimal('0'),
                        status=row.get('status', 'received').strip() or 'received',
                        inspection_notes=row.get('inspection_notes', '').strip(),
                        upload_batch=batch_id
                    )

                stats['successful'] += 1
            except Exception:
                stats['failed'] += 1

        return stats

    def _get_template_example_row(self):
        return [
            'GR-2024-001', 'PO-2024-001', '2024-02-10', '100',
            '98', '98', '24500.00', 'received', 'Minor packaging damage, items OK'
        ]

    def _parse_date(self, date_str):
        if not date_str or date_str.strip() == '':
            return None
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _parse_decimal(self, value_str):
        if not value_str or value_str.strip() == '':
            return Decimal('0')
        try:
            return Decimal(value_str.strip().replace('$', '').replace(',', ''))
        except InvalidOperation:
            return None


@admin.register(Invoice)
class InvoiceAdmin(P2PImportMixin, admin.ModelAdmin):
    """Admin for Invoices - AP Aging & 3-Way Matching."""

    p2p_doc_type = 'invoice'
    p2p_import_fields = [
        'invoice_number', 'supplier_name', 'invoice_amount', 'invoice_date', 'due_date',
        'currency', 'tax_amount', 'net_amount', 'payment_terms', 'payment_terms_days',
        'status', 'match_status', 'po_number', 'gr_number', 'received_date',
        'approved_date', 'paid_date', 'has_exception', 'exception_type',
        'exception_amount', 'exception_notes'
    ]

    list_display = [
        'invoice_number', 'organization', 'supplier', 'status', 'match_status',
        'invoice_amount', 'due_date', 'aging_badge', 'exception_badge'
    ]
    list_filter = [
        'status', 'match_status', 'has_exception', 'exception_type',
        'organization', 'supplier', 'invoice_date', 'due_date'
    ]
    search_fields = ['invoice_number', 'supplier__name']
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    date_hierarchy = 'invoice_date'
    raw_id_fields = ['supplier', 'purchase_order', 'goods_receipt', 'exception_resolved_by']
    ordering = ['-invoice_date', '-created_at']
    change_list_template = 'admin/procurement/p2p_change_list.html'

    fieldsets = (
        ('Identity', {
            'fields': ('organization', 'invoice_number', 'supplier', 'uuid')
        }),
        ('Linkage (3-Way Match)', {
            'fields': ('purchase_order', 'goods_receipt')
        }),
        ('Financial', {
            'fields': ('invoice_amount', 'tax_amount', 'net_amount', 'currency')
        }),
        ('Payment Terms', {
            'fields': ('payment_terms', 'payment_terms_days', 'discount_percent', 'discount_days')
        }),
        ('Key Dates', {
            'fields': ('invoice_date', 'received_date', 'due_date', 'approved_date', 'paid_date')
        }),
        ('Status & Matching', {
            'fields': ('status', 'match_status')
        }),
        ('Exception Tracking', {
            'fields': (
                'has_exception', 'exception_type', 'exception_amount',
                'exception_notes', 'exception_resolved', 'exception_resolved_by',
                'exception_resolved_at'
            )
        }),
        ('Hold', {
            'fields': ('hold_reason',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('upload_batch', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def aging_badge(self, obj):
        """Display aging bucket with color-coded badge."""
        bucket = obj.aging_bucket
        colors = {
            'current': '#10b981',  # Green
            '31-60': '#f59e0b',    # Amber
            '61-90': '#f97316',    # Orange
            '90+': '#ef4444',      # Red
        }
        labels = {
            'current': 'Current',
            '31-60': '31-60 Days',
            '61-90': '61-90 Days',
            '90+': '90+ Days',
        }
        color = colors.get(bucket, '#6b7280')
        label = labels.get(bucket, bucket)

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 600;">{}</span>',
            color, label
        )
    aging_badge.short_description = 'Aging'

    def exception_badge(self, obj):
        """Display exception status with color-coded badge."""
        if not obj.has_exception:
            return format_html(
                '<span style="background-color: #10b981; color: white; padding: 3px 8px; '
                'border-radius: 4px; font-size: 11px; font-weight: 600;">✓</span>'
            )

        if obj.exception_resolved:
            color = '#6366f1'  # Indigo - resolved
            text = 'Resolved'
        else:
            color = '#ef4444'  # Red - open
            text = obj.get_exception_type_display() if obj.exception_type else 'Exception'

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 600;">{}</span>',
            color, text
        )
    exception_badge.short_description = 'Exception'

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'organization', 'supplier', 'purchase_order', 'goods_receipt',
            'exception_resolved_by'
        )
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            return qs.filter(organization=request.user.profile.organization)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter FK choices by organization to prevent IDOR."""
        if not request.user.is_superuser and hasattr(request.user, 'profile'):
            user_org = request.user.profile.organization
            if db_field.name == 'supplier':
                kwargs['queryset'] = Supplier.objects.filter(organization=user_org)
            elif db_field.name == 'purchase_order':
                kwargs['queryset'] = PurchaseOrder.objects.filter(organization=user_org)
            elif db_field.name == 'goods_receipt':
                kwargs['queryset'] = GoodsReceipt.objects.filter(organization=user_org)
            elif db_field.name == 'exception_resolved_by':
                kwargs['queryset'] = User.objects.filter(profile__organization=user_org)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def _process_p2p_import(self, rows, organization, batch_id, user):
        """Process Invoice import from CSV rows."""
        stats = {'successful': 0, 'failed': 0, 'skipped': 0, 'errors': []}

        for row_num, row in enumerate(rows, start=2):
            try:
                invoice_number = row.get('invoice_number', '').strip()
                if not invoice_number:
                    stats['failed'] += 1
                    continue

                # Skip duplicates
                if Invoice.objects.filter(
                    organization=organization, invoice_number=invoice_number
                ).exists():
                    stats['skipped'] += 1
                    continue

                supplier_name = row.get('supplier_name', '').strip()
                if not supplier_name:
                    stats['failed'] += 1
                    continue

                invoice_amount = self._parse_decimal(row.get('invoice_amount', ''))
                if invoice_amount is None:
                    stats['failed'] += 1
                    continue

                invoice_date = self._parse_date(row.get('invoice_date', ''))
                if not invoice_date:
                    stats['failed'] += 1
                    continue

                due_date = self._parse_date(row.get('due_date', ''))
                if not due_date:
                    stats['failed'] += 1
                    continue

                with transaction.atomic():
                    supplier = self._get_or_create_supplier(supplier_name, organization)

                    # Link to existing PO if provided
                    purchase_order = None
                    po_number = row.get('po_number', '').strip()
                    if po_number:
                        purchase_order = PurchaseOrder.objects.filter(
                            organization=organization, po_number=po_number
                        ).first()

                    # Link to existing GR if provided
                    goods_receipt = None
                    gr_number = row.get('gr_number', '').strip()
                    if gr_number:
                        goods_receipt = GoodsReceipt.objects.filter(
                            organization=organization, gr_number=gr_number
                        ).first()

                    has_exception = row.get('has_exception', '').strip().lower() in ('true', 'yes', '1')

                    Invoice.objects.create(
                        organization=organization,
                        invoice_number=invoice_number,
                        supplier=supplier,
                        invoice_amount=invoice_amount,
                        invoice_date=invoice_date,
                        due_date=due_date,
                        currency=row.get('currency', 'USD').strip() or 'USD',
                        tax_amount=self._parse_decimal(row.get('tax_amount', '')) or Decimal('0'),
                        net_amount=self._parse_decimal(row.get('net_amount', '')) or invoice_amount,
                        payment_terms=row.get('payment_terms', '').strip(),
                        payment_terms_days=int(row.get('payment_terms_days', '30') or '30'),
                        status=row.get('status', 'received').strip() or 'received',
                        match_status=row.get('match_status', 'unmatched').strip() or 'unmatched',
                        purchase_order=purchase_order,
                        goods_receipt=goods_receipt,
                        received_date=self._parse_date(row.get('received_date', '')) or invoice_date,
                        approved_date=self._parse_date(row.get('approved_date', '')),
                        paid_date=self._parse_date(row.get('paid_date', '')),
                        has_exception=has_exception,
                        exception_type=row.get('exception_type', '').strip() if has_exception else '',
                        exception_amount=self._parse_decimal(row.get('exception_amount', '')) if has_exception else None,
                        exception_notes=row.get('exception_notes', '').strip() if has_exception else '',
                        upload_batch=batch_id
                    )

                stats['successful'] += 1
            except Exception:
                stats['failed'] += 1

        return stats

    def _get_template_example_row(self):
        return [
            'INV-2024-001', 'ABC Supplies', '24500.00', '2024-02-15', '2024-03-15',
            'USD', '2000.00', '22500.00', 'Net 30', '30',
            'received', '3way_matched', 'PO-2024-001', 'GR-2024-001', '2024-02-16',
            '', '', 'false', '', '', ''
        ]

    def _parse_date(self, date_str):
        if not date_str or date_str.strip() == '':
            return None
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _parse_decimal(self, value_str):
        if not value_str or value_str.strip() == '':
            return Decimal('0')
        try:
            return Decimal(value_str.strip().replace('$', '').replace(',', ''))
        except InvalidOperation:
            return None

    def _get_or_create_supplier(self, name, organization):
        if not name or name.strip() == '':
            return None
        supplier, _ = Supplier.objects.get_or_create(
            organization=organization, name__iexact=name.strip(),
            defaults={'name': name.strip()}
        )
        return supplier
