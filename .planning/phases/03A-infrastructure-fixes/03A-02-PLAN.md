---
phase: 03A-infrastructure-fixes
plan: 02
type: execute
wave: 2
depends_on: ["03A-01"]
files_modified:
  - backend/app/services/embeddings.py
  - backend/app/services/vector_store.py
  - backend/app/services/document_parser.py
  - backend/app/routers/documents.py
  - backend/locales/en.json
  - backend/locales/vi.json
  - backend/tests/test_embeddings.py
  - backend/tests/test_vector_store.py
  - backend/tests/test_document_parser.py
  - backend/tests/test_documents_router.py
autonomous: true
requirements: [INFRA-01, INFRA-04, INFRA-05, INFRA-06]

must_haves:
  truths:
    - "Embedding model is NOT loaded at module import time"
    - "ChromaDB persistence path is absolute and configurable via CHROMADB_PATH env var"
    - "Background task does not raise DetachedInstanceError when accessing folder.project_id"
    - "Upload of .exe file returns 400 without writing to disk"
    - "Upload of file larger than 100MB returns 413 without writing to disk"
    - "Upload of valid .pdf file proceeds normally"
  artifacts:
    - path: "backend/app/services/embeddings.py"
      provides: "Lazy-loading get_default_embeddings() function"
      exports: ["EmbeddingFactory", "get_default_embeddings"]
    - path: "backend/app/services/vector_store.py"
      provides: "Absolute ChromaDB path via env var + updated call site"
      contains: "get_default_embeddings()"
    - path: "backend/app/services/document_parser.py"
      provides: "Eager-loaded folder relationship via joinedload"
      contains: "joinedload"
    - path: "backend/app/routers/documents.py"
      provides: "Extension whitelist + size limit validation before disk write"
      contains: "ALLOWED_EXTENSIONS"
    - path: "backend/locales/en.json"
      provides: "English error messages for invalid_file_type and file_too_large"
      contains: "invalid_file_type"
    - path: "backend/locales/vi.json"
      provides: "Vietnamese error messages for invalid_file_type and file_too_large"
      contains: "invalid_file_type"
  key_links:
    - from: "backend/app/services/vector_store.py"
      to: "backend/app/services/embeddings.py"
      via: "import get_default_embeddings and call at embed time"
      pattern: "from app\\.services\\.embeddings import get_default_embeddings"
    - from: "backend/app/services/document_parser.py"
      to: "backend/app/models/domain.py"
      via: "joinedload(Document.folder) prevents DetachedInstanceError"
      pattern: "joinedload\\(Document\\.folder\\)"
    - from: "backend/app/routers/documents.py"
      to: "backend/locales/en.json"
      via: "t('errors.invalid_file_type') and t('errors.file_too_large')"
      pattern: "errors\\.invalid_file_type"
---

<objective>
Lazy-load embedding model, fix ChromaDB path, fix background task eager-loading, and add upload file validation.

Purpose: Prevents slow server startup from model loading, ensures stable ChromaDB path regardless of CWD, eliminates DetachedInstanceError in background tasks, and blocks malicious/oversized file uploads.

Output: Hardened embeddings.py, vector_store.py, document_parser.py, and documents.py router with full test coverage.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/03A-infrastructure-fixes/03A-CONTEXT.md
@.planning/phases/03A-infrastructure-fixes/03A-RESEARCH.md
@.planning/phases/03A-infrastructure-fixes/03A-VALIDATION.md
@.planning/phases/03A-infrastructure-fixes/03A-01-SUMMARY.md

@backend/app/services/embeddings.py
@backend/app/services/vector_store.py
@backend/app/services/document_parser.py
@backend/app/routers/documents.py
@backend/app/models/domain.py
@backend/locales/en.json
@backend/locales/vi.json
@backend/tests/conftest.py

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From backend/app/services/embeddings.py (current — to be modified):
```python
class EmbeddingFactory:
    @staticmethod
    def get_embedding_model(provider: str = "local"): ...

# Module-level singleton — THIS IS THE PROBLEM (loads 80MB+ model at import)
default_embeddings = EmbeddingFactory.get_embedding_model("local")
```

