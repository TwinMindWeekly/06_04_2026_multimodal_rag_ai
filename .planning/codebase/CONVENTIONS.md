# Conventions

## Code Style

### Python (Backend)
- **Standard:** PEP 8
- **Imports:** Standard library first, then third-party, then local (no isort/black configured)
- **Type hints:** Partial usage — some functions have type annotations, others don't
- **Docstrings:** Mixed — some functions have triple-quote docstrings (Vietnamese + English), some have inline comments
- **Comments:** Bilingual — inline comments in Vietnamese for domain logic, English for technical notes

### JavaScript (Frontend)
- **Module system:** ES Modules (`import`/`export`)
- **Component style:** Functional components with hooks (`useState`)
- **JSX:** Standard React 19 JSX
- **Linting:** ESLint configured (`eslint.config.js`)
- **No TypeScript** — plain `.jsx` files

## Design Patterns

### Factory Pattern
Used extensively for AI/ML components:
- `EmbeddingFactory.get_embedding_model(provider)` in `backend/app/services/embeddings.py`
- `LLMProviderFactory.get_llm(provider, api_key, ...)` in `backend/app/services/llm_provider.py`

### Singleton Pattern
- `default_embeddings` in `backend/app/services/embeddings.py` — module-level instance loaded once
- `vector_store` in `backend/app/services/vector_store.py` — module-level instance

### Dependency Injection
- FastAPI `Depends()` for database sessions (`get_db`) and language detection (`get_language`)
- Pydantic schemas for request validation

### Repository-like Pattern
- SQLAlchemy queries directly in routers (no separate repository layer)
- CRUD operations inline in route handlers

## Error Handling

### Backend
- `HTTPException` with i18n error messages: `raise HTTPException(status_code=404, detail=t("errors.folder_not_found", lang))`
- `try/finally` for database session cleanup in background tasks
- `try/except` with warning logs for non-critical file deletion failures
- No global exception handler configured

### Frontend
- axios interceptor for language headers
- No global error boundary visible
- Error handling in API layer not fully standardized

## State Management

### Frontend
- React `useState` hooks (local component state)
- No external state manager (Redux, Zustand, etc.)
- Props drilling between components (`App` → `Sidebar`, `ChatArea`, `SettingsPanel`)

### Backend
- SQLAlchemy session per request (`get_db` dependency)
- Background tasks create their own `SessionLocal()` instances

## Internationalization (i18n)

### Frontend
- `react-i18next` with JSON locale files
- Language stored in `localStorage` (`i18nextLng`)
- Switcher component in UI

### Backend
- Custom i18n module (`backend/app/core/i18n.py`)
- `Accept-Language` header parsing via FastAPI dependency
- Translation files: `backend/locales/en.json`, `backend/locales/vi.json`
- Dot-notation key lookup with English fallback
