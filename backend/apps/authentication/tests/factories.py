"""
Factory classes for generating test data for authentication models.
"""
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth.models import User
from apps.authentication.models import Organization, UserProfile, AuditLog


class OrganizationFactory(DjangoModelFactory):
    """Factory for creating Organization instances."""

    class Meta:
        model = Organization
        django_get_or_create = ('slug',)

    name = factory.Sequence(lambda n: f'Organization {n}')
    slug = factory.Sequence(lambda n: f'org-{n}')
    description = factory.Faker('sentence')
    is_active = True
    is_demo = False


class DemoOrganizationFactory(OrganizationFactory):
    """Factory for synthetic/demo organization fixtures."""
    name = factory.Sequence(lambda n: f'Demo Organization {n}')
    slug = factory.Sequence(lambda n: f'demo-org-{n}')
    is_demo = True


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = factory.PostGenerationMethodCall('set_password', 'TestPass123!')
    is_active = True


class UserProfileFactory(DjangoModelFactory):
    """Factory for creating UserProfile instances."""

    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    organization = factory.SubFactory(OrganizationFactory)
    role = 'viewer'
    phone = factory.Faker('phone_number')
    department = factory.Faker('job')
    is_active = True


class AdminUserFactory(UserFactory):
    """Factory for creating admin users with profiles."""

    @factory.post_generation
    def profile(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            return extracted
        return UserProfileFactory(
            user=self,
            role='admin',
            **kwargs
        )


class ManagerUserFactory(UserFactory):
    """Factory for creating manager users with profiles."""

    @factory.post_generation
    def profile(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            return extracted
        return UserProfileFactory(
            user=self,
            role='manager',
            **kwargs
        )


class ViewerUserFactory(UserFactory):
    """Factory for creating viewer users with profiles."""

    @factory.post_generation
    def profile(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            return extracted
        return UserProfileFactory(
            user=self,
            role='viewer',
            **kwargs
        )


class AuditLogFactory(DjangoModelFactory):
    """Factory for creating AuditLog instances."""

    class Meta:
        model = AuditLog

    user = factory.SubFactory(UserFactory)
    organization = factory.SubFactory(OrganizationFactory)
    action = 'view'
    resource = 'transaction'
    resource_id = factory.Sequence(lambda n: str(n))
    details = {}
    ip_address = factory.Faker('ipv4')
    user_agent = factory.Faker('user_agent')
