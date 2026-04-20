"""
Tests for authentication models.
"""
import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from apps.authentication.models import Organization, UserProfile, AuditLog
from .factories import OrganizationFactory, UserFactory, UserProfileFactory, AuditLogFactory


@pytest.mark.django_db
class TestOrganization:
    """Tests for the Organization model."""

    def test_create_organization(self):
        """Test creating an organization."""
        org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            description='A test organization'
        )
        assert org.name == 'Test Org'
        assert org.slug == 'test-org'
        assert org.is_active is True
        assert str(org) == 'Test Org'

    def test_organization_unique_name(self):
        """Test that organization names must be unique."""
        OrganizationFactory(name='Unique Org', slug='unique-1')
        with pytest.raises(Exception):  # IntegrityError
            OrganizationFactory(name='Unique Org', slug='unique-2')

    def test_organization_unique_slug(self):
        """Test that organization slugs must be unique."""
        from django.db import IntegrityError, transaction
        from apps.authentication.models import Organization
        # Use model directly (not factory) since factory has get_or_create semantics
        Organization.objects.create(name='Org One', slug='same-slug')
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Organization.objects.create(name='Org Two', slug='same-slug')

    def test_organization_factory(self):
        """Test the organization factory."""
        org = OrganizationFactory()
        assert org.id is not None
        assert org.name is not None
        assert org.slug is not None
        assert org.is_active is True

    def test_organization_ordering(self):
        """Test that organizations are ordered by name."""
        org_c = OrganizationFactory(name='C Organization', slug='org-c')
        org_a = OrganizationFactory(name='A Organization', slug='org-a')
        org_b = OrganizationFactory(name='B Organization', slug='org-b')

        orgs = list(Organization.objects.all())
        assert orgs[0].name == 'A Organization'
        assert orgs[1].name == 'B Organization'
        assert orgs[2].name == 'C Organization'


@pytest.mark.django_db
class TestUserProfile:
    """Tests for the UserProfile model."""

    def test_create_user_profile(self, organization):
        """Test creating a user profile."""
        user = UserFactory()
        profile = UserProfile.objects.create(
            user=user,
            organization=organization,
            role='viewer'
        )
        assert profile.user == user
        assert profile.organization == organization
        assert profile.role == 'viewer'
        assert profile.is_active is True

    def test_user_profile_str(self, organization):
        """Test the string representation of UserProfile."""
        user = UserFactory(username='testuser')
        profile = UserProfile.objects.create(
            user=user,
            organization=organization,
            role='admin'
        )
        assert str(profile) == f'testuser - {organization.name} (admin)'

    def test_is_admin(self, organization):
        """Test is_admin method."""
        user = UserFactory()
        profile = UserProfile.objects.create(
            user=user,
            organization=organization,
            role='admin'
        )
        assert profile.is_admin() is True

        profile.role = 'manager'
        assert profile.is_admin() is False

        profile.role = 'viewer'
        assert profile.is_admin() is False

    def test_is_manager(self, organization):
        """Test is_manager method."""
        user = UserFactory()
        profile = UserProfile.objects.create(
            user=user,
            organization=organization,
            role='admin'
        )
        assert profile.is_manager() is True

        profile.role = 'manager'
        assert profile.is_manager() is True

        profile.role = 'viewer'
        assert profile.is_manager() is False

    def test_can_upload_data(self, organization):
        """Test can_upload_data method."""
        user = UserFactory()
        profile = UserProfile.objects.create(
            user=user,
            organization=organization,
            role='admin'
        )
        assert profile.can_upload_data() is True

        profile.role = 'manager'
        assert profile.can_upload_data() is True

        profile.role = 'viewer'
        assert profile.can_upload_data() is False

    def test_can_delete_data(self, organization):
        """Test can_delete_data method."""
        user = UserFactory()
        profile = UserProfile.objects.create(
            user=user,
            organization=organization,
            role='admin'
        )
        assert profile.can_delete_data() is True

        profile.role = 'manager'
        assert profile.can_delete_data() is False

        profile.role = 'viewer'
        assert profile.can_delete_data() is False

    def test_role_choices(self, organization):
        """Test valid role choices."""
        user = UserFactory()
        for role, _ in UserProfile.ROLE_CHOICES:
            profile = UserProfile(
                user=user,
                organization=organization,
                role=role
            )
            assert profile.role in ['admin', 'manager', 'viewer']


