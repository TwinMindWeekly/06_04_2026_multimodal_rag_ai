"""
Phase 5 Validation: E2E tests for the full RAG pipeline.

TEST-01: E2E Upload PDF -> verify chunks in ChromaDB -> chat query -> verify streamed response with citations
TEST-02: ChromaDB metadata round-trip (insert chunk with metadata, query, assert all fields survive)
TEST-03: Embedding provider switch triggers re-index, not silent corruption
"""
import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from chromadb import PersistentClient

from app.models.domain import Document, Folder, Project
from app.services.vector_store import VectorStoreService


# ---------------------------------------------------------------------------
# Shared helpers (reuse patterns from test_pipeline.py + test_chat_router.py)
# ---------------------------------------------------------------------------

class _NonClosingSession:
    """Wraps SQLAlchemy session to prevent close() from expunging test data.
    process_and_update_document() calls db.close() in finally block."""

    def __init__(self, session):
        self._session = session

    def close(self):
        # Do NOT close -- the test fixture owns the session lifecycle
        pass

    def __getattr__(self, name):
        return getattr(self._session, name)


def _make_mock_text_element(text='RAG test content about artificial intelligence.', page_number=1):
    """Create a mock unstructured text element."""
    el = MagicMock()
    el.text = text
    el.category = 'NarrativeText'
    el.metadata = MagicMock()
    el.metadata.page_number = page_number
    el.metadata.image_path = None
    return el


async def _mock_astream_ok(*args, **kwargs):
    """Simulate LLM streaming with AIMessageChunk-like objects."""
    for token in ['This', ' is', ' about', ' AI.']:
        chunk = MagicMock()
        chunk.content = token
        yield chunk


def _collect_sse_lines(response) -> list:
    """Collect all data: lines from a streaming response."""
    lines = []
    for line in response.iter_lines():
        if line.startswith('data:'):
            lines.append(line)
    return lines


def _create_vs_tmpdir():
    """Create a VectorStoreService with a real ChromaDB PersistentClient in a tmpdir."""
    tmpdir = tempfile.mkdtemp()
    vs = VectorStoreService.__new__(VectorStoreService)
    vs.client = PersistentClient(path=tmpdir)
    return vs, tmpdir


def _cleanup_vs(vs, tmpdir):
    """Clean up VectorStoreService and tmpdir. MUST del client before rmtree on Windows."""
    del vs.client
    shutil.rmtree(tmpdir, ignore_errors=True)


# ===========================================================================
# TEST-01: E2E Upload PDF -> ChromaDB -> Chat with Citations
# ===========================================================================

