# Structure

## Directory Layout

```
multimodal_rag_ai/
├── AI_AGENT_PROTOCOL.md          # Master AI agent guidelines (Vietnamese)
├── README.md                      # Project overview and how-to-run
├── implementation_plan.md         # Technical roadmap (4 phases)
├── task.md                        # Progress tracker with checkboxes
├── start.bat                      # Dev server launcher (frontend + backend)
├── restart.bat                    # Restart script
├── .gitignore                     # Git ignore rules
│
├── backend/                       # FastAPI Python backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app entry point, CORS, router registration
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── database.py       # SQLAlchemy engine, session, Base
│   │   │   └── i18n.py           # Language detection, translation lookup
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── domain.py         # SQLAlchemy models: Project, Folder, Document
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── domain.py         # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── projects.py       # Project + Folder CRUD endpoints
│   │   │   └── documents.py      # Document upload, list, delete endpoints
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── document_parser.py # Document extraction (stubbed unstructured.io)
│   │       ├── embeddings.py      # Embedding model factory (HuggingFace/OpenAI/Gemini)
│   │       ├── vector_store.py    # ChromaDB operations (insert, search)
│   │       └── llm_provider.py    # LLM provider factory (OpenAI/Gemini/Claude/Ollama)
│   ├── locales/
│   │   ├── en.json               # English error messages
│   │   └── vi.json               # Vietnamese error messages
│   ├── requirements.txt          # Python dependencies (frozen)
│   └── venv/                     # Python virtual environment
│
├── frontend/                      # Vite + React frontend
│   ├── index.html                # HTML entry point
│   ├── package.json              # Node dependencies
│   ├── vite.config.js            # Vite configuration
│   ├── eslint.config.js          # ESLint configuration
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   ├── src/
│   │   ├── main.jsx              # React entry point
│   │   ├── App.jsx               # Root component (Sidebar + ChatArea + Settings)
│   │   ├── App.css               # Root layout styles
│   │   ├── index.css             # Global styles, CSS variables, design tokens
│   │   ├── i18n.js               # i18next configuration
│   │   ├── api/
│   │   │   ├── client.js         # axios instance with language interceptor
│   │   │   ├── projectApi.js     # Project/Folder API functions
│   │   │   └── documentApi.js    # Document API functions
│   │   ├── components/
│   │   │   ├── Sidebar.jsx       # Project tree, folder management, upload
│   │   │   ├── Sidebar.css
│   │   │   ├── ChatArea.jsx      # Chat messages, input, citations
│   │   │   ├── ChatArea.css
│   │   │   ├── SettingsPanel.jsx  # Model provider config (API key, temperature)
│   │   │   ├── SettingsPanel.css
│   │   │   ├── ArchitectureModal.jsx # System architecture viewer
│   │   │   └── ArchitectureModal.css
│   │   └── assets/
│   │       ├── hero.png
│   │       ├── react.svg
│   │       └── vite.svg
│   └── node_modules/             # Node dependencies
│
├── docs/                          # Documentation folder
│   └── (technical reference docs)
│
└── .planning/                     # GSD planning artifacts (being created)
    └── codebase/                  # Codebase mapping documents
```

## Key Locations

| What | Where |
|------|-------|
| Backend entry point | `backend/app/main.py` |
| Frontend entry point | `frontend/src/main.jsx` |
| Database config | `backend/app/core/database.py` |
| SQLAlchemy models | `backend/app/models/domain.py` |
| API routes | `backend/app/routers/` |
| Services/Business logic | `backend/app/services/` |
| React components | `frontend/src/components/` |
| API client | `frontend/src/api/client.js` |
| i18n config (frontend) | `frontend/src/i18n.js` |
| i18n config (backend) | `backend/app/core/i18n.py` |
| Backend translations | `backend/locales/` |
| CSS design tokens | `frontend/src/index.css` |

## Naming Conventions

- **Python files:** `snake_case.py` (PEP 8)
- **Python classes:** `PascalCase` (e.g., `VectorStoreService`, `LLMProviderFactory`)
- **Python functions:** `snake_case` (e.g., `get_db`, `process_and_update_document`)
- **React components:** `PascalCase.jsx` (e.g., `ChatArea.jsx`, `SettingsPanel.jsx`)
- **CSS files:** Match component name (e.g., `ChatArea.css` for `ChatArea.jsx`)
- **API files:** `camelCase.js` (e.g., `projectApi.js`, `documentApi.js`)
- **Routes prefix:** `/api/` namespace (e.g., `/api/projects/`, `/api/documents/`)
