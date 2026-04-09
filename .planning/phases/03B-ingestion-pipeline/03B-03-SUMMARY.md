---
phase: 03B-ingestion-pipeline
plan: "03"
subsystem: backend/document-parser
tags: [unstructured, chunking, pipeline, image-summarization, tdd]
dependency_graph:
  requires: [03B-01, 03B-02]
  provides: [DocumentParserService, _build_chunks, process_and_update_document-rewrite]
  affects:
    - backend/app/services/document_parser.py
    - backend/tests/test_document_parser.py
    - backend/tests/test_chunking.py
    - backend/tests/test_pipeline.py
    - backend/tests/conftest.py
tech_stack:
  added: []
  patterns:
    - unstructured-partition-auto
    - RecursiveCharacterTextSplitter-512-64
    - image-summary-interleaving
    - globally-unique-chunk-index
    - NonClosingSession-test-wrapper
    - sys.modules-pre-mock-for-segfault
key_files:
  created:
    - backend/tests/test_chunking.py
    - backend/tests/test_pipeline.py
  modified:
    - backend/app/services/document_parser.py
    - backend/tests/test_document_parser.py
    - backend/tests/conftest.py
decisions:
  - "unstructured.partition.auto segfaults on Windows/WSL2 due to partition.image -> detectron2/torch C-extension; fixed via sys.modules pre-mock in conftest.py before any app import"
  - "_NonClosingSession wrapper prevents test session expunge when process_and_update_document calls db.close() in finally block"
  - "document_parser import order: all imports at top-level (not lazy) per PEP8; segfault mitigated via conftest pre-mock not lazy import"
metrics:
  duration: "~30 minutes"
  completed_date: "2026-04-09"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 3
requirements: [PARSE-01, PARSE-02, PARSE-05, CHUNK-01, CHUNK-02, CHUNK-03]
---

# Phase 03B Plan 03: DocumentParserService Rewrite + Pipeline Summary

**One-liner:** Full ingestion pipeline rewrite with unstructured.io partition(), RecursiveCharacterTextSplitter (512/64), image summary interleaving at page position, globally-unique chunk_index, and pending->processing->completed/failed status transitions.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rewrite DocumentParserService + _build_chunks + tests | 773b2ae | document_parser.py, conftest.py, test_document_parser.py, test_chunking.py |
| 2 | Pipeline integration tests | a2b909c | test_pipeline.py |

---

## What Was Built

### Task 1: DocumentParserService + _build_chunks

**backend/app/services/document_parser.py** — Full rewrite. Three components:

1. **`DocumentParserService.parse_document()`** — Calls `partition(filename=..., strategy="auto", extract_images_in_pdf=True, extract_image_block_output_dir=temp_dir, extract_image_block_types=["Image","Table"])`. Returns `{"elements": [...], "temp_dir": "..."}`. Each element dict carries `text`, `category`, `page_number`, `image_path`. Temp dir cleaned up in except block on partition failure (T-3b-07).

2. **`_build_chunks()`** — Module-level helper. Four phases:
   - Phase 1: Iterate elements; Image elements with image_path → `image_processor.summarize_image()` → `element_type="image_summary"`; empty text → skipped
   - Phase 2: `intermediate.sort(key=lambda x: x["page_number"])` — interleaves image summaries at original page position (D-11)
   - Phase 3: `RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64, add_start_index=True).create_documents()` per item; metadata: `document_id` (str), `filename`, `page_number`, `element_type`
   - Phase 4: Global `chunk_index` assigned as sequential integer 0..N-1 across all elements (Pitfall 7)

3. **`process_and_update_document()`** — Full pipeline orchestration:
   - `joinedload(Document.folder)` to prevent DetachedInstanceError
   - `status="processing"` before parsing
   - Try `parser.parse_document()` → on exception: `status="failed"`, return
   - Try `_build_chunks()` + `vector_store.delete_by_document()` + `vector_store.insert_documents()` → on exception: `status="failed"`
   - Finally: `shutil.rmtree(temp_dir, ignore_errors=True)` always runs (D-03, T-3b-07)
   - On success: `status="completed"`, `metadata_json` updated with `total_chunks` and `total_images`

**backend/tests/conftest.py** — Added `sys.modules` pre-mock for `unstructured.partition.auto` at module top-level (before any app imports). Required because `unstructured.partition.image` imports detectron2/torch C-extensions that segfault on Windows/WSL2.

