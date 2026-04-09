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
