import os
import uuid
import threading
import logging
import numpy as np
from pathlib import Path

from chromadb import PersistentClient
from app.services.embeddings import get_default_embeddings

logger = logging.getLogger(__name__)


def _sanitize_metadata(meta: dict) -> dict:
    """Sanitize metadata for ChromaDB: only str/int/float/bool allowed."""
    result = {}
    for k, v in meta.items():
        if v is None:
            result[k] = ""
        elif isinstance(v, (str, int, float, bool)):
            result[k] = v
        else:
            result[k] = str(v)
    return result


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

# Per-project write lock infrastructure (EMBED-06)
_project_locks: dict[int | None, threading.Lock] = {}
_locks_mutex: threading.Lock = threading.Lock()


def _get_project_lock(project_id: int | None) -> threading.Lock:
    """Return a per-project threading.Lock, creating if needed."""
    with _locks_mutex:
        if project_id not in _project_locks:
            _project_locks[project_id] = threading.Lock()
        return _project_locks[project_id]


class VectorStoreService:
    def __init__(self):
        self.client = PersistentClient(path=CHROMADB_DIR)

    def _get_collection_name(self, project_id: int | None) -> str:
        if project_id:
            return f"project_{project_id}"
        return "general_collection"

    def _check_provider_match(self, collection, active_provider: str) -> None:
        """Raise ValueError if active provider mismatches collection's stored provider (EMBED-04)."""
        stored = (collection.metadata or {}).get('embedding_provider')
        if stored and stored != active_provider:
            raise ValueError(
                f'Embedding provider mismatch: collection uses "{stored}", '
                f'active provider is "{active_provider}". Re-index to switch providers.'
            )

    def insert_documents(
        self,
        text_chunks: list[str],
        metadatas: list[dict],
        project_id: int | None = None,
        embedding_model=None,
        provider: str = 'local',
        model: str = 'all-MiniLM-L6-v2',
    ) -> None:
        """Embed text chunks and insert into the ChromaDB collection."""
        if not text_chunks:
            return

        collection_name = self._get_collection_name(project_id)
        collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                'embedding_provider': provider,
                'embedding_model': model,
                'hnsw:space': 'cosine',
            },
        )

        emb = embedding_model or get_default_embeddings()
        embeddings = emb.embed_documents(text_chunks)

        ids = [str(uuid.uuid4()) for _ in text_chunks]

        with _get_project_lock(project_id):
            collection.upsert(
                documents=text_chunks,
                embeddings=embeddings,
                metadatas=[_sanitize_metadata(m) for m in metadatas],
                ids=ids,
            )

    def delete_by_document(self, document_id: int, project_id: int | None = None) -> None:
        """Delete all vectors for a given document_id from the collection. Per D-15."""
        collection_name = self._get_collection_name(project_id)
        try:
            collection = self.client.get_collection(name=collection_name)
            collection.delete(where={"document_id": str(document_id)})
            logger.info("Deleted vectors for document_id=%d from %s", document_id, collection_name)
        except Exception as e:
            logger.debug("No vectors to delete for document_id=%d: %s", document_id, e)

    def similarity_search(
        self,
        query: str,
        top_k: int = 4,
        project_id: int | None = None,
        embedding_model=None,
    ) -> list[dict]:
        collection_name = self._get_collection_name(project_id)
        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            return []

        emb = embedding_model or get_default_embeddings()
        query_embedding = emb.embed_query(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
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

    def similarity_search_mmr(
        self,
        query: str,
        top_k: int = 5,
        fetch_k: int = 20,
        score_threshold: float = 0.3,
        lambda_mult: float = 0.5,
        project_id: int | None = None,
        embedding_model=None,
        provider: str = 'local',
    ) -> list[dict]:
        """Semantic search with score filtering and MMR deduplication.

        SEARCH-01: Returns Top-K chunks with distances and metadata.
        SEARCH-02: Filters out chunks below score_threshold.
        SEARCH-03: Applies MMR to reduce near-duplicate results.
        """
        from langchain_core.vectorstores.utils import maximal_marginal_relevance

        collection_name = self._get_collection_name(project_id)
        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            return []

        # EMBED-04: check provider matches collection
        self._check_provider_match(collection, provider)

        emb = embedding_model or get_default_embeddings()
        query_embedding = emb.embed_query(query)

        # Fetch fetch_k results WITH embeddings (required for MMR)
        count = collection.count()
        if count == 0:
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(fetch_k, count),
            include=['documents', 'metadatas', 'distances', 'embeddings'],
        )

        if not results['documents'] or not results['documents'][0]:
            return []

        docs = results['documents'][0]
        metadatas_list = results['metadatas'][0]
        distances = results['distances'][0]
        embeddings_list = results['embeddings'][0]

        # SEARCH-02: cosine distance -> similarity, apply threshold
        # cosine distance: 0=identical, 2=opposite; similarity = 1 - distance
        above_threshold = []
        for doc, meta, dist, emb_vec in zip(docs, metadatas_list, distances, embeddings_list):
            sim = 1.0 - dist
            if sim >= score_threshold:
                above_threshold.append((doc, meta, sim, emb_vec))

        if not above_threshold:
            return []

        filtered_docs, filtered_metas, filtered_sims, filtered_embs = zip(*above_threshold)

        # SEARCH-03: MMR deduplication
        query_arr = np.array(query_embedding)
        selected_indices = maximal_marginal_relevance(
            query_arr,
            list(filtered_embs),
            lambda_mult=lambda_mult,
            k=min(top_k, len(filtered_docs)),
        )

        return [
            {
                'content': filtered_docs[i],
                'metadata': filtered_metas[i],
                'similarity': filtered_sims[i],
                'distance': 1.0 - filtered_sims[i],
            }
            for i in selected_indices
        ]


vector_store = VectorStoreService()