class TestE2EUploadToChat:
    """TEST-01: E2E test -- upload PDF, verify chunks in ChromaDB, chat query, verify SSE citations."""

    def test_upload_pipeline_to_chat_with_citations(self, client, test_db):
        """Full pipeline: create doc -> parse -> chunk -> embed -> chat -> SSE citations."""
        vs, tmpdir = _create_vs_tmpdir()
        try:
            # 1. Seed database: project + folder + document
            project = Project(name='E2E Test Project')
            test_db.add(project)
            test_db.commit()
            test_db.refresh(project)

            folder = Folder(name='E2E Folder', project_id=project.id)
            test_db.add(folder)
            test_db.commit()
            test_db.refresh(folder)

            # Create temp file for document
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                f.write(b'%PDF-1.4 fake content for E2E test')
                tmp_file = f.name

            doc = Document(
                filename='e2e_test.pdf',
                file_path=tmp_file,
                folder_id=folder.id,
                status='pending',
            )
            test_db.add(doc)
            test_db.commit()
            test_db.refresh(doc)
            doc_id = doc.id

            # 2. Mock embeddings for vector_store.insert_documents
            # (process_and_update_document does not pass embedding_model, so it calls
            # get_default_embeddings() -- we must mock this to avoid loading HuggingFace model)
            mock_emb_insert = MagicMock()
            mock_emb_insert.embed_documents.return_value = [[0.1] * 384, [0.1] * 384]

            # 3. Run pipeline with real ChromaDB (tmpdir), mock partition + ImageProcessor
            mock_partition_result = [
                _make_mock_text_element(
                    'Artificial intelligence is transforming research and science.',
                    page_number=1,
                ),
                _make_mock_text_element(
                    'Machine learning models need large datasets to generalize well.',
                    page_number=2,
                ),
            ]
            wrapped = _NonClosingSession(test_db)

            with patch('app.services.document_parser.SessionLocal', return_value=wrapped), \
                 patch('app.services.document_parser.partition', return_value=mock_partition_result), \
                 patch('app.services.document_parser.vector_store', vs), \
                 patch('app.services.document_parser.ImageProcessorService'), \
                 patch('app.services.vector_store.get_default_embeddings', return_value=mock_emb_insert):
                from app.services.document_parser import process_and_update_document
                process_and_update_document(doc_id)

            # 4. Verify document status completed
            refreshed = test_db.query(Document).filter(Document.id == doc_id).first()
            assert refreshed.status == 'completed', f"Expected 'completed', got '{refreshed.status}'"

            # 5. Verify chunks in ChromaDB with all 5 metadata fields (CHUNK-02)
            collection = vs.client.get_collection(f'project_{project.id}')
            assert collection.count() > 0, 'No chunks found in ChromaDB after pipeline'

            results_raw = collection.get(include=['metadatas'])
            for meta in results_raw['metadatas']:
                assert 'document_id' in meta, f'Missing document_id in metadata: {meta}'
                assert 'filename' in meta, f'Missing filename in metadata: {meta}'
                assert 'page_number' in meta, f'Missing page_number in metadata: {meta}'
                assert 'chunk_index' in meta, f'Missing chunk_index in metadata: {meta}'
                assert 'element_type' in meta, f'Missing element_type in metadata: {meta}'
                assert meta['document_id'] == str(doc_id), f"document_id mismatch: {meta['document_id']}"
                assert meta['filename'] == 'e2e_test.pdf'

            # 6. Chat query -- mock LLM and embeddings, real ChromaDB vector search via vs
            mock_emb_query = MagicMock()
            mock_emb_query.embed_query.return_value = [0.1] * 384
            mock_llm = MagicMock()
            mock_llm.astream = _mock_astream_ok

            with patch('app.routers.chat.vector_store', vs), \
                 patch('app.routers.chat.EmbeddingFactory.get_embedding_model', return_value=mock_emb_query), \
                 patch('app.routers.chat.LLMProviderFactory.get_llm', return_value=mock_llm):
                with client.stream('POST', '/api/chat', json={
                    'message': 'What is this about?',
                    'project_id': project.id,
                    'score_threshold': 0.0,  # ensure results returned regardless of similarity
                }) as response:
                    assert response.status_code == 200
                    data_lines = _collect_sse_lines(response)

            # 7. Verify SSE text events exist
            text_events = [l for l in data_lines if '"text"' in l]
            assert len(text_events) >= 1, 'No text SSE events found in chat response'

            # 8. Verify terminal event has done=true and citations list
            assert len(data_lines) >= 1, 'No SSE data lines in response'
            last_payload = json.loads(data_lines[-1][len('data: '):])
            assert last_payload.get('done') is True, f'Terminal event missing done=true: {last_payload}'
            assert isinstance(last_payload.get('citations'), list), \
                f'Terminal event missing citations list: {last_payload}'

            # 9. Verify citations contain filename and page_number (if any citations)
            citations = last_payload['citations']
            for cit in citations:
                assert 'filename' in cit, f'Citation missing filename: {cit}'
                assert 'page_number' in cit, f'Citation missing page_number: {cit}'

            # Cleanup temp file
            os.unlink(tmp_file)
        finally:
            _cleanup_vs(vs, tmpdir)


# ===========================================================================
# TEST-02: ChromaDB Metadata Round-Trip
# ===========================================================================

