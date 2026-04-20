"""
Pytest configuration and shared fixtures for the Versatex Analytics test suite.
"""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def organization(db):
    """Create a test organization."""
    from apps.authentication.models import Organization
    return Organization.objects.create(
        name='Test Organization',
        slug='test-org',
        description='A test organization',
        is_active=True
    )


@pytest.fixture
def other_organization(db):
    """Create another organization for multi-tenant isolation tests."""
    from apps.authentication.models import Organization
    return Organization.objects.create(
        name='Other Organization',
        slug='other-org',
        description='Another organization for isolation tests',
        is_active=True
    )


@pytest.fixture
def user(db, organization):
    """Create a test user with a profile."""
    from apps.authentication.models import UserProfile
    user = User.objects.create_user(
        username='testuser',
        email='testuser@example.com',
        password='TestPass123!',
        first_name='Test',
        last_name='User'
    )
    UserProfile.objects.create(
        user=user,
        organization=organization,
        role='viewer',
        is_active=True
    )
    return user


@pytest.fixture
def admin_user(db, organization):
    """Create an admin user with a profile."""
    from apps.authentication.models import UserProfile
    user = User.objects.create_user(
        username='adminuser',
        email='admin@example.com',
        password='AdminPass123!',
        first_name='Admin',
        last_name='User'
    )
    UserProfile.objects.create(
        user=user,
        organization=organization,
        role='admin',
        is_active=True
    )
    return user


@pytest.fixture
def manager_user(db, organization):
    """Create a manager user with a profile."""
    from apps.authentication.models import UserProfile
    user = User.objects.create_user(
        username='manageruser',
        email='manager@example.com',
        password='ManagerPass123!',
        first_name='Manager',
        last_name='User'
    )
    UserProfile.objects.create(
        user=user,
        organization=organization,
        role='manager',
        is_active=True
    )
    return user


@pytest.fixture
def other_org_user(db, other_organization):
    """Create a user in a different organization for isolation tests."""
    from apps.authentication.models import UserProfile
    user = User.objects.create_user(
        username='otherorguser',
        email='otherorg@example.com',
        password='OtherPass123!',
        first_name='Other',
        last_name='User'
    )
    UserProfile.objects.create(
        user=user,
        organization=other_organization,
        role='admin',
        is_active=True
    )
    return user


@pytest.fixture
def inactive_user(db, organization):
    """Create an inactive user for testing blocked access."""
    from apps.authentication.models import UserProfile
    user = User.objects.create_user(
        username='inactiveuser',
        email='inactive@example.com',
        password='InactivePass123!',
        is_active=False
    )
    UserProfile.objects.create(
        user=user,
        organization=organization,
        role='viewer',
        is_active=True
    )
    return user


@pytest.fixture
def inactive_profile_user(db, organization):
    """Create a user with inactive profile for testing blocked access."""
    from apps.authentication.models import UserProfile
    user = User.objects.create_user(
        username='inactiveprofile',
        email='inactiveprofile@example.com',
        password='InactiveProfile123!'
    )
    UserProfile.objects.create(
        user=user,
        organization=organization,
        role='viewer',
        is_active=False
    )
    return user


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client for a regular user."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an authenticated API client for an admin user."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def manager_client(api_client, manager_user):
    """Return an authenticated API client for a manager user."""
    refresh = RefreshToken.for_user(manager_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def other_org_client(api_client, other_org_user):
    """Return an authenticated API client for a user in another organization."""
    refresh = RefreshToken.for_user(other_org_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def supplier(db, organization, admin_user):
    """Create a test supplier."""
    from apps.procurement.models import Supplier
    return Supplier.objects.create(
        organization=organization,
        name='Test Supplier',
        code='SUP001',
        contact_email='supplier@example.com',
        is_active=True
    )


@pytest.fixture
def category(db, organization):
    """Create a test category."""
    from apps.procurement.models import Category
    return Category.objects.create(
        organization=organization,
        name='Test Category',
        description='A test category',
        is_active=True
    )


@pytest.fixture
def transaction(db, organization, supplier, category, admin_user):
    """Create a test transaction."""
    from apps.procurement.models import Transaction
    from decimal import Decimal
    from datetime import date
    return Transaction.objects.create(
        organization=organization,
        supplier=supplier,
        category=category,
        amount=Decimal('1000.00'),
        date=date.today(),
        description='Test transaction',
        uploaded_by=admin_user,
        upload_batch='test-batch-001'
    )


@pytest.fixture
def multiple_transactions(db, organization, supplier, category, admin_user):
    """Create multiple transactions for analytics testing."""
    from apps.procurement.models import Transaction
    from decimal import Decimal
    from datetime import date, timedelta

    transactions = []
    base_date = date.today() - timedelta(days=365)

    # Create 12 months of transaction data
    for month in range(12):
        for i in range(5):  # 5 transactions per month
            tx = Transaction.objects.create(
                organization=organization,
                supplier=supplier,
                category=category,
                amount=Decimal(str(1000 + (i * 100) + (month * 50))),
                date=base_date + timedelta(days=month * 30 + i),
                description=f'Transaction {month}-{i}',
                uploaded_by=admin_user,
                upload_batch=f'batch-{month}'
            )
            transactions.append(tx)

    return transactions


@pytest.fixture
def csv_file():
    """Create a simple CSV file for upload testing."""
    import io
    content = """supplier,category,amount,date,description
Test Supplier,Test Category,1000.00,2024-01-15,Test transaction 1
Test Supplier,Test Category,2000.00,2024-01-16,Test transaction 2
Another Supplier,Another Category,3000.00,2024-01-17,Test transaction 3"""
    return io.BytesIO(content.encode('utf-8'))


@pytest.fixture
def csv_file_with_formulas():
    """Create a CSV file with formula injection attempts."""
    import io
    content = """supplier,category,amount,date,description
=CMD|' /C calc'!A0,Test Category,1000.00,2024-01-15,Test
+cmd|' /C notepad'!A0,Test Category,2000.00,2024-01-16,Test
-2+3,Test Category,3000.00,2024-01-17,Test
@SUM(A1:A10),Test Category,4000.00,2024-01-18,Test"""
    return io.BytesIO(content.encode('utf-8'))


@pytest.fixture
def mock_request():
    """Create a mock request object for testing utilities."""
    from unittest.mock import Mock
    request = Mock()
    request.META = {
        'REMOTE_ADDR': '192.168.1.1',
        'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Test Browser',
        'HTTP_X_FORWARDED_FOR': None,
        'HTTP_X_REAL_IP': None,
    }
    return request


@pytest.fixture
def mock_request_with_proxy():
    """Create a mock request with X-Forwarded-For header."""
    from unittest.mock import Mock
    request = Mock()
    request.META = {
        'REMOTE_ADDR': '10.0.0.1',
        'HTTP_USER_AGENT': 'Mozilla/5.0 Test Browser',
        'HTTP_X_FORWARDED_FOR': '203.0.113.195, 70.41.3.18, 150.172.238.178',
        'HTTP_X_REAL_IP': None,
    }
    return request


# Database settings for pytest-django
@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    """Configure database for tests - runs migrations."""
    from django.core.management import call_command
    with django_db_blocker.unblock():
        call_command('migrate', '--run-syncdb', verbosity=0)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear Django cache before each test."""
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()
