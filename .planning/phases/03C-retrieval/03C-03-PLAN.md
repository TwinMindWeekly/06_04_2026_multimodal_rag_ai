---
phase: 03C-retrieval
plan: "03"
type: execute
wave: 2
depends_on: ["03C-01", "03C-02"]
files_modified:
  - backend/app/routers/search.py
  - backend/app/schemas/domain.py
  - backend/app/main.py
  - backend/tests/test_search_router.py
autonomous: true
requirements: [EMBED-05, SEARCH-01]
must_haves:
  truths:
    - "GET /api/search returns Top-K chunks with content, metadata, similarity, and distance"
    - "GET /api/search with low score_threshold returns fewer results"
    - "POST /api/projects/{id}/reindex returns 202, deletes collection, queues re-processing"
    - "Re-index endpoint marks all project documents as pending"
    - "Search with nonexistent project returns empty results array"
    - "Search router is mounted in main.py and accessible"
  artifacts:
    - path: "backend/app/routers/search.py"
      provides: "Search and reindex endpoints"
      exports: ["router"]
    - path: "backend/app/schemas/domain.py"
      provides: "SearchResult and SearchResponse Pydantic models"
      contains: "class SearchResult"
    - path: "backend/app/main.py"
      provides: "Search router mounted"
      contains: "search"
    - path: "backend/tests/test_search_router.py"
      provides: "Integration tests for search and reindex endpoints"
      contains: "test_search_returns_results"
  key_links:
    - from: "backend/app/routers/search.py"
      to: "backend/app/services/vector_store.py"
      via: "vector_store.similarity_search_mmr()"
      pattern: "vector_store\\.similarity_search_mmr"
    - from: "backend/app/routers/search.py"
      to: "backend/app/services/embeddings.py"
      via: "EmbeddingFactory.get_embedding_model()"
      pattern: "EmbeddingFactory\\.get_embedding_model"
    - from: "backend/app/routers/search.py"
      to: "backend/app/services/document_parser.py"
      via: "process_and_update_document for reindex"
      pattern: "process_and_update_document"
    - from: "backend/app/main.py"
      to: "backend/app/routers/search.py"
      via: "app.include_router"
      pattern: "include_router.*search"
---

<objective>
Create the search router with GET /api/search and POST /api/projects/{id}/reindex endpoints, add Pydantic response schemas, mount in main.py, and write integration tests.

Purpose: SEARCH-01 requires a semantic search endpoint. EMBED-05 requires a re-index endpoint. These are the API surface that Phase 4a (Chat Backend) will consume.

Output: New search.py router with 2 endpoints, response schemas in domain.py, router mounted in main.py, and integration tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/03C-retrieval/03C-RESEARCH.md
@.planning/phases/03C-retrieval/03C-01-SUMMARY.md
@.planning/phases/03C-retrieval/03C-02-SUMMARY.md

<interfaces>
<!-- VectorStoreService after Plan 02 -->
From backend/app/services/vector_store.py (after Plan 02):
```python
class VectorStoreService:
    def __init__(self): ...
    def _get_collection_name(self, project_id: int): ...
    def _check_provider_match(self, collection, active_provider: str) -> None: ...
    def insert_documents(self, text_chunks, metadatas, project_id=None, embedding_model=None, provider='local', model='all-MiniLM-L6-v2'): ...
    def delete_by_document(self, document_id, project_id=None): ...
    def similarity_search(self, query, top_k=4, project_id=None, embedding_model=None): ...
    def similarity_search_mmr(self, query, top_k=5, fetch_k=20, score_threshold=0.3, lambda_mult=0.5, project_id=None, embedding_model=None, provider='local') -> list[dict]: ...

vector_store = VectorStoreService()  # module-level singleton
```

<!-- EmbeddingFactory after Plan 01 -->
From backend/app/services/embeddings.py (after Plan 01):
```python
class EmbeddingFactory:
    @staticmethod
    def get_embedding_model(provider: str = 'local', api_key: str | None = None): ...
```

<!-- Existing router patterns -->
From backend/app/routers/projects.py:
```python
router = APIRouter(prefix="/api/projects", tags=["projects"])
# Uses: Depends(get_db), Depends(get_language), HTTPException, t()
```

From backend/app/routers/documents.py:
```python
router = APIRouter(prefix="/api/documents", tags=["documents"])
# Uses: BackgroundTasks, process_and_update_document
```

<!-- Domain models -->
From backend/app/models/domain.py:
```python
class Project(Base): __tablename__ = "projects"  # id, name, created_at, folders
class Folder(Base): __tablename__ = "folders"    # id, name, project_id, parent_id, documents
class Document(Base): __tablename__ = "documents" # id, filename, file_path, folder_id, metadata_json, uploaded_at, status
```

