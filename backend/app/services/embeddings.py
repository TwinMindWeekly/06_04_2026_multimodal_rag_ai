import os
from langchain_community.embeddings import HuggingFaceEmbeddings


class EmbeddingFactory:
    """
    Factory pattern to generate embedding models dynamically
    based on configurations.
    """
    @staticmethod
    def get_embedding_model(provider: str = "local"):
        if provider == "local":
            # sentence-transformers via HuggingFace
            return HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': False}
            )
        elif provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(model="text-embedding-3-small")
        elif provider == "gemini":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")


# Lazy singleton — model loaded on first call, NOT at import time (per D-09)
_default_embeddings = None


def get_default_embeddings():
    """Return the default local embedding model, loading it on first call."""
    global _default_embeddings
    if _default_embeddings is None:
        _default_embeddings = EmbeddingFactory.get_embedding_model("local")
    return _default_embeddings
