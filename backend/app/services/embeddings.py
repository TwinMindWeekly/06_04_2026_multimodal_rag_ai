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
                model_kwargs={'device': 'cpu'}, # Use CPU by default for stability
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

# Khởi tạo mô hình mặc định (singleton pattern) để không phải load model nhiều lần.
default_embeddings = EmbeddingFactory.get_embedding_model("local")
