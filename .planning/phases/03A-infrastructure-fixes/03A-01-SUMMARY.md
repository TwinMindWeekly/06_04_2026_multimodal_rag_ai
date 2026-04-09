---
phase: 03A-infrastructure-fixes
plan: 01
subsystem: infra
tags: [sqlite, wal-mode, pathlib, dotenv, pytest, shutil]

# Dependency graph
requires: []
provides:
  - "UTF-8 encoded requirements.txt with test dependencies"
  - "Absolute SQLite path via DATABASE_PATH env var with __file__-relative default"
  - "WAL mode on every SQLite connection via engine event listener"
  - "Startup probe for pdfinfo/tesseract with WARNING log"
  - "load_dotenv() before app.core imports"
  - "Shared test fixtures (test_engine, client, mock_embeddings)"
affects: [03A-02, 03B, 03C]

# Tech tracking
tech-stack:
  added: [pytest, pytest-asyncio, httpx]
  patterns: [__file__-relative-paths, engine-connect-event-listener, startup-probe, test-scaffold]

key-files:
  created:
    - backend/tests/__init__.py
    - backend/tests/conftest.py
    - backend/tests/test_requirements_encoding.py
    - backend/tests/test_database.py
    - backend/tests/test_startup.py
  modified:
    - backend/requirements.txt
    - backend/app/core/database.py
    - backend/app/main.py

key-decisions:
  - "Used sqlite:// (pure in-memory) instead of sqlite:///file::memory:?cache=shared for Windows compatibility in test fixtures"
  - "WAL mode listener scoped to engine instance (not Engine class) to avoid cross-engine interference"
  - "load_dotenv() placed at very top of main.py before any app.core imports to ensure env vars available during module initialization"

patterns-established:
  - "Path pattern: Path(__file__).resolve().parent.parent.parent for __file__-relative absolute paths"
  - "WAL pattern: @event.listens_for(engine, 'connect') with isinstance guard for sqlite3.Connection"
  - "Probe pattern: shutil.which() at startup with WARNING log for missing system deps"
  - "Test pattern: conftest.py with test_engine, test_db, client, mock_embeddings fixtures"

requirements-completed: [INFRA-07, INFRA-02, INFRA-03, INFRA-08]

# Metrics
duration: 13min
completed: 2026-04-09
---

# Phase 03A Plan 01: Infrastructure Fixes Summary

**UTF-8 requirements.txt, absolute SQLite path with WAL mode via engine event listener, and startup probe for pdfinfo/tesseract with load_dotenv**

## Performance

- **Duration:** 13 min
- **Started:** 2026-04-09T07:42:44Z
- **Completed:** 2026-04-09T07:55:46Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- requirements.txt confirmed UTF-8 encoded (no null bytes, no BOM) with test dependencies added
- database.py rewritten with absolute SQLite path via `Path(__file__).resolve()`, DATABASE_PATH env var override, auto-created data directory, and WAL mode via engine-level connect event listener
- main.py enhanced with load_dotenv() at top (before app.core imports) and probe_system_dependencies() that logs WARNING for missing pdfinfo/tesseract without blocking startup
- Test scaffold established with conftest.py shared fixtures and 12 passing tests across 3 test files

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix requirements.txt encoding and create test scaffold** - `7e9a59c` (feat)
2. **Task 2: Absolute SQLite path with env var override and WAL mode** - `98fbbc8` (feat)
3. **Task 3: System dependency startup probe and load_dotenv** - `5e61620` (feat)

## Files Created/Modified
- `backend/requirements.txt` - UTF-8 encoded with pytest/pytest-asyncio/httpx test deps added
- `backend/app/core/database.py` - Absolute path via __file__, DATABASE_PATH env var, WAL mode event listener
- `backend/app/main.py` - load_dotenv() at top, probe_system_dependencies() with WARNING log
- `backend/tests/__init__.py` - Package marker (empty)
- `backend/tests/conftest.py` - Shared fixtures: test_engine, test_db, client, mock_embeddings
- `backend/tests/test_requirements_encoding.py` - 3 tests for UTF-8, no null bytes, no BOM
- `backend/tests/test_database.py` - 5 tests for absolute path, WAL mode, env override, data dir
- `backend/tests/test_startup.py` - 4 tests for probe logging, no-raise, app startup

## Decisions Made
- Used `sqlite://` (pure in-memory) instead of `sqlite:///file::memory:?cache=shared` for Windows compatibility -- colons in the URI path are invalid on Windows filesystems
- WAL mode listener scoped to specific engine instance (`@event.listens_for(engine, "connect")`) rather than Engine class to prevent cross-engine interference in tests
- load_dotenv() placed at very top of main.py as bare statements before any `from app.core` imports

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed conftest.py test database URL for Windows**
- **Found during:** Task 3 (test_app_still_starts)
- **Issue:** `sqlite:///file::memory:?cache=shared` URL caused `OperationalError: unable to open database file` on Windows because colons are invalid in Windows file paths
- **Fix:** Changed to `sqlite://` (pure in-memory SQLite, no file path)
- **Files modified:** backend/tests/conftest.py
- **Verification:** All 12 tests pass including test_app_still_starts
- **Committed in:** 5e61620 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Essential fix for Windows platform compatibility. No scope creep.

## Issues Encountered
None beyond the auto-fixed conftest.py URL issue.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Test scaffold with shared fixtures ready for Plan 02 (lazy embeddings, eager load, upload validation)
- database.py exports preserved: engine, Base, SessionLocal, get_db, DATABASE_PATH, SQLALCHEMY_DATABASE_URL
- WAL mode active on all connections -- concurrent background tasks safe for Plan 02
- load_dotenv() ensures .env vars available for DATABASE_PATH and CHROMADB_PATH overrides

## Self-Check: PASSED

All 8 files verified present. All 3 task commits verified in git log (7e9a59c, 98fbbc8, 5e61620). 12/12 tests passing.

---
*Phase: 03A-infrastructure-fixes*
*Completed: 2026-04-09*
