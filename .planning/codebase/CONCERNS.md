# Concerns

## Critical Issues

### 1. Document Parser is Stubbed
- **File:** `backend/app/services/document_parser.py`
- **Issue:** The `unstructured` imports are commented out. The parser returns mock data (`[MOCK] This is a chunk...`). No real document extraction happens.
- **Impact:** The entire RAG pipeline is non-functional for real documents. Uploads go through but produce fake chunks in ChromaDB.
- **Fix:** Uncomment unstructured.io imports and install system dependencies (poppler, tesseract).

### 2. CORS Wide Open
- **File:** `backend/app/main.py:12-18`
- **Issue:** `allow_origins=["*"]` allows any origin. Acceptable for development, must be locked down for production.
- **Impact:** Security risk in production deployment.

### 3. No Authentication/Authorization
- **Issue:** All API endpoints are publicly accessible. No user authentication, no API key validation for backend access.
- **Impact:** Anyone can create/delete projects and upload files.

## Security Concerns

### 4. API Keys in Request Body
- **File:** `backend/app/services/llm_provider.py`
- **Issue:** LLM provider API keys are expected from the request body (user-supplied from SettingsPanel). These keys travel over HTTP in plaintext unless HTTPS is enforced.
- **Mitigation:** Use HTTPS in production; consider server-side key storage.

### 5. No Input Validation on File Uploads
- **File:** `backend/app/routers/documents.py`
- **Issue:** No file size limit, no file type validation. Any file extension is accepted. Could lead to storage abuse or malicious file uploads.
- **Fix:** Add file size limits and allowed extension whitelist.

## Technical Debt

### 6. No Text Chunking Implementation
- **Issue:** `RecursiveCharacterTextSplitter` from `langchain-text-splitters` is installed but not used anywhere. Documents are not properly chunked before embedding.
- **Impact:** Vector search quality will be poor without proper chunking.

### 7. Hardcoded Database Path
- **File:** `backend/app/core/database.py:4`
- **Issue:** `sqlite:///./rag_database.db` is hardcoded. Should be configurable via environment variable.

### 8. Hardcoded ChromaDB Path
- **File:** `backend/app/services/vector_store.py:5`
- **Issue:** `os.path.join(os.getcwd(), "chroma_db")` is CWD-relative. Changes if the server is started from a different directory.

### 9. No Chat API Endpoint
- **Issue:** LLM providers are configured via factory pattern but no `/api/chat` endpoint exists. The frontend ChatArea component has no backend to talk to for AI responses.

### 10. Background Task DB Session Management
- **File:** `backend/app/services/document_parser.py:53-95`
- **Issue:** `process_and_update_document()` creates its own `SessionLocal()` — this is correct for background tasks, but the `db_document.folder.project_id` access on line 81 triggers a lazy load that may fail if the session doesn't eagerly load the relationship.
- **Risk:** Potential `DetachedInstanceError` if the document's folder relationship isn't loaded.

### 11. requirements.txt Encoding
- **Issue:** `requirements.txt` appears to be UTF-16 encoded (null bytes visible in content). This can cause issues with `pip install -r requirements.txt` on some systems.

## Performance Concerns

### 12. Embedding Model Loaded at Import Time
- **File:** `backend/app/services/embeddings.py:28`
- **Issue:** `default_embeddings = EmbeddingFactory.get_embedding_model("local")` loads the 80MB+ `all-MiniLM-L6-v2` model at module import time. This slows down server startup and uses ~200MB RAM even if embeddings aren't needed.
- **Mitigation:** Lazy load the model on first use.

### 13. No Pagination on List Endpoints
- **File:** `backend/app/routers/projects.py:21`
- **Issue:** `get_projects` has optional `skip`/`limit` but `get_folders` and `get_documents_by_folder` have none. Large projects could return unbounded results.

## Missing Features (from task.md)

- Image summarization pipeline (Gemini Vision)
- Text chunking with RecursiveCharacterTextSplitter
- Semantic search endpoint
- Chat API with streaming (SSE)
- Citation rendering in frontend
- Dynamic provider credential loading
- End-to-end testing
