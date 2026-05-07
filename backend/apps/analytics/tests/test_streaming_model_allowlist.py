"""Finding #8 permanent: ai_chat_stream validates model against allowlist.

Phase 0 hardcoded the model to block client-controlled cost escalation. Phase 4
task 4.2 reintroduces client-supplied 'model' but gates it through
AI_CHAT_ALLOWED_MODELS + AI_CHAT_DEFAULT_MODEL settings:

- Missing/blank `model` falls back to AI_CHAT_DEFAULT_MODEL.
- Any value in AI_CHAT_ALLOWED_MODELS passes validation.
- Anything else returns 400 with a clear message.

Mocking matches `test_sse_error_sanitization.py` — `patch("anthropic.Anthropic")`
inside the request, so the streaming generator never touches the real network.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.urls import reverse


def _consume(streaming_response):
    """Drain a StreamingHttpResponse and return decoded body."""
    return b"".join(streaming_response.streaming_content).decode("utf-8")


def _stub_anthropic():
    """Return a MagicMock that mimics an `anthropic.Anthropic` client whose
    `messages.stream(...)` context-manager yields no tokens (empty stream).
    Used so the streaming generator never touches the real network.
    """
    mock_client = MagicMock()
    stream_ctx = mock_client.messages.stream.return_value
    stream_ctx.__enter__.return_value.text_stream = iter([])
    final_message = MagicMock()
    final_message.usage.input_tokens = 0
    final_message.usage.output_tokens = 0
    stream_ctx.__enter__.return_value.get_final_message.return_value = final_message
    return mock_client


@pytest.mark.django_db
class TestStreamingModelAllowlist:
    """Finding #8 permanent: client may supply `model`, but only allowlisted
    values are honored. Empty/missing falls back to AI_CHAT_DEFAULT_MODEL.
    """

    @override_settings(
        ANTHROPIC_API_KEY="test-key-not-used-mock-takes-over",
        AI_CHAT_ALLOWED_MODELS=["claude-sonnet-4-20250514", "claude-opus-4-20250514"],
        AI_CHAT_DEFAULT_MODEL="claude-sonnet-4-20250514",
    )
    def test_disallowed_model_rejected_with_400(self, authenticated_client):
        url = reverse("ai-chat-stream")
        response = authenticated_client.post(
            url,
            {
                "messages": [{"role": "user", "content": "hi"}],
                "model": "claude-opus-EVIL-EXPENSIVE-MODEL",
            },
            format="json",
        )
        assert response.status_code == 400, (
            f"Expected 400 for disallowed model, got {response.status_code}. "
            f"Body: {getattr(response, 'data', None)!r}"
        )
        body = str(response.data).lower()
        assert (
            "model" in body
        ), f"Error response must mention 'model': {response.data!r}"

    @override_settings(
        ANTHROPIC_API_KEY="test-key-not-used-mock-takes-over",
        AI_CHAT_ALLOWED_MODELS=["claude-sonnet-4-20250514", "claude-opus-4-20250514"],
        AI_CHAT_DEFAULT_MODEL="claude-sonnet-4-20250514",
    )
    def test_allowed_model_accepted(self, authenticated_client):
        url = reverse("ai-chat-stream")
        with patch(
            "anthropic.Anthropic", return_value=_stub_anthropic()
        ) as mock_anthropic:
            response = authenticated_client.post(
                url,
                {
                    "messages": [{"role": "user", "content": "hi"}],
                    "model": "claude-opus-4-20250514",
                },
                format="json",
            )
            # Streaming endpoint returns 200 with an SSE body once it reaches
            # the generator; the allowlist must not short-circuit it to 400.
            assert response.status_code != 400, (
                f"Allowed model rejected by allowlist: status={response.status_code} "
                f"body={getattr(response, 'data', getattr(response, 'content', None))!r}"
            )
            assert response.status_code == 200
            _consume(response)
            assert mock_anthropic.called, (
                "anthropic.Anthropic was never instantiated — generator never "
                "reached the streaming path, so the allowlist test is moot."
            )
            # The allowed model must be the one passed to messages.stream.
            mock_client = mock_anthropic.return_value
            stream_call = mock_client.messages.stream.call_args
            assert stream_call.kwargs.get("model") == "claude-opus-4-20250514", (
                f"Allowed client-supplied model not forwarded to anthropic.stream(): "
                f"{stream_call.kwargs!r}"
            )

    @override_settings(
        ANTHROPIC_API_KEY="test-key-not-used-mock-takes-over",
        AI_CHAT_ALLOWED_MODELS=["claude-sonnet-4-20250514"],
        AI_CHAT_DEFAULT_MODEL="claude-sonnet-4-20250514",
    )
    def test_no_model_uses_default(self, authenticated_client):
        url = reverse("ai-chat-stream")
        with patch(
            "anthropic.Anthropic", return_value=_stub_anthropic()
        ) as mock_anthropic:
            response = authenticated_client.post(
                url,
                {"messages": [{"role": "user", "content": "hi"}]},  # no 'model'
                format="json",
            )
            assert response.status_code != 400, (
                f"Default model path returned 400 unexpectedly: "
                f"{getattr(response, 'data', getattr(response, 'content', None))!r}"
            )
            assert response.status_code == 200
            _consume(response)
            assert mock_anthropic.called
            mock_client = mock_anthropic.return_value
            stream_call = mock_client.messages.stream.call_args
            assert stream_call.kwargs.get("model") == "claude-sonnet-4-20250514", (
                f"Default model not forwarded to anthropic.stream(): "
                f"{stream_call.kwargs!r}"
            )

    @override_settings(
        ANTHROPIC_API_KEY="test-key-not-used-mock-takes-over",
        AI_CHAT_ALLOWED_MODELS=["claude-sonnet-4-20250514"],
        AI_CHAT_DEFAULT_MODEL="claude-sonnet-4-20250514",
    )
    def test_blank_model_uses_default(self, authenticated_client):
        """Empty-string 'model' must fall back to default, not 400 the request.

        Mirrors the request.data.get('model') or default_model pattern: a blank
        string from the client is indistinguishable from "no model specified".
        """
        url = reverse("ai-chat-stream")
        with patch(
            "anthropic.Anthropic", return_value=_stub_anthropic()
        ) as mock_anthropic:
            response = authenticated_client.post(
                url,
                {"messages": [{"role": "user", "content": "hi"}], "model": ""},
                format="json",
            )
            assert response.status_code != 400, (
                f"Blank model wrongly rejected: "
                f"{getattr(response, 'data', getattr(response, 'content', None))!r}"
            )
            assert response.status_code == 200, (
                f"Expected 200 streaming response, got {response.status_code}: "
                f"{getattr(response, 'data', getattr(response, 'content', None))!r}"
            )
            # Drain the streaming body so the generator runs the anthropic
            # client; without this the lazy SSE generator never executes.
            _consume(response)
            assert mock_anthropic.called
            mock_client = mock_anthropic.return_value
            stream_call = mock_client.messages.stream.call_args
            assert stream_call.kwargs.get("model") == "claude-sonnet-4-20250514"
