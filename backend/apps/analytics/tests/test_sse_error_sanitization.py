"""Finding #6: SSE error path must not leak raw exception text.

The two streaming endpoints (`ai_chat_stream`, `ai_quick_query`) wrap the
Anthropic stream in `except Exception as e: yield ... str(e) ...`. An
`anthropic.AuthenticationError` carries the offending API-key fragment in
its message, which then bleeds out to the browser as an SSE event.

These tests force the streaming generator to take the error path and
assert the raw exception message does not appear in the response body.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.urls import reverse

LEAKY_MESSAGE = "Invalid API key sk-ant-FAKEKEYFRAGMENT not authorized"


def _consume(streaming_response):
    """Drain the StreamingHttpResponse and return decoded body."""
    return b"".join(streaming_response.streaming_content).decode("utf-8")


@pytest.mark.django_db
class TestSSEErrorSanitization:
    """Both streaming endpoints must scrub raw exception text from SSE output."""

    @override_settings(ANTHROPIC_API_KEY="test-key-not-used-mock-takes-over")
    def test_ai_chat_stream_does_not_leak_exception_text(self, authenticated_client):
        url = reverse("ai-chat-stream")

        mock_client = MagicMock()
        mock_client.messages.stream.side_effect = Exception(LEAKY_MESSAGE)

        with patch("anthropic.Anthropic", return_value=mock_client) as mock_anthropic:
            response = authenticated_client.post(
                url,
                {"messages": [{"role": "user", "content": "hi"}]},
                format="json",
            )

            assert response.status_code == 200, (
                f"Expected the streaming view to reach the generator (200) but got "
                f"{response.status_code}. Body: {getattr(response, 'content', b'')!r}"
            )

            body = _consume(response)

            assert mock_anthropic.called, (
                "anthropic.Anthropic was never instantiated — the test never "
                "exercised the streaming error path. Body was: " + body[:500]
            )

        assert (
            "sk-ant-FAKEKEYFRAGMENT" not in body
        ), f"Raw exception text leaked into SSE response. Body was: {body[:500]}"
        assert "FAKEKEYFRAGMENT" not in body
        assert '"error"' in body, f"Expected an SSE 'error' event, got: {body[:500]}"

    @override_settings(ANTHROPIC_API_KEY="test-key-not-used-mock-takes-over")
    def test_ai_quick_query_does_not_leak_exception_text(self, authenticated_client):
        url = reverse("ai-quick-query")

        mock_client = MagicMock()
        mock_client.messages.stream.side_effect = Exception(LEAKY_MESSAGE)

        with patch("anthropic.Anthropic", return_value=mock_client) as mock_anthropic:
            response = authenticated_client.post(
                url,
                {"query": "hi", "include_context": False},
                format="json",
            )

            assert response.status_code == 200
            body = _consume(response)

            assert mock_anthropic.called, (
                "anthropic.Anthropic was never instantiated — the test never "
                "exercised the streaming error path. Body was: " + body[:500]
            )

        assert (
            "sk-ant-FAKEKEYFRAGMENT" not in body
        ), f"Raw exception text leaked into SSE response. Body was: {body[:500]}"
        assert "FAKEKEYFRAGMENT" not in body
        assert '"error"' in body
