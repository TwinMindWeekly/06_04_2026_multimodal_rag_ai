---
phase: 3a
slug: infrastructure-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 3a — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| W0-01 | 01 | 0 | — | — | N/A | setup | `pip install pytest pytest-asyncio httpx` | N/A | ⬜ pending |
| W0-02 | 01 | 0 | — | — | N/A | setup | `test -f backend/tests/conftest.py` | ❌ W0 | ⬜ pending |
| 01-01 | 01 | 1 | INFRA-07 | — | N/A | smoke | `pytest tests/test_requirements_encoding.py::test_requirements_utf8 -x` | ❌ W0 | ⬜ pending |
| 01-02 | 01 | 1 | INFRA-02 | — | N/A | unit | `pytest tests/test_database.py::test_sqlite_path_is_absolute -x` | ❌ W0 | ⬜ pending |
| 01-03 | 01 | 1 | INFRA-01 | — | N/A | unit | `pytest tests/test_vector_store.py::test_chromadb_path_is_absolute -x` | ❌ W0 | ⬜ pending |
| 01-04 | 01 | 1 | INFRA-03 | — | N/A | unit | `pytest tests/test_database.py::test_wal_mode_enabled -x` | ❌ W0 | ⬜ pending |
| 01-05 | 01 | 1 | INFRA-04 | — | N/A | unit | `pytest tests/test_embeddings.py::test_no_model_at_import -x` | ❌ W0 | ⬜ pending |
| 01-06 | 01 | 1 | INFRA-05 | — | N/A | integration | `pytest tests/test_document_parser.py::test_background_task_no_detached_error -x` | ❌ W0 | ⬜ pending |
| 01-07 | 01 | 1 | INFRA-06 | T-3a-01 | Extension whitelist blocks .exe; 100MB limit blocks oversized | unit | `pytest tests/test_documents_router.py -x` | ❌ W0 | ⬜ pending |
| 01-08 | 01 | 1 | INFRA-08 | — | N/A | unit | `pytest tests/test_startup.py::test_missing_system_deps_warns -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/__init__.py` — package marker
- [ ] `backend/tests/conftest.py` — shared fixtures (test DB, mock embeddings)
- [ ] `backend/tests/test_database.py` — covers INFRA-02, INFRA-03
- [ ] `backend/tests/test_vector_store.py` — covers INFRA-01
- [ ] `backend/tests/test_embeddings.py` — covers INFRA-04
- [ ] `backend/tests/test_document_parser.py` — covers INFRA-05
- [ ] `backend/tests/test_documents_router.py` — covers INFRA-06
- [ ] `backend/tests/test_requirements_encoding.py` — covers INFRA-07
- [ ] `backend/tests/test_startup.py` — covers INFRA-08
- [ ] `pip install pytest pytest-asyncio httpx` — test dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Server startup log shows absolute paths | INFRA-01, INFRA-02 | Log output verification | Start server, check console for absolute path log lines |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