**backend/tests/test_document_parser.py** — Rewrote 3 source-inspection tests with 5 real unit tests:
- `test_parse_document_returns_elements` — mocked partition, checks elements list + temp_dir key
- `test_image_extraction_paths` — image_path preserved in element dict
- `test_metadata_preserved_page_number` — page_number=3 flows through
- `test_metadata_null_page_number_defaults_to_zero` — None page_number → 0
- `test_parse_failure_cleans_temp_dir` — partition raises → temp dir deleted

**backend/tests/test_chunking.py** — New file, 8 tests:
- `test_chunk_size_within_limit` — no chunk > 512 chars
- `test_chunk_overlap` — consecutive chunks share content
- `test_chunk_metadata_schema` — all 5 keys present
- `test_chunk_metadata_values_are_scalars` — all values are str/int/float/bool
- `test_image_summary_interleaved` — image_summary between page1 and page3 chunks
- `test_image_summary_element_type` — image chunks have element_type="image_summary"
- `test_chunk_index_globally_unique` — chunk_index is [0,1,2,...] no gaps/duplicates
- `test_empty_text_elements_skipped` — empty text → no chunks produced

### Task 2: Pipeline Integration Tests

**backend/tests/test_pipeline.py** — New file, 7 tests:
- `test_status_transitions_success` — status becomes "completed"
- `test_status_failed_on_parse_error` — partition raises → "failed"
- `test_status_failed_on_embedding_error` — insert_documents raises → "failed"
- `test_delete_before_insert` — call order: delete then insert (D-15)
- `test_image_failure_does_not_fail_document` — placeholder → "completed"
- `test_temp_dir_cleaned_on_success` — temp dir gone after success
- `test_temp_dir_cleaned_on_failure` — temp dir gone after failure

All tests use `_NonClosingSession` wrapper — prevents `db.close()` from expunging SQLAlchemy objects mid-test.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] unstructured.partition.auto segfault on Windows/WSL2**
- **Found during:** Task 1 verification
- **Issue:** `from unstructured.partition.auto import partition` causes segfault (exit code 139) because `partition.image` imports detectron2/torch C-extensions not compatible with WSL2 GLIBC on this machine
- **Fix:** Added `sys.modules` pre-mock for `unstructured`, `unstructured.partition`, and `unstructured.partition.auto` at conftest.py module top-level (before any pytest collection imports app code). All tests mock `partition` anyway so this is semantically equivalent.
- **Files modified:** `backend/tests/conftest.py`
- **Commit:** 773b2ae

**2. [Rule 1 - Bug] Session expunge breaks status assertion in pipeline tests**
- **Found during:** Task 2 first test run
- **Issue:** `process_and_update_document` calls `db.close()` in finally block. When the test passes `test_db` as the session, `close()` expunges all ORM objects, making `test_db.refresh(document)` raise `InvalidRequestError: Instance not persistent`
- **Fix:** Added `_NonClosingSession` proxy class that intercepts `close()` calls without executing them. Test session lifecycle remains owned by the test fixture. Status verified via fresh `test_db.query(Document)` call after pipeline.
- **Files modified:** `backend/tests/test_pipeline.py`
- **Commit:** a2b909c

---

## Known Stubs

None — `DocumentParserService.parse_document()` calls real `partition()` (mocked only in tests). `_build_chunks()` calls real `RecursiveCharacterTextSplitter`. `process_and_update_document()` fully wired.

---

## Threat Flags

No new trust boundaries beyond those already in the plan's threat model (T-3b-06 through T-3b-09 all addressed in implementation).

---

## Self-Check: PASSED

**Files exist:**
- `backend/app/services/document_parser.py` — FOUND (contains `from unstructured.partition.auto import partition`, `chunk_size=512`, `element_type.*image_summary`, `status.*completed`)
- `backend/tests/test_document_parser.py` — FOUND (contains `test_parse_document_returns_elements`, `test_metadata_null_page_number_defaults_to_zero`)
- `backend/tests/test_chunking.py` — FOUND (contains `test_chunk_size_within_limit`, `test_chunk_metadata_schema`, `test_image_summary_interleaved`, `test_chunk_index_globally_unique`)
- `backend/tests/test_pipeline.py` — FOUND (contains `test_status_transitions_success`, `test_delete_before_insert`, `test_temp_dir_cleaned_on_success`)
- `backend/tests/conftest.py` — FOUND (contains `sys.modules` pre-mock for unstructured)

**Commits exist:**
- `773b2ae` — feat(03B-03): rewrite DocumentParserService with unstructured parsing and chunking
- `a2b909c` — feat(03B-03): add pipeline integration tests

**Test results:** 20 passed (5 parser + 8 chunking + 7 pipeline), 0 failed
