import os
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings


class _GeminiEmbeddings(Embeddings):
    """Thin LangChain-compatible wrapper around google-genai SDK for text-embedding-004."""

    def __init__(self, model: str = 'models/text-embedding-004', api_key: str | None = None):
        self._model = model
        self._api_key = api_key or os.getenv('GOOGLE_API_KEY')

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        from google import genai
        client = genai.Client(api_key=self._api_key)
        result = client.models.embed_content(model=self._model, contents=texts)
        return [e.values for e in result.embeddings]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class EmbeddingFactory:
    """
    Factory pattern to generate embedding models dynamically
    based on configurations.
    """
    @staticmethod
    def get_embedding_model(provider: str = 'local', api_key: str | None = None):
        if provider == 'local':
            # sentence-transformers via HuggingFace
            return HuggingFaceEmbeddings(
                model_name='all-MiniLM-L6-v2',
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': False}
            )
        elif provider == 'openai':
            return OpenAIEmbeddings(model='text-embedding-3-small', api_key=api_key)
        elif provider == 'gemini':
            return _GeminiEmbeddings(model='models/text-embedding-004', api_key=api_key)
        else:
            raise ValueError(f'Unsupported embedding provider: {provider}')


# Lazy singleton — model loaded on first call, NOT at import time (per D-09)
_default_embeddings = None


def get_default_embeddings():
    """Return the default local embedding model, loading it on first call."""
    global _default_embeddings
    if _default_embeddings is None:
        _default_embeddings = EmbeddingFactory.get_embedding_model('local')
    return _default_embeddings
