---
phase: 03A-infrastructure-fixes
plan: 02
subsystem: infra
tags: [lazy-loading, chromadb, joinedload, upload-validation, i18n]

# Dependency graph
requires: ["03A-01"]
provides:
  - "Lazy-loading get_default_embeddings() function (model NOT loaded at import)"
  - "Absolute ChromaDB path via CHROMADB_PATH env var with __file__-relative default"
  - "Eager-loaded folder relationship via joinedload in background tasks"
  - "Extension whitelist + size limit validation before disk write"
  - "i18n keys for invalid_file_type and file_too_large in EN/VI"
affects: [03B, 03C]

# Tech tracking
tech-stack:
  added: []
  patterns: [lazy-singleton, joinedload-eager-loading, read-before-write-validation, content-type-defense-in-depth]

key-files:
  created:
    - backend/tests/test_embeddings.py
    - backend/tests/test_vector_store.py
    - backend/tests/test_document_parser.py
    - backend/tests/test_documents_router.py
  modified:
    - backend/app/services/embeddings.py
    - backend/app/services/vector_store.py
    - backend/app/services/document_parser.py
    - backend/app/routers/documents.py
    - backend/locales/en.json
    - backend/locales/vi.json
    - backend/app/schemas/domain.py
    - backend/tests/conftest.py

key-decisions:
  - "Lazy singleton via global guard variable (_default_embeddings = None) rather than functools.lru_cache for explicit mockability in tests"
  - "joinedload(Document.folder) chosen over separate scalar query for fewer DB round-trips"
  - "Read-before-write pattern for size validation: read up to 100MB+1 into memory, reject if oversized, then write to disk"
  - "Content-Type validation as secondary defense-in-depth (clients can spoof headers; extension check is primary gate)"

patterns-established:
  - "Lazy singleton: _var = None; def get_var(): global _var; if _var is None: _var = ...; return _var"
  - "Upload validation: extension whitelist + content-type + size check BEFORE any disk I/O"
  - "joinedload pattern: .options(joinedload(Model.relationship)) to prevent DetachedInstanceError in background tasks"

requirements-completed: [INFRA-01, INFRA-04, INFRA-05, INFRA-06]

# Metrics
duration: 8min
completed: 2026-04-09
---

# Phase 03A Plan 02: Lazy-load Embeddings, ChromaDB Path, Eager-load Fix, Upload Validation Summary

**Lazy-loading embedding singleton, absolute ChromaDB path via __file__ with env var override, joinedload for background task folder access, and 3-stage upload validation (extension/content-type/size) before disk write**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-09T08:07:52Z
- **Completed:** 2026-04-09T08:16:10Z
- **Tasks:** 3
- **Files modified:** 12

## Accomplishments
- embeddings.py refactored from eager module-level singleton to lazy get_default_embeddings() -- model NOT loaded at import time
- vector_store.py updated with __file__-relative absolute ChromaDB path, CHROMADB_PATH env var override, and call sites changed to get_default_embeddings()
- document_parser.py fixed with joinedload(Document.folder) to prevent DetachedInstanceError; duplicate proj_id access consolidated
- documents.py router hardened with ALLOWED_EXTENSIONS whitelist, MAX_FILE_SIZE_BYTES (100MB), Content-Type secondary check -- all validated BEFORE disk write
- i18n keys added for invalid_file_type and file_too_large in both en.json and vi.json (with proper Vietnamese diacritics)
- 17 new tests across 4 test files, 29 total tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Lazy-load embedding model and update ChromaDB path + call site** - `498f41c` (feat)
2. **Task 2: Fix background task eager-loading of folder relationship** - `5dc1b8a` (feat)
3. **Task 3: File upload validation with extension whitelist and size limit** - `37cd1b7` (feat)