class TestChromaDBMetadataRoundTrip:
    """TEST-02: Insert chunk with full metadata, query, assert all 5 fields survive."""

    def test_metadata_roundtrip_all_five_fields(self):
        """All 5 CHUNK-02 metadata fields survive ChromaDB insert -> query round-trip."""
        vs, tmpdir = _create_vs_tmpdir()
        try:
            mock_emb = MagicMock()
            mock_emb.embed_documents.return_value = [[0.1] * 384]
            mock_emb.embed_query.return_value = [0.1] * 384

            # Insert with all 5 fields per CHUNK-02
            metadata = {
                'document_id': '42',        # string -- per _sanitize_metadata
                'filename': 'test.pdf',
                'page_number': 3,
                'chunk_index': 0,
                'element_type': 'NarrativeText',
            }
            vs.insert_documents(
                ['Chunk content for metadata round-trip validation test.'],
                [metadata],
                project_id=1,
                embedding_model=mock_emb,
                provider='local',
                model='all-MiniLM-L6-v2',
            )

            # Query and verify all metadata fields survive
            results = vs.similarity_search_mmr(
                query='round-trip test',
                score_threshold=0.0,
                project_id=1,
                embedding_model=mock_emb,
                provider='local',
            )

            assert len(results) == 1, f'Expected 1 result, got {len(results)}'
            returned_meta = results[0]['metadata']
            assert returned_meta['document_id'] == '42', \
                f"document_id: {returned_meta.get('document_id')}"
            assert returned_meta['filename'] == 'test.pdf', \
                f"filename: {returned_meta.get('filename')}"
            assert returned_meta['page_number'] == 3, \
                f"page_number: {returned_meta.get('page_number')}"
            assert returned_meta['chunk_index'] == 0, \
                f"chunk_index: {returned_meta.get('chunk_index')}"
            assert returned_meta['element_type'] == 'NarrativeText', \
                f"element_type: {returned_meta.get('element_type')}"
        finally:
            _cleanup_vs(vs, tmpdir)

    def test_metadata_roundtrip_multiple_chunks(self):
        """Multiple chunks with different page_numbers all survive round-trip."""
        vs, tmpdir = _create_vs_tmpdir()
        try:
            mock_emb = MagicMock()
            mock_emb.embed_documents.return_value = [[0.1] * 384, [0.2] * 384]
            mock_emb.embed_query.return_value = [0.15] * 384

            metadata_list = [
                {
                    'document_id': '10',
                    'filename': 'multi.pdf',
                    'page_number': 1,
                    'chunk_index': 0,
                    'element_type': 'Title',
                },
                {
                    'document_id': '10',
                    'filename': 'multi.pdf',
                    'page_number': 5,
                    'chunk_index': 1,
                    'element_type': 'NarrativeText',
                },
            ]
            vs.insert_documents(
                ['First chunk on page one.', 'Second chunk on page five about different topic.'],
                metadata_list,
                project_id=2,
                embedding_model=mock_emb,
                provider='local',
                model='all-MiniLM-L6-v2',
            )

            results = vs.similarity_search_mmr(
                query='chunk content',
                score_threshold=0.0,
                top_k=10,
                project_id=2,
                embedding_model=mock_emb,
                provider='local',
            )

            assert len(results) == 2, f'Expected 2 results, got {len(results)}'
            page_numbers = {r['metadata']['page_number'] for r in results}
            assert page_numbers == {1, 5}, f'Expected pages {{1, 5}}, got {page_numbers}'

            for r in results:
                meta = r['metadata']
                assert meta['document_id'] == '10'
                assert meta['filename'] == 'multi.pdf'
                assert 'chunk_index' in meta
                assert 'element_type' in meta
        finally:
            _cleanup_vs(vs, tmpdir)


# ===========================================================================
# TEST-03: Embedding Provider Switch Re-Index
# ===========================================================================

