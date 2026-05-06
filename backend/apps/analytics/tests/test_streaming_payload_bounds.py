"""Finding B10: ai_chat_stream must reject oversized payloads with 400.

Three settings-driven limits guard the streaming chat surface before any LLM
call is made:

- AI_CHAT_MAX_MESSAGES         — cap on len(messages)
- AI_CHAT_MAX_MESSAGE_CONTENT_CHARS — cap on each message's content length
- AI_CHAT_MAX_PAYLOAD_BYTES    — cap on total request body size (UTF-8 bytes)

The existing "messages required" guard remains.
"""
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from apps.authentication.models import Organization, UserProfile

User = get_user_model()


class TestStreamingPayloadBounds(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Org PB", slug="org-pb")

    def setUp(self):
        self.user = User.objects.create_user(username="pb_u", password="pw")
        UserProfile.objects.create(
            user=self.user, organization=self.org, role="viewer"
        )
        self.client.force_authenticate(self.user)
        self.url = reverse("ai-chat-stream")

    def _post(self, payload):
        return self.client.post(self.url, payload, format="json")

    @override_settings(AI_CHAT_MAX_MESSAGES=3)
    def test_too_many_messages_rejected(self):
        response = self._post({
            "messages": [{"role": "user", "content": "hi"}] * 4,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("messages", str(response.data).lower())

    @override_settings(AI_CHAT_MAX_MESSAGES=3)
    def test_at_message_limit_passes_validation(self):
        """3 messages == max; the payload guard must NOT fire.

        The request may still 4xx/5xx for other reasons (e.g., no API key
        → 503), but it must not be rejected with a payload-bounds 400.
        """
        response = self._post({
            "messages": [{"role": "user", "content": "hi"}] * 3,
        })
        if response.status_code == 400:
            body = str(response.data).lower()
            self.assertNotIn("too many messages", body)
            self.assertNotIn("payload", body)

    @override_settings(AI_CHAT_MAX_MESSAGE_CONTENT_CHARS=100)
    def test_too_long_message_content_rejected(self):
        response = self._post({
            "messages": [{"role": "user", "content": "x" * 200}],
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", str(response.data).lower())

    @override_settings(
        AI_CHAT_MAX_PAYLOAD_BYTES=500,
        AI_CHAT_MAX_MESSAGE_CONTENT_CHARS=10_000,
    )
    def test_oversized_payload_rejected(self):
        response = self._post({
            "messages": [{"role": "user", "content": "x" * 800}],
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("payload", str(response.data).lower())

    def test_empty_messages_still_rejected(self):
        response = self._post({"messages": []})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