## Files Created/Modified
- `backend/app/services/embeddings.py` - Lazy singleton pattern: _default_embeddings = None + get_default_embeddings()
- `backend/app/services/vector_store.py` - Absolute ChromaDB path via Path(__file__).resolve(), CHROMADB_PATH env var, get_default_embeddings() call sites
- `backend/app/services/document_parser.py` - joinedload(Document.folder), explicit None return, consolidated proj_id access
- `backend/app/routers/documents.py` - ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES, ALLOWED_CONTENT_TYPES, 3-stage validation before disk write, logging.warning in delete
- `backend/locales/en.json` - Added invalid_file_type and file_too_large error keys
- `backend/locales/vi.json` - Added invalid_file_type and file_too_large error keys with Vietnamese diacritics
- `backend/app/schemas/domain.py` - Fixed DocumentBase.folder_id to Optional[int] (was int, broke None folder uploads)
- `backend/tests/conftest.py` - Added StaticPool for proper in-memory SQLite test isolation
- `backend/tests/test_embeddings.py` - 4 tests: no-model-at-import, no-eager-assignment, returns-model, singleton
- `backend/tests/test_vector_store.py` - 3 tests: path-is-absolute, path-ends-with-backend-data, imports-get_default_embeddings
- `backend/tests/test_document_parser.py` - 3 tests: uses-joinedload, joinedload-imported, handles-missing-document
- `backend/tests/test_documents_router.py` - 7 tests: exe-400, txt-400, pdf-accepted, case-insensitive, oversized-413, extensions-constant, size-constant

## Decisions Made
- Lazy singleton via global guard variable rather than functools.lru_cache -- simpler to mock in tests
- joinedload chosen over separate scalar query -- fewer DB round-trips, cleaner code
- Read-before-write for size validation -- acceptable for 100MB limit on local single-user tool
- Content-Type as secondary check only -- clients can spoof headers, extension whitelist is the primary gate

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed DocumentBase.folder_id schema type**
- **Found during:** Task 3 (test_valid_extension_pdf_accepted)
- **Issue:** DocumentBase.folder_id was typed as `int` (required) but the upload endpoint and domain model allow None when no folder is specified
- **Fix:** Changed to `Optional[int] = None` in backend/app/schemas/domain.py
- **Files modified:** backend/app/schemas/domain.py
- **Committed in:** 37cd1b7 (Task 3 commit)

**2. [Rule 3 - Blocking] Added StaticPool to conftest.py test engine**
- **Found during:** Task 3 (test_valid_extension_pdf_accepted)
- **Issue:** In-memory SQLite with `sqlite://` creates a new database per connection; tables created by `create_all()` were invisible to test sessions
- **Fix:** Added `poolclass=StaticPool` to test engine so all connections share the same in-memory database
- **Files modified:** backend/tests/conftest.py
- **Committed in:** 37cd1b7 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 bug fix, 1 blocking issue)
**Impact on plan:** Essential fixes for test correctness. No scope creep.

## Threat Model Verification

| Threat ID | Disposition | Status |
|-----------|-------------|--------|
| T-3a-01 (Tampering: file upload) | mitigate | DONE - ALLOWED_EXTENSIONS whitelist + Content-Type check + case-insensitive .lower() |
| T-3a-02 (DoS: oversized upload) | mitigate | DONE - MAX_FILE_SIZE_BYTES = 100MB via file.read(limit+1), returns 413 without disk write |
| T-3a-05 (Tampering: filename) | accept | VERIFIED - uuid4() filename generation already in place |
| T-3a-06 (EoP: lazy load) | accept | VERIFIED - model name hardcoded "all-MiniLM-L6-v2", no user input reaches lazy load |

## Issues Encountered
None beyond the auto-fixed schema and conftest issues.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 8 INFRA requirements complete (INFRA-01 through INFRA-08 across Plans 01 and 02)
- 29 tests passing across 7 test files
- Infrastructure stable for Phase 3b (ingestion pipeline)
- System deps (poppler, tesseract) still need manual installation before Phase 3b

## Self-Check: PASSED

All 12 files verified present. All 3 task commits verified in git log (498f41c, 5dc1b8a, 37cd1b7). 29/29 tests passing.

---
*Phase: 03A-infrastructure-fixes*
*Completed: 2026-04-09*
