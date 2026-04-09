import os


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
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        from chromadb import PersistentClient
        svc = VectorStoreService.__new__(VectorStoreService)
        svc.client = PersistentClient(path=tmpdir)
        # Should not raise — collection doesn't exist
        svc.delete_by_document(document_id=999, project_id=1)
