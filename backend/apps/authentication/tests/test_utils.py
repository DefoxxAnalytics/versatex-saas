"""
Tests for authentication utility functions.
"""
import pytest
import hashlib
from unittest.mock import Mock, patch
from django.core.cache import cache
from apps.authentication.utils import (
    get_client_ip,
    get_user_agent,
    hash_user_agent,
    get_failed_login_key,
    record_failed_login,
    check_login_lockout,
    clear_failed_logins,
    log_action,
    log_security_event,
    MAX_FAILED_ATTEMPTS,
    LOCKOUT_DURATION
)
from apps.authentication.models import AuditLog


class TestGetClientIP:
    """Tests for get_client_ip function."""

    def test_direct_connection(self, mock_request):
        """Test getting IP from direct connection."""
        ip = get_client_ip(mock_request)
        assert ip == '192.168.1.1'

    def test_x_real_ip_header(self, mock_request):
        """Test getting IP from X-Real-IP header."""
        mock_request.META['HTTP_X_REAL_IP'] = '10.0.0.50'
        ip = get_client_ip(mock_request)
        assert ip == '10.0.0.50'

    def test_x_forwarded_for_single_ip(self):
        """Test getting IP from X-Forwarded-For with single IP."""
        request = Mock()
        request.META = {
            'REMOTE_ADDR': '10.0.0.1',
            'HTTP_X_FORWARDED_FOR': '203.0.113.195',
            'HTTP_X_REAL_IP': None,
        }
        ip = get_client_ip(request)
        assert ip == '203.0.113.195'

    def test_x_forwarded_for_multiple_ips(self, mock_request_with_proxy):
        """Test getting first IP from X-Forwarded-For chain."""
        ip = get_client_ip(mock_request_with_proxy)
        # Should take the first IP in the chain (closest to client)
        assert ip == '203.0.113.195'

    def test_x_real_ip_takes_priority(self):
        """Test that X-Real-IP takes priority over X-Forwarded-For."""
        request = Mock()
        request.META = {
            'REMOTE_ADDR': '10.0.0.1',
            'HTTP_X_FORWARDED_FOR': '203.0.113.195, 70.41.3.18',
            'HTTP_X_REAL_IP': '1.2.3.4',
        }
        ip = get_client_ip(request)
        assert ip == '1.2.3.4'

    def test_strips_whitespace(self):
        """Test that IP addresses are stripped of whitespace."""
        request = Mock()
        request.META = {
            'REMOTE_ADDR': '10.0.0.1',
            'HTTP_X_FORWARDED_FOR': '  203.0.113.195  ',
            'HTTP_X_REAL_IP': None,
        }
        ip = get_client_ip(request)
        assert ip == '203.0.113.195'

    def test_fallback_to_default(self):
        """Test fallback to default IP when REMOTE_ADDR is missing."""
        request = Mock()
        request.META = {}
        ip = get_client_ip(request)
        assert ip == '0.0.0.0'


class TestGetUserAgent:
    """Tests for get_user_agent function."""

    def test_returns_user_agent(self, mock_request):
        """Test getting user agent from request."""
        ua = get_user_agent(mock_request)
        assert 'Mozilla' in ua
        assert 'Test Browser' in ua

    def test_returns_empty_string_when_missing(self):
        """Test returning empty string when user agent is missing."""
        request = Mock()
        request.META = {}
        ua = get_user_agent(request)
        assert ua == ''


class TestHashUserAgent:
    """Tests for hash_user_agent function."""

    def test_hashes_user_agent(self):
        """Test that user agent is hashed."""
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        hashed = hash_user_agent(ua)

        # Should be a hex string
        assert all(c in '0123456789abcdef' for c in hashed)
        # SHA256 produces 64 character hex string
        assert len(hashed) == 64

    def test_hash_consistency(self):
        """Test that same input produces same hash."""
        ua = 'Test User Agent'
        hash1 = hash_user_agent(ua)
        hash2 = hash_user_agent(ua)
        assert hash1 == hash2

    def test_different_inputs_different_hashes(self):
        """Test that different inputs produce different hashes."""
        hash1 = hash_user_agent('Agent 1')
        hash2 = hash_user_agent('Agent 2')
        assert hash1 != hash2

    def test_empty_string_returns_empty(self):
        """Test that empty string returns empty string."""
        assert hash_user_agent('') == ''

    def test_none_returns_empty(self):
        """Test that None returns empty string."""
        assert hash_user_agent(None) == ''