class TestProviderSwitchReindex:
    """TEST-03: Embedding provider switch triggers re-index, not silent corruption."""

    def test_provider_mismatch_raises_valueerror(self):
        """Query with mismatched provider raises ValueError (EMBED-04)."""
        vs, tmpdir = _create_vs_tmpdir()
        try:
            mock_emb = MagicMock()
            mock_emb.embed_documents.return_value = [[0.1] * 384]
            mock_emb.embed_query.return_value = [0.1] * 384

            # Insert with provider='local'
            vs.insert_documents(
                ['Content about local embeddings.'],
                [{
                    'document_id': '1',
                    'filename': 'a.pdf',
                    'page_number': 1,
                    'chunk_index': 0,
                    'element_type': 'Text',
                }],
                project_id=1,
                embedding_model=mock_emb,
                provider='local',
                model='all-MiniLM-L6-v2',
            )

            # Query with provider='openai' must raise ValueError
            mock_emb2 = MagicMock()
            mock_emb2.embed_query.return_value = [0.2] * 384

            with pytest.raises(ValueError, match='mismatch'):
                vs.similarity_search_mmr(
                    query='test',
                    project_id=1,
                    embedding_model=mock_emb2,
                    provider='openai',
                )
        finally:
            _cleanup_vs(vs, tmpdir)

    def test_delete_and_reinsert_with_new_provider_succeeds(self):
        """After delete_collection + re-insert with new provider, query succeeds."""
        vs, tmpdir = _create_vs_tmpdir()
        try:
            mock_emb_local = MagicMock()
            mock_emb_local.embed_documents.return_value = [[0.1] * 384]

            # 1. Insert with provider='local'
            vs.insert_documents(
                ['Original content.'],
                [{
                    'document_id': '1',
                    'filename': 'a.pdf',
                    'page_number': 1,
                    'chunk_index': 0,
                    'element_type': 'Text',
                }],
                project_id=1,
                embedding_model=mock_emb_local,
                provider='local',
                model='all-MiniLM-L6-v2',
            )

            # 2. Delete collection (simulates what reindex endpoint does)
            vs.client.delete_collection('project_1')

            # 3. Re-insert with provider='openai'
            mock_emb_openai = MagicMock()
            mock_emb_openai.embed_documents.return_value = [[0.3] * 384]
            mock_emb_openai.embed_query.return_value = [0.3] * 384

            vs.insert_documents(
                ['Re-indexed content.'],
                [{
                    'document_id': '1',
                    'filename': 'a.pdf',
                    'page_number': 1,
                    'chunk_index': 0,
                    'element_type': 'Text',
                }],
                project_id=1,
                embedding_model=mock_emb_openai,
                provider='openai',
                model='text-embedding-3-small',
            )

            # 4. Query with provider='openai' should work (no mismatch)
            results = vs.similarity_search_mmr(
                query='content',
                score_threshold=0.0,
                project_id=1,
                embedding_model=mock_emb_openai,
                provider='openai',
            )

            assert len(results) >= 1, 'Expected at least 1 result after re-index with new provider'
            assert results[0]['metadata']['document_id'] == '1'
        finally:
            _cleanup_vs(vs, tmpdir)

    def test_reindex_endpoint_marks_pending_and_deletes_collection(self, client, test_db):
        """POST /api/projects/{id}/reindex marks documents pending and deletes collection."""
        # Seed database
        project = Project(name='Provider Switch Project')
        test_db.add(project)
        test_db.commit()
        test_db.refresh(project)

        folder = Folder(name='f', project_id=project.id)
        test_db.add(folder)
        test_db.commit()
        test_db.refresh(folder)

        doc = Document(
            filename='switch.pdf',
            file_path='/tmp/switch.pdf',
            folder_id=folder.id,
            status='completed',
        )
        test_db.add(doc)
        test_db.commit()
        test_db.refresh(doc)

        with patch('app.routers.search.process_and_update_document'), \
             patch('app.routers.search.vector_store') as mock_vs:
            mock_vs.client.delete_collection = MagicMock()
            response = client.post(f'/api/projects/{project.id}/reindex')

        assert response.status_code == 202, f'Expected 202, got {response.status_code}'
        data = response.json()
        assert data['status'] == 'reindex_queued'
        assert data['document_count'] == 1

        # Verify document marked as pending
        test_db.refresh(doc)
        assert doc.status == 'pending', f"Expected 'pending', got '{doc.status}'"

        # Verify delete_collection was called with correct collection name
        mock_vs.client.delete_collection.assert_called_once_with(f'project_{project.id}')
