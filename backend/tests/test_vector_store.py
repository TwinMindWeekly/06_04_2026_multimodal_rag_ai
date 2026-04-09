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
