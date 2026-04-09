import os
import threading
import tempfile
import shutil
from unittest.mock import MagicMock, patch


def test_chromadb_path_is_absolute():
    from app.services.vector_store import CHROMADB_DIR
    assert os.path.isabs(CHROMADB_DIR), (
        f"CHROMADB_DIR is not absolute: {CHROMADB_DIR}"
    )


def test_chromadb_path_default_ends_with_backend_data():
    from app.services.vector_store import CHROMADB_DIR
    normalized = CHROMADB_DIR.replace("\\", "/")
    assert normalized.endswith("backend/data/chroma_db"), (
        f"Default path does not end with backend/data/chroma_db: {CHROMADB_DIR}"
    )


def test_vector_store_imports_get_default_embeddings():
    """vector_store.py must import get_default_embeddings, NOT default_embeddings."""
    import inspect
    import app.services.vector_store as vs_module
    source = inspect.getsource(vs_module)
    assert "import default_embeddings" not in source, (
        "vector_store.py still imports default_embeddings (should be get_default_embeddings)"
    )
    assert "get_default_embeddings" in source, (
        "vector_store.py does not reference get_default_embeddings"
    )


def test_sanitize_metadata_removes_none():
    from app.services.vector_store import _sanitize_metadata
    result = _sanitize_metadata({"a": None, "b": "hello", "c": 42})
    assert result == {"a": "", "b": "hello", "c": 42}


def test_sanitize_metadata_converts_non_scalar():
    from app.services.vector_store import _sanitize_metadata
    result = _sanitize_metadata({"a": [1, 2], "b": {"nested": True}})
    assert result["a"] == "[1, 2]"
    assert result["b"] == "{'nested': True}"


def test_delete_by_document_no_collection_no_error():
    """delete_by_document should not raise if the collection does not exist."""
    from app.services.vector_store import VectorStoreService
    tmpdir = tempfile.mkdtemp()
    try:
        from chromadb import PersistentClient
        svc = VectorStoreService.__new__(VectorStoreService)
        svc.client = PersistentClient(path=tmpdir)
        # Should not raise — collection doesn't exist
        svc.delete_by_document(document_id=999, project_id=1)
        del svc.client  # release sqlite file lock before cleanup
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# Task 1: New tests - collection metadata, provider mismatch, write lock
# ============================================================

def test_collection_metadata_stored():
    """Collection created via insert_documents stores embedding provider metadata."""
    from app.services.vector_store import VectorStoreService
    from chromadb import PersistentClient

    tmpdir = tempfile.mkdtemp()
    try:
        mock_emb = MagicMock()
        mock_emb.embed_documents.return_value = [[0.1] * 384]

        svc = VectorStoreService.__new__(VectorStoreService)
        svc.client = PersistentClient(path=tmpdir)

        svc.insert_documents(
            ['test text'],
            [{'document_id': '1', 'filename': 'test.pdf'}],
            project_id=1,
            embedding_model=mock_emb,
            provider='local',
            model='all-MiniLM-L6-v2',
        )

        collection = svc.client.get_collection('project_1')
        assert collection.metadata['embedding_provider'] == 'local'
        assert collection.metadata['embedding_model'] == 'all-MiniLM-L6-v2'
        assert collection.metadata['hnsw:space'] == 'cosine'

        del svc.client
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_provider_mismatch_raises():
    """_check_provider_match raises ValueError when providers don't match."""
    from app.services.vector_store import VectorStoreService
    from chromadb import PersistentClient
    import pytest

    tmpdir = tempfile.mkdtemp()
    try:
        svc = VectorStoreService.__new__(VectorStoreService)
        svc.client = PersistentClient(path=tmpdir)

        collection = svc.client.get_or_create_collection(
            name='project_1',
            metadata={'embedding_provider': 'local'},
        )

        with pytest.raises(ValueError, match='mismatch'):
            svc._check_provider_match(collection, 'openai')

        del svc.client
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_provider_match_passes():
    """_check_provider_match does not raise when providers match."""
    from app.services.vector_store import VectorStoreService
    from chromadb import PersistentClient

    tmpdir = tempfile.mkdtemp()
    try:
        svc = VectorStoreService.__new__(VectorStoreService)
        svc.client = PersistentClient(path=tmpdir)

        collection = svc.client.get_or_create_collection(
            name='project_1',
            metadata={'embedding_provider': 'local'},
        )

        # Should not raise
        svc._check_provider_match(collection, 'local')

        del svc.client
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_write_lock_serializes():
    """_get_project_lock returns same Lock for same project_id."""
    from app.services.vector_store import _get_project_lock

    lock1 = _get_project_lock(project_id=1)
    lock2 = _get_project_lock(project_id=1)
    assert lock1 is lock2, 'Same project_id must return same Lock instance'


