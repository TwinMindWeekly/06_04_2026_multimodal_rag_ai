import os
import uuid
import logging
from pathlib import Path

from chromadb import PersistentClient
from app.services.embeddings import get_default_embeddings

logger = logging.getLogger(__name__)

# __file__ = backend/app/services/vector_store.py
# .parent = backend/app/services/
# .parent.parent = backend/app/
# .parent.parent.parent = backend/
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_CHROMADB_PATH = str(_BACKEND_DIR / "data" / "chroma_db")

# Per D-01, D-03: env var CHROMADB_PATH with __file__-relative default
CHROMADB_DIR = os.getenv("CHROMADB_PATH", _DEFAULT_CHROMADB_PATH)
os.makedirs(CHROMADB_DIR, exist_ok=True)
logger.info("ChromaDB path: %s", CHROMADB_DIR)


class VectorStoreService:
    def __init__(self):
        self.client = PersistentClient(path=CHROMADB_DIR)

    def _get_collection_name(self, project_id: int):
        if project_id:
            return f"project_{project_id}"
        return "general_collection"

    def insert_documents(self, text_chunks: list[str], metadatas: list[dict], project_id: int = None):
        """Embed text chunks and insert into the ChromaDB collection."""
        if not text_chunks:
            return

        collection_name = self._get_collection_name(project_id)
        collection = self.client.get_or_create_collection(name=collection_name)

        # Call lazy-loaded embeddings (per D-09 call site update)
        embeddings = get_default_embeddings().embed_documents(text_chunks)

        ids = [str(uuid.uuid4()) for _ in text_chunks]

        collection.upsert(
            documents=text_chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    def similarity_search(self, query: str, top_k: int = 4, project_id: int = None):
        collection_name = self._get_collection_name(project_id)
        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            return []

        # Call lazy-loaded embeddings (per D-09 call site update)
        query_embedding = get_default_embeddings().embed_query(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        formatted_results = []
        if results['documents'] and len(results['documents'][0]) > 0:
            docs = results['documents'][0]
            metadatas_list = results['metadatas'][0]
            for idx, doc in enumerate(docs):
                formatted_results.append({
                    "content": doc,
                    "metadata": metadatas_list[idx] if idx < len(metadatas_list) else {}
                })
        return formatted_results


vector_store = VectorStoreService()
