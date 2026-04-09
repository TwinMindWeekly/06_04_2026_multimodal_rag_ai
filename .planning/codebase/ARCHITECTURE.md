# Architecture

## Pattern

**Layered Architecture** with Factory patterns for AI/ML components.

```
Frontend (React SPA)
    ↓ axios HTTP
Backend (FastAPI REST API)
    ├── Routers (API endpoints)
    ├── Services (business logic)
    ├── Models (SQLAlchemy ORM)
    └── Core (database, i18n config)
        ├── SQLite (relational data)
        ├── ChromaDB (vector embeddings)
        └── LLM Providers (OpenAI, Gemini, Claude, Ollama)
```

## Layers

### 1. Presentation Layer (Frontend)
- **Framework:** React 19 with Vite
- **Components:** `Sidebar`, `ChatArea`, `SettingsPanel`, `ArchitectureModal`
- **State:** React `useState` hooks (no external state manager)
- **API layer:** `frontend/src/api/` with axios client
- **i18n:** `react-i18next` with EN/VI JSON locale files

### 2. API Layer (Routers)
- **`backend/app/routers/projects.py`** — CRUD for projects and folders
- **`backend/app/routers/documents.py`** — File upload, listing, deletion with background processing
- **Pattern:** FastAPI dependency injection (`Depends(get_db)`, `Depends(get_language)`)

### 3. Service Layer
- **`backend/app/services/document_parser.py`** — Document extraction pipeline (stubbed unstructured.io)
- **`backend/app/services/vector_store.py`** — ChromaDB operations (insert, similarity search)
- **`backend/app/services/embeddings.py`** — Embedding model factory (local/OpenAI/Gemini)
- **`backend/app/services/llm_provider.py`** — LLM provider factory (OpenAI/Gemini/Claude/Ollama)

### 4. Data Layer
- **`backend/app/models/domain.py`** — SQLAlchemy models (Project, Folder, Document)
- **`backend/app/schemas/domain.py`** — Pydantic request/response schemas
- **`backend/app/core/database.py`** — SQLite engine, session factory

### 5. Cross-Cutting Concerns
- **i18n:** `backend/app/core/i18n.py` — `Accept-Language` header parsing, translation lookup
- **CORS:** Middleware in `main.py` — allows all origins (development mode)

## Data Flow

### Document Upload Flow
```
User uploads file (UI)
  → POST /api/documents/upload (multipart form)
    → Save file to ./uploads/ (UUID filename)
    → Create Document record in SQLite
    → Spawn BackgroundTask: process_and_update_document()
      → DocumentParserService.parse_document() [stubbed]
      → Extract text_chunks + images
      → Update Document metadata in SQLite
      → vector_store.insert_documents() → ChromaDB
```

### RAG Query Flow (planned, not implemented)
```
User sends message (UI)
  → POST /api/chat
    → vector_store.similarity_search(query, project_id)
    → Get top-K relevant chunks from ChromaDB
    → Build augmented prompt (context + query)
    → LLMProviderFactory.get_llm(provider, api_key)
    → Stream response via SSE
    → Return response + citations to UI
```

## Entry Points
- **Frontend:** `frontend/src/main.jsx` → `App.jsx`
- **Backend:** `backend/app/main.py` → FastAPI app with routers
- **Dev server:** `start.bat` (launches both frontend and backend)

## Key Design Decisions
- **Factory pattern** for both embeddings and LLM providers — allows runtime switching
- **Collection-per-project** in ChromaDB — isolates vector data per project
- **Background tasks** for document processing — non-blocking uploads
- **Singleton embedding model** — loaded once at module level to avoid repeated model loading
