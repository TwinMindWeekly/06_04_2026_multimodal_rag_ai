# Phase 3a: Infrastructure Fixes - Research

**Researched:** 2026-04-09
**Domain:** FastAPI / SQLAlchemy / ChromaDB infrastructure stabilization
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Path Configuration**
- D-01: ChromaDB and SQLite paths must use env vars (`CHROMADB_PATH`, `DATABASE_PATH`) with `__file__`-relative defaults pointing to `backend/data/` directory.
- D-02: Default data directory is `backend/data/` — keeps DB files together, out of the source tree. Directory auto-created at startup if missing.
- D-03: Env var names: `CHROMADB_PATH` for ChromaDB persistence, `DATABASE_PATH` for SQLite database.

**Upload Validation**
- D-04: Validate file extension and Content-Type BEFORE saving to disk. If invalid, return 400 immediately without writing to disk.
- D-05: File size limit is 100MB as specified in REQUIREMENTS.md. Return 413 for oversized files.
- D-06: Extension whitelist: `.pdf`, `.docx`, `.pptx`, `.xlsx` — case-insensitive check.

**Startup Probes**
- D-07: Missing poppler/tesseract produces a clear WARNING log at startup but does NOT block server startup. Server runs normally — parsing will fail later when a PDF is uploaded, but the rest of the app works fine.

### Claude's Discretion
- D-08: INFRA-03 (SQLite WAL mode) — Enable WAL via `PRAGMA journal_mode=WAL` event listener on engine connect. Standard approach.
- D-09: INFRA-04 (Lazy embedding loading) — Replace module-level `default_embeddings` singleton with a lazy-loading pattern (e.g., `_model = None; def get_default_embeddings()` or similar). Model loaded on first call, not at import time.
- D-10: INFRA-05 (Background task sessions) — `process_and_update_document` already receives scalar `document_id` and creates its own `SessionLocal()`. Fix: eager-load the `folder` relationship or query `project_id` separately to avoid `DetachedInstanceError` on `db_document.folder.project_id`.
- D-11: INFRA-07 (requirements.txt encoding) — Convert from UTF-16 LE to UTF-8. One-time fix.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 3a fixes 8 concrete infrastructure blockers in 6 existing files. All fixes are self-contained single-file changes except the `backend/data/` directory creation which touches both `database.py` and `vector_store.py`. None of the fixes require new dependencies; every technique (SQLAlchemy event listeners, `pathlib.Path`, `shutil.which`, `joinedload`) is in the already-installed stack.

The highest-risk fix is the lazy-embedding refactor (INFRA-04) because `vector_store.py` imports `default_embeddings` at module scope on line 3. Changing `embeddings.py` to a function-based lazy pattern requires updating the call site in `vector_store.py` from `default_embeddings.embed_documents(...)` to `get_default_embeddings().embed_documents(...)`. Failing to update the call site will cause an `AttributeError` at runtime. All other fixes are isolated and have no cross-file impact.

The requirements.txt is confirmed UTF-16 LE (null bytes visible on every character in the raw read). Converting it to UTF-8 before making any other changes prevents `pip install` from breaking mid-phase on any new dependency additions.

**Primary recommendation:** Execute fixes in dependency order — (1) requirements.txt encoding first so pip works, (2) path + WAL + startup probe as a batch, (3) lazy embedding + vector_store call site together, (4) eager-load fix in document_parser, (5) upload validation last (standalone router change).

---

## Standard Stack

### Core (already installed — no new installs needed for this phase)

| Library | Version (from requirements.txt) | Purpose in this phase |
|---------|----------------------------------|----------------------|
| SQLAlchemy | 2.0.49 | WAL mode event listener, `joinedload` eager load |
| FastAPI | 0.135.3 | Upload validation, HTTPException 400/413 |
| chromadb | 1.5.7 | PersistentClient with absolute path |
| langchain-community | 0.4.1 | HuggingFaceEmbeddings (lazy load target) |
| python-dotenv | 1.2.2 | `.env` loading for `CHROMADB_PATH` / `DATABASE_PATH` |
| pathlib (stdlib) | Python 3.13 | `__file__`-relative absolute path construction |
| shutil (stdlib) | Python 3.13 | `shutil.which("pdfinfo")`, `shutil.which("tesseract")` |
| logging (stdlib) | Python 3.13 | WARNING log for missing system deps |
| os (stdlib) | Python 3.13 | `os.makedirs`, `os.getenv` |

