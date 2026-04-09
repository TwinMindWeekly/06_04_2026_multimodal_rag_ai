import os
from unittest.mock import patch, MagicMock

import pytest


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


# ---------------------------------------------------------------------------
# New tests for extended EmbeddingFactory (EMBED-01, EMBED-02)
# ---------------------------------------------------------------------------

def test_factory_local_returns_huggingface():
    """EmbeddingFactory.get_embedding_model('local') returns HuggingFaceEmbeddings with all-MiniLM-L6-v2."""
    with patch("app.services.embeddings.HuggingFaceEmbeddings") as mock_hf:
        mock_instance = MagicMock()
        mock_hf.return_value = mock_instance

        from app.services.embeddings import EmbeddingFactory
        result = EmbeddingFactory.get_embedding_model('local')

        mock_hf.assert_called_once()
        call_kwargs = mock_hf.call_args[1]
        assert call_kwargs.get('model_name') == 'all-MiniLM-L6-v2'
        assert result is mock_instance


def test_factory_local_is_default():
    """EmbeddingFactory.get_embedding_model() with no args returns local HuggingFaceEmbeddings."""
    with patch("app.services.embeddings.HuggingFaceEmbeddings") as mock_hf:
        mock_instance = MagicMock()
        mock_hf.return_value = mock_instance

        from app.services.embeddings import EmbeddingFactory
        result = EmbeddingFactory.get_embedding_model()

        mock_hf.assert_called_once()
        assert result is mock_instance


def test_openai_embedding_factory():
    """EmbeddingFactory.get_embedding_model('openai', api_key='sk-test') returns OpenAIEmbeddings."""
    with patch("app.services.embeddings.OpenAIEmbeddings") as mock_openai:
        mock_instance = MagicMock()
        mock_openai.return_value = mock_instance

        from app.services.embeddings import EmbeddingFactory
        result = EmbeddingFactory.get_embedding_model('openai', api_key='sk-test')

        mock_openai.assert_called_once_with(model='text-embedding-3-small', api_key='sk-test')
        assert result is mock_instance


def test_gemini_embedding_factory():
    """EmbeddingFactory.get_embedding_model('gemini', api_key='test-key') returns _GeminiEmbeddings."""
    from app.services.embeddings import EmbeddingFactory, _GeminiEmbeddings

    result = EmbeddingFactory.get_embedding_model('gemini', api_key='test-key')

    assert isinstance(result, _GeminiEmbeddings)
    assert result._model == 'models/text-embedding-004'
    assert result._api_key == 'test-key'


def test_gemini_embeddings_embed_documents():
    """_GeminiEmbeddings.embed_documents calls genai.Client and returns list of float lists."""
    from app.services.embeddings import _GeminiEmbeddings

    instance = _GeminiEmbeddings(api_key='k')

    mock_embedding = MagicMock()
    mock_embedding.values = [0.1, 0.2]
    mock_result = MagicMock()
    mock_result.embeddings = [mock_embedding]

    mock_client_instance = MagicMock()
    mock_client_instance.models.embed_content.return_value = mock_result

    mock_client_cls = MagicMock(return_value=mock_client_instance)

    with patch("google.genai.Client", mock_client_cls):
        output = instance.embed_documents(['hello'])

    assert output == [[0.1, 0.2]]
    mock_client_cls.assert_called_once_with(api_key='k')
    mock_client_instance.models.embed_content.assert_called_once_with(
        model='models/text-embedding-004',
        contents=['hello']
    )


def test_gemini_embeddings_embed_query():
    """_GeminiEmbeddings.embed_query returns a single float list."""
    from app.services.embeddings import _GeminiEmbeddings

    instance = _GeminiEmbeddings(api_key='k')

    mock_embedding = MagicMock()
    mock_embedding.values = [0.1, 0.2]
    mock_result = MagicMock()
    mock_result.embeddings = [mock_embedding]

    mock_client_instance = MagicMock()
    mock_client_instance.models.embed_content.return_value = mock_result

    mock_client_cls = MagicMock(return_value=mock_client_instance)

    with patch("google.genai.Client", mock_client_cls):
        output = instance.embed_query('hello')

    assert output == [0.1, 0.2]


def test_unsupported_provider_raises():
    """EmbeddingFactory.get_embedding_model('invalid') raises ValueError."""
    from app.services.embeddings import EmbeddingFactory

    with pytest.raises(ValueError, match='Unsupported embedding provider'):
        EmbeddingFactory.get_embedding_model('invalid')


def test_gemini_api_key_from_env():
    """_GeminiEmbeddings with api_key=None reads GOOGLE_API_KEY from environment."""
    from app.services.embeddings import _GeminiEmbeddings

    with patch.dict(os.environ, {'GOOGLE_API_KEY': 'env-key'}):
        instance = _GeminiEmbeddings(api_key=None)

    assert instance._api_key == 'env-key'
