"""
Tests for authentication permission classes.
"""
import pytest
from unittest.mock import Mock
from apps.authentication.permissions import (
    IsAdmin,
    IsManager,
    CanUploadData,
    CanDeleteData,
    IsSameOrganization
)
from apps.authentication.models import Organization


@pytest.mark.django_db
class TestIsAdmin:
    """Tests for IsAdmin permission class."""

    def test_admin_has_permission(self, admin_user):
        """Test that admin users have permission."""
        permission = IsAdmin()
        request = Mock()
        request.user = admin_user

        assert permission.has_permission(request, None)

    def test_manager_no_permission(self, manager_user):
        """Test that manager users don't have admin permission."""
        permission = IsAdmin()
        request = Mock()
        request.user = manager_user

        assert not permission.has_permission(request, None)

    def test_viewer_no_permission(self, user):
        """Test that viewer users don't have admin permission."""
        permission = IsAdmin()
        request = Mock()
        request.user = user

        assert not permission.has_permission(request, None)

    def test_unauthenticated_no_permission(self):
        """Test that unauthenticated users don't have permission."""
        permission = IsAdmin()
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False

        assert not permission.has_permission(request, None)

    def test_user_without_profile_no_permission(self):
        """Test that user without profile doesn't have permission."""
        permission = IsAdmin()
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = True
        del request.user.profile  # Simulate no profile attribute

        assert not permission.has_permission(request, None)


@pytest.mark.django_db
class TestIsManager:
    """Tests for IsManager permission class."""

    def test_admin_has_permission(self, admin_user):
        """Test that admin users have manager permission."""
        permission = IsManager()
        request = Mock()
        request.user = admin_user

        assert permission.has_permission(request, None)

    def test_manager_has_permission(self, manager_user):
        """Test that manager users have permission."""
        permission = IsManager()
        request = Mock()
        request.user = manager_user

        assert permission.has_permission(request, None)

    def test_viewer_no_permission(self, user):
        """Test that viewer users don't have manager permission."""
        permission = IsManager()
        request = Mock()
        request.user = user

        assert not permission.has_permission(request, None)

    def test_unauthenticated_no_permission(self):
        """Test that unauthenticated users don't have permission."""
        permission = IsManager()
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False

        assert not permission.has_permission(request, None)


@pytest.mark.django_db
class TestCanUploadData:
    """Tests for CanUploadData permission class."""

    def test_admin_can_upload(self, admin_user):
        """Test that admin users can upload data."""
        permission = CanUploadData()
        request = Mock()
        request.user = admin_user

        assert permission.has_permission(request, None)

    def test_manager_can_upload(self, manager_user):
        """Test that manager users can upload data."""
        permission = CanUploadData()
        request = Mock()
        request.user = manager_user

        assert permission.has_permission(request, None)

    def test_viewer_cannot_upload(self, user):
        """Test that viewer users cannot upload data."""
        permission = CanUploadData()
        request = Mock()
        request.user = user

        assert not permission.has_permission(request, None)


@pytest.mark.django_db
class TestCanDeleteData:
    """Tests for CanDeleteData permission class."""

    def test_admin_can_delete(self, admin_user):
        """Test that admin users can delete data."""
        permission = CanDeleteData()
        request = Mock()
        request.user = admin_user

        assert permission.has_permission(request, None)

    def test_manager_cannot_delete(self, manager_user):
        """Test that manager users cannot delete data."""
        permission = CanDeleteData()
        request = Mock()
        request.user = manager_user

        assert not permission.has_permission(request, None)

    def test_viewer_cannot_delete(self, user):
        """Test that viewer users cannot delete data."""
        permission = CanDeleteData()
        request = Mock()
        request.user = user

        assert not permission.has_permission(request, None)


@pytest.mark.django_db
class TestIsSameOrganization:
    """Tests for IsSameOrganization permission class."""

    def test_same_org_has_permission(self, user, organization):
        """Test that user has permission for same org object."""
        permission = IsSameOrganization()
        request = Mock()
        request.user = user

        # Object with organization field
        obj = Mock()
        obj.organization = organization

        assert permission.has_object_permission(request, None, obj)

    def test_different_org_no_permission(self, user, other_organization):
        """Test that user doesn't have permission for different org object."""
        permission = IsSameOrganization()
        request = Mock()
        request.user = user

        obj = Mock()
        obj.organization = other_organization

        assert not permission.has_object_permission(request, None, obj)

    def test_object_with_user_field(self, user, organization):
        """Test permission check via object's user.profile.organization."""
        permission = IsSameOrganization()
        request = Mock()
        request.user = user

        # Object with user field instead of organization
        obj = Mock(spec=[])  # Empty spec to avoid 'organization' attribute
        obj.user = Mock()
        obj.user.profile = Mock()
        obj.user.profile.organization = organization

        assert permission.has_object_permission(request, None, obj)

    def test_unauthenticated_no_permission(self):
        """Test that unauthenticated users don't have permission."""
        permission = IsSameOrganization()
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False

        obj = Mock()
        obj.organization = Mock()

        assert not permission.has_object_permission(request, None, obj)

    def test_user_without_profile_no_permission(self):
        """Test that user without profile doesn't have permission."""
        permission = IsSameOrganization()
        request = Mock()
        # Use spec to explicitly exclude 'profile' attribute
        request.user = Mock(spec=['is_authenticated', 'is_superuser'])
        request.user.is_authenticated = True
        request.user.is_superuser = False

        obj = Mock()
        obj.organization = Mock()

        assert not permission.has_object_permission(request, None, obj)

    def test_object_without_org_or_user_no_permission(self, user):
        """Test that permission fails for objects without org or user."""
        permission = IsSameOrganization()
        request = Mock()
        request.user = user

        # Object with neither organization nor user
        obj = Mock(spec=[])

        assert not permission.has_object_permission(request, None, obj)


@pytest.mark.django_db
class TestPermissionIntegration:
    """Integration tests for permission classes with real requests."""

    def test_admin_can_do_everything(self, admin_user, organization):
        """Test that admin has all permissions."""
        request = Mock()
        request.user = admin_user

        assert IsAdmin().has_permission(request, None)
        assert IsManager().has_permission(request, None)
        assert CanUploadData().has_permission(request, None)
        assert CanDeleteData().has_permission(request, None)

    def test_manager_limited_permissions(self, manager_user):
        """Test that manager has limited permissions."""
        request = Mock()
        request.user = manager_user

        assert not IsAdmin().has_permission(request, None)
        assert IsManager().has_permission(request, None)
        assert CanUploadData().has_permission(request, None)
        assert not CanDeleteData().has_permission(request, None)

    def test_viewer_minimal_permissions(self, user):
        """Test that viewer has minimal permissions."""
        request = Mock()
        request.user = user

        assert not IsAdmin().has_permission(request, None)
        assert not IsManager().has_permission(request, None)
        assert not CanUploadData().has_permission(request, None)
        assert not CanDeleteData().has_permission(request, None)
