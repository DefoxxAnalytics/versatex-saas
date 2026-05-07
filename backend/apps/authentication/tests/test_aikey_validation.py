"""Finding A5: aiApiKey must validate against aiProvider's prefix."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import Organization, UserProfile

User = get_user_model()


class TestAiApiKeyValidation(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Org X", slug="org-x-aik")
        self.user = User.objects.create_user(username="aikuser", password="pw")
        UserProfile.objects.create(
            user=self.user,
            organization=self.org,
            role="admin",
            preferences={},
        )
        self.client.force_authenticate(self.user)

    def _patch_preferences(self, payload):
        return self.client.patch("/api/v1/auth/preferences/", payload, format="json")

    # --- Anthropic provider ---
    def test_anthropic_provider_with_valid_anthropic_key(self):
        response = self._patch_preferences(
            {
                "aiProvider": "anthropic",
                "aiApiKey": "sk-ant-abcdef-123456",
            }
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"{response.status_code}: {response.data!r}",
        )

    def test_anthropic_provider_with_openai_prefix_rejected(self):
        response = self._patch_preferences(
            {
                "aiProvider": "anthropic",
                "aiApiKey": "sk-FAKE-openai-key",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "sk-ant-",
            str(response.data),
            "Error message should mention the expected 'sk-ant-' prefix.",
        )

    def test_anthropic_provider_with_garbage_rejected(self):
        response = self._patch_preferences(
            {
                "aiProvider": "anthropic",
                "aiApiKey": "totally-not-an-api-key",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- OpenAI provider ---
    def test_openai_provider_with_valid_openai_key(self):
        response = self._patch_preferences(
            {
                "aiProvider": "openai",
                "aiApiKey": "sk-FAKEOPENAIKEY-123",
            }
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"{response.status_code}: {response.data!r}",
        )

    def test_openai_provider_with_anthropic_prefix_accepted(self):
        # 'sk-ant-' starts with 'sk-' so it passes the openai prefix check.
        # This is intentional: openai's prefix is 'sk-' (broad).
        # If product wants stricter openai matching (sk- but NOT sk-ant-),
        # that's a future refinement.
        response = self._patch_preferences(
            {
                "aiProvider": "openai",
                "aiApiKey": "sk-ant-this-is-anthropic-shape",
            }
        )
        # Document the current behavior — 'sk-ant-' starts with 'sk-' so this passes.
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Empty / clearing ---
    def test_empty_aiApiKey_accepted(self):
        response = self._patch_preferences(
            {
                "aiProvider": "anthropic",
                "aiApiKey": "",
            }
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "Empty string should be allowed (clears the key).",
        )

    # --- Provider context fallback ---
    def test_uses_currently_saved_provider_if_not_in_request(self):
        # Pre-set provider via direct save.
        profile = self.user.profile
        profile.preferences = {"aiProvider": "anthropic"}
        profile.save()

        response = self._patch_preferences(
            {
                "aiApiKey": "sk-ant-valid-key",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_uses_currently_saved_provider_for_rejection(self):
        profile = self.user.profile
        profile.preferences = {"aiProvider": "anthropic"}
        profile.save()

        response = self._patch_preferences(
            {
                "aiApiKey": "sk-FAKE-openai-shape",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_provider_context_accepts_any_nonempty_key(self):
        """If neither incoming nor saved aiProvider, accept any non-empty key."""
        response = self._patch_preferences(
            {
                "aiApiKey": "literally-anything",
            }
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"No provider context should not block a key. Got {response.data!r}",
        )