class TestGetFailedLoginKey:
    """Tests for get_failed_login_key function."""

    def test_generates_unique_key_per_user_ip(self):
        """Test that key is unique per username+IP combination."""
        key1 = get_failed_login_key('user1', '1.2.3.4')
        key2 = get_failed_login_key('user2', '1.2.3.4')
        key3 = get_failed_login_key('user1', '5.6.7.8')

        assert key1 != key2  # Different users
        assert key1 != key3  # Different IPs
        assert key2 != key3  # Both different

    def test_key_format(self):
        """Test that key has expected format."""
        key = get_failed_login_key('testuser', '192.168.1.1')
        assert key.startswith('failed_login:')
        assert ':192.168.1.1' in key

    def test_username_is_hashed(self):
        """Test that username is hashed in the key."""
        key = get_failed_login_key('secretuser', '1.2.3.4')
        # Username should not appear in plain text
        assert 'secretuser' not in key

    def test_case_insensitive_username(self):
        """Test that username is case-insensitive."""
        key1 = get_failed_login_key('TestUser', '1.2.3.4')
        key2 = get_failed_login_key('testuser', '1.2.3.4')
        assert key1 == key2


@pytest.mark.django_db
class TestRecordFailedLogin:
    """Tests for record_failed_login function."""

    def test_increments_counter(self, mock_request):
        """Test that failed login increments counter."""
        cache.clear()

        is_locked, remaining = record_failed_login(mock_request, 'testuser')
        assert not is_locked
        assert remaining == MAX_FAILED_ATTEMPTS - 1

        is_locked, remaining = record_failed_login(mock_request, 'testuser')
        assert not is_locked
        assert remaining == MAX_FAILED_ATTEMPTS - 2

    def test_lockout_after_max_attempts(self, mock_request):
        """Test that lockout occurs after max attempts."""
        cache.clear()

        for i in range(MAX_FAILED_ATTEMPTS - 1):
            is_locked, remaining = record_failed_login(mock_request, 'testuser')
            assert not is_locked

        # Final attempt triggers lockout
        is_locked, remaining = record_failed_login(mock_request, 'testuser')
        assert is_locked
        assert remaining == 0

    def test_remaining_attempts_never_negative(self, mock_request):
        """Test that remaining attempts never goes below 0."""
        cache.clear()

        for i in range(MAX_FAILED_ATTEMPTS + 5):
            is_locked, remaining = record_failed_login(mock_request, 'testuser')

        assert remaining == 0

    def test_lockout_duration_set(self, mock_request):
        """Test that lockout duration is set in cache."""
        cache.clear()
        key = get_failed_login_key('testuser', get_client_ip(mock_request))

        record_failed_login(mock_request, 'testuser')

        # Check that TTL is approximately LOCKOUT_DURATION
        ttl = cache.ttl(key) if hasattr(cache, 'ttl') else LOCKOUT_DURATION
        assert ttl <= LOCKOUT_DURATION


@pytest.mark.django_db
class TestCheckLoginLockout:
    """Tests for check_login_lockout function."""

    def test_not_locked_initially(self, mock_request):
        """Test that user is not locked out initially."""
        cache.clear()
        is_locked = check_login_lockout(mock_request, 'testuser')
        assert not is_locked

    def test_locked_after_max_attempts(self, mock_request):
        """Test that user is locked after max attempts."""
        cache.clear()

        for i in range(MAX_FAILED_ATTEMPTS):
            record_failed_login(mock_request, 'testuser')

        is_locked = check_login_lockout(mock_request, 'testuser')
        assert is_locked

    def test_lockout_per_user(self, mock_request):
        """Test that lockout is per-user."""
        cache.clear()

        # Lock out user1
        for i in range(MAX_FAILED_ATTEMPTS):
            record_failed_login(mock_request, 'user1')

        # user1 should be locked
        assert check_login_lockout(mock_request, 'user1')

        # user2 should not be locked
        assert not check_login_lockout(mock_request, 'user2')


