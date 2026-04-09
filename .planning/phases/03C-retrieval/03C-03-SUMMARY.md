---
phase: 03C-retrieval
plan: "03"
subsystem: search-api
tags: [search, retrieval, fastapi, router, pydantic, tdd, reindex]
dependency_graph:
  requires: [03C-01, 03C-02]
  provides: [search-router, reindex-endpoint]
  affects: [backend/app/main.py]
tech_stack:
  added: []
  patterns:
    - FastAPI router with Query param validation (max_length, ge/le bounds)
    - BackgroundTasks for async reindex pipeline
    - Mock EmbeddingFactory in tests to prevent real API key calls
    - TDD: RED (test) -> GREEN (impl) commit sequence
key_files:
  created:
    - backend/app/routers/search.py
    - backend/tests/test_search_router.py
  modified:
    - backend/app/schemas/domain.py
    - backend/app/main.py
decisions:
  - "Mock EmbeddingFactory.get_embedding_model in provider mismatch test — real OpenAI call fails without API key"
  - "collection_name derived from integer project_id only (f'project_{project_id}') — no user-controlled string injection"
  - "delete_collection wrapped in try/except — collection may not exist for new projects"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-09T17:03:08Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 4
---

# Phase 03C Plan 03: Search Router Summary

**One-liner:** Created FastAPI search router with GET /api/search (MMR semantic search, SEARCH-01) and POST /api/projects/{id}/reindex (delete+re-queue all project documents, EMBED-05), mounted in main.py, with 10 TDD integration tests passing.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add Pydantic schemas: SearchResult, SearchResponse, ReindexResponse | 32f13ac | backend/app/schemas/domain.py |
| 2 (RED) | Failing tests for search router | f6b34e0 | backend/tests/test_search_router.py |
| 2 (GREEN) | Create search.py router + mount in main.py | 5c5189e | backend/app/routers/search.py, backend/app/main.py, backend/tests/test_search_router.py |

---

## What Was Built

### Task 1: Pydantic Response Schemas

Three new models added to `backend/app/schemas/domain.py`:

- **`SearchResult`**: `content: str`, `metadata: dict`, `similarity: float`, `distance: float`
- **`SearchResponse`**: `results: list[SearchResult]`, `query: str`, `project_id: int`, `result_count: int`
- **`ReindexResponse`**: `status: str`, `project_id: int`, `document_count: int`

### Task 2: Search Router (`backend/app/routers/search.py`)

**`GET /api/search`** (SEARCH-01):
- Query params: `q` (required, min_length=1, max_length=1000), `project_id` (required), `top_k` (1-20, default 5), `score_threshold` (0.0-1.0, default 0.3), `provider` (local/openai/gemini), `api_key` (optional)
- Calls `EmbeddingFactory.get_embedding_model()` → passes model to `vector_store.similarity_search_mmr()`
- Provider mismatch `ValueError` → HTTP 400
- Returns `SearchResponse` with typed `SearchResult` items

**`POST /api/projects/{project_id}/reindex`** (EMBED-05):
- Verifies project exists in DB → 404 if not found
- Calls `vector_store.client.delete_collection(f'project_{project_id}')` — silently ignores if not found
- Marks all project documents (via `Folder` join) as `status='pending'`
- Queues `process_and_update_document(doc.id)` for each document as BackgroundTask
- Returns `ReindexResponse(status='reindex_queued', ...)` with HTTP 202

**`backend/app/main.py`** updated to import and mount `search.router`.

### Test Coverage (10 tests)

| Test | What it Verifies |
|------|-----------------|
| test_search_returns_results | 200, results array, all 4 keys present |
| test_search_empty_project | 200, results=[], result_count=0 |
| test_search_requires_query | 422 without q param |
| test_search_requires_project_id | 422 without project_id |
| test_search_score_threshold | Empty results with high threshold |
| test_search_provider_mismatch | ValueError from mmr -> 400, 'mismatch' in detail |
| test_search_query_max_length | 422 for query > 1000 chars |
| test_reindex_returns_202 | 202, status='reindex_queued', project_id correct |
| test_reindex_nonexistent_project | 404 for project 999 |
| test_reindex_marks_documents_pending | Documents transitioned to status='pending' |
| test_reindex_document_count | document_count=1 in response |

**Full suite: 84/84 tests pass (no regressions)**

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_search_provider_mismatch needed EmbeddingFactory mock**

- **Found during:** Task 2 GREEN phase — test failed with `OpenAIError` instead of expected 400
- **Issue:** Test used `provider=openai` but did not mock `EmbeddingFactory.get_embedding_model`. Router calls EmbeddingFactory before calling `similarity_search_mmr`, so real OpenAI client was instantiated, failing with missing API key.
- **Fix:** Added `@patch('app.routers.search.EmbeddingFactory.get_embedding_model')` decorator to test, returning a `MagicMock()` embedding model.
- **Files modified:** `backend/tests/test_search_router.py`
- **Commit:** 5c5189e (included in GREEN commit)

---

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|-----------|
| T-3c-08 | `q` param has `max_length=1000`; `top_k` has `le=20`; fetch_k internally capped in VectorStore |
| T-3c-10 | `project_id` validated against DB before any collection deletion; 404 for nonexistent |
| T-3c-12 | `collection_name = f'project_{project_id}'` — project_id is an integer from URL path, no user-controlled string |

---

## Known Stubs

None. Both endpoints are fully implemented:
- `/api/search` calls real `similarity_search_mmr` (mocked only in tests)
- `/api/projects/{id}/reindex` calls real `delete_collection` and queues real `process_and_update_document`

---

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: information-disclosure | backend/app/routers/search.py | `api_key` passed as query parameter — visible in server access logs. Accepted per REQUIREMENTS.md (single-user local tool, no auth). Documented in RESEARCH.md Open Question 3. |

---

## Self-Check: PASSED

- [x] `backend/app/routers/search.py` — EXISTS (91 lines)
- [x] `backend/app/schemas/domain.py` — contains `class SearchResult`, `class SearchResponse`, `class ReindexResponse`
- [x] `backend/app/main.py` — contains `search` in import and `include_router(search.router)`
- [x] `backend/tests/test_search_router.py` — EXISTS with 10 tests
- [x] Commit `32f13ac` — EXISTS (feat(03C-03): add SearchResult...)
- [x] Commit `f6b34e0` — EXISTS (test(03C-03): add failing tests...)
- [x] Commit `5c5189e` — EXISTS (feat(03C-03): create search router...)
- [x] 11/11 test_search_router.py tests pass
- [x] 84/84 full suite tests pass (no regressions)