All packages are already present in the installed venv. `pip install` is not needed for any fix in this phase.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pathlib.Path(__file__).resolve().parent` | `os.path.abspath(os.path.dirname(__file__))` | Both produce absolute paths; `pathlib` is more readable and idiomatic in Python 3.6+ |
| SQLAlchemy event listener for WAL | `connect_args={"check_same_thread": False}` + raw PRAGMA on each session | Event listener fires once per physical connection (correct); per-session PRAGMA is redundant overhead |
| `functools.lru_cache` for lazy embedding | Module-level `_model = None` guard | `lru_cache` is cleaner but `_model` guard is explicit and easier to mock in tests |
| `joinedload` for eager load | Separate scalar query for `project_id` | Both correct; separate query is simpler and avoids relationship loading entirely |

---

## Architecture Patterns

### Recommended Fix Structure

All fixes are in-place edits. No new files, no new directories in `app/`. The only new directory is `backend/data/` (created at runtime by `os.makedirs`).

```
backend/
├── app/
│   ├── core/
│   │   └── database.py          # INFRA-01, INFRA-02, INFRA-03: paths + WAL
│   ├── services/
│   │   ├── embeddings.py        # INFRA-04: lazy load
│   │   ├── vector_store.py      # INFRA-01: ChromaDB path + call site update
│   │   └── document_parser.py   # INFRA-05: eager-load fix + INFRA-08: startup probe
│   └── routers/
│       └── documents.py         # INFRA-06: upload validation
├── data/                        # Created at startup — git-ignored
│   ├── rag_database.db
│   └── chroma_db/
└── requirements.txt             # INFRA-07: re-encode to UTF-8
```

### Pattern 1: `__file__`-relative absolute path with env var override

**What:** Compute absolute path anchored to the source file's location, fallback when env var not set.

**When to use:** Any persistent resource that must survive server restarts from different working directories.

```python
# Source: Python stdlib pathlib docs [ASSUMED - standard pattern]
import os
from pathlib import Path

# backend/app/core/database.py
_DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent.parent / "data" / "rag_database.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.getenv('DATABASE_PATH', _DEFAULT_DB_PATH)}"

