import logging

from config.logging_filters import RedactSensitiveFilter


def _record(message: str) -> logging.LogRecord:
    return logging.LogRecord("x", logging.INFO, "", 0, message, (), None)


def test_redacts_aikey():
    record = _record('login error: {"aiApiKey": "sk-secret123", "user": "alice"}')
    RedactSensitiveFilter().filter(record)
    assert "sk-secret123" not in record.getMessage()
    assert "***REDACTED***" in record.getMessage()
    assert "alice" in record.getMessage()


def test_redacts_password_kv():
    record = _record("auth fail: password=hunter2")
    RedactSensitiveFilter().filter(record)
    assert "hunter2" not in record.getMessage()
    assert "***REDACTED***" in record.getMessage()


def test_redacts_authorization_header():
    record = _record("request: Authorization: Bearer eyJhbGc...")
    RedactSensitiveFilter().filter(record)
    assert "eyJhbGc" not in record.getMessage()
    assert "***REDACTED***" in record.getMessage()
