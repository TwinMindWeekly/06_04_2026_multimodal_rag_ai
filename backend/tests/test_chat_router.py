"""Tests for POST /api/chat SSE endpoint (CHAT-01, CHAT-04, CHAT-05, CHAT-06, CHAT-07).
Scaffold created in Plan 01; test bodies filled in Plan 02.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestChatEndpoint:
    """CHAT-01: POST /api/chat accepts ChatRequest."""

    def test_chat_returns_200_sse(self, client):
        """POST /api/chat returns 200 with text/event-stream content-type (CHAT-04)."""
        pytest.skip('Implemented in Plan 02')

    def test_chat_requires_message(self, client):
        """Missing message field returns 422."""
        pytest.skip('Implemented in Plan 02')

    def test_chat_requires_project_id(self, client):
        """Missing project_id returns 422."""
        pytest.skip('Implemented in Plan 02')


class TestSSEFormat:
    """CHAT-05: SSE data format specification."""

    def test_sse_text_chunks(self, client):
        """Stream contains data: {"text": "..."} events."""
        pytest.skip('Implemented in Plan 02')

    def test_sse_terminal_event(self, client):
        """Stream ends with data: {"done": true, "citations": [...]} event (CHAT-05, CHAT-07)."""
        pytest.skip('Implemented in Plan 02')

    def test_sse_headers(self, client):
        """Response has X-Accel-Buffering=no and Cache-Control=no-cache (CHAT-04)."""
        pytest.skip('Implemented in Plan 02')


class TestSSEErrorHandling:
    """CHAT-06: Error events mid-stream."""

    def test_sse_error_event_on_llm_failure(self, client):
        """LLM error produces data: {"error": "..."} SSE event."""
        pytest.skip('Implemented in Plan 02')

    def test_sse_error_event_on_embedding_failure(self, client):
        """Embedding provider error produces SSE error event."""
        pytest.skip('Implemented in Plan 02')
