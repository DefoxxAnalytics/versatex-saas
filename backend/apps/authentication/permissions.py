"""
Custom permissions for role-based access control.

Supports both single-org users (legacy) and multi-org users (via UserOrganizationMembership).
"""
from rest_framework import permissions

from .organization_utils import (
    get_target_organization,
    user_can_access_org,
    user_is_admin_in_org,
    user_is_manager_in_org,
    get_user_role_in_org,
)


def _resolve_target_org(request, view, obj=None):
    """Resolve the target organization for a permission check.

    Priority:
    1. obj.organization (object-level checks)
    2. view.kwargs['org_id'] / 'organization_id' / 'organization' (URL-scoped views)
    3. request.data['organization'] (body-scoped writes)
    4. request.user.profile.organization (legacy single-org fallback)

    Returns the Organization instance, an int (org_id), or None. The
    membership helpers (user_is_admin_in_org / user_is_manager_in_org)
    accept both shapes.
    """
    if obj is not None and hasattr(obj, 'organization'):
        return obj.organization

    kwargs = getattr(view, 'kwargs', None)
    if isinstance(kwargs, dict):
        for key in ('org_id', 'organization_id', 'organization'):
            if key in kwargs:
                return kwargs[key]

    # Restrict to real dicts so unit-test Mock objects don't leak a Mock value here.
    data = getattr(request, 'data', None)
    if isinstance(data, dict):
        org_from_body = data.get('organization')
        if org_from_body is not None:
            return org_from_body

    user = getattr(request, 'user', None)
    profile = getattr(user, 'profile', None)
    if profile is not None:
        return getattr(profile, 'organization', None)

    return None


class IsAdmin(permissions.BasePermission):
    """Allows access only to admins of the target organization.

    Uses membership-aware role lookup (Findings A1 + B9). Multi-org users
    get correct role evaluation per target org.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        target_org = _resolve_target_org(request, view)
        if target_org is None:
            return False
        return user_is_admin_in_org(request.user, target_org)

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        target_org = _resolve_target_org(request, view, obj)
        if target_org is None:
            return False
        return user_is_admin_in_org(request.user, target_org)


class IsManager(permissions.BasePermission):
    """Allows access to admins and managers of the target organization.

    Uses membership-aware role lookup (Findings A1 + B9). Multi-org users
    get correct role evaluation per target org.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        target_org = _resolve_target_org(request, view)
        if target_org is None:
            return False
        return user_is_manager_in_org(request.user, target_org)

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        target_org = _resolve_target_org(request, view, obj)
        if target_org is None:
            return False
        return user_is_manager_in_org(request.user, target_org)


class CanUploadData(permissions.BasePermission):
    """
    Permission class for users who can upload data
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.can_upload_data()
        )


class CanDeleteData(permissions.BasePermission):
    """
    Permission class for users who can delete data
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.can_delete_data()
        )


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission class for super admin (Django superuser) access.

    Super admins have platform-level privileges that transcend organization
    boundaries, such as uploading data for multiple organizations at once.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_superuser
        )


class IsSameOrganization(permissions.BasePermission):
    """
    Permission class to ensure users can only access their organization's data.

    Supports multi-org users: checks if user has any membership in the object's org.
    Super admins (Django superusers) bypass this check and can access data
    from any organization.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Super admins can access any organization's data
        if request.user.is_superuser:
            return True

        if not hasattr(request.user, 'profile'):
            return False

        # Get the object's organization
        obj_org = None
        if hasattr(obj, 'organization'):
            obj_org = obj.organization
        elif hasattr(obj, 'user') and hasattr(obj.user, 'profile'):
            obj_org = obj.user.profile.organization

        if not obj_org:
            return False

        # Check if user has access to this organization (supports multi-org)
        return user_can_access_org(request.user, obj_org)


# =============================================================================
# P2P (Procure-to-Pay) Permissions
# =============================================================================

class HasP2PAccess(permissions.BasePermission):
    """
    Check if user has access to P2P Analytics module.
    All authenticated users with a profile can access P2P data by default.
    Can be extended to check organization-level feature flags.
    """
    message = 'P2P Analytics module access required.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Superusers always have access
        if request.user.is_superuser:
            return True

        if not hasattr(request.user, 'profile'):
            return False

        # Check organization-level P2P module flag if it exists
        # (can be added to Organization model later)
        org = request.user.profile.organization
        if hasattr(org, 'p2p_module_enabled'):
            return org.p2p_module_enabled

        # Default: all users can access P2P if they have a profile
        return request.user.profile.is_active


class CanResolveExceptions(permissions.BasePermission):
    """
    Only managers and admins of the target organization can resolve invoice
    exceptions. Uses membership-aware role lookup (Findings A1 + B9).
    """
    message = 'Only managers and admins can resolve invoice exceptions.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        target_org = _resolve_target_org(request, view)
        if target_org is None:
            return False
        return user_is_manager_in_org(request.user, target_org)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        target_org = _resolve_target_org(request, view, obj)
        if target_org is None:
            return False
        return user_is_manager_in_org(request.user, target_org)


class CanViewPaymentData(permissions.BasePermission):
    """
    Only managers and admins of the target organization can view sensitive
    payment data. Uses membership-aware role lookup (Findings A1 + B9).
    """
    message = 'Only managers and admins can view payment data.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        target_org = _resolve_target_org(request, view)
        if target_org is None:
            return False
        return user_is_manager_in_org(request.user, target_org)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        target_org = _resolve_target_org(request, view, obj)
        if target_org is None:
            return False
        return user_is_manager_in_org(request.user, target_org)


class CanApprovePO(permissions.BasePermission):
    """
    Only managers and admins of the target organization can approve purchase
    orders. Uses membership-aware role lookup (Findings A1 + B9).
    """
    message = 'Only managers and admins can approve purchase orders.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        target_org = _resolve_target_org(request, view)
        if target_org is None:
            return False
        return user_is_manager_in_org(request.user, target_org)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        target_org = _resolve_target_org(request, view, obj)
        if target_org is None:
            return False
        return user_is_manager_in_org(request.user, target_org)


class CanApprovePR(permissions.BasePermission):
    """
    Only managers and admins of the target organization can approve purchase
    requisitions. Uses membership-aware role lookup (Findings A1 + B9).
    """
    message = 'Only managers and admins can approve purchase requisitions.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        target_org = _resolve_target_org(request, view)
        if target_org is None:
            return False
        return user_is_manager_in_org(request.user, target_org)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        target_org = _resolve_target_org(request, view, obj)
        if target_org is None:
            return False
        return user_is_manager_in_org(request.user, target_org)


class CanViewOwnRequisitions(permissions.BasePermission):
    """
    Viewers can only see their own requisitions. Managers and admins can see
    all requisitions in the target organization.

    Uses membership-aware role lookup (Findings A1 + B9): the role check is
    resolved against obj.organization, not the user's legacy
    profile.organization. Multi-org users get correct evaluation per PR.
    """
    message = 'You can only view your own requisitions.'

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True

        target_org = _resolve_target_org(request, view, obj)
        if target_org is None:
            return False

        # Org membership is required either way.
        if not user_can_access_org(request.user, target_org):
            return False

        # Managers and admins of the target org can see all org PRs.
        if user_is_manager_in_org(request.user, target_org):
            return True

        # Viewers can only see their own PRs.
        return obj.requested_by == request.user
