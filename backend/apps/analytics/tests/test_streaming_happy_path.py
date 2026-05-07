"""Happy-path coverage for the SSE streaming endpoints.

Existing streaming tests cover the throttle, payload bounds, model allowlist,
and SSE error sanitization paths. This suite locks in the streaming-format
contract that the frontend (`streamdown` + `useChatStream`) depends on:

  - Tokens are emitted in order (not reordered or batched into one frame).
  - Each token frame is shaped `data: {"token": "..."}\n\n`.
  - The terminal frame is `data: {"done": true, "usage": {...}}\n\n` so the
    client knows when to release the typing indicator.
  - `ai_quick_query` emits the same token-then-done shape.

Mocking matches `test_streaming_model_allowlist.py` — `patch("anthropic.Anthropic")`
inside the request, so the streaming generator never touches the real network.
The stub mimics the SDK's `messages.stream(...)` context manager: yields tokens
from `text_stream`, then returns a final message with usage.

See docs/codebase-review-2026-05-06-second-pass.md (Agent 6 coverage gaps) for
the second-pass review requesting this coverage.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.urls import reverse


def _consume(streaming_response) -> str:
    """Drain a StreamingHttpResponse and return decoded body."""
    return b"".join(streaming_response.streaming_content).decode("utf-8")


def _stub_anthropic_with_tokens(tokens, input_tokens=10, output_tokens=20):
    """Return a MagicMock that mimics `anthropic.Anthropic` with a token stream.

    The real SDK exposes:
        with client.messages.stream(...) as stream:
            for text in stream.text_stream: ...
            final = stream.get_final_message()
            final.usage.input_tokens / output_tokens
    """
    mock_client = MagicMock()
    stream_ctx = mock_client.messages.stream.return_value
    stream_ctx.__enter__.return_value.text_stream = iter(tokens)
    final_message = MagicMock()
    final_message.usage.input_tokens = input_tokens
    final_message.usage.output_tokens = output_tokens
    stream_ctx.__enter__.return_value.get_final_message.return_value = final_message
    return mock_client


@pytest.mark.django_db
class TestAiChatStreamHappyPath:
    """Locks in the SSE wire format for `ai_chat_stream`."""

    @override_settings(
        ANTHROPIC_API_KEY="test-key-not-used-mock-takes-over",
        AI_CHAT_ALLOWED_MODELS=['claude-sonnet-4-20250514'],
        AI_CHAT_DEFAULT_MODEL='claude-sonnet-4-20250514',
    )
    def test_emits_tokens_in_order_then_done_sentinel(self, authenticated_client):
        # #given a stubbed Anthropic client that yields three tokens
        url = reverse("ai-chat-stream")
        tokens = ["Hello", " world", "!"]

        with patch(
            "anthropic.Anthropic",
            return_value=_stub_anthropic_with_tokens(tokens),
        ):
            # #when the SSE endpoint is consumed end-to-end
            response = authenticated_client.post(
                url,
                {"messages": [{"role": "user", "content": "hi"}]},
                format="json",
            )
            assert response.status_code == 200, (
                f"Streaming endpoint returned {response.status_code} on happy path: "
                f"{getattr(response, 'data', getattr(response, 'content', None))!r}"
            )
            body = _consume(response)

        # #then each token appears in the body, in the order yielded
        idx_hello = body.index("Hello")
        idx_world = body.index("world")
        idx_bang = body.index("!")
        assert idx_hello < idx_world < idx_bang, (
            f"SSE tokens out of order or missing in body. Indices: "
            f"hello={idx_hello}, world={idx_world}, !={idx_bang}. Body: {body!r}"
        )

        # #then each token is wrapped in the SSE `data: {"token": ...}` frame
        assert 'data: {"token": "Hello"}' in body
        assert 'data: {"token": " world"}' in body
        assert 'data: {"token": "!"}' in body

        # #then a terminal `done` frame closes the stream with usage stats
        assert '"done": true' in body, (
            f"SSE stream missing terminal done sentinel. Frontend "
            f"useChatStream relies on this to drop the typing indicator. "
            f"Body: {body!r}"
        )
        # #then the terminal frame carries token-usage telemetry
        assert '"input_tokens": 10' in body
        assert '"output_tokens": 20' in body

    @override_settings(
        ANTHROPIC_API_KEY="test-key-not-used-mock-takes-over",
        AI_CHAT_ALLOWED_MODELS=['claude-sonnet-4-20250514'],
        AI_CHAT_DEFAULT_MODEL='claude-sonnet-4-20250514',
    )
    def test_each_token_is_its_own_sse_frame(self, authenticated_client):
        # #given three distinct tokens
        url = reverse("ai-chat-stream")
        tokens = ["Alpha", "Beta", "Gamma"]

        with patch(
            "anthropic.Anthropic",
            return_value=_stub_anthropic_with_tokens(tokens),
        ):
            # #when the stream is consumed
            response = authenticated_client.post(
                url,
                {"messages": [{"role": "user", "content": "hi"}]},
                format="json",
            )
            body = _consume(response)

        # #then SSE frames are separated by the canonical `\n\n` delimiter
        # and each token gets its own data: line (no batching).
        token_frames = [
            frame for frame in body.split("\n\n") if frame.startswith("data: ")
        ]
        # 3 token frames + 1 done frame = 4
        assert len(token_frames) == 4, (
            f"Expected 4 SSE frames (3 tokens + done), got {len(token_frames)}. "
            f"Frames: {token_frames!r}"
        )

        # #then the parsed token-frame payloads carry exactly one token each
        token_payloads = []
        for frame in token_frames[:-1]:  # last is the done frame
            payload = json.loads(frame.removeprefix("data: "))
            assert "token" in payload, (
                f"Non-terminal SSE frame missing 'token' key: {payload!r}"
            )
            token_payloads.append(payload["token"])
        assert token_payloads == tokens, (
            f"Token order/content drift: expected {tokens!r}, got {token_payloads!r}"
        )

    @override_settings(
        ANTHROPIC_API_KEY="test-key-not-used-mock-takes-over",
        AI_CHAT_ALLOWED_MODELS=['claude-sonnet-4-20250514'],
        AI_CHAT_DEFAULT_MODEL='claude-sonnet-4-20250514',
    )
    def test_response_carries_sse_content_type_and_proxy_headers(
        self, authenticated_client
    ):
        # #given a single-token stub
        url = reverse("ai-chat-stream")

        with patch(
            "anthropic.Anthropic",
            return_value=_stub_anthropic_with_tokens(["ok"]),
        ):
            # #when the stream is initiated
            response = authenticated_client.post(
                url,
                {"messages": [{"role": "user", "content": "hi"}]},
                format="json",
            )
            _consume(response)  # drain so the generator runs

        # #then the response carries SSE content-type + nginx-proxy hints
        # (X-Accel-Buffering: no is required for nginx to forward chunks live).
        assert response["Content-Type"].startswith("text/event-stream")
        assert response["Cache-Control"] == "no-cache"
        assert response["X-Accel-Buffering"] == "no"


@pytest.mark.django_db
class TestAiQuickQueryHappyPath:
    """`ai_quick_query` is a streaming endpoint too — same wire format."""

    @override_settings(
        ANTHROPIC_API_KEY="test-key-not-used-mock-takes-over",
        AI_CHAT_ALLOWED_MODELS=['claude-sonnet-4-20250514'],
        AI_CHAT_DEFAULT_MODEL='claude-sonnet-4-20250514',
    )
    def test_emits_tokens_in_order_then_done_sentinel(self, authenticated_client):
        # #given a stubbed Anthropic client that yields ordered tokens
        url = reverse("ai-quick-query")
        tokens = ["First", "Second", "Third"]

        with patch(
            "anthropic.Anthropic",
            return_value=_stub_anthropic_with_tokens(tokens),
        ):
            # #when the quick-query SSE endpoint is consumed
            response = authenticated_client.post(
                url,
                {"query": "what are my top spending categories?"},
                format="json",
            )
            assert response.status_code == 200, (
                f"ai_quick_query returned {response.status_code} on happy path: "
                f"{getattr(response, 'data', getattr(response, 'content', None))!r}"
            )
            body = _consume(response)

        # #then tokens stream out in order
        idx_first = body.index("First")
        idx_second = body.index("Second")
        idx_third = body.index("Third")
        assert idx_first < idx_second < idx_third

        # #then the terminal done sentinel is present
        assert '"done": true' in body