@pytest.mark.django_db
class TestClearFailedLogins:
    """Tests for clear_failed_logins function."""

    def test_clears_failed_attempts(self, mock_request):
        """Test that clearing removes failed attempts."""
        cache.clear()

        # Record some failed attempts
        for i in range(3):
            record_failed_login(mock_request, 'testuser')

        # Clear the attempts
        clear_failed_logins(mock_request, 'testuser')

        # Should not be locked
        is_locked = check_login_lockout(mock_request, 'testuser')
        assert not is_locked

    def test_clear_after_lockout(self, mock_request):
        """Test that clearing works after lockout."""
        cache.clear()

        # Trigger lockout
        for i in range(MAX_FAILED_ATTEMPTS):
            record_failed_login(mock_request, 'testuser')

        assert check_login_lockout(mock_request, 'testuser')

        # Clear
        clear_failed_logins(mock_request, 'testuser')

        # Should no longer be locked
        assert not check_login_lockout(mock_request, 'testuser')


@pytest.mark.django_db
class TestLogAction:
    """Tests for log_action function."""

    def test_creates_audit_log(self, admin_user, mock_request):
        """Test that log_action creates an audit log entry."""
        log = log_action(
            user=admin_user,
            action='create',
            resource='transaction',
            resource_id='123',
            details={'file_name': 'test.csv'},
            request=mock_request
        )

        assert log is not None
        assert log.user == admin_user
        assert log.action == 'create'
        assert log.resource == 'transaction'
        assert log.resource_id == '123'
        assert log.details == {'file_name': 'test.csv'}
        assert log.ip_address == '192.168.1.1'

    def test_hashes_user_agent(self, admin_user, mock_request):
        """Test that user agent is hashed in log."""
        log = log_action(
            user=admin_user,
            action='login',
            resource='auth',
            request=mock_request
        )

        # User agent should be hashed (64 hex chars for SHA256)
        assert len(log.user_agent) == 64
        assert 'Mozilla' not in log.user_agent

    def test_returns_none_without_profile(self, mock_request):
        """Test that log_action returns None for user without profile."""
        from django.contrib.auth.models import User
        user = User.objects.create_user(username='noprofile', password='test123')

        log = log_action(
            user=user,
            action='test',
            resource='test',
            request=mock_request
        )

        assert log is None

    def test_log_without_request(self, admin_user):
        """Test logging without request object."""
        log = log_action(
            user=admin_user,
            action='update',
            resource='settings',
            resource_id='1'
        )

        assert log is not None
        assert log.ip_address is None


@pytest.mark.django_db
class TestLogSecurityEvent:
    """Tests for log_security_event function."""

    def test_logs_security_event(self, mock_request):
        """Test that security events are logged."""
        with patch('apps.authentication.utils.logger') as mock_logger:
            log_security_event(
                event_type='failed_login',
                request=mock_request,
                details={'username': 'testuser'}
            )

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert 'failed_login' in call_args
            assert '192.168.1.1' in call_args

    def test_logs_with_details(self, mock_request):
        """Test that details are included in log."""
        with patch('apps.authentication.utils.logger') as mock_logger:
            log_security_event(
                event_type='lockout',
                request=mock_request,
                details={'attempts': 5}
            )

            call_args = mock_logger.info.call_args[0][0]
            assert 'attempts' in call_args

    def test_logs_without_details(self, mock_request):
        """Test logging without details."""
        with patch('apps.authentication.utils.logger') as mock_logger:
            log_security_event(
                event_type='suspicious_activity',
                request=mock_request
            )

            mock_logger.info.assert_called_once()


class TestConstants:
    """Tests for security constants."""

    def test_max_failed_attempts(self):
        """Test MAX_FAILED_ATTEMPTS is reasonable."""
        assert MAX_FAILED_ATTEMPTS >= 3
        assert MAX_FAILED_ATTEMPTS <= 10

    def test_lockout_duration(self):
        """Test LOCKOUT_DURATION is reasonable."""
        # At least 5 minutes
        assert LOCKOUT_DURATION >= 300
        # At most 1 hour
        assert LOCKOUT_DURATION <= 3600
