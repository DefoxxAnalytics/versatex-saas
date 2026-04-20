"""
Custom middleware for security and API versioning.
"""
import logging

# Logger for tracking legacy API usage
legacy_api_logger = logging.getLogger('legacy_api')


class DeprecationMiddleware:
    """
    Middleware to add deprecation headers to legacy API endpoints.

    Legacy endpoints (without /v1/ in the path) are deprecated in favor of
    versioned endpoints (/api/v1/...). This middleware adds standard HTTP
    deprecation headers to help clients migrate.

    Headers added:
    - Deprecation: true
    - Sunset: Date when the legacy endpoints will be removed
    - Link: URL to the new versioned endpoint
    """

    # Legacy endpoint prefixes (without /v1/)
    LEGACY_PREFIXES = (
        '/api/auth/',
        '/api/procurement/',
        '/api/analytics/',
    )

    # Sunset date for legacy endpoints (RFC 7231 HTTP-date format)
    # Updated to June 1, 2026 to give clients more time to migrate
    SUNSET_DATE = 'Mon, 01 Jun 2026 00:00:00 GMT'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Check if this is a legacy endpoint
        path = request.path
        if self._is_legacy_endpoint(path):
            # Log legacy API usage for monitoring and migration tracking
            self._log_legacy_usage(request)

            response['Deprecation'] = 'true'
            response['Sunset'] = self.SUNSET_DATE

            # Add link to versioned endpoint
            versioned_path = self._get_versioned_path(path)
            if versioned_path:
                # Use the Link header format from RFC 8594
                response['Link'] = f'<{versioned_path}>; rel="successor-version"'

        return response

    def _log_legacy_usage(self, request):
        """Log legacy API usage for monitoring and migration tracking."""
        user_id = getattr(request.user, 'id', None) if hasattr(request, 'user') else None
        legacy_api_logger.warning(
            'Legacy API endpoint accessed',
            extra={
                'path': request.path,
                'method': request.method,
                'user_id': user_id,
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],  # Truncate user agent
            }
        )

    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP in the chain (original client)
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def _is_legacy_endpoint(self, path: str) -> bool:
        """Check if the path is a legacy (non-versioned) endpoint."""
        # Must start with one of the legacy prefixes
        if not any(path.startswith(prefix) for prefix in self.LEGACY_PREFIXES):
            return False

        # Must NOT contain /v1/ (which would make it a versioned endpoint)
        return '/v1/' not in path

    def _get_versioned_path(self, path: str) -> str:
        """Convert a legacy path to its versioned equivalent."""
        # Replace /api/auth/ with /api/v1/auth/, etc.
        for prefix in self.LEGACY_PREFIXES:
            if path.startswith(prefix):
                suffix = path[len(prefix):]
                versioned_prefix = prefix.replace('/api/', '/api/v1/')
                return f'{versioned_prefix}{suffix}'
        return None