@pytest.mark.django_db
class TestAuditLog:
    """Tests for the AuditLog model."""

    def test_create_audit_log(self, organization):
        """Test creating an audit log entry."""
        user = UserFactory()
        log = AuditLog.objects.create(
            user=user,
            organization=organization,
            action='login',
            resource='session',
            details={'username': 'testuser'}
        )
        assert log.user == user
        assert log.organization == organization
        assert log.action == 'login'
        assert log.details == {'username': 'testuser'}

    def test_audit_log_str(self, organization):
        """Test the string representation of AuditLog."""
        user = UserFactory(username='audituser')
        log = AuditLog.objects.create(
            user=user,
            organization=organization,
            action='create',
            resource='transaction'
        )
        assert 'audituser' in str(log)
        assert 'create' in str(log)
        assert 'transaction' in str(log)

    def test_audit_log_allowed_detail_keys(self, organization):
        """Test that only allowed keys are accepted in details."""
        user = UserFactory()
        log = AuditLog(
            user=user,
            organization=organization,
            action='create',
            resource='transaction',
            details={'file_name': 'test.csv', 'count': 10}
        )
        log.full_clean()  # Should not raise
        log.save()
        assert log.id is not None

    def test_audit_log_invalid_detail_keys(self, organization):
        """Test that invalid keys are rejected in details."""
        user = UserFactory()
        log = AuditLog(
            user=user,
            organization=organization,
            action='create',
            resource='transaction',
            details={'invalid_key': 'should fail', 'another_bad_key': 123}
        )
        with pytest.raises(ValidationError) as exc_info:
            log.full_clean()
        assert 'invalid_key' in str(exc_info.value)

    def test_audit_log_details_must_be_dict(self, organization):
        """Test that details must be a dictionary."""
        user = UserFactory()
        log = AuditLog(
            user=user,
            organization=organization,
            action='create',
            resource='transaction',
            details=['not', 'a', 'dict']
        )
        with pytest.raises(ValidationError) as exc_info:
            log.full_clean()
        assert 'must be a dictionary' in str(exc_info.value)

    def test_audit_log_details_value_types(self, organization):
        """Test that details values must be simple types."""
        user = UserFactory()

        # Valid types should work
        log = AuditLog(
            user=user,
            organization=organization,
            action='create',
            resource='transaction',
            details={
                'file_name': 'test.csv',
                'count': 10,
                'successful': True,
                'changes': ['change1', 'change2']
            }
        )
        log.full_clean()  # Should not raise

        # Nested dict should fail
        log2 = AuditLog(
            user=user,
            organization=organization,
            action='create',
            resource='transaction',
            details={'file_name': {'nested': 'dict'}}
        )
        with pytest.raises(ValidationError):
            log2.full_clean()

    def test_audit_log_empty_details(self, organization):
        """Test that empty details are valid."""
        user = UserFactory()
        log = AuditLog(
            user=user,
            organization=organization,
            action='login',
            resource='session',
            details={}
        )
        log.full_clean()  # Should not raise
        log.save()
        assert log.id is not None

    def test_audit_log_action_choices(self, organization):
        """Test valid action choices."""
        user = UserFactory()
        for action, _ in AuditLog.ACTION_CHOICES:
            log = AuditLog.objects.create(
                user=user,
                organization=organization,
                action=action,
                resource='test'
            )
            assert log.action == action

    def test_audit_log_ordering(self, organization):
        """Test that audit logs are ordered by timestamp descending."""
        user = UserFactory()
        log1 = AuditLog.objects.create(
            user=user,
            organization=organization,
            action='login',
            resource='session'
        )
        log2 = AuditLog.objects.create(
            user=user,
            organization=organization,
            action='logout',
            resource='session'
        )
        log3 = AuditLog.objects.create(
            user=user,
            organization=organization,
            action='view',
            resource='dashboard'
        )

        logs = list(AuditLog.objects.all())
        assert logs[0] == log3
        assert logs[1] == log2
        assert logs[2] == log1

    def test_audit_log_indexes(self, organization):
        """Test that audit log has proper indexes defined."""
        # Check that indexes are defined in Meta
        indexes = AuditLog._meta.indexes
        index_fields = [tuple(idx.fields) for idx in indexes]

        assert ('organization', '-timestamp') in index_fields
        assert ('user', '-timestamp') in index_fields
        assert ('action', '-timestamp') in index_fields

    def test_audit_log_null_user(self, organization):
        """Test that audit log field allows null user (for system events)."""
        # The model allows null=True on user field
        user_field = AuditLog._meta.get_field('user')
        assert user_field.null is True

    def test_audit_log_ip_address_generic(self, organization):
        """Test that IP address field accepts both IPv4 and IPv6."""
        user = UserFactory()

        # IPv4
        log1 = AuditLog.objects.create(
            user=user,
            organization=organization,
            action='login',
            resource='session',
            ip_address='192.168.1.1'
        )
        assert log1.ip_address == '192.168.1.1'

        # IPv6
        log2 = AuditLog.objects.create(
            user=user,
            organization=organization,
            action='login',
            resource='session',
            ip_address='2001:db8::1'
        )
        assert log2.ip_address == '2001:db8::1'
