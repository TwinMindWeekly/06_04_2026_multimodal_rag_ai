---
phase: 05-validation
plan: 01
subsystem: backend/tests
tags: [testing, e2e, chromadb, rag, validation, pytest]
dependency_graph:
  requires:
    - 03B-03 (process_and_update_document pipeline with status transitions)
    - 03C-02 (VectorStoreService with MMR, provider mismatch guard)
    - 04A-02 (chat SSE endpoint with LLMProviderFactory)
  provides:
    - E2E test coverage for full RAG pipeline (TEST-01)
    - Metadata round-trip validation for ChromaDB (TEST-02)
    - Provider switch safety enforcement test (TEST-03)
  affects: []
tech_stack:
  added: []
  patterns:
    - _NonClosingSession wrapper reused from test_pipeline.py
    - ChromaDB PersistentClient in tmpdir with del client before rmtree (Windows lock)
    - get_default_embeddings mocked to avoid loading HuggingFace model in E2E test
    - SSE collection via client.stream + iter_lines() from test_chat_router.py
key_files:
  created:
    - backend/tests/test_e2e_validation.py
  modified: []
decisions:
  - Mock get_default_embeddings in app.services.vector_store during E2E pipeline test
    (process_and_update_document calls insert_documents without embedding_model, so
    the default HuggingFace model would be loaded without this mock — would require
    the model to be present and slow CI)
  - Use score_threshold=0.0 in E2E chat query to guarantee results are returned
    regardless of vector similarity between mocked embeddings and query embedding
  - Tasks 1 and 2 committed as single atomic commit since both concern the same file
    and were written/tested together
metrics:
  duration: "~12 minutes"
  completed: "2026-04-09"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 1
requirements_satisfied:
  - TEST-01
  - TEST-02
  - TEST-03
---

# Phase 05 Plan 01: E2E Validation Test Suite Summary

**One-liner:** pytest E2E suite with 6 tests covering full RAG pipeline (upload→ChromaDB→chat→SSE citations), metadata round-trip for all 5 CHUNK-02 fields, and provider-switch safety via ValueError + reindex endpoint.

## What Was Built

Created `backend/tests/test_e2e_validation.py` with 3 test classes covering all 3 validation requirements:

### TestE2EUploadToChat (TEST-01)
- Seeds SQLite with Project + Folder + Document
- Runs `process_and_update_document` with real ChromaDB (tmpdir), mocked partition and ImageProcessorService
- Verifies `document.status == 'completed'`
- Verifies all 5 metadata fields present in ChromaDB collection
- POSTs to `/api/chat` with mocked LLM and embeddings, real ChromaDB vector search
- Verifies SSE stream contains text events and terminal `{"done": true, "citations": [...]}` event

### TestChromaDBMetadataRoundTrip (TEST-02)
- `test_metadata_roundtrip_all_five_fields`: inserts one chunk with all 5 CHUNK-02 fields, queries, asserts `document_id='42'` (string), `filename='test.pdf'`, `page_number=3`, `chunk_index=0`, `element_type='NarrativeText'` all survive
- `test_metadata_roundtrip_multiple_chunks`: inserts 2 chunks with different page_numbers (1 and 5), verifies both returned with correct metadata

### TestProviderSwitchReindex (TEST-03)
- `test_provider_mismatch_raises_valueerror`: insert with `provider='local'`, query with `provider='openai'` → `ValueError` matching `'mismatch'`
- `test_delete_and_reinsert_with_new_provider_succeeds`: delete_collection + re-insert with `provider='openai'` → query succeeds
- `test_reindex_endpoint_marks_pending_and_deletes_collection`: POST `/api/projects/{id}/reindex` → 202, `document.status='pending'`, `delete_collection` called once with correct name

## Test Results

```
6 passed in 0.60s (test_e2e_validation.py)
105 passed in 23.24s (full suite — zero regressions)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Mock get_default_embeddings during E2E pipeline test**

- **Found during:** Task 1
- **Issue:** `process_and_update_document` calls `vector_store.insert_documents` without `embedding_model` parameter. This causes the function to call `get_default_embeddings()` which loads the real HuggingFace `all-MiniLM-L6-v2` model. In the E2E test where we patch `app.services.document_parser.vector_store` with a real ChromaDB tmpdir instance, the actual `get_default_embeddings` in `app.services.vector_store` module is still called unless explicitly mocked.
- **Fix:** Added `patch('app.services.vector_store.get_default_embeddings', return_value=mock_emb_insert)` to the E2E test context manager. This avoids loading the real HuggingFace model while still using a real ChromaDB instance.
- **Files modified:** `backend/tests/test_e2e_validation.py`
- **Commit:** eeeabde

The plan's code template had `mock_emb_insert` variable ready but missed this patch. The fix is required for correct test behavior — without it the test would attempt to download/load the HuggingFace model which is not guaranteed in CI.

## Known Stubs

None. All test assertions verify real behavior — no placeholder data that blocks the test's goal.

## Threat Flags

None. Test-only code; no new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

- FOUND: `backend/tests/test_e2e_validation.py`
- FOUND commit: `eeeabde`
- 6/6 tests pass (`pytest tests/test_e2e_validation.py -v`)
- 105/105 tests pass (full suite, zero regressions)
