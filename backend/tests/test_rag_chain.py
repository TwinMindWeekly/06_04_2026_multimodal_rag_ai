"""Tests for RAG chain service (CHAT-02, CHAT-03, CHAT-07)."""
import pytest
from app.services.rag_chain import build_context_with_citations, chat_prompt, RAG_SYSTEM_PROMPT


class TestBuildContextWithCitations:
    """CHAT-02, CHAT-07: Context builder from MMR search results."""

    def test_empty_chunks_returns_empty(self):
        context, citations = build_context_with_citations([])
        assert context == ''
        assert citations == []

    def test_single_chunk_produces_marker(self):
        chunks = [{'content': 'hello world', 'metadata': {'filename': 'doc.pdf', 'page_number': 1, 'chunk_index': 0}, 'similarity': 0.9, 'distance': 0.1}]
        context, citations = build_context_with_citations(chunks)
        assert '[1] hello world' in context
        assert len(citations) == 1
        assert citations[0]['filename'] == 'doc.pdf'
        assert citations[0]['page_number'] == 1
        assert citations[0]['chunk_index'] == 0
        assert citations[0]['marker'] == '[1]'

    def test_multiple_chunks_numbered_sequentially(self):
        chunks = [
            {'content': f'chunk {i}', 'metadata': {'filename': f'f{i}.pdf', 'page_number': i, 'chunk_index': i}, 'similarity': 0.8, 'distance': 0.2}
            for i in range(3)
        ]
        context, citations = build_context_with_citations(chunks)
        assert '[1] chunk 0' in context
        assert '[2] chunk 1' in context
        assert '[3] chunk 2' in context
        assert len(citations) == 3

    def test_citation_metadata_forwarded(self):
        chunks = [{'content': 'text', 'metadata': {'filename': 'report.docx', 'page_number': 5, 'chunk_index': 12}, 'similarity': 0.7, 'distance': 0.3}]
        _, citations = build_context_with_citations(chunks)
        c = citations[0]
        assert c['filename'] == 'report.docx'
        assert c['page_number'] == 5
        assert c['chunk_index'] == 12

    def test_missing_metadata_defaults(self):
        chunks = [{'content': 'text', 'metadata': {}, 'similarity': 0.5, 'distance': 0.5}]
        _, citations = build_context_with_citations(chunks)
        c = citations[0]
        assert c['filename'] == ''
        assert c['page_number'] == 0
        assert c['chunk_index'] == 0


class TestPromptTemplate:
    """CHAT-03: ChatPromptTemplate format verification."""

    def test_prompt_includes_context_and_question(self):
        messages = chat_prompt.format_messages(context='my context here', question='what is this?')
        # System message should contain context
        system_content = messages[0].content
        assert 'my context here' in system_content
        # Human message should contain question
        human_content = messages[1].content
        assert 'what is this?' in human_content

    def test_prompt_no_retrieval_qa(self):
        import app.services.rag_chain as mod
        source = open(mod.__file__).read()
        assert 'RetrievalQA' not in source