def test_write_lock_different_projects():
    """_get_project_lock returns different Locks for different project_ids."""
    from app.services.vector_store import _get_project_lock

    lock1 = _get_project_lock(project_id=1)
    lock2 = _get_project_lock(project_id=2)
    assert lock1 is not lock2, 'Different project_ids must return different Lock instances'


def test_insert_documents_uses_lock():
    """insert_documents acquires the per-project lock as a context manager."""
    from app.services.vector_store import VectorStoreService
    from chromadb import PersistentClient

    tmpdir = tempfile.mkdtemp()
    try:
        mock_emb = MagicMock()
        mock_emb.embed_documents.return_value = [[0.1] * 384]

        svc = VectorStoreService.__new__(VectorStoreService)
        svc.client = PersistentClient(path=tmpdir)

        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=False)

        with patch('app.services.vector_store._get_project_lock', return_value=mock_lock):
            svc.insert_documents(
                ['test text'],
                [{'document_id': '1', 'filename': 'test.pdf'}],
                project_id=1,
                embedding_model=mock_emb,
                provider='local',
                model='all-MiniLM-L6-v2',
            )

        mock_lock.__enter__.assert_called_once()

        del svc.client
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# Task 2: New tests - score threshold, MMR deduplication, similarity_search_mmr
# ============================================================