From backend/app/main.py (router mounting pattern):
```python
from app.routers import projects, documents
app.include_router(projects.router)
app.include_router(documents.router)
```

From backend/tests/conftest.py:
```python
@pytest.fixture
def client(test_engine): ...  # TestClient with dependency overrides
@pytest.fixture
def test_db(test_engine): ...  # SQLAlchemy session
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add Pydantic schemas for search response</name>
  <files>backend/app/schemas/domain.py</files>
  <read_first>
    - backend/app/schemas/domain.py
  </read_first>
  <action>
Add two new Pydantic models at the end of `backend/app/schemas/domain.py`:

```python
class SearchResult(BaseModel):
    """Single search result with chunk content, metadata, and similarity scores."""
    content: str
    metadata: dict
    similarity: float
    distance: float


class SearchResponse(BaseModel):
    """Response wrapper for search endpoint."""
    results: list[SearchResult]
    query: str
    project_id: int
    result_count: int
```

Also add a reindex response model:

```python
class ReindexResponse(BaseModel):
    """Response for reindex endpoint."""
    status: str
    project_id: int
    document_count: int
```

Use single quotes in string defaults per project convention. Keep all existing models untouched.
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/TwinMindWeekly/06_04_2026_multimodal_rag_ai && backend/.venv/Scripts/python -c "from app.schemas.domain import SearchResult, SearchResponse, ReindexResponse; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - grep "class SearchResult" backend/app/schemas/domain.py returns a match
    - grep "class SearchResponse" backend/app/schemas/domain.py returns a match
    - grep "class ReindexResponse" backend/app/schemas/domain.py returns a match
    - grep "content: str" backend/app/schemas/domain.py returns a match
    - grep "similarity: float" backend/app/schemas/domain.py returns a match
    - python -c "from app.schemas.domain import SearchResult, SearchResponse, ReindexResponse" succeeds
  </acceptance_criteria>
  <done>SearchResult, SearchResponse, and ReindexResponse Pydantic models exist in schemas/domain.py and are importable.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create search router + reindex endpoint + mount in main.py + tests</name>
  <files>backend/app/routers/search.py, backend/app/main.py, backend/tests/test_search_router.py</files>
  <read_first>
    - backend/app/main.py
    - backend/app/routers/projects.py (pattern reference for router structure)
    - backend/app/routers/documents.py (pattern reference for BackgroundTasks usage)
    - backend/app/services/vector_store.py (after Plan 02 — consumer of similarity_search_mmr)
    - backend/app/services/embeddings.py (after Plan 01 — EmbeddingFactory)
    - backend/app/services/document_parser.py (process_and_update_document for reindex)
    - backend/app/schemas/domain.py (after Task 1 — SearchResponse, ReindexResponse)
    - backend/tests/conftest.py (client fixture)
  </read_first>
  <behavior>
    - test_search_returns_results: POST search query to project with documents. Assert 200, response has 'results' array, each result has content/metadata/similarity/distance keys.
    - test_search_empty_project: Search on project with no documents. Assert 200, results==[].
    - test_search_requires_query: Call /api/search without q param. Assert 422 (validation error).
    - test_search_requires_project_id: Call /api/search without project_id. Assert 422.
    - test_search_score_threshold: Call with high score_threshold. Fewer or no results returned.
    - test_search_provider_mismatch: Search with provider different from collection. Assert 400 with mismatch error.
    - test_reindex_returns_202: POST /api/projects/{id}/reindex on existing project. Assert 202, response has status='reindex_queued'.
    - test_reindex_nonexistent_project: POST /api/projects/999/reindex. Assert 404.
    - test_reindex_marks_documents_pending: After reindex, all project documents have status='pending'.
    - test_search_query_max_length: Query with >1000 chars. Assert 422 (validation error).
  </behavior>
  <action>
1. **Create test file first:** `backend/tests/test_search_router.py`:

   ```python
   import pytest
   from unittest.mock import patch, MagicMock
   from app.models.domain import Project, Folder, Document


   def _seed_project_with_document(db):
       """Helper: create a project with a folder and a document."""
       project = Project(name='Test Project')
       db.add(project)
       db.commit()
       db.refresh(project)
       folder = Folder(name='test', project_id=project.id)
       db.add(folder)
       db.commit()
       db.refresh(folder)
       doc = Document(
           filename='test.pdf',
           file_path='/tmp/test.pdf',
           folder_id=folder.id,
           status='completed',
       )
       db.add(doc)
       db.commit()
       db.refresh(doc)
       return project, folder, doc
   ```

   Write 10 tests using the `client` and `test_db` fixtures from conftest.py. Mock `vector_store.similarity_search_mmr` to return controlled data for search tests. Mock `vector_store.client.delete_collection` and `process_and_update_document` for reindex tests.

   Key mock patterns:
   - For search: `@patch('app.routers.search.vector_store.similarity_search_mmr')` returning `[{'content': 'test chunk', 'metadata': {'filename': 'test.pdf', 'page_number': 1}, 'similarity': 0.85, 'distance': 0.15}]`
   - For provider mismatch: mock raises `ValueError('Embedding provider mismatch...')`
   - For reindex: `@patch('app.routers.search.process_and_update_document')` and `@patch('app.routers.search.vector_store.client.delete_collection')`

   For tests that need DB data (reindex tests), use the `test_db` fixture to seed data, then use `client` (which shares the same test_engine) to make HTTP requests.

   **Important:** The `client` fixture creates its own session via `override_get_db`. To share DB state, seed data in a separate test that uses the `test_engine` directly, or restructure the seed to use the client's POST endpoints. The simplest approach: for reindex tests, create project+folder+document via the `test_db` fixture (which shares the same in-memory SQLite via StaticPool), then call the reindex endpoint via `client`.

2. Run tests — they should FAIL (RED).

3. **Create** `backend/app/routers/search.py`:

   ```python
   import logging
   from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
   from sqlalchemy.orm import Session

   from app.core.database import get_db
   from app.core.i18n import get_language, t
   from app.models.domain import Project, Folder, Document
   from app.schemas.domain import SearchResponse, SearchResult, ReindexResponse
   from app.services.vector_store import vector_store
   from app.services.embeddings import EmbeddingFactory
   from app.services.document_parser import process_and_update_document

   logger = logging.getLogger(__name__)

   router = APIRouter(tags=['search'])


   @router.get('/api/search', response_model=SearchResponse)
   def search(
       q: str = Query(..., min_length=1, max_length=1000, description='Search query text'),
       project_id: int = Query(..., description='Project ID to search within'),
       top_k: int = Query(5, ge=1, le=20, description='Number of results'),
       score_threshold: float = Query(0.3, ge=0.0, le=1.0, description='Minimum similarity score'),
       provider: str = Query('local', description='Embedding provider: local/openai/gemini'),
       api_key: str | None = Query(None, description='API key for paid providers'),
       lang: str = Depends(get_language),
   ):
       """Semantic search endpoint returning Top-K chunks with distances and metadata (SEARCH-01)."""
       try:
           embedding_model = EmbeddingFactory.get_embedding_model(provider=provider, api_key=api_key)
       except ValueError as e:
           raise HTTPException(status_code=400, detail=str(e))

       try:
           results = vector_store.similarity_search_mmr(
               query=q,
               top_k=top_k,
               score_threshold=score_threshold,
               project_id=project_id,
               embedding_model=embedding_model,
               provider=provider,
           )
       except ValueError as e:
           # EMBED-04: provider mismatch
           raise HTTPException(status_code=400, detail=str(e))

       return SearchResponse(
           results=[SearchResult(**r) for r in results],
           query=q,
           project_id=project_id,
           result_count=len(results),
       )


   @router.post('/api/projects/{project_id}/reindex', response_model=ReindexResponse, status_code=202)
   def reindex_project(
       project_id: int,
       background_tasks: BackgroundTasks,
       db: Session = Depends(get_db),
       lang: str = Depends(get_language),
   ):
       """Delete all vectors for a project and re-queue all documents for re-embedding (EMBED-05)."""
       # Verify project exists
       db_project = db.query(Project).filter(Project.id == project_id).first()
       if not db_project:
           raise HTTPException(status_code=404, detail=t('errors.project_not_found', lang))

       # Delete entire ChromaDB collection for this project
       collection_name = f'project_{project_id}'
       try:
           vector_store.client.delete_collection(collection_name)
       except Exception:
           pass  # Collection may not exist yet

       # Mark all documents in project as pending and queue re-processing
       documents = (
           db.query(Document)
           .join(Folder)
           .filter(Folder.project_id == project_id)
           .all()
       )
       for doc in documents:
           doc.status = 'pending'
       db.commit()

       for doc in documents:
           background_tasks.add_task(process_and_update_document, doc.id)

       return ReindexResponse(
           status='reindex_queued',
           project_id=project_id,
           document_count=len(documents),
       )
   ```

4. **Mount in main.py:** Add `search` to the router imports and include it:

   In `backend/app/main.py`, change line 52 from:
   ```python
   from app.routers import projects, documents  # noqa: E402
   ```
   to:
   ```python
   from app.routers import projects, documents, search  # noqa: E402
   ```

   And add after line 55:
   ```python
   app.include_router(search.router)
   ```

5. Run tests — they should PASS (GREEN).

6. Run full test suite to confirm no regressions:
   ```
   backend/.venv/Scripts/python -m pytest backend/tests/ -x -q
   ```
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/TwinMindWeekly/06_04_2026_multimodal_rag_ai && backend/.venv/Scripts/python -m pytest backend/tests/test_search_router.py -x -v && backend/.venv/Scripts/python -m pytest backend/tests/ -x -q</automated>
  </verify>
  <acceptance_criteria>
    - file backend/app/routers/search.py exists
    - grep "router = APIRouter" backend/app/routers/search.py returns a match
    - grep "/api/search" backend/app/routers/search.py returns a match
    - grep "/api/projects/{project_id}/reindex" backend/app/routers/search.py returns a match
    - grep "similarity_search_mmr" backend/app/routers/search.py returns a match
    - grep "EmbeddingFactory.get_embedding_model" backend/app/routers/search.py returns a match
    - grep "process_and_update_document" backend/app/routers/search.py returns a match
    - grep "status_code=202" backend/app/routers/search.py returns a match
    - grep "max_length=1000" backend/app/routers/search.py returns a match
    - grep "delete_collection" backend/app/routers/search.py returns a match
    - grep "search" backend/app/main.py returns matches (import + include_router)
    - grep "include_router.*search" backend/app/main.py returns a match
    - file backend/tests/test_search_router.py exists
    - grep "test_search_returns_results" backend/tests/test_search_router.py returns a match
    - grep "test_reindex_returns_202" backend/tests/test_search_router.py returns a match
    - grep "test_search_provider_mismatch" backend/tests/test_search_router.py returns a match
    - grep "test_search_query_max_length" backend/tests/test_search_router.py returns a match
    - pytest backend/tests/test_search_router.py -x -v shows 10 tests passed
    - pytest backend/tests/ -x -q shows all tests passed (0 failures)
  </acceptance_criteria>
  <done>Search router with GET /api/search (SEARCH-01) and POST /api/projects/{id}/reindex (EMBED-05) endpoints created and mounted. Search returns Top-K chunks with content, metadata, similarity, distance. Reindex deletes collection and queues background re-processing. All 10 router tests + full suite pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| HTTP client -> /api/search | Untrusted query text, project_id, api_key from HTTP query params |
| HTTP client -> /api/projects/{id}/reindex | project_id from URL path |
| search router -> VectorStoreService | Validated params passed to service layer |
| reindex router -> BackgroundTasks | Document IDs queued for background processing |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-3c-08 | Denial of Service | /api/search | mitigate | q param has max_length=1000; top_k has le=20; fetch_k internally capped at min(fetch_k, count). Prevents unbounded memory/compute. |
| T-3c-09 | Information Disclosure | /api/search api_key | accept | API key passed as query param (logged in access logs). Accepted per REQUIREMENTS.md: single-user local tool, no auth required. RESEARCH.md Open Question 3 documents this limitation. |
| T-3c-10 | Tampering | /api/projects/{id}/reindex | mitigate | project_id validated against DB before any action. 404 returned for nonexistent projects. |
| T-3c-11 | Denial of Service | /api/projects/{id}/reindex | accept | No rate limiting on reindex. Single-user local tool; re-index is intentional user action. |
| T-3c-12 | Tampering | collection_name injection | mitigate | collection_name derived from integer project_id via f'project_{project_id}'. No user-controlled string in collection name. |
</threat_model>

<verification>
1. `backend/.venv/Scripts/python -m pytest backend/tests/test_search_router.py -x -v` — all 10 tests pass
2. `backend/.venv/Scripts/python -m pytest backend/tests/ -x -q` — full suite green
3. `curl http://localhost:8000/api/search?q=test&project_id=1` returns valid JSON (if server running)
4. `grep "include_router.*search" backend/app/main.py` — search router mounted
</verification>

<success_criteria>
- GET /api/search accepts q, project_id, top_k, score_threshold, provider, api_key query params
- GET /api/search returns SearchResponse with results array of SearchResult objects
- POST /api/projects/{id}/reindex returns 202 with ReindexResponse
- Reindex deletes ChromaDB collection and marks all project documents as pending
- Query text limited to 1000 chars (DoS mitigation)
- Provider mismatch returns 400 with clear error message
- Nonexistent project returns 404 on reindex
- All 10 search router tests pass
- Full test suite green (no regressions)
</success_criteria>

<output>
After completion, create `.planning/phases/03C-retrieval/03C-03-SUMMARY.md`
</output>
