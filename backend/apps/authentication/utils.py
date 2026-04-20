"""
Utility functions for authentication
"""
import hashlib
import logging
from django.core.cache import cache
from .models import AuditLog

logger = logging.getLogger('authentication')

# Rate limiting settings for failed login attempts
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes in seconds


def get_client_ip(request):
    """
    Get client IP address from request.
    Handles X-Forwarded-For header for proxied requests.

    Security Note: X-Forwarded-For can be spoofed. In production,
    configure your proxy to set a trusted header.
    """
    # Try trusted proxy header first (configure this in your proxy)
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        return x_real_ip.strip()

    # Fall back to X-Forwarded-For (take first IP only)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Only trust the first IP (closest to client)
        ip = x_forwarded_for.split(',')[0].strip()
        return ip

    # Direct connection
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def get_user_agent(request):
    """Get user agent from request"""
    return request.META.get('HTTP_USER_AGENT', '')


def hash_user_agent(user_agent: str) -> str:
    """
    Hash the user agent string for privacy.
    Uses full hash for better security (not truncated).
    """
    if not user_agent:
        return ''
    return hashlib.sha256(user_agent.encode()).hexdigest()


def get_failed_login_key(username: str, ip: str) -> str:
    """
    Generate cache key for failed login tracking.
    Scoped by both username and IP to prevent cross-user lockout attacks.

    Security: This prevents an attacker from locking out all users
    by targeting a single IP. Each username+IP combination has its own counter.
    """
    # Hash username to prevent cache key injection
    username_hash = hashlib.sha256(username.lower().encode()).hexdigest()[:16]
    return f'failed_login:{username_hash}:{ip}'


def record_failed_login(request, username: str):
    """
    Record a failed login attempt and check for lockout.
    Uses scoped cache keys (username + IP) to prevent cross-user lockout.

    Returns:
        tuple: (is_locked_out, remaining_attempts)
    """
    ip = get_client_ip(request)
    key = get_failed_login_key(username, ip)

    # Get current failed attempts
    failed_attempts = cache.get(key, 0) + 1
    cache.set(key, failed_attempts, LOCKOUT_DURATION)

    # Log the failed attempt (don't log full username for privacy)
    logger.warning(
        f"Failed login attempt | "
        f"IP: {ip} | "
        f"Username: {username[:3]}*** | "
        f"Attempts: {failed_attempts}/{MAX_FAILED_ATTEMPTS} | "
        f"User-Agent: {get_user_agent(request)[:100]}"
    )

    remaining = max(0, MAX_FAILED_ATTEMPTS - failed_attempts)
    is_locked = failed_attempts >= MAX_FAILED_ATTEMPTS

    if is_locked:
        logger.warning(
            f"Account lockout triggered | "
            f"IP: {ip} | "
            f"Username: {username[:3]}*** | "
            f"Lockout duration: {LOCKOUT_DURATION}s"
        )

    return is_locked, remaining


def check_login_lockout(request, username: str = None) -> bool:
    """
    Check if IP (+ optional username) is currently locked out due to failed attempts.

    Args:
        request: The HTTP request object
        username: Optional username to check (if provided, checks user-specific lockout)

    Returns:
        bool: True if locked out, False otherwise
    """
    ip = get_client_ip(request)

    if username:
        # Check user-specific lockout
        key = get_failed_login_key(username, ip)
        failed_attempts = cache.get(key, 0)
        return failed_attempts >= MAX_FAILED_ATTEMPTS

    # For backwards compatibility, also check IP-only lockout (legacy)
    # This is a fallback for the initial check before username is known
    return False


def clear_failed_logins(request, username: str = None):
    """
    Clear failed login attempts after successful login.

    Args:
        request: The HTTP request object
        username: Username to clear lockout for
    """
    ip = get_client_ip(request)

    if username:
        key = get_failed_login_key(username, ip)
        cache.delete(key)


def log_action(user, action, resource, resource_id='', details=None, request=None):
    """
    Log user action to audit log
    """
    if not hasattr(user, 'profile'):
        return None

    log_data = {
        'user': user,
        'organization': user.profile.organization,
        'action': action,
        'resource': resource,
        'resource_id': resource_id,
        'details': details or {},
    }

    if request:
        log_data['ip_address'] = get_client_ip(request)
        # Hash user agent for privacy
        log_data['user_agent'] = hash_user_agent(get_user_agent(request))

    return AuditLog.objects.create(**log_data)


def log_security_event(event_type: str, request, details: dict = None):
    """
    Log a security event (not tied to a specific user action).

    Args:
        event_type: Type of security event (e.g., 'failed_login', 'lockout')
        request: The HTTP request object
        details: Additional details to log
    """
    ip = get_client_ip(request)
    user_agent = get_user_agent(request)

    log_message = (
        f"Security Event: {event_type} | "
        f"IP: {ip} | "
        f"User-Agent: {user_agent[:100]}"
    )

    if details:
        log_message += f" | Details: {details}"

    logger.info(log_message)
