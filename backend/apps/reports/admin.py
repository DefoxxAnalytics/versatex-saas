"""
Django Admin configuration for the reports module.
"""
from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Admin interface for Report model."""

    list_display = [
        'name', 'report_type', 'report_format', 'status_badge',
        'organization', 'created_by', 'created_at', 'generated_at'
    ]
    list_filter = [
        'status', 'report_type', 'report_format', 'organization',
        'is_scheduled', 'created_at'
    ]
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'generated_at',
        'file_size', 'summary_data_preview'
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'description', 'report_type', 'report_format')
        }),
        ('Organization & Ownership', {
            'fields': ('organization', 'created_by')
        }),
        ('Date Range', {
            'fields': ('period_start', 'period_end')
        }),
        ('Filters & Parameters', {
            'fields': ('filters', 'parameters'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'error_message', 'file_path', 'file_size')
        }),
        ('Generated Data', {
            'fields': ('summary_data_preview',),
            'classes': ('collapse',)
        }),
        ('Sharing', {
            'fields': ('is_public', 'shared_with')
        }),
        ('Scheduling', {
            'fields': ('is_scheduled', 'schedule_frequency', 'next_run', 'last_run')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'generated_at')
        }),
    )

    filter_horizontal = ['shared_with']

    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'draft': '#6b7280',      # gray
            'generating': '#f59e0b',  # amber
            'completed': '#10b981',   # green
            'failed': '#ef4444',      # red
            'scheduled': '#3b82f6',   # blue
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def summary_data_preview(self, obj):
        """Show truncated preview of summary_data."""
        if not obj.summary_data:
            return "No data"
        import json
        preview = json.dumps(obj.summary_data, indent=2)[:2000]
        if len(json.dumps(obj.summary_data)) > 2000:
            preview += "\n... (truncated)"
        return format_html('<pre style="max-height: 400px; overflow: auto;">{}</pre>', preview)
    summary_data_preview.short_description = 'Summary Data (Preview)'

    def get_queryset(self, request):
        """Optimize queryset with select_related and org filtering."""
        qs = super().get_queryset(request).select_related(
            'organization', 'created_by'
        )
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            return qs.filter(organization=request.user.profile.organization)
        return qs.none()

    def formfield_for_many_to_many(self, db_field, request, **kwargs):
        """Filter M2M choices by organization to prevent data leakage."""
        if db_field.name == 'shared_with':
            if not request.user.is_superuser and hasattr(request.user, 'profile'):
                kwargs['queryset'] = User.objects.filter(
                    profile__organization=request.user.profile.organization
                )
        return super().formfield_for_many_to_many(db_field, request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter FK choices by organization to prevent IDOR."""
        if not request.user.is_superuser and hasattr(request.user, 'profile'):
            user_org = request.user.profile.organization
            if db_field.name == 'created_by':
                kwargs['queryset'] = User.objects.filter(profile__organization=user_org)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    actions = ['mark_completed', 'mark_failed', 'regenerate']

    def mark_completed(self, request, queryset):
        """Mark selected reports as completed."""
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} reports marked as completed.')
    mark_completed.short_description = 'Mark as completed'

    def mark_failed(self, request, queryset):
        """Mark selected reports as failed."""
        updated = queryset.update(status='failed')
        self.message_user(request, f'{updated} reports marked as failed.')
    mark_failed.short_description = 'Mark as failed'

    def regenerate(self, request, queryset):
        """Regenerate selected reports (rate limited to 100)."""
        from .tasks import generate_report_async
        # Rate limit to prevent abuse
        MAX_BULK_REGENERATE = 100
        limited_queryset = queryset[:MAX_BULK_REGENERATE]
        count = 0
        for report in limited_queryset:
            generate_report_async.delay(str(report.pk))
            count += 1
        if queryset.count() > MAX_BULK_REGENERATE:
            self.message_user(
                request,
                f'{count} reports queued for regeneration (limited to {MAX_BULK_REGENERATE}).',
                level='warning'
            )
        else:
            self.message_user(request, f'{count} reports queued for regeneration.')
    regenerate.short_description = 'Regenerate reports'
