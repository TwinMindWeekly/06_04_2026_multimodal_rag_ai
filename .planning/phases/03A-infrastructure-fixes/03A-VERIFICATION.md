---
phase: 03A-infrastructure-fixes
verified: 2026-04-09T09:30:00Z
status: passed
score: 9/9 must-haves verified
gaps: []
human_verification: []
---

# Phase 03A: Infrastructure Fixes Verification Report

**Phase Goal:** Fix known blockers so the RAG pipeline has a stable foundation.
**Verified:** 2026-04-09T09:30:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Server starts with absolute DB/ChromaDB paths logged to console | VERIFIED | database.py:25 `logger.info("SQLite database path: %s", DATABASE_PATH)` with Path(__file__).resolve(); vector_store.py:21 `logger.info("ChromaDB path: %s", CHROMADB_DIR)` with Path(__file__).resolve(); tests test_sqlite_path_is_absolute and test_chromadb_path_is_absolute pass |
| 2 | WAL mode confirmed via PRAGMA journal_mode query | VERIFIED | database.py:34-39 `@event.listens_for(engine, "connect")` fires `PRAGMA journal_mode=WAL` with isinstance guard; test_wal_mode_enabled passes asserting scalar() == "wal" |
| 3 | Embedding model NOT loaded until first embedding request | VERIFIED | embeddings.py:30 `_default_embeddings = None` (no eager init); embeddings.py:33-38 lazy `get_default_embeddings()` function; no `default_embeddings = EmbeddingFactory...` line; tests test_no_model_at_import, test_module_has_no_eager_default_embeddings pass |
| 4 | Upload of .exe returns 400; oversized file returns 413 (without disk write) | VERIFIED | documents.py:23 ALLOWED_EXTENSIONS whitelist; documents.py:26 MAX_FILE_SIZE_BYTES = 100MB; validation at lines 47-68 occurs BEFORE disk write at line 83; tests test_invalid_extension_exe_returns_400 and test_oversized_file_returns_413 pass |
| 5 | pip install -r requirements.txt works (no encoding errors) | VERIFIED | requirements.txt is valid UTF-8 (127 lines, readable ASCII); test deps pytest/pytest-asyncio/httpx appended at lines 124-126; tests test_requirements_utf8, test_requirements_no_null_bytes, test_requirements_no_bom all pass |
| 6 | Missing poppler/tesseract produces clear warning at startup | VERIFIED | main.py:16-32 `probe_system_dependencies()` with shutil.which("pdfinfo") and shutil.which("tesseract"); main.py:27 `logger.warning(...)` (not error, not raise); main.py:36 called before app = FastAPI; tests test_missing_pdfinfo_logs_warning, test_missing_tesseract_logs_warning, test_probe_does_not_raise all pass |
| 7 | Background task does not raise DetachedInstanceError | VERIFIED | document_parser.py:3 imports joinedload from sqlalchemy.orm; document_parser.py:54 `.options(joinedload(Document.folder))`; document_parser.py:74 safe folder.project_id access after eager load; tests test_background_task_uses_joinedload, test_joinedload_imported pass |
| 8 | Upload of valid .pdf file proceeds normally | VERIFIED | documents.py:48 case-insensitive `.lower()` extension check; tests test_valid_extension_pdf_accepted and test_valid_extension_case_insensitive pass (status != 400 and != 413) |
| 9 | ChromaDB path configurable via CHROMADB_PATH env var | VERIFIED | vector_store.py:19 `CHROMADB_DIR = os.getenv("CHROMADB_PATH", _DEFAULT_CHROMADB_PATH)` with __file__-relative default; tests test_chromadb_path_is_absolute, test_chromadb_path_default_ends_with_backend_data pass |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/requirements.txt` | UTF-8 encoded dependency list with test deps | VERIFIED | 127 lines, valid UTF-8, pytest/pytest-asyncio/httpx at lines 124-126 |
| `backend/app/core/database.py` | Absolute SQLite path + WAL mode via event listener | VERIFIED | 53 lines; contains Path(__file__).resolve(), os.getenv("DATABASE_PATH"), PRAGMA journal_mode=WAL, isinstance guard |
| `backend/app/main.py` | Startup probe + load_dotenv | VERIFIED | 61 lines; load_dotenv() at lines 1-2 (before app.core imports), probe_system_dependencies() at line 36, shutil.which checks |
| `backend/tests/conftest.py` | Shared test fixtures | VERIFIED | 62 lines; test_engine with StaticPool, test_db, client with dependency override, mock_embeddings |
| `backend/tests/__init__.py` | Package marker | VERIFIED | Exists (empty file) |
| `backend/tests/test_requirements_encoding.py` | 3 encoding tests | VERIFIED | 26 lines; test_requirements_utf8, test_requirements_no_null_bytes, test_requirements_no_bom |
| `backend/tests/test_database.py` | 5 database tests | VERIFIED | 45 lines; test_sqlite_path_is_absolute, test_sqlite_path_default_ends_with_backend_data, test_data_directory_created, test_wal_mode_enabled, test_database_path_env_override |
| `backend/tests/test_startup.py` | 4 startup tests | VERIFIED | 43 lines; test_missing_pdfinfo_logs_warning, test_missing_tesseract_logs_warning, test_probe_does_not_raise, test_app_still_starts |
| `backend/app/services/embeddings.py` | Lazy-loading get_default_embeddings() | VERIFIED | 39 lines; _default_embeddings = None, def get_default_embeddings() lazy singleton; exports EmbeddingFactory and get_default_embeddings |
| `backend/app/services/vector_store.py` | Absolute ChromaDB path + updated call site | VERIFIED | 81 lines; Path(__file__).resolve(), os.getenv("CHROMADB_PATH"), get_default_embeddings().embed_documents/embed_query |
| `backend/app/services/document_parser.py` | Eager-loaded folder via joinedload | VERIFIED | 93 lines; joinedload(Document.folder) in query options |
| `backend/app/routers/documents.py` | Extension whitelist + size limit before disk write | VERIFIED | 131 lines; ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES, 3-stage validation before buffer.write |
| `backend/locales/en.json` | English error messages for validation | VERIFIED | Contains invalid_file_type and file_too_large keys |
| `backend/locales/vi.json` | Vietnamese error messages for validation | VERIFIED | Contains invalid_file_type and file_too_large keys with proper diacritics |
| `backend/tests/test_embeddings.py` | 4 lazy-load tests | VERIFIED | 72 lines; test_no_model_at_import, test_module_has_no_eager_default_embeddings, test_get_default_embeddings_returns_object_with_methods, test_get_default_embeddings_is_singleton |
| `backend/tests/test_vector_store.py` | 3 vector store tests | VERIFIED | 30 lines; test_chromadb_path_is_absolute, test_chromadb_path_default_ends_with_backend_data, test_vector_store_imports_get_default_embeddings |
| `backend/tests/test_document_parser.py` | 3 parser tests | VERIFIED | 27 lines; test_background_task_uses_joinedload, test_joinedload_imported, test_process_document_handles_missing_document |
| `backend/tests/test_documents_router.py` | 7 upload validation tests | VERIFIED | 71 lines; exe/txt returns 400, pdf/PDF accepted, oversized returns 413, constants verified |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| database.py | SQLAlchemy engine | `@event.listens_for(engine, "connect")` | WIRED | Line 34: event listener fires PRAGMA on connect with isinstance guard |
| main.py | shutil.which | `probe_system_dependencies()` at startup | WIRED | Lines 21, 23: shutil.which("pdfinfo") and shutil.which("tesseract"); called at module level line 36 |
| main.py | dotenv | `load_dotenv()` before app imports | WIRED | Lines 1-2: load_dotenv() before line 10 `from app.core.database import engine, Base` |
| vector_store.py | embeddings.py | `from app.services.embeddings import get_default_embeddings` | WIRED | Line 7: import; Lines 42, 61: get_default_embeddings().embed_documents/embed_query |
| document_parser.py | domain.py | `joinedload(Document.folder)` | WIRED | Line 54: .options(joinedload(Document.folder)) in query; Line 74: safe folder.project_id access |
| documents.py | locales/en.json | `t("errors.invalid_file_type")` and `t("errors.file_too_large")` | WIRED | Lines 52, 59: t("errors.invalid_file_type"); Line 67: t("errors.file_too_large"); Keys present in both en.json and vi.json |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 29 tests pass | `cd backend && ./venv/Scripts/python.exe -m pytest tests/ -v --tb=short` | 29 passed, 5 warnings in 0.46s | PASS |
| Commits exist in git | `git log --oneline -10` | All 6 commits verified: 7e9a59c, 98fbbc8, 5e61620, 498f41c, 5dc1b8a, 37cd1b7 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INFRA-01 | 03A-02 | ChromaDB persistence path must be absolute | SATISFIED | vector_store.py: Path(__file__).resolve() + os.getenv("CHROMADB_PATH"); test_chromadb_path_is_absolute passes |
| INFRA-02 | 03A-01 | SQLite database path configurable via env var with absolute default | SATISFIED | database.py: Path(__file__).resolve() + os.getenv("DATABASE_PATH"); test_sqlite_path_is_absolute passes |
| INFRA-03 | 03A-01 | SQLite WAL mode enabled at connection init | SATISFIED | database.py: @event.listens_for(engine, "connect") + PRAGMA journal_mode=WAL; test_wal_mode_enabled passes |
| INFRA-04 | 03A-02 | Embedding model must lazy-load on first use | SATISFIED | embeddings.py: _default_embeddings = None + get_default_embeddings() lazy singleton; test_no_model_at_import passes |
| INFRA-05 | 03A-02 | Background tasks must eager-load relationships | SATISFIED | document_parser.py: joinedload(Document.folder) in query; test_background_task_uses_joinedload passes |
| INFRA-06 | 03A-02 | File upload must validate extension whitelist and size limit | SATISFIED | documents.py: ALLOWED_EXTENSIONS + MAX_FILE_SIZE_BYTES + 3-stage validation before disk write; 7 router tests pass |
| INFRA-07 | 03A-01 | requirements.txt must be UTF-8 encoded | SATISFIED | File is valid UTF-8 with no null bytes and no BOM; 3 encoding tests pass |
| INFRA-08 | 03A-01 | System dependency probe at startup | SATISFIED | main.py: probe_system_dependencies() with shutil.which + logger.warning; 4 startup tests pass |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| document_parser.py | 22-23 | `# Stub logic -- real parsing implemented in Phase 3b` with `[MOCK]` text chunks | INFO | Expected: real parsing is Phase 3b scope; Phase 3a only fixes the joinedload/session issue. Not a gap for this phase. |
| vector_store.py | 58 | `return []` in except handler | INFO | Correct error handling: returns empty list when ChromaDB collection does not exist. Not a stub. |

### Human Verification Required

None. All phase 03A changes are backend infrastructure fixes verifiable through automated tests, code inspection, and grep-based pattern matching. No UI changes, no visual behavior, no external service integration requiring manual testing.

### Gaps Summary

No gaps found. All 9 observable truths verified. All 18 artifacts exist, are substantive, and are properly wired. All 6 key links confirmed. All 8 INFRA requirements satisfied. All 29 tests pass. All 6 commits verified in git history. No orphaned requirements.

---

_Verified: 2026-04-09T09:30:00Z_
_Verifier: Claude (gsd-verifier)_
