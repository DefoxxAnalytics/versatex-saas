"""
Django admin configuration for authentication

Optimized for query efficiency:
- Cached admin_org_ids to avoid repeated permission queries
- Annotated counts to eliminate N+1 queries in list_display
- select_related/prefetch_related for foreign key optimization
"""
import io
import json
import zipfile

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html

from .admin_export import build_org_zip
from .models import Organization, UserProfile, AuditLog, UserOrganizationMembership
from .utils import log_action


@admin.action(description='Export seeded dataset as ZIP (demo orgs only)')
def export_demo_datasets(modeladmin, request, queryset):
    """Bundle selected demo orgs into a single ZIP of per-slug folders."""
    if not request.user.is_superuser:
        messages.error(request, 'Exporting datasets requires superuser privileges.')
        return

    non_demo = list(queryset.filter(is_demo=False).values_list('name', flat=True))
    if non_demo:
        messages.error(
            request,
            f'Cannot export non-demo organization(s): {", ".join(non_demo)}. '
            f'Toggle is_demo=True on the org first, or remove from selection.',
        )
        return

    outer = io.BytesIO()
    with zipfile.ZipFile(outer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        for org in queryset:
            payload, counts = build_org_zip(org)
            zf.writestr(f'{org.slug}-dataset.zip', payload)
            log_action(
                user=request.user,
                action='export',
                resource='organization_dataset',
                resource_id=org.slug,
                details={
                    'organization_name': org.name,
                    'is_demo': org.is_demo,
                    'row_counts': json.dumps(counts, sort_keys=True),
                    'zip_bytes': len(payload),
                },
                request=request,
            )

    response = HttpResponse(outer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = (
        f'attachment; filename="seeded-datasets-{timezone.now():%Y%m%d-%H%M%S}.zip"'
    )
    return response


# =============================================================================
# Helper Functions
# =============================================================================

def get_admin_org_ids(request):
    """
    Cache admin org IDs on request to avoid repeated queries.

    Returns:
        None: For superusers (no filtering needed)
        list: List of organization IDs where user is admin
        []: Empty list if user has no admin access
    """
    if not hasattr(request, '_admin_org_ids_cache'):
        if request.user.is_superuser:
            request._admin_org_ids_cache = None  # No filtering needed
        elif hasattr(request.user, 'profile'):
            request._admin_org_ids_cache = list(
                UserOrganizationMembership.objects.filter(
                    user=request.user,
                    role='admin',
                    is_active=True
                ).values_list('organization_id', flat=True)
            )
        else:
            request._admin_org_ids_cache = []
    return request._admin_org_ids_cache


# =============================================================================
# Bulk Actions
# =============================================================================

@admin.action(description="Activate selected memberships")
def activate_memberships(modeladmin, request, queryset):
    """Bulk activate selected memberships (with org validation)."""
    admin_org_ids = get_admin_org_ids(request)
    if admin_org_ids is not None:  # Non-superuser
        queryset = queryset.filter(organization_id__in=admin_org_ids)
    queryset.update(is_active=True)


@admin.action(description="Deactivate selected memberships")
def deactivate_memberships(modeladmin, request, queryset):
    """Bulk deactivate selected memberships (with org validation)."""
    admin_org_ids = get_admin_org_ids(request)
    if admin_org_ids is not None:  # Non-superuser
        queryset = queryset.filter(organization_id__in=admin_org_ids)
    queryset.update(is_active=False)


@admin.action(description="Set role to Admin")
def set_role_admin(modeladmin, request, queryset):
    """Bulk set role to admin (with org validation)."""
    admin_org_ids = get_admin_org_ids(request)
    if admin_org_ids is not None:  # Non-superuser
        queryset = queryset.filter(organization_id__in=admin_org_ids)
    queryset.update(role='admin')


@admin.action(description="Set role to Manager")
def set_role_manager(modeladmin, request, queryset):
    """Bulk set role to manager (with org validation)."""
    admin_org_ids = get_admin_org_ids(request)
    if admin_org_ids is not None:  # Non-superuser
        queryset = queryset.filter(organization_id__in=admin_org_ids)
    queryset.update(role='manager')


@admin.action(description="Set role to Viewer")
def set_role_viewer(modeladmin, request, queryset):
    """Bulk set role to viewer (with org validation)."""
    admin_org_ids = get_admin_org_ids(request)
    if admin_org_ids is not None:  # Non-superuser
        queryset = queryset.filter(organization_id__in=admin_org_ids)
    queryset.update(role='viewer')


# =============================================================================
# Inline Admin Classes
# =============================================================================

class UserOrganizationMembershipInline(admin.TabularInline):
    """
    Inline admin for managing user memberships from User admin.

    Optimizations:
    - Uses cached get_admin_org_ids() to avoid repeated permission queries
    - select_related('organization') for FK optimization
    """
    model = UserOrganizationMembership
    fk_name = 'user'
    extra = 0
    fields = ['organization', 'role', 'is_primary', 'is_active', 'created_at']
    readonly_fields = ['created_at']
    autocomplete_fields = ['organization']

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('organization')
        admin_org_ids = get_admin_org_ids(request)

        if admin_org_ids is None:  # Superuser
            return qs
        if admin_org_ids:
            return qs.filter(organization_id__in=admin_org_ids)
        return qs.none()


class UserProfileInline(admin.StackedInline):
    """Inline for UserProfile on User admin."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ['organization', 'role', 'phone', 'department', 'is_active']


# =============================================================================
# User Admin
# =============================================================================

# Unregister the default User admin and re-register with inlines
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Extended User admin with profile and memberships inlines.

    Optimizations:
    - select_related for profile and organization to avoid N+1 on get_organization
    - Annotated membership count to avoid N+1 query per row
    """
    inlines = [UserProfileInline, UserOrganizationMembershipInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'get_organization', 'membership_count']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Optimize: prefetch profile and organization in single query
        qs = qs.select_related('profile', 'profile__organization')
        # Annotate membership count to avoid N+1
        qs = qs.annotate(
            _membership_count=Count(
                'organization_memberships',
                filter=Q(organization_memberships__is_active=True)
            )
        )
        return qs

    def get_organization(self, obj):
        """Get user's primary organization (optimized via select_related)."""
        if hasattr(obj, 'profile') and obj.profile:
            return obj.profile.organization.name if obj.profile.organization else '-'
        return '-'
    get_organization.short_description = 'Organization'
    get_organization.admin_order_field = 'profile__organization__name'

    def membership_count(self, obj):
        """Get count of organizations user belongs to (optimized via annotation)."""
        return getattr(obj, '_membership_count', 0)
    membership_count.short_description = 'Orgs'
    membership_count.admin_order_field = '_membership_count'


# =============================================================================
# Organization Admin
# =============================================================================

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """
    Organization admin with optimized member count.

    Optimizations:
    - Annotated member_count to avoid N+1 query per row
    """
    list_display = ['name', 'slug', 'is_active', 'demo_badge', 'member_count', 'created_at']
    list_filter = ['is_active', 'is_demo', 'created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    actions = [export_demo_datasets]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            actions.pop('export_demo_datasets', None)
        return actions

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'is_active', 'is_demo')
        }),
        ('Branding', {
            'fields': ('logo', 'primary_color', 'secondary_color', 'website', 'report_footer'),
            'classes': ('collapse',)
        }),
        ('Savings Configuration', {
            'fields': ('savings_config',),
            'classes': ('collapse',),
            'description': 'Configure industry-benchmark savings rates for AI Insights. '
                          'Use benchmark_profile (conservative/moderate/aggressive) or set custom rates.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate member count to avoid N+1
        qs = qs.annotate(
            _member_count=Count(
                'user_memberships',
                filter=Q(user_memberships__is_active=True)
            )
        )
        return qs

    def member_count(self, obj):
        """Return count of active members (optimized via annotation)."""
        return getattr(obj, '_member_count', 0)
    member_count.short_description = 'Members'
    member_count.admin_order_field = '_member_count'

    def demo_badge(self, obj):
        """Amber DEMO chip when the org holds synthetic data."""
        if obj.is_demo:
            return format_html(
                '<span style="display:inline-block;padding:2px 8px;'
                'background:#fef3c7;color:#92400e;border-radius:4px;'
                'font-size:11px;font-weight:600;letter-spacing:0.02em;">DEMO</span>'
            )
        return format_html('<span style="color:#9ca3af;">—</span>')
    demo_badge.short_description = 'Demo'
    demo_badge.admin_order_field = 'is_demo'


# =============================================================================
# User Profile Admin
# =============================================================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    User profile admin with optimized membership count.

    Optimizations:
    - select_related for user and organization
    - Annotated membership_count to avoid N+1 query per row
    """
    list_display = ['user', 'organization', 'role', 'membership_count', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'organization', 'created_at']
    search_fields = ['user__username', 'user__email', 'organization__name']
    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Optimize: prefetch related objects
        qs = qs.select_related('user', 'organization')
        # Annotate membership count to avoid N+1
        qs = qs.annotate(
            _membership_count=Count(
                'user__organization_memberships',
                filter=Q(user__organization_memberships__is_active=True)
            )
        )
        # Filter by organization for non-superusers
        if not request.user.is_superuser:
            if hasattr(request.user, 'profile'):
                qs = qs.filter(organization=request.user.profile.organization)
            else:
                qs = qs.none()
        return qs

    def membership_count(self, obj):
        """Return count of organizations this user belongs to (optimized via annotation)."""
        return getattr(obj, '_membership_count', 0)
    membership_count.short_description = 'Orgs'
    membership_count.admin_order_field = '_membership_count'


# =============================================================================
# Audit Log Admin
# =============================================================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Audit log admin (read-only except for superuser delete)."""
    list_display = ['user', 'organization', 'action', 'resource', 'timestamp']
    list_filter = ['action', 'organization', 'timestamp']
    search_fields = ['user__username', 'resource', 'resource_id']
    readonly_fields = ['user', 'organization', 'action', 'resource', 'resource_id',
                      'details', 'ip_address', 'user_agent', 'timestamp']

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('user', 'organization')
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            return qs.filter(organization=request.user.profile.organization)
        return qs.none()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# =============================================================================
# User Organization Membership Admin
# =============================================================================

@admin.register(UserOrganizationMembership)
class UserOrganizationMembershipAdmin(admin.ModelAdmin):
    """
    Admin for managing organization memberships directly.

    Optimizations:
    - Uses cached get_admin_org_ids() to avoid repeated permission queries
    - select_related for all FK fields
    - Bulk actions for common operations
    """
    list_display = ['user', 'organization', 'role', 'is_primary', 'is_active', 'created_at']
    list_filter = ['role', 'is_primary', 'is_active', 'organization', 'created_at']
    search_fields = ['user__username', 'user__email', 'organization__name']
    autocomplete_fields = ['user', 'organization']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['invited_by']
    list_editable = ['role', 'is_primary', 'is_active']
    actions = [activate_memberships, deactivate_memberships, set_role_admin, set_role_manager, set_role_viewer]

    fieldsets = (
        (None, {
            'fields': ('user', 'organization', 'role')
        }),
        ('Status', {
            'fields': ('is_primary', 'is_active')
        }),
        ('Metadata', {
            'fields': ('invited_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('user', 'organization', 'invited_by')
        admin_org_ids = get_admin_org_ids(request)

        if admin_org_ids is None:  # Superuser
            return qs
        if admin_org_ids:
            return qs.filter(organization_id__in=admin_org_ids)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit organization choices for non-superusers (uses cached org IDs)."""
        if db_field.name == 'organization':
            admin_org_ids = get_admin_org_ids(request)
            if admin_org_ids is not None:  # Not superuser
                kwargs['queryset'] = Organization.objects.filter(id__in=admin_org_ids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
