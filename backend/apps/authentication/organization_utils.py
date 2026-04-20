"""
Organization utility functions for multi-tenant access control.

This module consolidates organization resolution logic used across all apps,
replacing duplicate implementations in analytics/views.py, procurement/views.py,
and reports/views.py.

Supports both single-org users (legacy) and multi-org users (new membership model).
"""
from rest_framework.exceptions import ValidationError

from .models import Organization, UserOrganizationMembership


def get_user_organizations(user):
    """
    Get all organizations a user has access to.

    Args:
        user: Django User instance

    Returns:
        QuerySet of Organization objects the user can access
    """
    if not user or not user.is_authenticated:
        return Organization.objects.none()

    if user.is_superuser:
        return Organization.objects.filter(is_active=True)

    if not hasattr(user, 'profile'):
        return Organization.objects.none()

    # Get orgs from memberships
    membership_org_ids = UserOrganizationMembership.objects.filter(
        user=user,
        is_active=True,
        organization__is_active=True
    ).values_list('organization_id', flat=True)

    if membership_org_ids:
        return Organization.objects.filter(id__in=membership_org_ids)

    # Fall back to legacy single org from profile
    return Organization.objects.filter(id=user.profile.organization_id, is_active=True)


def get_primary_organization(user):
    """
    Get user's primary organization.

    Args:
        user: Django User instance

    Returns:
        Organization instance or None
    """
    if not user or not user.is_authenticated:
        return None

    if not hasattr(user, 'profile'):
        return None

    # First check new membership model for primary
    primary_membership = UserOrganizationMembership.objects.filter(
        user=user,
        is_primary=True,
        is_active=True
    ).select_related('organization').first()

    if primary_membership:
        return primary_membership.organization

    # Fall back to legacy UserProfile.organization
    return user.profile.organization


def get_target_organization(request):
    """
    Resolve the target organization for API requests.

    For superusers: Checks for organization_id query param, falls back to primary org.
    For multi-org users: Checks for organization_id if they have access, else primary org.
    For single-org users: Always returns their organization.

    Args:
        request: DRF request object

    Returns:
        Organization instance or None if user has no profile

    Raises:
        ValidationError: If organization_id is invalid or user lacks access
    """
    user = request.user

    if not hasattr(user, 'profile'):
        return None

    # Get user's primary organization as default
    primary_org = get_primary_organization(user)

    # Check for organization_id query param
    org_id = request.query_params.get('organization_id')

    if org_id:
        try:
            org_id = int(org_id)
        except (ValueError, TypeError):
            raise ValidationError({'organization_id': 'Must be a valid integer'})

        try:
            target_org = Organization.objects.get(id=org_id, is_active=True)
        except Organization.DoesNotExist:
            raise ValidationError({'organization_id': 'Organization not found or inactive'})

        # Superusers can access any org
        if user.is_superuser:
            return target_org

        # Check if user has membership in target org
        if user_can_access_org(user, target_org):
            return target_org

        raise ValidationError({
            'organization_id': 'You do not have access to this organization'
        })

    return primary_org


def get_user_role_in_org(user, organization):
    """
    Get user's role in a specific organization.

    Args:
        user: Django User instance
        organization: Organization instance or organization ID (int)

    Returns:
        Role string ('admin', 'manager', 'viewer') or None
    """
    if not user or not user.is_authenticated:
        return None

    if user.is_superuser:
        return 'admin'  # Superusers have admin access everywhere

    org_id = organization.id if hasattr(organization, 'id') else organization

    membership = UserOrganizationMembership.objects.filter(
        user=user,
        organization_id=org_id,
        is_active=True
    ).first()

    if membership:
        return membership.role

    # Fall back to legacy profile if it matches
    if hasattr(user, 'profile') and user.profile.organization_id == org_id:
        return user.profile.role

    return None


def user_can_access_org(user, organization):
    """
    Check if user has access to an organization.

    Args:
        user: Django User instance
        organization: Organization instance or organization ID (int)

    Returns:
        Boolean indicating whether user can access the organization
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    org_id = organization.id if hasattr(organization, 'id') else organization

    # Check memberships first
    has_membership = UserOrganizationMembership.objects.filter(
        user=user,
        organization_id=org_id,
        is_active=True
    ).exists()

    if has_membership:
        return True

    # Fall back to legacy profile check
    if hasattr(user, 'profile') and user.profile.organization_id == org_id:
        return True

    return False


def user_is_admin_in_org(user, organization):
    """
    Check if user has admin role in organization.

    Args:
        user: Django User instance
        organization: Organization instance or organization ID (int)

    Returns:
        Boolean
    """
    role = get_user_role_in_org(user, organization)
    return role == 'admin'


def user_is_manager_in_org(user, organization):
    """
    Check if user has manager+ role in organization.

    Args:
        user: Django User instance
        organization: Organization instance or organization ID (int)

    Returns:
        Boolean
    """
    role = get_user_role_in_org(user, organization)
    return role in ['admin', 'manager']


def user_can_upload_in_org(user, organization):
    """
    Check if user can upload data in the organization.

    Args:
        user: Django User instance
        organization: Organization instance or organization ID (int)

    Returns:
        Boolean
    """
    role = get_user_role_in_org(user, organization)
    return role in ['admin', 'manager']


def user_can_delete_in_org(user, organization):
    """
    Check if user can delete data in the organization.

    Args:
        user: Django User instance
        organization: Organization instance or organization ID (int)

    Returns:
        Boolean
    """
    role = get_user_role_in_org(user, organization)
    return role == 'admin'
