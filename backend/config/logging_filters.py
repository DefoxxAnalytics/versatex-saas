"""Logging filters that scrub sensitive values before records hit handlers.

The security file handler uses the `verbose` formatter, which can capture
full exception messages. Those messages may include request bodies, env
values, or stack-trace locals containing credentials (aiApiKey, password,
Authorization headers, etc.). Without redaction these values land in
`logs/security.log` and persist on the container volume.
"""

import logging
import re


_SENSITIVE_KEYS = {
    'aiApiKey',
    'password',
    'Authorization',
    'authorization',
    'token',
    'access_token',
    'refresh_token',
    'api_key',
    'apiKey',
    'secret',
    'SECRET_KEY',
}


_PATTERNS = [
    re.compile(
        rf"(['\"]?{key}['\"]?\s*[:=]\s*['\"]?)[^'\"\s,}}]+",
        re.IGNORECASE,
    )
    for key in _SENSITIVE_KEYS
]


# `Authorization: Bearer <jwt>` (and `Basic <base64>`) carry the secret AFTER
# a scheme word. The generic key=value pattern stops at the space between the
# header name and the scheme, leaving the actual token in the clear. This
# pattern explicitly consumes the scheme + token pair so the credential
# itself never lands in the log.
_AUTH_SCHEME_PATTERN = re.compile(
    r"(authorization\s*:\s*)(bearer|basic|token|digest)\s+\S+",
    re.IGNORECASE,
)


class RedactSensitiveFilter(logging.Filter):
    """Mask sensitive keys in log records (msg + args)."""

    def filter(self, record):
        msg = record.getMessage()
        msg = _AUTH_SCHEME_PATTERN.sub(r'\1***REDACTED***', msg)
        for pattern in _PATTERNS:
            msg = pattern.sub(r'\1***REDACTED***', msg)
        record.msg = msg
        record.args = ()
        return True
