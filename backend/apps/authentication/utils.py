"""
Utility functions for authentication
"""
import hashlib
import logging
from django.conf import settings
from django.core.cache import cache
from .models import AuditLog

logger = logging.getLogger('authentication')

# Rate limiting settings for failed login attempts
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes in seconds


def get_client_ip(request):
    """
    Get client IP address from request.

    Finding A2: forwarded headers (X-Real-IP, X-Forwarded-For) are honored
    only when the immediate connection (REMOTE_ADDR) is in
    settings.TRUSTED_PROXIES. Without this gate, any client could spoof
    X-Real-IP to defeat the per-IP-scoped lockout key (record_failed_login)
    and pollute audit logs.

    settings.TRUSTED_PROXIES defaults to an empty list — meaning forwarded
    headers are ignored unless the deployment explicitly trusts a proxy IP.
    For Docker dev, set TRUSTED_PROXIES=127.0.0.1,172.17.0.1 (or whatever
    the bridge subnet is). For production behind nginx, set it to the
    nginx loopback address.
    """
    remote_addr = request.META.get('REMOTE_ADDR', '0.0.0.0')
    trusted_proxies = getattr(settings, 'TRUSTED_PROXIES', []) or []

    if remote_addr in trusted_proxies:
        # Honor forwarded headers from a trusted upstream proxy.
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip.strip()
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # First IP is closest to the client; rest are intermediate hops.
            return x_forwarded_for.split(',')[0].strip()

    # Untrusted (direct) connection or no forwarded headers — use REMOTE_ADDR.
    return remote_addr


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

    # Finding A3: preserve the original window from first failure. The prior
    # cache.set(...) overwrote TTL on every failure, letting a slow attacker
    # pace attempts indefinitely. Use add() to seed the counter on first
    # failure (with the full LOCKOUT_DURATION), then incr() for subsequent
    # failures within that fixed window. Once the window expires, the key
    # is gone and a fresh attacker gets a fresh window — same lockout
    # ergonomics for legitimate users, no slow-rate bypass.
    cache.add(key, 0, LOCKOUT_DURATION)
    failed_attempts = cache.incr(key)

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