def test_similarity_search_mmr_empty_collection():
    """similarity_search_mmr on non-existent collection returns empty list."""
    from app.services.vector_store import VectorStoreService
    from chromadb import PersistentClient

    tmpdir = tempfile.mkdtemp()
    try:
        svc = VectorStoreService.__new__(VectorStoreService)
        svc.client = PersistentClient(path=tmpdir)

        mock_emb = MagicMock()
        mock_emb.embed_query.return_value = [0.1] * 384

        result = svc.similarity_search_mmr(
            query='test',
            project_id=99,
            embedding_model=mock_emb,
        )
        assert result == []

        del svc.client
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_similarity_search_mmr_returns_format():
    """similarity_search_mmr results have content, metadata, similarity, distance keys."""
    from app.services.vector_store import VectorStoreService
    from chromadb import PersistentClient

    tmpdir = tempfile.mkdtemp()
    try:
        svc = VectorStoreService.__new__(VectorStoreService)
        svc.client = PersistentClient(path=tmpdir)

        mock_emb = MagicMock()
        mock_emb.embed_documents.return_value = [[0.1] * 384]
        mock_emb.embed_query.return_value = [0.1] * 384

        svc.insert_documents(
            ['result text'],
            [{'document_id': '1', 'filename': 'doc.pdf'}],
            project_id=1,
            embedding_model=mock_emb,
            provider='local',
            model='all-MiniLM-L6-v2',
        )

        results = svc.similarity_search_mmr(
            query='result text',
            score_threshold=0.0,
            project_id=1,
            embedding_model=mock_emb,
            provider='local',
        )

        assert len(results) > 0
        for r in results:
            assert set(r.keys()) == {'content', 'metadata', 'similarity', 'distance'}

        del svc.client
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_score_threshold_filters():
    """similarity_search_mmr excludes results below score_threshold."""
    from app.services.vector_store import VectorStoreService
    from chromadb import PersistentClient

    tmpdir = tempfile.mkdtemp()
    try:
        svc = VectorStoreService.__new__(VectorStoreService)
        svc.client = PersistentClient(path=tmpdir)

        # Insert 3 documents with distinct embeddings
        mock_emb_insert = MagicMock()
        emb1 = [0.9] + [0.0] * 383
        emb2 = [0.0, 0.5] + [0.0] * 382
        emb3 = [0.0, 0.0, 0.1] + [0.0] * 381
        mock_emb_insert.embed_documents.return_value = [emb1, emb2, emb3]

        svc.insert_documents(
            ['very relevant', 'somewhat relevant', 'not relevant'],
            [
                {'document_id': '1', 'filename': 'a.pdf'},
                {'document_id': '2', 'filename': 'b.pdf'},
                {'document_id': '3', 'filename': 'c.pdf'},
            ],
            project_id=1,
            embedding_model=mock_emb_insert,
            provider='local',
            model='all-MiniLM-L6-v2',
        )

        # Query with mocked distances [0.1, 0.5, 0.9] via patched query
        mock_query_emb = MagicMock()
        mock_query_emb.embed_query.return_value = [0.9] + [0.0] * 383

        collection = svc.client.get_collection('project_1')
        original_query = collection.query

        def mock_query(**kwargs):
            res = original_query(**kwargs)
            # Override distances to test threshold filtering
            res['distances'] = [[0.1, 0.5, 0.9]]
            # Ensure we have right number of embeddings
            if 'embeddings' in (kwargs.get('include') or []):
                res['embeddings'] = [[emb1, emb2, emb3][:len(res['distances'][0])]]
            return res

        with patch.object(collection, 'query', side_effect=mock_query):
            with patch.object(svc.client, 'get_collection', return_value=collection):
                # score_threshold=0.6 means sim >= 0.6, i.e. distance <= 0.4
                results = svc.similarity_search_mmr(
                    query='test',
                    score_threshold=0.6,
                    fetch_k=3,
                    project_id=1,
                    embedding_model=mock_query_emb,
                    provider='local',
                )

        # Only distance=0.1 (sim=0.9) and distance=0.5 (sim=0.5)... wait:
        # sim = 1 - dist => dist=0.1 -> sim=0.9 >= 0.6 PASS
        # dist=0.5 -> sim=0.5 < 0.6 FAIL
        # dist=0.9 -> sim=0.1 < 0.6 FAIL
        assert len(results) == 1
        assert abs(results[0]['similarity'] - 0.9) < 0.01

        del svc.client
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_mmr_deduplication():
    """similarity_search_mmr applies MMR to select diverse results."""
    from app.services.vector_store import VectorStoreService
    from chromadb import PersistentClient

    tmpdir = tempfile.mkdtemp()
    try:
        svc = VectorStoreService.__new__(VectorStoreService)
        svc.client = PersistentClient(path=tmpdir)

        # Insert 5 docs: 3 near-duplicates + 2 diverse
        near_dup = [1.0, 0.0] + [0.0] * 382
        diverse1 = [0.0, 1.0] + [0.0] * 382
        diverse2 = [0.5, 0.5] + [0.0] * 382

        mock_emb_insert = MagicMock()
        mock_emb_insert.embed_documents.return_value = [
            near_dup,
            [0.99, 0.01] + [0.0] * 382,  # near-dup 2
            [0.98, 0.02] + [0.0] * 382,  # near-dup 3
            diverse1,
            diverse2,
        ]

        svc.insert_documents(
            ['dup1', 'dup2', 'dup3', 'diverse1', 'diverse2'],
            [{'document_id': str(i), 'filename': f'{i}.pdf'} for i in range(1, 6)],
            project_id=1,
            embedding_model=mock_emb_insert,
            provider='local',
            model='all-MiniLM-L6-v2',
        )

        mock_query_emb = MagicMock()
        mock_query_emb.embed_query.return_value = [1.0, 0.0] + [0.0] * 382

        results = svc.similarity_search_mmr(
            query='test',
            top_k=3,
            fetch_k=5,
            score_threshold=0.0,
            lambda_mult=0.5,
            project_id=1,
            embedding_model=mock_query_emb,
            provider='local',
        )

        # MMR should return at most top_k=3 results
        assert len(results) <= 3
        # All results have required keys
        for r in results:
            assert 'content' in r
            assert 'similarity' in r

        del svc.client
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_similarity_search_mmr_provider_check():
    """similarity_search_mmr raises ValueError when provider mismatches collection."""
    from app.services.vector_store import VectorStoreService
    from chromadb import PersistentClient
    import pytest

    tmpdir = tempfile.mkdtemp()
    try:
        svc = VectorStoreService.__new__(VectorStoreService)
        svc.client = PersistentClient(path=tmpdir)

        mock_emb = MagicMock()
        mock_emb.embed_documents.return_value = [[0.1] * 384]
        mock_emb.embed_query.return_value = [0.1] * 384

        # Create collection with 'local' provider
        svc.insert_documents(
            ['some text'],
            [{'document_id': '1', 'filename': 'doc.pdf'}],
            project_id=1,
            embedding_model=mock_emb,
            provider='local',
            model='all-MiniLM-L6-v2',
        )

        # Query with different provider should raise
        with pytest.raises(ValueError, match='mismatch'):
            svc.similarity_search_mmr(
                query='test',
                project_id=1,
                embedding_model=mock_emb,
                provider='openai',
            )

        del svc.client
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
