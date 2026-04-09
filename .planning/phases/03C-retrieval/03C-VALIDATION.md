---
phase: 03C
slug: retrieval
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 03C — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | none |
| **Quick run command** | `cd backend && .venv/Scripts/python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && .venv/Scripts/python -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| TBD | TBD | TBD | EMBED-01 | unit | `pytest tests/test_embeddings.py -x` | pending |
| TBD | TBD | TBD | EMBED-02 | unit | `pytest tests/test_embeddings.py -x` | pending |
| TBD | TBD | TBD | EMBED-03 | unit | `pytest tests/test_vector_store.py -x` | pending |
| TBD | TBD | TBD | EMBED-04 | unit | `pytest tests/test_vector_store.py -x` | pending |
| TBD | TBD | TBD | EMBED-05 | integration | `pytest tests/test_reindex.py -x` | pending |
| TBD | TBD | TBD | EMBED-06 | unit | `pytest tests/test_vector_store.py -x` | pending |
| TBD | TBD | TBD | SEARCH-01 | integration | `pytest tests/test_search.py -x` | pending |
| TBD | TBD | TBD | SEARCH-02 | unit | `pytest tests/test_search.py -x` | pending |
| TBD | TBD | TBD | SEARCH-03 | unit | `pytest tests/test_search.py -x` | pending |
