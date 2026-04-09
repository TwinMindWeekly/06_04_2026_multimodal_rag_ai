import os
from chromadb import PersistentClient
from app.services.embeddings import default_embeddings

CHROMADB_DIR = os.path.join(os.getcwd(), "chroma_db")
os.makedirs(CHROMADB_DIR, exist_ok=True)

class VectorStoreService:
    def __init__(self):
        self.client = PersistentClient(path=CHROMADB_DIR)
        
    def _get_collection_name(self, project_id: int):
        if project_id:
            return f"project_{project_id}"
        return "general_collection"
        
    def insert_documents(self, text_chunks: list[str], metadatas: list[dict], project_id: int = None):
        """Nhúng các chunk văn bản và chèn vào ChromaDB Collection tương ứng"""
        if not text_chunks:
            return
            
        collection_name = self._get_collection_name(project_id)
        collection = self.client.get_or_create_collection(name=collection_name)
        
        # Generate embeddings bằng Factory (sentence-transformers local default)
        embeddings = default_embeddings.embed_documents(text_chunks)
        
        # Tạo IDs duy nhất
        import uuid
        ids = [str(uuid.uuid4()) for _ in text_chunks]
        
        # Upsert vào ChromaDB
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
            # Collection không tồn tại báo hiệu chưa có data
            return []
            
        # Sinh vector từ câu query
        query_embedding = default_embeddings.embed_query(query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        # format lại response giống module documents chuẩn
        formatted_results = []
        if results['documents'] and len(results['documents'][0]) > 0:
            docs = results['documents'][0]
            metadatas = results['metadatas'][0]
            for idx, doc in enumerate(docs):
                formatted_results.append({
                    "content": doc,
                    "metadata": metadatas[idx] if idx < len(metadatas) else {}
                })
        return formatted_results

vector_store = VectorStoreService()
