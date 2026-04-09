# Stack

## Languages & Runtimes

| Language | Version | Usage |
|----------|---------|-------|
| Python | 3.x | Backend API, document parsing, AI/ML pipeline |
| JavaScript (ES Modules) | ES2020+ | Frontend React application |

## Frontend

| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 19.2.4 | UI component library |
| Vite | 8.0.4 | Build tool and dev server |
| Vanilla CSS | N/A | Styling (no CSS framework — custom design system) |
| axios | 1.15.0 | HTTP client for API calls |
| i18next | 26.0.4 | Internationalization framework |
| react-i18next | 17.0.2 | React bindings for i18next |

**Dev Dependencies:** ESLint 9.x, `@vitejs/plugin-react` 6.x

## Backend

| Technology | Version | Purpose |
|-----------|---------|---------|
| FastAPI | 0.135.3 | Web framework / REST API |
| uvicorn | 0.44.0 | ASGI server |
| SQLAlchemy | 2.0.49 | ORM / database abstraction |
| SQLite | built-in | Relational database (file-based) |
| python-multipart | 0.0.24 | File upload handling |
| python-dotenv | 1.2.2 | Environment variable management |
| pydantic | 2.12.5 | Data validation and serialization |

## AI/ML Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| LangChain | 1.2.15 | LLM orchestration framework |
| langchain-core | 1.2.28 | Core LangChain abstractions |
| langchain-community | 0.4.1 | Community integrations (HuggingFace, Ollama) |
| langchain-text-splitters | 1.1.1 | Text chunking utilities |
| ChromaDB | 1.5.7 | Vector database (local persistent) |
| sentence-transformers | 5.3.0 | Local embedding model (`all-MiniLM-L6-v2`) |
| transformers | 5.5.0 | HuggingFace transformers |
| torch | 2.11.0 | PyTorch (CPU mode for embeddings) |
| numpy | 2.4.4 | Numerical computing |
| scikit-learn | 1.8.0 | ML utilities |

## LLM Provider Dependencies (installed but not yet wired)

| Technology | Version | Purpose |
|-----------|---------|---------|
| langchain-openai | (via langchain) | OpenAI GPT integration |
| langchain-google-genai | (via langchain) | Google Gemini integration |
| langchain-anthropic | (via langchain) | Anthropic Claude integration |
| langchain-community (ChatOllama) | (via langchain) | Local Ollama integration |

## Document Parsing (stubbed)

| Technology | Version | Purpose |
|-----------|---------|---------|
| unstructured | (commented out) | Document parsing (PDF, DOCX, PPTX) — stub implementation |
| PyPika | 0.51.1 | SQL query builder |

## Configuration

- **Backend config:** Hardcoded SQLite path in `backend/app/core/database.py`
- **Frontend config:** `VITE_API_URL` env var, defaults to `http://localhost:8000/api`
- **ChromaDB storage:** `./chroma_db/` directory (relative to CWD)
- **File uploads:** `./uploads/` directory (relative to CWD)
- **i18n locales:** `backend/locales/en.json`, `backend/locales/vi.json`

## Package Management

- **Backend:** `pip` with `requirements.txt` (frozen with versions)
- **Frontend:** `npm` with `package.json`
- **Virtual env:** `backend/venv/` (Python venv)
