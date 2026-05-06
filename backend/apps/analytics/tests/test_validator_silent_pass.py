"""Finding #10: validator must not silently pass on crash.

When `AIProviderManager._validate_and_adjust_response` raises mid-run, the
returned response must carry `_validation = {validated: False,
reason: validator_crashed}`, NOT be missing.

Three downstream sites in `ai_providers.py` (lines ~1291, ~1365, ~1449)
read `result.get('_validation', {}).get('validated', True)` -- defaulting
the missing key to `True`. With the buggy try/except, a validator crash
produces a response with no `_validation` key, and downstream silently
treats hallucinated AI output as validated.

The fix: initialize `response['_validation']` to the failure-state marker
BEFORE the try block; the try overwrites on success. A crash leaves the
marker visible.
"""
from unittest.mock import MagicMock

from django.test import TestCase

from apps.analytics.ai_providers import AIProviderManager


class TestValidatorSilentPass(TestCase):
    """Validator crash must not produce a response missing _validation."""

    def _make_manager_with_crashing_validator(self):
        """Build a manager whose validator's .validate() raises."""
        manager = AIProviderManager.__new__(AIProviderManager)

        crashing_validator = MagicMock()
        crashing_validator.validate.side_effect = RuntimeError(
            "simulated validator crash"
        )
        manager._validator = crashing_validator
        return manager

    def test_validator_crash_returns_unvalidated_marker(self):
        manager = self._make_manager_with_crashing_validator()

        response = {"text": "fake llm output", "confidence": 0.9}
        result = manager._validate_and_adjust_response(
            response,
            source_data={"total_spend": 100},
            request_type="enhance",
        )

        validation = result.get("_validation")
        self.assertIsNotNone(
            validation,
            "validator crashed but result has NO _validation key; "
            "downstream defaults missing to validated=True (silent pass).",
        )
        self.assertFalse(
            validation.get("validated", True),
            f"validator crashed but _validation={validation!r}; "
            f"downstream defaults missing 'validated' to True (silent pass).",
        )
        self.assertEqual(
            validation.get("reason"),
            "validator_crashed",
            f"expected reason='validator_crashed', got {validation!r}",
        )

    def test_downstream_consumer_sees_unvalidated_on_crash(self):
        """Simulate the downstream `validation_info.get('validated', True)` read."""
        manager = self._make_manager_with_crashing_validator()

        result = manager._validate_and_adjust_response(
            {"text": "x"}, source_data=None, request_type="enhance"
        )

        validation_info = result.get("_validation", {})
        validation_passed = validation_info.get("validated", True)
        self.assertFalse(
            validation_passed,
            "downstream silent-pass: a crashed validator was treated as validated.",
        )

    def test_no_validator_returns_response_unchanged(self):
        """Sanity: without a validator configured, the response passes through."""
        manager = AIProviderManager.__new__(AIProviderManager)
        manager._validator = None

        response = {"text": "x"}
        result = manager._validate_and_adjust_response(response, None, "enhance")

        self.assertIs(result, response)
        self.assertNotIn("_validation", result)
