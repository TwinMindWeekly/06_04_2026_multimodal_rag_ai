"""Tests for RAG chain service (CHAT-02, CHAT-03, CHAT-07).
Scaffold created in Plan 01; test bodies filled in Plan 02.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestBuildContextWithCitations:
    """CHAT-02, CHAT-07: Context builder from MMR search results."""

    def test_empty_chunks_returns_empty(self):
        """Empty input produces empty context string and empty citations list."""
        pytest.skip('Implemented in Plan 02')

    def test_single_chunk_produces_marker(self):
        """Single chunk produces [1] marker in context and one citation."""
        pytest.skip('Implemented in Plan 02')

    def test_multiple_chunks_numbered_sequentially(self):
        """N chunks produce [1]..[N] markers in context and N citations."""
        pytest.skip('Implemented in Plan 02')

    def test_citation_metadata_forwarded(self):
        """filename, page_number, chunk_index extracted from chunk metadata (CHAT-07)."""
        pytest.skip('Implemented in Plan 02')

    def test_missing_metadata_defaults(self):
        """Missing metadata fields default to empty string / 0."""
        pytest.skip('Implemented in Plan 02')


class TestPromptTemplate:
    """CHAT-03: ChatPromptTemplate format verification."""

    def test_prompt_includes_context_and_question(self):
        """Formatted messages contain context in system and question in human."""
        pytest.skip('Implemented in Plan 02')

    def test_prompt_no_retrieval_qa(self):
        """Prompt uses ChatPromptTemplate, not RetrievalQA."""
        pytest.skip('Implemented in Plan 02')
