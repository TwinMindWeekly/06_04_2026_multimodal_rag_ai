# Testing

## Current State

**No tests exist in the codebase.** No test framework is configured for either frontend or backend.

## Backend

- **Framework:** None configured (pytest recommended per project conventions)
- **Test directory:** Does not exist
- **Coverage tool:** None
- **requirements.txt:** Does not include `pytest` or any test dependencies

### Recommended Setup
```
backend/
├── tests/
│   ├── __init__.py
│   ├── test_projects.py      # Project/Folder CRUD API tests
│   ├── test_documents.py     # Document upload/delete API tests
│   ├── test_vector_store.py  # ChromaDB operations tests
│   ├── test_embeddings.py    # Embedding factory tests
│   └── test_i18n.py          # i18n translation tests
```

## Frontend

- **Framework:** None configured (Vitest recommended for Vite projects)
- **Test directory:** Does not exist
- **E2E:** None configured (Playwright recommended)
- **package.json:** No test script defined

### Recommended Setup
```json
{
  "devDependencies": {
    "vitest": "^x.x.x",
    "@testing-library/react": "^x.x.x"
  },
  "scripts": {
    "test": "vitest"
  }
}
```

## Critical Modules Needing Tests

1. **`backend/app/services/document_parser.py`** — Document parsing pipeline (currently stubbed)
2. **`backend/app/services/vector_store.py`** — ChromaDB insert and similarity search
3. **`backend/app/services/embeddings.py`** — Embedding factory provider switching
4. **`backend/app/services/llm_provider.py`** — LLM factory provider switching
5. **`backend/app/core/i18n.py`** — Translation lookup with fallback logic
6. **`backend/app/routers/documents.py`** — File upload with background processing
