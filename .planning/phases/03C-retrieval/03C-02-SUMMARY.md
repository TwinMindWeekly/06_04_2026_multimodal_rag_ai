---
phase: 03C-retrieval
plan: "02"
subsystem: vector-store
tags: [chromadb, embeddings, mmr, threading, search, retrieval]
dependency_graph:
  requires: [03B-01]
  provides: [03C-03]
  affects: [backend/app/services/vector_store.py]
tech_stack:
  added: []
  patterns:
    - per-project threading.Lock dict for write serialization
    - ChromaDB collection metadata for provider tracking
    - cosine distance to similarity conversion (sim = 1 - dist)
    - MMR deduplication via langchain_core.vectorstores.utils
key_files:
  created: []
  modified:
    - backend/app/services/vector_store.py
    - backend/tests/test_vector_store.py
decisions:
  - "Use get_or_create_collection metadata param to store provider info on first creation only (ChromaDB behavior verified in RESEARCH.md)"
  - "similarity = 1 - cosine_distance formula verified against ChromaDB 1.5.7 cosine metric"
  - "Lazy import of maximal_marginal_relevance inside similarity_search_mmr method to avoid top-level dependency"
  - "fetch_k capped at min(fetch_k, collection.count()) to prevent unbounded memory usage (T-3c-05)"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-09T16:53:19Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 03C Plan 02: VectorStore Extended Capabilities Summary

**One-liner:** Extended VectorStoreService with ChromaDB collection metadata, per-project threading.Lock write serialization, provider mismatch guard, score threshold filtering, and MMR deduplication using langchain_core.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Collection metadata + provider mismatch + write lock | 16d60da | vector_store.py, test_vector_store.py |
| 2 | similarity_search_mmr with score threshold + MMR | 2e86260 | test_vector_store.py |

---

## What Was Built

### Task 1: Collection Metadata, Provider Mismatch Check, Write Lock (EMBED-03, EMBED-04, EMBED-06)

**`_get_project_lock(project_id)`** — Module-level function that maintains a dict of `threading.Lock` objects keyed by project_id. Protected by a global `_locks_mutex` for thread-safe creation. Returns the same Lock for the same project_id (identity guarantee).

**`VectorStoreService._check_provider_match(collection, active_provider)`** — Reads `collection.metadata['embedding_provider']` and raises `ValueError` with "mismatch" message if stored provider differs from the active provider. No-op when metadata is absent (new collections).

**Extended `insert_documents`** — Now accepts `embedding_model`, `provider`, `model` params. Sets `metadata={'embedding_provider': provider, 'embedding_model': model, 'hnsw:space': 'cosine'}` on `get_or_create_collection`. Wraps ChromaDB `upsert` in `_get_project_lock(project_id)` context manager.

**Extended `similarity_search`** — Now accepts injectable `embedding_model` param; falls back to `get_default_embeddings()`.

### Task 2: similarity_search_mmr (SEARCH-01, SEARCH-02, SEARCH-03)

**`VectorStoreService.similarity_search_mmr`** — Full semantic search pipeline:
1. Retrieves collection (returns `[]` if not found)
2. Calls `_check_provider_match` (EMBED-04)
3. Fetches `min(fetch_k, count)` results with embeddings included
4. Converts cosine distances to similarities: `sim = 1.0 - dist`
5. Filters results with `sim < score_threshold` (SEARCH-02)
6. Applies `maximal_marginal_relevance` from `langchain_core.vectorstores.utils` for deduplication (SEARCH-03)
7. Returns list of dicts: `{content, metadata, similarity, distance}`

---

## Test Coverage

| Test | Purpose |
|------|---------|
| test_collection_metadata_stored | Verifies embedding_provider, embedding_model, hnsw:space=cosine in ChromaDB metadata |
| test_provider_mismatch_raises | ValueError raised when active_provider != stored provider |
| test_provider_match_passes | No exception when providers match |
| test_write_lock_serializes | Same project_id returns identical Lock object |
| test_write_lock_different_projects | Different project_ids return different Lock objects |
| test_insert_documents_uses_lock | Lock context manager (__enter__) called during upsert |
| test_similarity_search_mmr_empty_collection | Non-existent collection returns [] |
| test_similarity_search_mmr_returns_format | Result dicts have exactly {content, metadata, similarity, distance} keys |
| test_score_threshold_filters | Only results with sim >= threshold returned (tested with mocked distances [0.1, 0.5, 0.9]) |
| test_mmr_deduplication | MMR selects diverse results from near-duplicate embeddings, returns <= top_k |
| test_similarity_search_mmr_provider_check | Mismatch between collection provider and query provider raises ValueError |

**Total: 17 tests pass (6 pre-existing + 6 Task 1 + 5 Task 2)**

---

## Deviations from Plan

### No unplanned deviations

The implementation followed the plan exactly. Both Task 1 and Task 2 were implemented in a single pass to `vector_store.py` since the MMR method was architecturally straightforward to add alongside the Task 1 changes. All tests were written first (RED) before confirming GREEN.

---

## Threat Mitigations Applied

| Threat ID | Mitigation Applied |
|-----------|-------------------|
| T-3c-04 | `get_or_create_collection` sets metadata only on first creation. `_check_provider_match` validates on every query. |
| T-3c-05 | `n_results=min(fetch_k, count)` prevents unbounded memory usage. |
| T-3c-06 | Per-project `threading.Lock` via `_get_project_lock` wraps every `upsert` call. |

---

## Known Stubs

None — all methods are fully implemented and wired.

---

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced. All changes are internal to VectorStoreService.

---

## Self-Check: PASSED

- `backend/app/services/vector_store.py` — EXISTS (231 lines)
- `backend/tests/test_vector_store.py` — EXISTS (433 lines)
- Commit `16d60da` — EXISTS (feat(03C-02): add collection metadata...)
- Commit `2e86260` — EXISTS (feat(03C-02): add similarity_search_mmr...)
- 17 tests pass, 73 total suite tests pass
