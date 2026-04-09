---
phase: 03B-ingestion-pipeline
plan: "01"
subsystem: backend-data-layer
tags: [schema-migration, vector-store, chromadb, sqlalchemy, dependencies]
dependency_graph:
  requires: []
  provides: [Document.status-column, VectorStoreService.delete_by_document, VectorStoreService._sanitize_metadata, unstructured-dep, google-generativeai-dep]
  affects: [backend/app/models/domain.py, backend/app/services/vector_store.py, backend/app/core/database.py]
tech_stack:
  added: [unstructured[pdf,docx,pptx,xlsx], google-generativeai]
  patterns: [startup-migration, metadata-sanitization, delete-before-insert]
key_files:
  created: []
  modified:
    - backend/requirements.txt
    - backend/app/models/domain.py
    - backend/app/schemas/domain.py
    - backend/app/core/database.py
    - backend/app/services/vector_store.py
    - backend/tests/test_vector_store.py
decisions:
  - "document_id stored as str() in ChromaDB where-clause for safe metadata matching (per RESEARCH.md Pitfall 2, Open Question 3)"
  - "_sanitize_metadata as module-level function (not class method) for reuse by future parser code"
  - "Migration runs at import time (idempotent PRAGMA check) — no Alembic needed for single-column addition"
metrics:
  duration: "~15 minutes"
  completed_date: "2026-04-09T15:14:52Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 6
---

# Phase 03B Plan 01: Foundational Schema + Vector Store Capabilities Summary

**One-liner:** Added Document.status pipeline-state column with idempotent ALTER TABLE migration, ChromaDB metadata sanitizer, and delete_by_document for safe re-processing.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add deps + Document.status + schema + migration | 47a9664 | requirements.txt, models/domain.py, schemas/domain.py, core/database.py |
| 2 | Add delete_by_document + _sanitize_metadata | a1da8d3 | services/vector_store.py, tests/test_vector_store.py |

## What Was Built

### Task 1: Dependencies, Schema, Migration

**requirements.txt** — Appended two new package lines:
- `unstructured[pdf,docx,pptx,xlsx]` — required by Plan 03 parser rewrite
- `google-generativeai` — required by Plan 03 Gemini Vision image summarization

**backend/app/models/domain.py** — Added `status` column to Document SQLAlchemy model:
```python
status = Column(String, default="pending", nullable=False)
```
Placed after `uploaded_at`. Supports pipeline state tracking (pending → processing → done/failed).

**backend/app/schemas/domain.py** — Added `status: Optional[str] = None` to both `DocumentBase` and `DocumentResponse` so the field is exposed in API responses and accepted in create requests.

**backend/app/core/database.py** — Added `_migrate_add_status_column(engine)` function that:
- Reads the SQLite file path from `engine.url`
- Uses `PRAGMA table_info(documents)` to check if `status` column already exists
- Runs `ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'pending' NOT NULL` only if missing
- Wrapped in try/except, calls `conn.close()` in finally block
- Called at module level immediately after engine creation (idempotent on every startup)

### Task 2: Vector Store Capabilities

**backend/app/services/vector_store.py** — Three additions:

1. **`_sanitize_metadata(meta: dict) -> dict`** (module-level) — Converts all metadata values to ChromaDB-safe scalar types: `None` → `""`, non-scalar (list/dict) → `str(v)`, valid scalars (str/int/float/bool) pass through.

2. **`VectorStoreService.delete_by_document()`** — Deletes all vectors for a given `document_id` using `collection.delete(where={"document_id": str(document_id)})`. Catches all exceptions (collection may not exist on first run) and logs at DEBUG level. `document_id` cast to `str` for consistent where-clause matching.

3. **`insert_documents()` updated** — Now passes `metadatas=[_sanitize_metadata(m) for m in metadatas]` to `collection.upsert()` instead of raw `metadatas`.

**backend/tests/test_vector_store.py** — Three new tests appended:
- `test_sanitize_metadata_removes_none` — verifies None becomes ""
- `test_sanitize_metadata_converts_non_scalar` — verifies list/dict become str representations
- `test_delete_by_document_no_collection_no_error` — verifies no exception when collection absent

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — no placeholder or hardcoded stubs introduced.

## Threat Flags

No new security surface introduced. Changes are:
- Static SQL (PRAGMA + ALTER TABLE) with no user input — T-3b-02 accepted per plan threat model
- Metadata sanitization applied before ChromaDB insert — T-3b-01 mitigated per plan threat model

## Self-Check: PASSED

**Files exist:**
- backend/requirements.txt — FOUND (contains unstructured, google-generativeai)
- backend/app/models/domain.py — FOUND (contains status column)
- backend/app/schemas/domain.py — FOUND (contains status: Optional[str])
- backend/app/core/database.py — FOUND (contains _migrate_add_status_column)
- backend/app/services/vector_store.py — FOUND (contains _sanitize_metadata, delete_by_document)
- backend/tests/test_vector_store.py — FOUND (contains all 3 new tests)

**Commits exist:**
- 47a9664 — feat(03B-01): add Document.status column, schema, migration, new deps
- a1da8d3 — feat(03B-01): add _sanitize_metadata and delete_by_document to VectorStoreService