# Ensure parent directory exists
os.makedirs(os.path.dirname(SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")), exist_ok=True)
```

Note: `Path(__file__)` in `backend/app/core/database.py` resolves to that file. `.parent` = `backend/app/core/`, `.parent.parent` = `backend/app/`, `.parent.parent.parent` = `backend/`. So `/ "data" / "rag_database.db"` lands at `backend/data/rag_database.db`. [VERIFIED: manual path traversal against codebase structure]

### Pattern 2: SQLAlchemy WAL mode via event listener

**What:** Fire `PRAGMA journal_mode=WAL` on every new physical SQLite connection, not per-session.

**When to use:** Any SQLite + SQLAlchemy app where background tasks write concurrently with request threads.

```python
# Source: SQLAlchemy docs — connection events [ASSUMED - standard SQLite WAL pattern]
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
```

Place this listener definition in `database.py` immediately after the `engine = create_engine(...)` call. The `isinstance` guard prevents the pragma from firing on non-SQLite engines (important if the app ever switches to PostgreSQL).

### Pattern 3: Lazy singleton with module-level guard

**What:** Initialize expensive object on first call, cache in module-level variable.

**When to use:** ML models, large data structures, anything that costs >1 second or >100MB to initialize.

```python
# Source: Standard Python lazy initialization pattern [ASSUMED]
# backend/app/services/embeddings.py

_default_embeddings = None

def get_default_embeddings():
    global _default_embeddings
    if _default_embeddings is None:
        _default_embeddings = EmbeddingFactory.get_embedding_model("local")
    return _default_embeddings
```

**Call site change required in `vector_store.py`:**

```python
# Before (line 3 and usages):
from app.services.embeddings import default_embeddings
# ...
embeddings = default_embeddings.embed_documents(text_chunks)
query_embedding = default_embeddings.embed_query(query)

# After:
from app.services.embeddings import get_default_embeddings
# ...
embeddings = get_default_embeddings().embed_documents(text_chunks)
query_embedding = get_default_embeddings().embed_query(query)
```

### Pattern 4: Eager-load to fix DetachedInstanceError

**What:** Query `project_id` directly from a fresh session using the scalar `document_id`, avoiding relationship traversal across session boundaries.

**When to use:** Background tasks that need relationship data from an ORM object loaded in a prior (now-closed) session.

```python
# backend/app/services/document_parser.py
# Existing code already correctly uses SessionLocal() — only the relationship access is broken.

# CURRENT (broken): db_document.folder.project_id  <- lazy load on closed request session
# FIX OPTION A: separate scalar query (simplest, no ORM relationship risk)
from app.models.domain import Document, Folder

db = SessionLocal()
try:
    db_document = db.query(Document).filter(Document.id == document_id).first()
    # Get project_id via separate query — no relationship traversal
    folder = db.query(Folder).filter(Folder.id == db_document.folder_id).first()
    proj_id = folder.project_id if folder else None
    ...
finally:
    db.close()

# FIX OPTION B: joinedload (cleaner, fewer queries)
from sqlalchemy.orm import joinedload

db_document = db.query(Document).options(
    joinedload(Document.folder)
).filter(Document.id == document_id).first()
proj_id = db_document.folder.project_id if db_document.folder else None
```

Both options are correct. Option A (separate query) is recommended for simplicity — the planner can choose either.

### Pattern 5: Upload validation before disk write

**What:** Check extension and size before `shutil.copyfileobj`, return appropriate HTTP error codes without writing files.

**When to use:** Any file upload endpoint; validation must be cheap and early.

```python
# backend/app/routers/documents.py
import os
from fastapi import HTTPException, UploadFile

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB

async def upload_document(file: UploadFile = File(...), ...):
    # 1. Extension check (before reading file content)
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=t("errors.invalid_file_type", lang)
        )

    # 2. Content-Type check (defense in depth)
    ALLOWED_CONTENT_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=t("errors.invalid_file_type", lang))

    # 3. Size check via Content-Length header (fast path) or post-read check
    # Note: Content-Length may not be present; enforce a hard limit post-read
    # Read into memory only up to limit + 1 byte to detect oversized files
    content = await file.read(MAX_FILE_SIZE_BYTES + 1)
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=t("errors.file_too_large", lang))

    # Write to disk from in-memory buffer (file is already read and validated)
    ...
```

**Important:** D-04 says validate BEFORE saving to disk. The size check above reads the file into memory (up to 100MB + 1 byte) to detect oversized files without writing to disk. This is acceptable for the 100MB limit on a local tool — it avoids the complexity of streaming validation.

### Pattern 6: Startup probe for system dependencies

**What:** Check for binary dependencies at application startup using `shutil.which`.

**When to use:** Any app that shells out to system binaries (poppler, tesseract, ffmpeg, etc.).

```python
# Can be placed in main.py startup event or document_parser.py module level
import shutil
import logging

logger = logging.getLogger(__name__)

def probe_system_dependencies():
    missing = []
    if not shutil.which("pdfinfo"):
        missing.append("poppler (pdfinfo)")
    if not shutil.which("tesseract"):
        missing.append("tesseract")

    if missing:
        logger.warning(
            "System dependencies not found: %s. "
            "PDF parsing will fail when documents are processed. "
            "Install missing tools and restart the server.",
            ", ".join(missing)
        )

