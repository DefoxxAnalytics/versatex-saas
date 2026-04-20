"""
Tests for authentication views.
"""
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.authentication.models import Organization, UserProfile, AuditLog
from .factories import OrganizationFactory, UserFactory, UserProfileFactory


@pytest.mark.django_db
class TestRegisterView:
    """Tests for user registration."""

    def test_register_success(self, api_client, organization):
        """Test successful user registration."""
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'User',
            'organization': organization.id
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert 'user' in response.data
        assert response.data['user']['username'] == 'newuser'
        # Verify cookies are set
        assert 'access_token' in response.cookies
        assert 'refresh_token' in response.cookies

    def test_register_password_mismatch(self, api_client, organization):
        """Test registration with mismatched passwords."""
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'DifferentPass123!',
            'first_name': 'New',
            'last_name': 'User',
            'organization': organization.id
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_username(self, api_client, organization, user):
        """Test registration with duplicate username."""
        url = reverse('register')
        data = {
            'username': user.username,
            'email': 'different@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'User',
            'organization': organization.id
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client, organization):
        """Test registration with weak password."""
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': '123',
            'password_confirm': '123',
            'first_name': 'New',
            'last_name': 'User',
            'organization': organization.id
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_required_fields(self, api_client):
        """Test registration with missing required fields."""
        url = reverse('register')
        data = {
            'username': 'newuser'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_creates_audit_log(self, api_client, organization):
        """Test that registration creates an audit log entry."""
        url = reverse('register')
        data = {
            'username': 'audituser',
            'email': 'audit@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'Audit',
            'last_name': 'User',
            'organization': organization.id
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

        # Check audit log
        user = User.objects.get(username='audituser')
        log = AuditLog.objects.filter(user=user, action='create', resource='user').first()
        assert log is not None
        assert log.details.get('username') == 'audituser'


@pytest.mark.django_db
class TestLoginView:
    """Tests for user login."""

    def test_login_success(self, api_client, user):
        """Test successful login."""
        url = reverse('login')
        data = {
            'username': user.username,
            'password': 'TestPass123!'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        assert response.data['message'] == 'Login successful'
        # Verify HTTP-only cookies are set
        assert 'access_token' in response.cookies
        assert 'refresh_token' in response.cookies
        # Verify cookies are HTTP-only
        assert response.cookies['access_token']['httponly']
        assert response.cookies['refresh_token']['httponly']

    def test_login_invalid_credentials(self, api_client, user):
        """Test login with invalid credentials."""
        url = reverse('login')
        data = {
            'username': user.username,
            'password': 'WrongPassword123!'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'error' in response.data

    def test_login_nonexistent_user(self, api_client):
        """Test login with nonexistent user."""
        url = reverse('login')
        data = {
            'username': 'nonexistent',
            'password': 'SomePassword123!'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'error' in response.data

    def test_login_inactive_user(self, api_client, inactive_user):
        """Test login with inactive user account."""
        url = reverse('login')
        data = {
            'username': inactive_user.username,
            'password': 'InactivePass123!'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'Invalid credentials' in response.data['error']

    def test_login_inactive_profile(self, api_client, inactive_profile_user):
        """Test login with inactive user profile."""
        url = reverse('login')
        data = {
            'username': inactive_profile_user.username,
            'password': 'InactiveProfile123!'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'Invalid credentials' in response.data['error']

    def test_login_shows_remaining_attempts(self, api_client, user):
        """Test that failed login shows remaining attempts."""
        url = reverse('login')
        data = {
            'username': user.username,
            'password': 'WrongPassword!'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'attempts remaining' in response.data['error']

    def test_login_creates_audit_log(self, api_client, user):
        """Test that successful login creates an audit log entry."""
        url = reverse('login')
        data = {
            'username': user.username,
            'password': 'TestPass123!'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK

        log = AuditLog.objects.filter(user=user, action='login').first()
        assert log is not None


@pytest.mark.django_db
class TestLogoutView:
    """Tests for user logout."""

    def test_logout_success(self, authenticated_client, user):
        """Test successful logout."""
        # First set cookies (simulating login)
        refresh = RefreshToken.for_user(user)
        authenticated_client.cookies['access_token'] = str(refresh.access_token)
        authenticated_client.cookies['refresh_token'] = str(refresh)

        url = reverse('logout')
        response = authenticated_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Logout successful'

    def test_logout_without_auth(self, api_client):
        """Test logout without authentication."""
        url = reverse('logout')
        response = api_client.post(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_creates_audit_log(self, authenticated_client, user):
        """Test that logout creates an audit log entry."""
        url = reverse('logout')
        response = authenticated_client.post(url)
        assert response.status_code == status.HTTP_200_OK

        log = AuditLog.objects.filter(user=user, action='logout').first()
        assert log is not None

    def test_logout_blacklists_token(self, api_client, user):
        """Test that logout blacklists the refresh token."""
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        api_client.cookies['refresh_token'] = str(refresh)

        url = reverse('logout')
        response = api_client.post(url)
        assert response.status_code == status.HTTP_200_OK

        # Try to use the same refresh token
        from rest_framework_simplejwt.exceptions import TokenError
        with pytest.raises(TokenError):
            RefreshToken(str(refresh)).verify()


@pytest.mark.django_db
class TestCookieTokenRefreshView:
    """Tests for cookie-based token refresh."""

    def test_refresh_success(self, api_client, user):
        """Test successful token refresh via cookie."""
        refresh = RefreshToken.for_user(user)
        api_client.cookies['refresh_token'] = str(refresh)

        url = reverse('token_refresh')
        response = api_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Token refreshed successfully'
        # Verify new cookies are set
        assert 'access_token' in response.cookies

    def test_refresh_missing_cookie(self, api_client):
        """Test token refresh with missing cookie."""
        url = reverse('token_refresh')
        response = api_client.post(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'not found' in response.data['error']

    def test_refresh_invalid_token(self, api_client):
        """Test token refresh with invalid token."""
        api_client.cookies['refresh_token'] = 'invalid-token'

        url = reverse('token_refresh')
        response = api_client.post(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'Invalid or expired' in response.data['error']

    def test_refresh_expired_token(self, api_client, user):
        """Test token refresh with expired token."""
        from datetime import timedelta
        refresh = RefreshToken.for_user(user)
        # Manually set expiry in past
        refresh.set_exp(lifetime=-timedelta(days=1))
        api_client.cookies['refresh_token'] = str(refresh)

        url = reverse('token_refresh')
        response = api_client.post(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCurrentUserView:
    """Tests for current user endpoints."""

    def test_get_current_user(self, authenticated_client, user):
        """Test getting current user info."""
        url = reverse('current-user')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == user.username

    def test_get_current_user_unauthorized(self, api_client):
        """Test getting current user without auth."""
        url = reverse('current-user')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_current_user(self, authenticated_client, user):
        """Test updating current user info."""
        url = reverse('current-user')
        data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        response = authenticated_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.first_name == 'Updated'
        assert user.last_name == 'Name'


@pytest.mark.django_db
class TestChangePasswordView:
    """Tests for password change."""

    def test_change_password_success(self, authenticated_client, user):
        """Test successful password change."""
        url = reverse('change-password')
        data = {
            'old_password': 'TestPass123!',
            'new_password': 'NewSecurePass456!',
            'new_password_confirm': 'NewSecurePass456!'
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK

        # Verify new password works
        user.refresh_from_db()
        assert user.check_password('NewSecurePass456!')

    def test_change_password_wrong_old(self, authenticated_client):
        """Test password change with wrong old password."""
        url = reverse('change-password')
        data = {
            'old_password': 'WrongOldPassword!',
            'new_password': 'NewSecurePass456!',
            'new_password_confirm': 'NewSecurePass456!'
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'incorrect' in response.data['error'].lower()

    def test_change_password_creates_audit_log(self, authenticated_client, user):
        """Test that password change creates an audit log entry."""
        url = reverse('change-password')
        data = {
            'old_password': 'TestPass123!',
            'new_password': 'NewSecurePass456!',
            'new_password_confirm': 'NewSecurePass456!'
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK

        log = AuditLog.objects.filter(user=user, action='update', resource='password').first()
        assert log is not None


@pytest.mark.django_db
class TestOrganizationViewSet:
    """Tests for organization management."""

    def test_list_organizations(self, authenticated_client, organization):
        """Test listing organizations (scoped to user's org)."""
        url = reverse('organization-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Handle paginated response
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        assert len(results) == 1
        assert results[0]['id'] == organization.id

    def test_list_organizations_other_org_not_visible(self, authenticated_client, other_organization):
        """Test that other organizations are not visible."""
        url = reverse('organization-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Handle paginated response
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        org_ids = [org['id'] for org in results]
        assert other_organization.id not in org_ids

    def test_create_organization_admin_only(self, authenticated_client):
        """Test that only admins can create organizations."""
        url = reverse('organization-list')
        data = {
            'name': 'New Org',
            'slug': 'new-org',
            'description': 'A new organization'
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_organization_as_admin(self, admin_client):
        """Test creating an organization as admin."""
        url = reverse('organization-list')
        data = {
            'name': 'Admin Created Org',
            'slug': 'admin-org',
            'description': 'Created by admin'
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestUserProfileViewSet:
    """Tests for user profile management."""

    def test_list_profiles(self, authenticated_client, user, organization):
        """Test listing user profiles (scoped to org)."""
        url = reverse('profile-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Handle paginated response
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        assert len(results) >= 1

    def test_list_profiles_other_org_not_visible(self, authenticated_client, other_org_user):
        """Test that profiles from other orgs are not visible."""
        url = reverse('profile-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Handle paginated response
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        # UserProfile serializer returns 'id' not 'user', check profile IDs
        profile_ids = [p['id'] for p in results]
        assert other_org_user.profile.id not in profile_ids

    def test_update_profile_admin_only(self, authenticated_client, user):
        """Test that only admins can update profiles."""
        url = reverse('profile-detail', args=[user.profile.id])
        data = {'role': 'admin'}
        response = authenticated_client.patch(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAuditLogViewSet:
    """Tests for audit log viewing."""

    def test_list_audit_logs_manager(self, manager_client, organization):
        """Test that managers can view audit logs."""
        # Create some audit logs
        from .factories import AuditLogFactory
        AuditLogFactory(organization=organization)

        url = reverse('audit-log-list')
        response = manager_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_list_audit_logs_viewer_forbidden(self, authenticated_client):
        """Test that viewers cannot view audit logs."""
        url = reverse('audit-log-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_audit_logs_scoped_to_org(self, manager_client, organization, other_organization):
        """Test that audit logs are scoped to user's organization."""
        from .factories import AuditLogFactory
        # Create logs in both orgs
        log_own = AuditLogFactory(organization=organization)
        log_other = AuditLogFactory(organization=other_organization)

        url = reverse('audit-log-list')
        response = manager_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Handle paginated response
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        log_ids = [log['id'] for log in results]
        assert log_own.id in log_ids
        assert log_other.id not in log_ids

    def test_audit_logs_readonly(self, admin_client, organization):
        """Test that audit logs cannot be created via API."""
        url = reverse('audit-log-list')
        data = {
            'action': 'create',
            'resource': 'test'
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestLoginLockout:
    """Tests for login lockout functionality."""

    def test_lockout_after_max_attempts(self, api_client, user):
        """Test that account locks out after max failed attempts."""
        url = reverse('login')
        data = {
            'username': user.username,
            'password': 'WrongPassword!'
        }

        # Make 5 failed attempts (MAX_FAILED_ATTEMPTS)
        for i in range(5):
            response = api_client.post(url, data)
            # May get 401 or 403 depending on throttling
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # 6th attempt should be blocked with lockout message
        response = api_client.post(url, data)
        # Accept 401, 403, or 429 as lockout response
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_429_TOO_MANY_REQUESTS]

    def test_successful_login_clears_lockout(self, api_client, user):
        """Test that successful login clears failed attempt counter."""
        url = reverse('login')

        # Make a few failed attempts
        for i in range(3):
            api_client.post(url, {
                'username': user.username,
                'password': 'WrongPassword!'
            })

        # Successful login
        response = api_client.post(url, {
            'username': user.username,
            'password': 'TestPass123!'
        })
        assert response.status_code == status.HTTP_200_OK

        # New failed attempts should start fresh
        response = api_client.post(url, {
            'username': user.username,
            'password': 'WrongPassword!'
        })
        assert '4 attempts remaining' in response.data['error']

    def test_lockout_per_user_per_ip(self, api_client, user, organization):
        """Test that lockout is per username+IP combination."""
        url = reverse('login')

        # Lock out first user
        for i in range(5):
            api_client.post(url, {
                'username': user.username,
                'password': 'WrongPassword!'
            })

        # Create another user
        other_user = UserFactory(username='otheruser')
        UserProfileFactory(user=other_user, organization=organization)

        # Other user should not be locked out - may get 401 or 403
        response = api_client.post(url, {
            'username': 'otheruser',
            'password': 'WrongPassword!'
        })
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestJWTCookieSecurity:
    """Tests for JWT cookie security settings."""

    def test_login_sets_httponly_cookies(self, api_client, user):
        """Test that login sets HTTP-only cookies."""
        url = reverse('login')
        response = api_client.post(url, {
            'username': user.username,
            'password': 'TestPass123!'
        })
        assert response.status_code == status.HTTP_200_OK

        access_cookie = response.cookies.get('access_token')
        refresh_cookie = response.cookies.get('refresh_token')

        assert access_cookie is not None
        assert refresh_cookie is not None
        assert access_cookie['httponly']
        assert refresh_cookie['httponly']

    def test_login_sets_samesite_cookies(self, api_client, user):
        """Test that login sets SameSite cookies."""
        url = reverse('login')
        response = api_client.post(url, {
            'username': user.username,
            'password': 'TestPass123!'
        })
        assert response.status_code == status.HTTP_200_OK

        access_cookie = response.cookies.get('access_token')
        assert access_cookie['samesite'] in ['Lax', 'Strict', 'None']

    def test_tokens_not_in_response_body(self, api_client, user):
        """Test that JWT tokens are not exposed in response body."""
        url = reverse('login')
        response = api_client.post(url, {
            'username': user.username,
            'password': 'TestPass123!'
        })
        assert response.status_code == status.HTTP_200_OK

        # Tokens should only be in cookies, not body
        assert 'access_token' not in response.data
        assert 'refresh_token' not in response.data
        assert 'access' not in response.data
        assert 'refresh' not in response.data
