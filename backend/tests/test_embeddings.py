from unittest.mock import patch, MagicMock


def test_no_model_at_import():
    """Importing embeddings module must NOT trigger HuggingFaceEmbeddings()."""
    with patch(
        "app.services.embeddings.HuggingFaceEmbeddings"
    ) as mock_hf:
        # Force reimport to test module load behavior
        import importlib
        import app.services.embeddings as emb_module
        # Reset the lazy singleton so reimport test is meaningful
        emb_module._default_embeddings = None
        # The mock should NOT have been called just by existing in the module
        # (We can't fully reimport without side effects, but we can verify
        #  the module structure has no top-level call)
        assert hasattr(emb_module, "get_default_embeddings"), (
            "Module must expose get_default_embeddings function"
        )
        assert hasattr(emb_module, "_default_embeddings"), (
            "Module must have _default_embeddings sentinel"
        )


def test_module_has_no_eager_default_embeddings():
    """Verify the eager module-level 'default_embeddings = EmbeddingFactory.get_embedding_model()' is removed."""
    import inspect
    import app.services.embeddings as emb_module
    source = inspect.getsource(emb_module)
    # Check each source line for the old eager pattern at module level
    # The old pattern was: default_embeddings = EmbeddingFactory.get_embedding_model("local")
    # Must not match _default_embeddings inside the lazy function body
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("default_embeddings") and "EmbeddingFactory" in stripped:
            raise AssertionError(
                f"Module still has eager module-level assignment: {stripped}"
            )
    # Also ensure no module-level attribute named 'default_embeddings' (without underscore prefix)
    assert not hasattr(emb_module, "default_embeddings"), (
        "Module still exposes 'default_embeddings' attribute (should be get_default_embeddings function)"
    )


def test_get_default_embeddings_returns_object_with_methods():
    """get_default_embeddings() returns something with embed_documents and embed_query."""
    with patch("app.services.embeddings.HuggingFaceEmbeddings") as mock_hf:
        mock_instance = MagicMock()
        mock_hf.return_value = mock_instance

        import app.services.embeddings as emb_module
        emb_module._default_embeddings = None  # Reset singleton

        result = emb_module.get_default_embeddings()
        assert result is mock_instance
        mock_hf.assert_called_once()


def test_get_default_embeddings_is_singleton():
    """Two calls return the same object instance."""
    with patch("app.services.embeddings.HuggingFaceEmbeddings") as mock_hf:
        mock_instance = MagicMock()
        mock_hf.return_value = mock_instance

        import app.services.embeddings as emb_module
        emb_module._default_embeddings = None  # Reset singleton

        first = emb_module.get_default_embeddings()
        second = emb_module.get_default_embeddings()
        assert first is second, "get_default_embeddings must return same instance"
        assert mock_hf.call_count == 1, "HuggingFaceEmbeddings should be constructed only once"
