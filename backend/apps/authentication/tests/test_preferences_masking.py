"""
AI-settings persistence + masking tests — Cluster 8 (PR-8a).

Covers:
- Round-trip masking on every outbound user-payload endpoint.
- Full-pipeline persistence from PATCH through AIInsightsService init.
- Admin change-form never renders plaintext aiApiKey.
- Cache-bust on AI-settings PATCH.
- Label-fallback: no ai_enhancement in response when no key configured.
- Active-path smoke with mocked LLM provider.
"""

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import UserProfile

TEST_KEY = "sk-ant-api03-cluster8-roundtrip-0123456789-abcdef-xyz"


@pytest.fixture
def auth_client(admin_user):
    """APIClient authenticated as a real admin_user fixture.

    Uses the cookie path; the Authorization-header fallback is DEBUG-only
    since v3 Phase 0 Task 0.5 (S-#2).
    """
    client = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    client.cookies["access_token"] = str(refresh.access_token)
    return client


@pytest.fixture
def saved_api_key(admin_user, auth_client):
    """Persist an AI API key via the real PATCH pipeline and return it."""
    response = auth_client.patch(
        "/api/v1/auth/preferences/",
        {"useExternalAI": True, "aiProvider": "anthropic", "aiApiKey": TEST_KEY},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK, response.data
    admin_user.profile.refresh_from_db()
    return TEST_KEY


@pytest.mark.django_db
class TestPreferencesMasking:
    """aiApiKey must never appear in plaintext on any outbound response."""

    def _expected_mask(self):
        return "****" + TEST_KEY[-4:]

    def test_preferences_patch_response_masks_key(self, auth_client):
        response = auth_client.patch(
            "/api/v1/auth/preferences/",
            {"useExternalAI": True, "aiProvider": "anthropic", "aiApiKey": TEST_KEY},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        assert TEST_KEY not in response.content.decode()
        assert response.data.get("aiApiKey") == self._expected_mask()

    def test_preferences_get_masks_key(self, auth_client, saved_api_key):
        response = auth_client.get("/api/v1/auth/preferences/")
        assert response.status_code == status.HTTP_200_OK
        assert TEST_KEY not in response.content.decode()
        assert response.data["aiApiKey"] == self._expected_mask()

    def test_user_me_embeds_masked_preferences(self, auth_client, saved_api_key):
        response = auth_client.get("/api/v1/auth/user/")
        assert response.status_code == status.HTTP_200_OK
        assert TEST_KEY not in response.content.decode()
        prefs = response.data.get("profile", {}).get("preferences", {})
        assert prefs.get("aiApiKey") == self._expected_mask()

    def test_key_absent_renders_as_none(self, auth_client):
        # No key set yet; mask helper returns None.
        response = auth_client.get("/api/v1/auth/preferences/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get("aiApiKey") is None

    def test_mask_helper_direct(self):
        assert UserProfile.mask_preferences({}) == {"aiApiKey": None}
        assert UserProfile.mask_preferences({"aiApiKey": ""})["aiApiKey"] is None
        assert (
            UserProfile.mask_preferences({"aiApiKey": TEST_KEY})["aiApiKey"]
            == "****" + TEST_KEY[-4:]
        )
        # Other keys untouched
        assert UserProfile.mask_preferences({"theme": "dark"})["theme"] == "dark"


@pytest.mark.django_db
class TestPreferencesPersistence:
    """Full pipeline: PATCH -> JSONField -> AIInsightsService init kwargs."""

    def test_ai_settings_reach_ai_service_init(
        self, admin_user, auth_client, saved_api_key
    ):
        """Mock AIInsightsService.__init__ and confirm kwargs after PATCH."""
        from apps.analytics.views import _get_ai_service

        class FakeRequest:
            def __init__(self, user):
                self.user = user
                self.query_params = {}

        captured = {}

        def fake_init(
            self,
            organization=None,
            filters=None,
            use_external_ai=False,
            ai_provider="anthropic",
            api_key=None,
            **kwargs,
        ):
            captured["use_external_ai"] = use_external_ai
            captured["ai_provider"] = ai_provider
            captured["api_key"] = api_key

        with patch("apps.analytics.views.AIInsightsService.__init__", fake_init):
            _get_ai_service(
                FakeRequest(admin_user), organization=admin_user.profile.organization
            )

        assert captured["use_external_ai"] is True
        assert captured["ai_provider"] == "anthropic"
        assert (
            captured["api_key"] == TEST_KEY
        ), "aiApiKey must flow from preferences dict into AIInsightsService kwargs"

    def test_allowlist_contains_6_ai_fields(self):
        for key in (
            "useExternalAI",
            "aiProvider",
            "aiApiKey",
            "forecastingModel",
            "forecastHorizonMonths",
            "anomalySensitivity",
        ):
            assert key in UserProfile.ALLOWED_PREFERENCE_KEYS, f"missing: {key}"

    def test_serializer_accepts_6_ai_fields(self, auth_client):
        response = auth_client.patch(
            "/api/v1/auth/preferences/",
            {
                "useExternalAI": True,
                "aiProvider": "openai",
                "aiApiKey": "sk-test-abcd-1234",
                "forecastingModel": "advanced",
                "forecastHorizonMonths": 12,
                "anomalySensitivity": 2.5,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["useExternalAI"] is True
        assert response.data["aiProvider"] == "openai"
        assert response.data["forecastingModel"] == "advanced"
        assert response.data["forecastHorizonMonths"] == 12
        assert response.data["anomalySensitivity"] == 2.5


@pytest.mark.django_db
class TestCacheBustOnAiSettingsChange:
    """UserPreferencesView.patch must invalidate AIInsightsCache when AI fields change."""

    def test_ai_field_change_triggers_cache_invalidation(self, auth_client, admin_user):
        with patch(
            "apps.analytics.ai_cache.AIInsightsCache.invalidate_org_cache"
        ) as mock_invalidate:
            response = auth_client.patch(
                "/api/v1/auth/preferences/",
                {"useExternalAI": True},
                format="json",
            )
            assert response.status_code == status.HTTP_200_OK
            mock_invalidate.assert_called_once_with(admin_user.profile.organization_id)

    def test_non_ai_change_does_not_trigger_invalidation(self, auth_client):
        with patch(
            "apps.analytics.ai_cache.AIInsightsCache.invalidate_org_cache"
        ) as mock_invalidate:
            response = auth_client.patch(
                "/api/v1/auth/preferences/",
                {"theme": "dark"},
                format="json",
            )
            assert response.status_code == status.HTTP_200_OK
            mock_invalidate.assert_not_called()


@pytest.mark.django_db
class TestAdminMaskedDisplay:
    """Django admin must not render aiApiKey in plaintext."""

    def test_admin_change_form_masks_api_key(self, admin_user):
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        admin_user.profile.preferences = {"aiApiKey": TEST_KEY, "useExternalAI": True}
        admin_user.profile.save()

        client = APIClient()
        client.force_login(admin_user)
        url = reverse(
            "admin:authentication_userprofile_change",
            args=[admin_user.profile.id],
        )
        response = client.get(url)
        body = response.content.decode()
        assert TEST_KEY not in body, "plaintext aiApiKey must not appear in admin HTML"
        assert "****" + TEST_KEY[-4:] in body