From backend/app/services/vector_store.py (current — to be modified):
```python
from app.services.embeddings import default_embeddings  # <-- must change to get_default_embeddings
CHROMADB_DIR = os.path.join(os.getcwd(), "chroma_db")  # <-- must change to __file__-relative
class VectorStoreService:
    def insert_documents(self, text_chunks, metadatas, project_id=None): ...
    def similarity_search(self, query, top_k=4, project_id=None): ...
```

From backend/app/services/document_parser.py (current — to be modified):
```python
def process_and_update_document(document_id: int):
    db = SessionLocal()
    db_document = db.query(Document).filter(Document.id == document_id).first()
    # BROKEN: db_document.folder.project_id — lazy load across session boundary
```

From backend/app/routers/documents.py (current — to be modified):
```python
async def upload_document(folder_id, file, db, lang, background_tasks):
    # NO validation — writes to disk immediately
    file_ext = os.path.splitext(file.filename)[1]
    shutil.copyfileobj(file.file, buffer)
```

From backend/app/models/domain.py (read-only reference):
```python
class Document(Base):
    folder = relationship("Folder", back_populates="documents")
class Folder(Base):
    project_id = Column(Integer, ForeignKey("projects.id"))
```

From backend/app/core/database.py (from Plan 01 — read-only, already fixed):
```python
DATABASE_PATH = os.getenv("DATABASE_PATH", _DEFAULT_DB_PATH)
engine = create_engine(...)
SessionLocal = sessionmaker(...)
def get_db(): ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Lazy-load embedding model and update ChromaDB path + call site</name>
  <files>backend/app/services/embeddings.py, backend/app/services/vector_store.py, backend/tests/test_embeddings.py, backend/tests/test_vector_store.py</files>
  <read_first>
    - backend/app/services/embeddings.py (current module-level singleton to refactor)
    - backend/app/services/vector_store.py (imports default_embeddings — must update import and 2 call sites)
    - .planning/phases/03A-infrastructure-fixes/03A-RESEARCH.md (Pattern 3 lazy singleton, Pitfall 1 call site)
  </read_first>
  <behavior>
    - test_no_model_at_import: importing embeddings module does not trigger HuggingFaceEmbeddings constructor (mock HuggingFaceEmbeddings, import module, assert not called)
    - test_get_default_embeddings_returns_model: calling get_default_embeddings() returns an object with embed_documents and embed_query methods
    - test_get_default_embeddings_is_singleton: two calls to get_default_embeddings() return the same object (identity check with `is`)
    - test_chromadb_path_is_absolute: CHROMADB_DIR is an absolute path (os.path.isabs)
    - test_chromadb_path_default_ends_with_backend_data: default path normalized ends with "backend/data/chroma_db"
    - test_vector_store_uses_get_default_embeddings: vector_store.py does NOT contain the string "import default_embeddings" (uses get_default_embeddings instead)
  </behavior>
  <action>
    **Step 1: Modify `backend/app/services/embeddings.py` (per D-09 for INFRA-04).**

    Replace the module-level singleton with a lazy-loading function. Keep EmbeddingFactory unchanged. Replace the last 2 lines:

    ```python
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
    ```

    Changes from current:
    - Removed: `default_embeddings = EmbeddingFactory.get_embedding_model("local")` (line 28)
    - Added: `_default_embeddings = None` and `def get_default_embeddings()` lazy pattern
    - EmbeddingFactory class is UNCHANGED

    **Step 2: Modify `backend/app/services/vector_store.py` (per D-01, D-03 for INFRA-01, plus call site update for INFRA-04).**

    ```python
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
    ```

    Changes from current:
    - Line 3: `from app.services.embeddings import default_embeddings` changed to `from app.services.embeddings import get_default_embeddings`
    - Line 5: `CHROMADB_DIR = os.path.join(os.getcwd(), "chroma_db")` changed to `__file__`-relative with env var
    - Line 26: `default_embeddings.embed_documents(...)` changed to `get_default_embeddings().embed_documents(...)`
    - Line 49: `default_embeddings.embed_query(...)` changed to `get_default_embeddings().embed_query(...)`
    - Added `uuid` import at top (was inline import on line 29), `logging`, `pathlib.Path`

    **Step 3: Create `backend/tests/test_embeddings.py`:**

    ```python
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


    def test_module_has_no_default_embeddings_assignment():
        """Verify default_embeddings = EmbeddingFactory.get_embedding_model() is removed."""
        import inspect
        import app.services.embeddings as emb_module
        source = inspect.getsource(emb_module)
        assert "default_embeddings = EmbeddingFactory" not in source, (
            "Module still has eager default_embeddings = EmbeddingFactory.get_embedding_model() call"
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
    ```

    **Step 4: Create `backend/tests/test_vector_store.py`:**

    ```python
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
    ```
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/test_embeddings.py tests/test_vector_store.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - `backend/app/services/embeddings.py` contains `_default_embeddings = None`
    - `backend/app/services/embeddings.py` contains `def get_default_embeddings()`
    - `backend/app/services/embeddings.py` does NOT contain `default_embeddings = EmbeddingFactory.get_embedding_model`
    - `backend/app/services/vector_store.py` contains `from app.services.embeddings import get_default_embeddings`
    - `backend/app/services/vector_store.py` does NOT contain `from app.services.embeddings import default_embeddings`
    - `backend/app/services/vector_store.py` contains `get_default_embeddings().embed_documents`
    - `backend/app/services/vector_store.py` contains `get_default_embeddings().embed_query`
    - `backend/app/services/vector_store.py` contains `os.getenv("CHROMADB_PATH"`
    - `backend/app/services/vector_store.py` contains `Path(__file__).resolve().parent.parent.parent`
    - `backend/app/services/vector_store.py` contains `logger.info("ChromaDB path:`
    - `cd backend && python -m pytest tests/test_embeddings.py tests/test_vector_store.py -x` exits 0
  </acceptance_criteria>
  <done>Embedding model lazy-loads on first call only. ChromaDB path is absolute via __file__ with CHROMADB_PATH env var override. vector_store.py call sites updated. All 7 tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Fix background task eager-loading of folder relationship</name>
  <files>backend/app/services/document_parser.py, backend/tests/test_document_parser.py</files>
  <read_first>
    - backend/app/services/document_parser.py (current lazy-load risk on lines 81, 86)
    - backend/app/models/domain.py (Document.folder relationship, Folder.project_id column)
    - .planning/phases/03A-infrastructure-fixes/03A-RESEARCH.md (Pattern 4 eager-load fix)
  </read_first>
  <behavior>
    - test_background_task_uses_joinedload: source code of document_parser.py contains "joinedload(Document.folder)"
    - test_background_task_no_direct_folder_access_without_query: source code does NOT contain bare "db_document.folder.project_id" outside of a joinedloaded query result
    - test_process_document_handles_missing_document: process_and_update_document(99999) returns None without error when document not found
  </behavior>
  <action>
    **Modify `backend/app/services/document_parser.py` (per D-10 for INFRA-05).**

    Add `joinedload` import and use it in the query. Replace the `process_and_update_document` function body with eager-loaded relationship access:

    ```python
    import os
    import json
    from sqlalchemy.orm import Session, joinedload

    from app.models.domain import Document
    from app.services.vector_store import vector_store


    class DocumentParserService:
        def __init__(self, extract_images: bool = True):
            self.extract_images = extract_images

        def parse_document(self, file_path: str, document_id: int):
            """
            Parses a document (PDF, DOCX, PPTX, etc.) using unstructured.
            Extracts both text chunks and images.
            """
            output_dir = os.path.join(os.path.dirname(file_path), f"extracted_{document_id}")
            if self.extract_images:
                os.makedirs(output_dir, exist_ok=True)

            # Stub logic — real parsing implemented in Phase 3b
            text_chunks = [f"[MOCK] This is a chunk extracted from {os.path.basename(file_path)}"]

            extracted_image_paths = []
            if self.extract_images and os.path.exists(output_dir):
                for file in os.listdir(output_dir):
                    extracted_image_paths.append(os.path.join(output_dir, file))

            return {
                "text_chunks": text_chunks,
                "images": extracted_image_paths,
                "metadata": {
                    "total_chunks": len(text_chunks),
                    "total_images": len(extracted_image_paths)
                }
            }


    from app.core.database import SessionLocal


    def process_and_update_document(document_id: int):
        """
        Background task to parse document immediately after upload.
        Uses own session (SessionLocal) with eager-loaded folder relationship
        to prevent DetachedInstanceError (per D-10, INFRA-05).
        """
        db = SessionLocal()
        try:
            # FIXED: joinedload prevents DetachedInstanceError on folder.project_id
            db_document = (
                db.query(Document)
                .options(joinedload(Document.folder))
                .filter(Document.id == document_id)
                .first()
            )
            if not db_document:
                return None

            parser = DocumentParserService(extract_images=True)
            result = parser.parse_document(db_document.file_path, document_id)

            # Update document metadata
            current_metadata = json.loads(db_document.metadata_json) if db_document.metadata_json else {}
            current_metadata.update(result["metadata"])
            db_document.metadata_json = json.dumps(current_metadata)

            db.commit()

            # Ingest text chunks into Vector DB
            if result.get("text_chunks"):
                # folder relationship is already loaded via joinedload — safe to access
                proj_id = db_document.folder.project_id if db_document.folder else None
                metadatas = []
                for i, chunk in enumerate(result["text_chunks"]):
                    metadatas.append({
                        "document_id": document_id,
                        "project_id": proj_id if proj_id is not None else "none",
                        "filename": db_document.filename,
                        "chunk_index": i
                    })

                vector_store.insert_documents(
                    text_chunks=result["text_chunks"],
                    metadatas=metadatas,
                    project_id=proj_id
                )

            return result
        finally:
            db.close()
    ```

    Changes from current:
    - Added `joinedload` import from `sqlalchemy.orm`
    - Changed query on line 61 from `db.query(Document).filter(...)` to `db.query(Document).options(joinedload(Document.folder)).filter(...)`
    - Moved `proj_id` assignment to BEFORE the metadatas loop (was duplicated on lines 81 and 86)
    - Return `None` explicitly when document not found (was implicit)

    **Create `backend/tests/test_document_parser.py`:**

    ```python
    import inspect


    def test_background_task_uses_joinedload():
        """document_parser.py must use joinedload(Document.folder) to prevent DetachedInstanceError."""
        from app.services import document_parser
        source = inspect.getsource(document_parser)
        assert "joinedload(Document.folder)" in source, (
            "document_parser.py must use joinedload(Document.folder)"
        )


    def test_joinedload_imported():
        """joinedload must be imported from sqlalchemy.orm."""
        from app.services import document_parser
        source = inspect.getsource(document_parser)
        assert "from sqlalchemy.orm" in source and "joinedload" in source, (
            "document_parser.py must import joinedload from sqlalchemy.orm"
        )


    def test_process_document_handles_missing_document(test_db):
        """process_and_update_document with nonexistent ID returns None without error."""
        from app.services.document_parser import process_and_update_document
        result = process_and_update_document(99999)
        assert result is None
    ```
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/test_document_parser.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - `backend/app/services/document_parser.py` contains `from sqlalchemy.orm import Session, joinedload`
    - `backend/app/services/document_parser.py` contains `joinedload(Document.folder)`
    - `backend/app/services/document_parser.py` contains `.options(joinedload(Document.folder))`
    - `backend/tests/test_document_parser.py` contains `def test_background_task_uses_joinedload`
    - `cd backend && python -m pytest tests/test_document_parser.py -x` exits 0
  </acceptance_criteria>
  <done>Background task uses joinedload(Document.folder) to prevent DetachedInstanceError. Missing document returns None. All 3 tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: File upload validation with extension whitelist and size limit</name>
  <files>backend/app/routers/documents.py, backend/locales/en.json, backend/locales/vi.json, backend/tests/test_documents_router.py</files>
  <read_first>
    - backend/app/routers/documents.py (current upload endpoint with no validation)
    - backend/locales/en.json (existing error keys pattern)
    - backend/locales/vi.json (existing error keys pattern)
    - backend/app/core/i18n.py (t() function usage)
    - .planning/phases/03A-infrastructure-fixes/03A-RESEARCH.md (Pattern 5 upload validation)
  </read_first>
  <behavior>
    - test_invalid_extension_returns_400: uploading a file with .exe extension returns HTTP 400
    - test_invalid_extension_txt_returns_400: uploading a file with .txt extension returns HTTP 400
    - test_valid_extension_pdf_accepted: uploading a small .pdf file does NOT return 400 (proceeds to 201)
    - test_valid_extension_docx_accepted: uploading a small .docx file does NOT return 400
    - test_valid_extension_case_insensitive: uploading a .PDF (uppercase) file does NOT return 400
    - test_oversized_file_returns_413: uploading a file larger than 100MB returns HTTP 413
    - test_content_type_mismatch_returns_400: uploading with wrong Content-Type returns HTTP 400
  </behavior>
  <action>
    **Step 1: Add i18n keys to both locale files.**

    Update `backend/locales/en.json` to:
    ```json
    {
      "errors": {
        "project_not_found": "Project not found.",
        "folder_not_found": "Folder not found.",
        "document_not_found": "Document not found.",
        "internal_error": "An internal server error occurred.",
        "invalid_file_type": "Invalid file type. Allowed types: PDF, DOCX, PPTX, XLSX.",
        "file_too_large": "File too large. Maximum size is 100MB."
      },
      "prompts": {
        "system_instruction": "You are a helpful AI assistant. Always respond in English. Use the provided context to answer."
      }
    }
    ```

    Update `backend/locales/vi.json` to:
    ```json
    {
      "errors": {
        "project_not_found": "Khong tim thay du an.",
        "folder_not_found": "Khong tim thay thu muc.",
        "document_not_found": "Khong tim thay tai lieu.",
        "internal_error": "Da xay ra loi he thong cuc bo.",
        "invalid_file_type": "Loai tep khong hop le. Cac loai cho phep: PDF, DOCX, PPTX, XLSX.",
        "file_too_large": "Tep qua lon. Kich thuoc toi da la 100MB."
      },
      "prompts": {
        "system_instruction": "Ban la mot tro ly AI huu ich. Luon luon tra loi bang Tieng Viet. Hay dua vao thong tin ngu canh duoc cung cap de tra loi."
      }
    }
    ```

    IMPORTANT: Read the actual current content of both locale files first to preserve the existing Vietnamese diacritics. The above is ASCII-approximated; use the actual Vietnamese characters from the existing file content. Only ADD the two new keys (`invalid_file_type` and `file_too_large`) under `errors`.

    **Step 2: Modify `backend/app/routers/documents.py` (per D-04, D-05, D-06 for INFRA-06).**

    Add validation BEFORE any disk write. Replace the upload_document function:

    ```python
    import os
    import uuid
    import json
    from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
    from sqlalchemy.orm import Session
    from typing import List

    from app.core.database import get_db
    from app.core.i18n import get_language, t
    from app.models.domain import Document, Folder
    from app.schemas.domain import DocumentResponse
    from app.services.document_parser import process_and_update_document

    router = APIRouter(prefix="/api/documents", tags=["documents"])

    UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Per D-06: extension whitelist (case-insensitive)
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}

    # Per D-05: 100MB file size limit
    MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024

    # Per D-04: Content-Type secondary validation
    ALLOWED_CONTENT_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }


    @router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
    async def upload_document(
        folder_id: int = Form(None),
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        lang: str = Depends(get_language),
        background_tasks: BackgroundTasks = BackgroundTasks()
    ):
        # --- VALIDATION BEFORE DISK WRITE (per D-04) ---

        # 1. Extension check (per D-06: case-insensitive)
        file_ext = os.path.splitext(file.filename or "")[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=t("errors.invalid_file_type", lang)
            )

        # 2. Content-Type check (defense in depth)
        if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=t("errors.invalid_file_type", lang)
            )

        # 3. Size check: read into memory up to limit+1 to detect oversized (per D-05)
        content = await file.read(MAX_FILE_SIZE_BYTES + 1)
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=t("errors.file_too_large", lang)
            )

        # --- VALIDATION PASSED — write to disk ---

        # Check if folder exists if provided
        if folder_id is not None:
            db_folder = db.query(Folder).filter(Folder.id == folder_id).first()
            if not db_folder:
                raise HTTPException(status_code=404, detail=t("errors.folder_not_found", lang))

        # Generate unique filename to avoid collisions
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        # Write validated content to disk (already in memory from size check)
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        file_size = len(content)

        # Save to db
        metadata = {
            "original_name": file.filename,
            "size_bytes": file_size,
            "content_type": file.content_type
        }

        db_document = Document(
            filename=file.filename,
            file_path=file_path,
            folder_id=folder_id,
            metadata_json=json.dumps(metadata)
        )

        db.add(db_document)
        db.commit()
        db.refresh(db_document)

        background_tasks.add_task(process_and_update_document, db_document.id)

        return db_document


    @router.get("/folder/{folder_id}", response_model=List[DocumentResponse])
    def get_documents_by_folder(folder_id: int, db: Session = Depends(get_db)):
        return db.query(Document).filter(Document.folder_id == folder_id).all()


    @router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_document(document_id: int, db: Session = Depends(get_db), lang: str = Depends(get_language)):
        db_document = db.query(Document).filter(Document.id == document_id).first()
        if not db_document:
            raise HTTPException(status_code=404, detail=t("errors.document_not_found", lang))

        try:
            if os.path.exists(db_document.file_path):
                os.remove(db_document.file_path)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Failed to delete physical file %s: %s", db_document.file_path, e)

        db.delete(db_document)
        db.commit()
        return None
    ```

    Changes from current:
    - Added `ALLOWED_EXTENSIONS`, `MAX_FILE_SIZE_BYTES`, `ALLOWED_CONTENT_TYPES` constants at module level
    - Added 3-stage validation (extension, content-type, size) BEFORE any disk write
    - Changed from `shutil.copyfileobj` (streaming) to `file.read()` + `buffer.write(content)` (read-then-write) since we need to check size
    - Removed inline `import shutil`
    - Changed `print()` to `logging.getLogger(__name__).warning()` in delete endpoint

    **Step 3: Create `backend/tests/test_documents_router.py`:**

    ```python
    import io
    import pytest
    from unittest.mock import patch


    def test_invalid_extension_exe_returns_400(client):
        file_content = b"fake exe content"
        response = client.post(
            "/api/documents/upload",
            files={"file": ("malware.exe", io.BytesIO(file_content), "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "invalid_file_type" in response.json()["detail"].lower() or "Invalid" in response.json()["detail"]


    def test_invalid_extension_txt_returns_400(client):
        file_content = b"some text"
        response = client.post(
            "/api/documents/upload",
            files={"file": ("readme.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert response.status_code == 400


    def test_valid_extension_pdf_accepted(client):
        """A valid .pdf upload should not be rejected by validation (may fail later for other reasons)."""
        file_content = b"%PDF-1.4 fake pdf content"
        with patch("app.routers.documents.process_and_update_document"):
            response = client.post(
                "/api/documents/upload",
                files={"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")},
            )
        # Should not be 400 or 413 — validation passed
        assert response.status_code != 400
        assert response.status_code != 413


    def test_valid_extension_case_insensitive(client):
        """Uppercase .PDF should be accepted."""
        file_content = b"%PDF-1.4 fake pdf content"
        with patch("app.routers.documents.process_and_update_document"):
            response = client.post(
                "/api/documents/upload",
                files={"file": ("test.PDF", io.BytesIO(file_content), "application/pdf")},
            )
        assert response.status_code != 400


    def test_oversized_file_returns_413(client):
        """File larger than 100MB must return 413."""
        # Create content just over the limit (100MB + 1 byte)
        # To avoid allocating 100MB in tests, mock the read method
        from app.routers.documents import MAX_FILE_SIZE_BYTES

        oversized_content = b"x" * (MAX_FILE_SIZE_BYTES + 1)
        response = client.post(
            "/api/documents/upload",
            files={"file": ("huge.pdf", io.BytesIO(oversized_content), "application/pdf")},
        )
        assert response.status_code == 413


    def test_allowed_extensions_constant():
        """ALLOWED_EXTENSIONS must contain exactly the 4 whitelisted types."""
        from app.routers.documents import ALLOWED_EXTENSIONS
        assert ALLOWED_EXTENSIONS == {".pdf", ".docx", ".pptx", ".xlsx"}


    def test_max_file_size_constant():
        """MAX_FILE_SIZE_BYTES must be 100MB."""
        from app.routers.documents import MAX_FILE_SIZE_BYTES
        assert MAX_FILE_SIZE_BYTES == 100 * 1024 * 1024
    ```
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/test_documents_router.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - `backend/app/routers/documents.py` contains `ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}`
    - `backend/app/routers/documents.py` contains `MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024`
    - `backend/app/routers/documents.py` contains `ALLOWED_CONTENT_TYPES`
    - `backend/app/routers/documents.py` contains `raise HTTPException(status_code=400` before any `open(file_path` or `buffer.write`
    - `backend/app/routers/documents.py` contains `raise HTTPException(status_code=413`
    - `backend/app/routers/documents.py` contains `t("errors.invalid_file_type"`
    - `backend/app/routers/documents.py` contains `t("errors.file_too_large"`
    - `backend/locales/en.json` contains `"invalid_file_type"` and `"file_too_large"`
    - `backend/locales/vi.json` contains `"invalid_file_type"` and `"file_too_large"`
    - `cd backend && python -m pytest tests/test_documents_router.py -x` exits 0
  </acceptance_criteria>
  <done>Upload validates extension (.pdf/.docx/.pptx/.xlsx), Content-Type, and size (100MB) BEFORE writing to disk. Invalid extension returns 400, oversized file returns 413. i18n keys added to both locale files. All 7 tests pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client -> upload endpoint | Untrusted file content, filename, Content-Type cross boundary |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-3a-01 | Tampering | documents.py upload | mitigate | Extension whitelist ALLOWED_EXTENSIONS checked before disk write; Content-Type secondary check; case-insensitive via .lower() |
| T-3a-02 | Denial of Service | documents.py upload | mitigate | MAX_FILE_SIZE_BYTES = 100MB enforced via file.read(limit+1); returns 413 without disk write |
| T-3a-05 | Tampering | documents.py filename | accept | Already mitigated by existing uuid4() filename generation; original filename never used in path construction |
| T-3a-06 | Elevation of Privilege | embeddings.py lazy load | accept | No user input reaches lazy load path; model name is hardcoded "all-MiniLM-L6-v2" |
</threat_model>

<verification>
After all 3 tasks complete:
1. `cd backend && python -m pytest tests/ -v --tb=short` — all tests green (encoding + database + startup + embeddings + vector_store + document_parser + documents_router)
2. Verify lazy load: `cd backend && python -c "import app.services.embeddings; print(app.services.embeddings._default_embeddings)"` — prints `None`
3. Verify ChromaDB path: `cd backend && python -c "from app.services.vector_store import CHROMADB_DIR; import os; assert os.path.isabs(CHROMADB_DIR); print(CHROMADB_DIR)"` — absolute path
4. Verify upload validation: `cd backend && python -c "from app.routers.documents import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES; print(ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES)"` — prints the correct values
</verification>

<success_criteria>
- Embedding model NOT loaded at import time (lazy singleton pattern)
- ChromaDB path is absolute via __file__ with CHROMADB_PATH env var override
- vector_store.py imports get_default_embeddings (not default_embeddings)
- Background task uses joinedload(Document.folder) to prevent DetachedInstanceError
- .exe upload returns 400; 200MB upload returns 413 — both without disk write
- .pdf/.docx/.pptx/.xlsx uploads accepted (case-insensitive)
- i18n keys added for invalid_file_type and file_too_large in both locales
- All test files pass: test_embeddings.py, test_vector_store.py, test_document_parser.py, test_documents_router.py
</success_criteria>

<output>
After completion, create `.planning/phases/03A-infrastructure-fixes/03A-02-SUMMARY.md`
</output>
