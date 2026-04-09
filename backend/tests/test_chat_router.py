"""Tests for POST /api/chat SSE endpoint (CHAT-01, CHAT-04, CHAT-05, CHAT-06, CHAT-07)."""
import json
import pytest
from unittest.mock import MagicMock, patch


SAMPLE_CHUNKS = [
    {
        'content': 'Hello world chunk',
        'metadata': {'filename': 'doc.pdf', 'page_number': 1, 'chunk_index': 0},
        'similarity': 0.9,
        'distance': 0.1,
    }
]


async def mock_astream_ok(*args, **kwargs):
    """Simulate LLM streaming with AIMessageChunk-like objects."""
    for text in ['Hello', ' world', '!']:
        chunk = MagicMock()
        chunk.content = text
        yield chunk


async def mock_astream_error(*args, **kwargs):
    """Simulate LLM streaming that raises mid-stream."""
    raise Exception('LLM crashed')
    yield  # make it an async generator


def _collect_sse_lines(response) -> list[str]:
    """Collect all data: lines from a streaming response."""
    lines = []
    for line in response.iter_lines():
        if line.startswith('data:'):
            lines.append(line)
    return lines


class TestChatEndpoint:
    """CHAT-01: POST /api/chat accepts ChatRequest."""

    def test_chat_returns_200_sse(self, client):
        """POST /api/chat returns 200 with text/event-stream content-type (CHAT-04)."""
        mock_emb = MagicMock()
        mock_llm = MagicMock()
        mock_llm.astream = mock_astream_ok

        with patch('app.routers.chat.EmbeddingFactory.get_embedding_model', return_value=mock_emb), \
             patch('app.routers.chat.vector_store.similarity_search_mmr', return_value=SAMPLE_CHUNKS), \
             patch('app.routers.chat.LLMProviderFactory.get_llm', return_value=mock_llm):
            with client.stream('POST', '/api/chat', json={'message': 'test', 'project_id': 1}) as response:
                assert response.status_code == 200
                assert 'text/event-stream' in response.headers.get('content-type', '')

    def test_chat_requires_message(self, client):
        """Missing message field returns 422."""
        response = client.post('/api/chat', json={'project_id': 1})
        assert response.status_code == 422

    def test_chat_requires_project_id(self, client):
        """Missing project_id returns 422."""
        response = client.post('/api/chat', json={'message': 'test'})
        assert response.status_code == 422


class TestSSEFormat:
    """CHAT-05: SSE data format specification."""

    def test_sse_text_chunks(self, client):
        """Stream contains data: {"text": "..."} events."""
        mock_emb = MagicMock()
        mock_llm = MagicMock()
        mock_llm.astream = mock_astream_ok

        with patch('app.routers.chat.EmbeddingFactory.get_embedding_model', return_value=mock_emb), \
             patch('app.routers.chat.vector_store.similarity_search_mmr', return_value=SAMPLE_CHUNKS), \
             patch('app.routers.chat.LLMProviderFactory.get_llm', return_value=mock_llm):
            with client.stream('POST', '/api/chat', json={'message': 'test', 'project_id': 1}) as response:
                data_lines = _collect_sse_lines(response)

        text_events = [l for l in data_lines if '"text"' in l]
        assert len(text_events) >= 1
        # Verify JSON structure
        for event in text_events:
            payload = json.loads(event[len('data: '):])
            assert 'text' in payload
            assert isinstance(payload['text'], str)

    def test_sse_terminal_event(self, client):
        """Stream ends with data: {"done": true, "citations": [...]} event (CHAT-05, CHAT-07)."""
        mock_emb = MagicMock()
        mock_llm = MagicMock()
        mock_llm.astream = mock_astream_ok

        with patch('app.routers.chat.EmbeddingFactory.get_embedding_model', return_value=mock_emb), \
             patch('app.routers.chat.vector_store.similarity_search_mmr', return_value=SAMPLE_CHUNKS), \
             patch('app.routers.chat.LLMProviderFactory.get_llm', return_value=mock_llm):
            with client.stream('POST', '/api/chat', json={'message': 'test', 'project_id': 1}) as response:
                data_lines = _collect_sse_lines(response)

        assert len(data_lines) >= 1
        last_payload = json.loads(data_lines[-1][len('data: '):])
        assert last_payload.get('done') is True
        assert isinstance(last_payload.get('citations'), list)

    def test_sse_headers(self, client):
        """Response has X-Accel-Buffering=no and Cache-Control=no-cache (CHAT-04)."""
        mock_emb = MagicMock()
        mock_llm = MagicMock()
        mock_llm.astream = mock_astream_ok

        with patch('app.routers.chat.EmbeddingFactory.get_embedding_model', return_value=mock_emb), \
             patch('app.routers.chat.vector_store.similarity_search_mmr', return_value=SAMPLE_CHUNKS), \
             patch('app.routers.chat.LLMProviderFactory.get_llm', return_value=mock_llm):
            with client.stream('POST', '/api/chat', json={'message': 'test', 'project_id': 1}) as response:
                assert response.headers.get('x-accel-buffering') == 'no'
                assert response.headers.get('cache-control') == 'no-cache'


class TestSSEErrorHandling:
    """CHAT-06: Error events mid-stream."""

    def test_sse_error_event_on_llm_failure(self, client):
        """LLM error produces data: {"error": "..."} SSE event."""
        mock_emb = MagicMock()
        mock_llm = MagicMock()
        mock_llm.astream = mock_astream_error

        with patch('app.routers.chat.EmbeddingFactory.get_embedding_model', return_value=mock_emb), \
             patch('app.routers.chat.vector_store.similarity_search_mmr', return_value=SAMPLE_CHUNKS), \
             patch('app.routers.chat.LLMProviderFactory.get_llm', return_value=mock_llm):
            with client.stream('POST', '/api/chat', json={'message': 'test', 'project_id': 1}) as response:
                data_lines = _collect_sse_lines(response)

        error_events = [l for l in data_lines if '"error"' in l]
        assert len(error_events) >= 1
        payload = json.loads(error_events[0][len('data: '):])
        assert 'error' in payload

    def test_sse_error_event_on_embedding_failure(self, client):
        """Embedding provider error produces SSE error event."""
        with patch('app.routers.chat.EmbeddingFactory.get_embedding_model', side_effect=ValueError('bad provider')):
            with client.stream('POST', '/api/chat', json={'message': 'test', 'project_id': 1}) as response:
                data_lines = _collect_sse_lines(response)

        error_events = [l for l in data_lines if '"error"' in l]
        assert len(error_events) >= 1
        payload = json.loads(error_events[0][len('data: '):])
        assert 'error' in payload
