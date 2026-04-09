---
phase: 3b
slug: ingestion-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 3b — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ (in requirements.txt) |
| **Config file** | None — Wave 0 creates `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

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
| 3b-01-01 | 01 | 1 | PARSE-01 | — | N/A | unit | `pytest tests/test_document_parser.py::test_parse_pdf -x` | ❌ W0 | ⬜ pending |
| 3b-01-02 | 01 | 1 | PARSE-02 | T-3b-05 | Verify image_path within temp_dir | unit | `pytest tests/test_document_parser.py::test_image_extraction -x` | ❌ W0 | ⬜ pending |
| 3b-01-03 | 01 | 1 | PARSE-05 | — | N/A | unit | `pytest tests/test_document_parser.py::test_metadata_preserved -x` | ❌ W0 | ⬜ pending |
| 3b-02-01 | 02 | 1 | PARSE-03 | T-3b-03 | Never log API key value | unit (mock) | `pytest tests/test_image_processor.py::test_summarize_success -x` | ❌ W0 | ⬜ pending |
| 3b-02-02 | 02 | 1 | PARSE-04 | — | N/A | unit (mock) | `pytest tests/test_image_processor.py::test_summarize_failure -x` | ❌ W0 | ⬜ pending |
| 3b-03-01 | 03 | 1 | CHUNK-01 | — | N/A | unit | `pytest tests/test_chunking.py::test_chunk_size -x` | ❌ W0 | ⬜ pending |
| 3b-03-02 | 03 | 1 | CHUNK-02 | — | N/A | unit | `pytest tests/test_chunking.py::test_chunk_metadata_schema -x` | ❌ W0 | ⬜ pending |
| 3b-03-03 | 03 | 1 | CHUNK-03 | — | N/A | unit | `pytest tests/test_chunking.py::test_image_summary_interleaved -x` | ❌ W0 | ⬜ pending |
| 3b-04-01 | 04 | 2 | D-13 | — | N/A | integration | `pytest tests/test_pipeline.py::test_status_transitions -x` | ❌ W0 | ⬜ pending |
| 3b-04-02 | 04 | 2 | D-15 | — | N/A | integration | `pytest tests/test_pipeline.py::test_delete_before_insert -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/__init__.py` — empty package init
- [ ] `backend/tests/conftest.py` — shared fixtures (sample PDF bytes, mock DB session, mock genai)
- [ ] `backend/tests/test_document_parser.py` — covers PARSE-01, PARSE-02, PARSE-05
- [ ] `backend/tests/test_image_processor.py` — covers PARSE-03, PARSE-04
- [ ] `backend/tests/test_chunking.py` — covers CHUNK-01, CHUNK-02, CHUNK-03
- [ ] `backend/tests/test_pipeline.py` — covers D-13, D-15 (integration)
- [ ] `backend/pytest.ini` — minimal config: `testpaths = tests`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Upload 10-page PDF → chunks in ChromaDB with page_number | Success criteria 1 | Requires real PDF + running ChromaDB | Upload via API, query ChromaDB directly |
| PPTX with images → image summaries embedded | Success criteria 2 | Requires real PPTX + Gemini API key | Upload PPTX, verify image_summary chunks |
| poppler/tesseract missing → graceful degradation | INFRA-08 (Phase 3a) | System dependency state | Remove from PATH, verify warning logged |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
