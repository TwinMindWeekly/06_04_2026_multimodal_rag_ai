---
phase: 03B-ingestion-pipeline
plan: "02"
subsystem: backend/image-processing
tags: [gemini-vision, tenacity, retry, image-summarization, tdd]
dependency_graph:
  requires: []
  provides: [ImageProcessorService]
  affects: [backend/app/services/document_parser.py]
tech_stack:
  added: [google-generativeai>=0.8.0]
  patterns: [tenacity-retry, placeholder-on-failure, lazy-api-key-validation]
key_files:
  created:
    - backend/app/services/image_processor.py
    - backend/tests/test_image_processor.py
  modified:
    - backend/requirements.txt
decisions:
  - "google-generativeai 0.8.x used despite FutureWarning (deprecated package): plan explicitly specifies genai.GenerativeModel interface; migration to google.genai deferred"
  - "FutureWarning suppressed at import time with warnings.catch_warnings to keep test output clean"
  - "google-generativeai added to requirements.txt (Rule 3: blocking dependency)"
metrics:
  duration_minutes: 35
  completed_date: "2026-04-09"
  tasks_total: 1
  tasks_completed: 1
  files_created: 2
  files_modified: 1
requirements: [PARSE-03, PARSE-04]
---

# Phase 03B Plan 02: ImageProcessorService Summary

**One-liner:** Gemini Vision image summarization with tenacity 3-attempt exponential backoff and safe placeholder-on-failure fallback.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create ImageProcessorService with Gemini Vision + tenacity retry | a257004 | backend/app/services/image_processor.py, backend/tests/test_image_processor.py, backend/requirements.txt |

---

## What Was Built

`ImageProcessorService` in `backend/app/services/image_processor.py`:

- **`summarize_image(image_path, filename) -> str`** — public interface consumed by document_parser.py (Plan 03). Validates `GOOGLE_API_KEY` at call time (not at import/startup). Missing key returns `"[Image: unable to process - {filename}]"` and logs a warning without ever logging the key value.
- **`_call_gemini(image_path) -> str`** — decorated with `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8), reraise=True)`. Reads image bytes inline and sends to `genai.GenerativeModel("gemini-1.5-pro-latest")`.
- **`_summarize_with_retry(image_path, filename) -> str`** — wraps `_call_gemini`, catches final exception after all retries, returns placeholder.

**Test coverage — 5 tests all passing:**

| Test | Validates |
|------|-----------|
| `test_summarize_success` | Happy path: Gemini returns text, service returns it |
| `test_summarize_failure_returns_placeholder` | All 3 retries fail → placeholder returned |
| `test_missing_api_key_returns_placeholder` | No env var → placeholder, no exception, Gemini not called |
| `test_api_key_not_logged` | Secret value never appears in any log record |
| `test_retry_count` | Fails twice, succeeds third time; generate_content called exactly 3 times |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added google-generativeai to requirements.txt**
- **Found during:** Task 1 setup
- **Issue:** `google-generativeai` was not in requirements.txt; `python -c "import google.generativeai"` failed with `ModuleNotFoundError`.
- **Fix:** Installed `google-generativeai` via pip; added `google-generativeai>=0.8.0` to `backend/requirements.txt`.
- **Files modified:** `backend/requirements.txt`
- **Commit:** a257004 (included in task commit)

**2. [Rule 2 - Missing functionality] FutureWarning suppression**
- **Found during:** Task 1 implementation
- **Issue:** `google-generativeai 0.8.x` emits `FutureWarning` on import noting the package is deprecated in favour of `google.genai`. This would pollute test output and log streams.
- **Fix:** Wrapped `import google.generativeai as genai` in `warnings.catch_warnings()` block to suppress `FutureWarning` at module level. Applied same suppression in test patches.
- **Files modified:** `backend/app/services/image_processor.py`
- **Commit:** a257004

---

## Known Stubs

None — `ImageProcessorService.summarize_image()` is fully wired. Placeholder text is an intentional graceful-failure return value, not a stub.

---

## Threat Flags

None — no new trust boundaries beyond those already in the plan's threat model (T-3b-03, T-3b-04, T-3b-05 all addressed).

---

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `backend/app/services/image_processor.py` | FOUND |
| `backend/tests/test_image_processor.py` | FOUND |
| `.planning/phases/03B-ingestion-pipeline/03B-02-SUMMARY.md` | FOUND |
| Commit `a257004` | FOUND |
| `python -m pytest tests/test_image_processor.py` | 5 passed |
