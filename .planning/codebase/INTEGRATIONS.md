# Integrations

## Databases

### SQLite (Primary Relational DB)
- **Connection:** `sqlite:///./rag_database.db` (file-based, relative to CWD)
- **ORM:** SQLAlchemy 2.0 with `declarative_base()`
- **Session management:** `SessionLocal` factory with `get_db()` dependency injection
- **Tables:** `projects`, `folders`, `documents`
- **File:** `backend/app/core/database.py`

### ChromaDB (Vector Database)
- **Mode:** `PersistentClient` (local file storage)
- **Storage path:** `./chroma_db/`
- **Collection strategy:** One collection per project (`project_{id}`), plus `general_collection` for unassigned docs
- **File:** `backend/app/services/vector_store.py`

## AI/ML Services

### Embedding Models
- **Default:** HuggingFace `all-MiniLM-L6-v2` via `sentence-transformers` (local, CPU, free)
- **Planned:** OpenAI `text-embedding-3-small`, Google `embedding-001`
- **Pattern:** Factory pattern in `backend/app/services/embeddings.py`

### LLM Providers (configured, not yet wired to chat API)
- **OpenAI:** `gpt-4o-mini` via `ChatOpenAI`
- **Google Gemini:** `gemini-1.5-pro` via `ChatGoogleGenerativeAI`
- **Anthropic Claude:** `claude-3-haiku-20240307` via `ChatAnthropic`
- **Ollama (local):** `llama3` via `ChatOllama` at `http://localhost:11434`
- **Pattern:** Factory pattern in `backend/app/services/llm_provider.py`
- **Auth:** API keys from request body or environment variables (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`)

## External APIs

### Frontend -> Backend
- **Base URL:** `http://localhost:8000/api` (configurable via `VITE_API_URL`)
- **Client:** axios with `Accept-Language` header interceptor
- **File:** `frontend/src/api/client.js`

### API Endpoints (active)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Health check |
| POST | `/api/projects/` | Create project |
| GET | `/api/projects/` | List projects |
| DELETE | `/api/projects/{id}` | Delete project |
| POST | `/api/projects/{id}/folders` | Create folder |
| GET | `/api/projects/{id}/folders` | List folders |
| POST | `/api/documents/upload` | Upload document (multipart) |
| GET | `/api/documents/folder/{id}` | Get docs by folder |
| DELETE | `/api/documents/{id}` | Delete document |

### API Endpoints (planned, not yet implemented)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/chat` | Chat with RAG context |
| GET | `/api/chat/stream` | SSE streaming response |

## Authentication
- **Current:** None (open access, CORS `allow_origins=["*"]`)
- **Planned:** API key-based provider authentication (user-supplied keys)

## File Storage
- **Upload directory:** `./uploads/` with UUID-based unique filenames
- **Extracted images:** `./uploads/extracted_{document_id}/`
- **Strategy:** Local filesystem (no cloud storage)