# Call at startup: probe_system_dependencies()
```

Per D-07, this is a WARNING log only — server continues to start normally.

### Anti-Patterns to Avoid

- **CWD-relative paths in module scope:** `os.path.join(os.getcwd(), "chroma_db")` — breaks silently when server is started from a different directory. Always use `__file__`-relative or env var.
- **Module-level expensive initialization:** `default_embeddings = EmbeddingFactory.get_embedding_model("local")` — loads 80MB+ model at import time, making every test that imports the module slow.
- **Validating after disk write:** Writing the file first, then checking its size — wastes I/O and requires cleanup on rejection.
- **PRAGMA in get_db():** Setting WAL mode in the `get_db()` dependency runs it on every request cycle, not just on new connections. Use the engine-level event listener instead.
- **Lazy load across session boundaries:** Accessing `db_document.folder.project_id` in a background task when the session from the request handler is already closed triggers `DetachedInstanceError`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Absolute path construction | Custom `os.path` string manipulation | `pathlib.Path(__file__).resolve()` | Handles symlinks, cross-platform separators |
| SQLite WAL enablement | Manual PRAGMA in every session | SQLAlchemy `@event.listens_for(Engine, "connect")` | Fires once per physical connection — correct semantics |
| Binary availability check | Subprocess `which` call | `shutil.which()` | Cross-platform, no subprocess overhead, stdlib |
| Eager relationship loading | Manual join query | SQLAlchemy `joinedload()` | Generates correct JOIN, handles None safely |
| File extension validation | Regex or string split | `os.path.splitext(filename)[1].lower()` | Stdlib, handles edge cases like no-extension files |

**Key insight:** Every problem in this phase has a stdlib or already-installed-library solution. No new packages needed.

---

## Common Pitfalls

### Pitfall 1: Forgetting the `vector_store.py` call site when refactoring embeddings

**What goes wrong:** `embeddings.py` is changed to expose `get_default_embeddings()` instead of `default_embeddings`, but `vector_store.py` line 3 still imports `from app.services.embeddings import default_embeddings`. The import succeeds (Python doesn't error on missing module attributes until they're accessed), but `default_embeddings` is `None` or raises `ImportError` at the first embedding call.

**Why it happens:** Two files are coupled on this name. The CONTEXT.md code context explicitly calls out this integration point: "`embeddings.py` `default_embeddings` is imported by `vector_store.py` — lazy pattern must be import-compatible."

**How to avoid:** Update both files atomically in the same task. Search for all usages of `default_embeddings` before the refactor: `grep -r "default_embeddings" backend/app/`.

**Warning signs:** Server starts fine, first embedding request raises `TypeError: 'NoneType' object has no attribute 'embed_documents'`.

### Pitfall 2: Path depth miscalculation for `__file__`-relative default

**What goes wrong:** `database.py` is at `backend/app/core/database.py`. Using `.parent.parent` (2 levels up) lands at `backend/app/`, not `backend/`. The correct default path needs `.parent.parent.parent` (3 levels up) to reach `backend/` and then `/ "data" / "rag_database.db"`.

**Why it happens:** Each `.parent` call traverses one directory level. Counting levels when files are nested 3 directories deep is easy to get wrong.

**How to avoid:** Log the resolved absolute path at startup (per success criteria: "Server starts with absolute DB/ChromaDB paths logged to console"). The log will immediately reveal the wrong path if miscounted.

**Warning signs:** Data directory created in the wrong location; existing `rag_database.db` not found after path change.

### Pitfall 3: WAL mode listener fires on non-SQLite connections

**What goes wrong:** The engine-level `connect` event listener runs for every database engine in the process. If a second engine (e.g., for a different database or in tests) is created, the PRAGMA fires on it too — including on non-SQLite drivers which raise an error.

**Why it happens:** `@event.listens_for(Engine, "connect")` is a class-level listener that applies to ALL Engine instances.

**How to avoid:** Add an `isinstance(dbapi_connection, sqlite3.Connection)` guard inside the listener. Already documented in the code example in Pattern 2 above.

**Warning signs:** `OperationalError: near "PRAGMA": syntax error` if another engine type is introduced.

### Pitfall 4: `requirements.txt` re-encoding creates a new BOM

**What goes wrong:** When converting UTF-16 LE to UTF-8, some editors or Python's `open(..., encoding="utf-8-sig")` write a UTF-8 BOM (`\xef\xbb\xbf`) at the start. pip may trip on the BOM in some versions.

**Why it happens:** `utf-8-sig` is "UTF-8 with BOM". Always use `encoding="utf-8"` (no BOM).

**How to avoid:** Use the Python one-liner with explicit encodings:
```bash
python -c "
content = open('backend/requirements.txt', encoding='utf-16').read()
open('backend/requirements.txt', 'w', encoding='utf-8', newline='').write(content)
"
```
Verify with: `file backend/requirements.txt` (should report ASCII or UTF-8, no BOM).

**Warning signs:** `pip install -r requirements.txt` raises `UnicodeDecodeError` or first line starts with a special character.

### Pitfall 5: File size validation reads entire 100MB into RAM

**What goes wrong:** Reading up to 100MB + 1 byte into memory to check size uses significant RAM for every upload attempt.

**Why it happens:** The Content-Length header is unreliable (clients can lie or omit it), so reading the content is the only reliable check without disk I/O.

**How to avoid:** For a local single-user tool this is acceptable. The alternative (stream to a temp file, check size, delete if too large) is more complex and not required by the user decisions. Document the tradeoff explicitly in code comments.

**Warning signs:** Memory spikes during upload of large files before the 413 is returned.

### Pitfall 6: Missing i18n keys for new error messages

**What goes wrong:** Upload validation raises `HTTPException(status_code=400, detail=t("errors.invalid_file_type", lang))`, but if `"invalid_file_type"` and `"file_too_large"` keys don't exist in `backend/locales/en.json` and `backend/locales/vi.json`, the `t()` function falls back to returning the key string itself — not ideal UX but not a crash.

**Why it happens:** The i18n system uses dot-notation key lookup with English fallback (per CONVENTIONS.md). Missing keys don't raise exceptions.

**How to avoid:** Add the new error keys to both locale files in the same task as the validation code. Check what existing error key patterns look like in the locale files before adding new ones.

---

## Code Examples

### INFRA-02 + INFRA-01: Absolute paths (database.py and vector_store.py)

```python
# backend/app/core/database.py — complete replacement
import os
import logging
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
import sqlite3

logger = logging.getLogger(__name__)

# __file__ = backend/app/core/database.py
# .parent.parent.parent = backend/
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DB_PATH = str(_BACKEND_DIR / "data" / "rag_database.db")

DATABASE_PATH = os.getenv("DATABASE_PATH", _DEFAULT_DB_PATH)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Ensure data directory exists
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
logger.info("SQLite database path: %s", DATABASE_PATH)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# INFRA-03: WAL mode via engine-level connection event
@event.listens_for(engine, "connect")
def set_sqlite_wal_mode(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

```python
# backend/app/services/vector_store.py — path and import changes only
import os
import logging
from pathlib import Path
from chromadb import PersistentClient
from app.services.embeddings import get_default_embeddings  # changed from default_embeddings

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_CHROMADB_PATH = str(_BACKEND_DIR / "data" / "chroma_db")
CHROMADB_DIR = os.getenv("CHROMADB_PATH", _DEFAULT_CHROMADB_PATH)
os.makedirs(CHROMADB_DIR, exist_ok=True)
logger.info("ChromaDB path: %s", CHROMADB_DIR)

class VectorStoreService:
    def __init__(self):
        self.client = PersistentClient(path=CHROMADB_DIR)

    # ... rest of methods unchanged except call sites:
    # default_embeddings.embed_documents(...) -> get_default_embeddings().embed_documents(...)
    # default_embeddings.embed_query(...) -> get_default_embeddings().embed_query(...)
```

### INFRA-07: requirements.txt re-encoding (one-time operation)

```bash
# Run from project root
python -c "
content = open('backend/requirements.txt', encoding='utf-16').read()
open('backend/requirements.txt', 'w', encoding='utf-8', newline='').write(content)
print('Converted successfully')
"
```

Verification: `python -c "f=open('backend/requirements.txt'); print(repr(f.read(20)))"` — should show normal ASCII characters, not `\x00` null bytes.

---

## State of the Art

| Old Approach | Current Approach | Impact for This Phase |
|--------------|------------------|-----------------------|
| `os.path.join(os.getcwd(), ...)` for paths | `pathlib.Path(__file__).resolve()` | Use `pathlib` — it is the current stdlib standard for path manipulation |
| Module-level singleton initialization | Lazy initialization with `functools.lru_cache` or guard variable | Guard variable is simpler; `lru_cache` is also correct but adds a layer |
| SQLite WAL via `connect_args` + per-connection PRAGMA | SQLAlchemy engine-level `connect` event listener | Event listener is the current recommended pattern for SQLAlchemy 2.x [ASSUMED] |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | SQLAlchemy 2.x event listener `@event.listens_for(engine, "connect")` is the current recommended WAL pattern | Architecture Patterns: Pattern 2 | Wrong approach could mean PRAGMA doesn't fire reliably; fallback is per-session PRAGMA in `get_db()` |
| A2 | `python-dotenv` is already loaded in `main.py` or elsewhere before `database.py` is imported | Architecture Patterns: Pattern 1 | If dotenv is not loaded, `os.getenv("DATABASE_PATH")` will not pick up `.env` file values; easy to fix by calling `load_dotenv()` at top of `database.py` |
| A3 | HuggingFaceEmbeddings from langchain-community 0.4.1 is not deprecated in favor of a langchain-huggingface package | Standard Stack | If deprecated, import path may need updating; check if `langchain-huggingface` is installed |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.
(Table is not empty — 3 assumptions flagged above.)

---

## Open Questions

1. **Where to place `probe_system_dependencies()`**
   - What we know: D-07 says "clear WARNING log at startup." `main.py` has a top-level startup where `Base.metadata.create_all()` is called.
   - What's unclear: Whether to put the probe directly in `main.py` or in a `lifespan` event or in `document_parser.py` module scope.
   - Recommendation: Place in `main.py` as a direct function call before `app = FastAPI(...)` or in a `@app.on_event("startup")` handler. Module scope in `document_parser.py` also works but is less visible.

2. **Whether `load_dotenv()` needs to be added**
   - What we know: `python-dotenv==1.2.2` is in requirements.txt but no `load_dotenv()` call is visible in `main.py`.
   - What's unclear: Whether it is called elsewhere (e.g., a `.env` loader script outside `app/`).
   - Recommendation: Add `from dotenv import load_dotenv; load_dotenv()` at the top of `main.py` or `database.py` to ensure env vars are loaded from `.env` before path resolution.

3. **Whether to add i18n keys for upload validation errors**
   - What we know: The i18n system uses `t("errors.key", lang)` with fallback to the key string.
   - What's unclear: Whether the locale files already have `invalid_file_type` and `file_too_large` keys.
   - Recommendation: The task for INFRA-06 should include adding these keys to `backend/locales/en.json` and `backend/locales/vi.json`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | All fixes | Yes (pip confirmed) | 3.13 (inferred from pip path) | — |
| pip | requirements.txt re-encode verify | Yes | 26.0.1 | — |
| pdfinfo (poppler) | INFRA-08 probe target | No | — | Probe logs WARNING, server continues |
| tesseract | INFRA-08 probe target | No | — | Probe logs WARNING, server continues |
| SQLAlchemy 2.0.49 | INFRA-02, INFRA-03 | Yes (in venv) | 2.0.49 | — |
| chromadb 1.5.7 | INFRA-01 | Yes (in venv) | 1.5.7 | — |
| langchain-community 0.4.1 | INFRA-04 | Yes (in venv) | 0.4.1 | — |

**Missing dependencies with no fallback:** None — all required Python packages are installed.

**Missing dependencies with fallback:** `pdfinfo` and `tesseract` are not installed, but per D-07 this is expected and handled by the startup probe warning. These are Phase 3b concerns, not Phase 3a blockers.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (per global rules: `~/.claude/rules/python/testing.md`) |
| Config file | None found — Wave 0 gap |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v --tb=short` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | ChromaDB path is absolute, not CWD-relative | unit | `pytest tests/test_vector_store.py::test_chromadb_path_is_absolute -x` | No — Wave 0 |
| INFRA-02 | SQLite path is absolute; env var override works | unit | `pytest tests/test_database.py::test_sqlite_path_is_absolute -x` | No — Wave 0 |
| INFRA-03 | WAL mode enabled on connection | unit | `pytest tests/test_database.py::test_wal_mode_enabled -x` | No — Wave 0 |
| INFRA-04 | Embedding model not loaded at import time | unit | `pytest tests/test_embeddings.py::test_no_model_at_import -x` | No — Wave 0 |
| INFRA-05 | Background task processes document without DetachedInstanceError | integration | `pytest tests/test_document_parser.py::test_background_task_no_detached_error -x` | No — Wave 0 |
| INFRA-06 | .exe upload returns 400; 200MB upload returns 413 | unit | `pytest tests/test_documents_router.py::test_invalid_extension_returns_400 tests/test_documents_router.py::test_oversized_file_returns_413 -x` | No — Wave 0 |
| INFRA-07 | requirements.txt is valid UTF-8 | smoke | `pytest tests/test_requirements_encoding.py::test_requirements_utf8 -x` | No — Wave 0 |
| INFRA-08 | Missing pdfinfo/tesseract logs WARNING, does not crash startup | unit | `pytest tests/test_startup.py::test_missing_system_deps_warns -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && python -m pytest tests/ -x -q` (fast, fail-fast)
- **Per wave merge:** `cd backend && python -m pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/__init__.py` — package marker
- [ ] `backend/tests/conftest.py` — shared fixtures (test DB, mock embeddings)
- [ ] `backend/tests/test_database.py` — covers INFRA-02, INFRA-03
- [ ] `backend/tests/test_vector_store.py` — covers INFRA-01
- [ ] `backend/tests/test_embeddings.py` — covers INFRA-04
- [ ] `backend/tests/test_document_parser.py` — covers INFRA-05
- [ ] `backend/tests/test_documents_router.py` — covers INFRA-06
- [ ] `backend/tests/test_requirements_encoding.py` — covers INFRA-07
- [ ] `backend/tests/test_startup.py` — covers INFRA-08
- [ ] `cd backend && pip install pytest pytest-asyncio httpx` — test dependencies not in requirements.txt

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Not in scope for this phase |
| V3 Session Management | No | Not in scope |
| V4 Access Control | No | Not in scope |
| V5 Input Validation | Yes | Extension whitelist + size limit in `documents.py` |
| V6 Cryptography | No | No crypto operations in this phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious file upload (zip bombs, executables disguised as PDFs) | Tampering | Extension whitelist (D-06) + Content-Type check; validate BEFORE disk write (D-04) |
| Path traversal via filename | Tampering | Already mitigated — `uuid.uuid4()` filename generation prevents original filename use in path |
| Oversized upload DoS | Denial of Service | 100MB limit with HTTP 413 (D-05) |

**Note on Content-Type validation:** Content-Type headers can be spoofed by clients. Extension check is the primary gate. Content-Type is a secondary defense layer. For a local single-user tool this is sufficient. True MIME validation (reading file magic bytes) is out of scope for v1.

---

## Sources

### Primary (HIGH confidence — verified against codebase)

- `backend/app/core/database.py` (lines 1-18) — confirmed current SQLite URL pattern, missing WAL mode
- `backend/app/services/embeddings.py` (lines 27-28) — confirmed module-level `default_embeddings` singleton
- `backend/app/services/vector_store.py` (lines 3, 5, 26, 49) — confirmed CWD-relative path and `default_embeddings` import
- `backend/app/services/document_parser.py` (lines 81, 86) — confirmed `db_document.folder.project_id` lazy-load risk
- `backend/app/routers/documents.py` (lines 16-66) — confirmed no validation before disk write
- `backend/requirements.txt` — confirmed UTF-16 LE encoding (null bytes on every character)
- `backend/app/models/domain.py` — confirmed `Document.folder` relationship structure for eager-load fix
- `.planning/phases/03A-infrastructure-fixes/03A-CONTEXT.md` — locked decisions D-01 through D-11

### Secondary (MEDIUM confidence — cross-referenced research documents)

- `.planning/research/PITFALLS.md` — Pitfall #3 (CWD path), #6 (DetachedInstanceError), #8 (eager load at import), #12 (UTF-16), #14 (WAL mode)
- `.planning/research/SUMMARY.md` — Critical Blockers table (8 items, all verified against codebase)
- `.planning/codebase/CONCERNS.md` — items #5, #7, #8, #10, #11, #12 (all confirmed against source files)
- `.planning/codebase/CONVENTIONS.md` — Factory pattern, singleton pattern, error handling conventions

### Tertiary (LOW confidence — training knowledge, not verified this session)

- SQLAlchemy engine-level `connect` event for WAL mode — standard pattern but not verified against SQLAlchemy 2.0.49 changelog [A1]
- `python-dotenv` load_dotenv() placement — not confirmed against actual main.py startup sequence [A2]

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all packages confirmed in requirements.txt against codebase
- Architecture: HIGH — all patterns verified against actual source files; path depth confirmed by counting directory levels in file tree
- Pitfalls: HIGH — derived from direct source file inspection, not just training knowledge
- Environment: HIGH — confirmed via shell commands (pdfinfo/tesseract absent, pip/python present)

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable libraries; SQLAlchemy/ChromaDB APIs unlikely to change)
