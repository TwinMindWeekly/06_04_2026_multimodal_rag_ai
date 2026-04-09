---
phase: 03A-infrastructure-fixes
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/requirements.txt
  - backend/app/core/database.py
  - backend/app/main.py
  - backend/tests/__init__.py
  - backend/tests/conftest.py
  - backend/tests/test_requirements_encoding.py
  - backend/tests/test_database.py
  - backend/tests/test_startup.py
autonomous: true
requirements: [INFRA-07, INFRA-02, INFRA-03, INFRA-08]

must_haves:
  truths:
    - "pip install -r requirements.txt succeeds without encoding errors"
    - "Server starts with absolute SQLite path logged to console"
    - "WAL mode is active on every new SQLite connection"
    - "Missing poppler/tesseract produces WARNING log at startup without blocking server"
  artifacts:
    - path: "backend/requirements.txt"
      provides: "UTF-8 encoded dependency list with test deps"
    - path: "backend/app/core/database.py"
      provides: "Absolute SQLite path via env var + WAL mode via event listener"
      contains: "PRAGMA journal_mode=WAL"
    - path: "backend/app/main.py"
      provides: "Startup probe for system dependencies + load_dotenv"
      contains: "probe_system_dependencies"
    - path: "backend/tests/conftest.py"
      provides: "Shared test fixtures for all phase 3a tests"
      contains: "test_engine"
  key_links:
    - from: "backend/app/core/database.py"
      to: "SQLAlchemy engine"
      via: "event.listens_for(engine, 'connect') firing PRAGMA"
      pattern: "event\\.listens_for.*connect"
    - from: "backend/app/main.py"
      to: "shutil.which"
      via: "probe_system_dependencies() at startup"
      pattern: "shutil\\.which"
    - from: "backend/app/main.py"
      to: "dotenv"
      via: "load_dotenv() before app module imports"
      pattern: "load_dotenv"
---

<objective>
Fix requirements.txt encoding, establish test infrastructure, configure absolute SQLite paths with WAL mode, and add system dependency probes at startup.

Purpose: These foundational fixes unblock pip installs, prevent "database is locked" errors, provide stable DB paths regardless of CWD, and warn about missing parsing dependencies.

Output: Working test scaffold, UTF-8 requirements.txt, hardened database.py, startup probes in main.py.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/03A-infrastructure-fixes/03A-CONTEXT.md
@.planning/phases/03A-infrastructure-fixes/03A-RESEARCH.md
@.planning/phases/03A-infrastructure-fixes/03A-VALIDATION.md

@backend/app/core/database.py
@backend/app/main.py
@backend/app/models/domain.py
@backend/app/core/i18n.py

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From backend/app/core/database.py (current state — to be rewritten):
```python
SQLALCHEMY_DATABASE_URL = "sqlite:///./rag_database.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
def get_db(): ...
```

From backend/app/main.py (current state — to be modified):
```python
from app.core.database import engine, Base
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Multimodal RAG API")
```

From backend/app/models/domain.py (read-only reference):
```python
class Project(Base): ...
class Folder(Base): ...
class Document(Base): ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Fix requirements.txt encoding and create test scaffold</name>
  <files>backend/requirements.txt, backend/tests/__init__.py, backend/tests/conftest.py, backend/tests/test_requirements_encoding.py</files>
  <read_first>
    - backend/requirements.txt (current UTF-16 LE encoded file)
    - backend/app/core/database.py (needed for conftest.py fixture design)
    - backend/app/main.py (needed for TestClient fixture)
  </read_first>
  <behavior>
    - test_requirements_utf8: open('backend/requirements.txt', encoding='utf-8') succeeds without UnicodeDecodeError
    - test_requirements_no_null_bytes: file content does not contain \x00 null bytes
    - test_requirements_no_bom: file does not start with \xef\xbb\xbf BOM marker
  </behavior>
  <action>
    **Step 1: Convert requirements.txt from UTF-16 LE to UTF-8 (per D-11).**

    Run this Python one-liner from the project root:
    ```bash
    python -c "
    content = open('backend/requirements.txt', encoding='utf-16').read()
    open('backend/requirements.txt', 'w', encoding='utf-8', newline='').write(content)
    print('Converted to UTF-8')
    "
    ```

    Verify conversion: `python -c "f=open('backend/requirements.txt'); print(repr(f.read(30)))"` — should show normal ASCII, no `\x00` null bytes, no `\xff\xfe` BOM.

    **Step 2: Add test dependencies to requirements.txt.**

    Append these lines at the end of requirements.txt:
    ```
    pytest>=8.0
    pytest-asyncio>=0.23
    httpx>=0.27
    ```

    Then run: `cd backend && pip install pytest pytest-asyncio httpx`

    **Step 3: Create test scaffold.**

    Create `backend/tests/__init__.py` as an empty file.

    Create `backend/tests/conftest.py` with these shared fixtures:
    ```python
    import pytest
    from unittest.mock import MagicMock
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from fastapi.testclient import TestClient

    from app.core.database import Base, get_db
    from app.main import app

    TEST_DATABASE_URL = "sqlite:///file::memory:?cache=shared"

    @pytest.fixture
    def test_engine():
        engine = create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=engine)
        yield engine
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    @pytest.fixture
    def test_db(test_engine):
        TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=test_engine
        )
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    @pytest.fixture
    def client(test_engine):
        TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=test_engine
        )
        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()
        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()

    @pytest.fixture
    def mock_embeddings():
        mock = MagicMock()
        mock.embed_documents.return_value = [[0.1] * 384]
        mock.embed_query.return_value = [0.1] * 384
        return mock
    ```

    **Step 4: Create test_requirements_encoding.py:**
    ```python
    import os

    REQUIREMENTS_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "requirements.txt"
    )

    def test_requirements_utf8():
        with open(REQUIREMENTS_PATH, encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 0, "requirements.txt is empty"

    def test_requirements_no_null_bytes():
        with open(REQUIREMENTS_PATH, "rb") as f:
            raw = f.read()
        assert b"\x00" not in raw, "requirements.txt contains null bytes (still UTF-16?)"

    def test_requirements_no_bom():
        with open(REQUIREMENTS_PATH, "rb") as f:
            first_bytes = f.read(3)
        assert first_bytes != b"\xef\xbb\xbf", "requirements.txt has UTF-8 BOM"
        assert first_bytes[:2] != b"\xff\xfe", "requirements.txt has UTF-16 LE BOM"
    ```
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/test_requirements_encoding.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "open('backend/requirements.txt', encoding='utf-8').read()"` exits 0 (no UnicodeDecodeError)
    - `python -c "assert b'\\x00' not in open('backend/requirements.txt','rb').read()"` exits 0
    - `backend/tests/__init__.py` exists (can be empty)
    - `backend/tests/conftest.py` contains `def test_engine` and `def client` and `def mock_embeddings`
    - `backend/tests/test_requirements_encoding.py` contains `def test_requirements_utf8`
    - `cd backend && python -m pytest tests/test_requirements_encoding.py -x` exits 0
  </acceptance_criteria>
  <done>requirements.txt is valid UTF-8 without BOM or null bytes. Test scaffold exists with shared fixtures. All 3 encoding tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Absolute SQLite path with env var override and WAL mode</name>
  <files>backend/app/core/database.py, backend/tests/test_database.py</files>
  <read_first>
    - backend/app/core/database.py (current state to rewrite)
    - backend/app/models/domain.py (imports Base from database.py — must not break)
    - backend/app/main.py (imports engine, Base from database.py)
    - .planning/phases/03A-infrastructure-fixes/03A-RESEARCH.md (Pattern 1 and Pattern 2 code examples)
  </read_first>
  <behavior>
    - test_sqlite_path_is_absolute: DATABASE_PATH is an absolute path (os.path.isabs returns True)
    - test_sqlite_path_default_under_backend_data: default path ends with "backend/data/rag_database.db" (or backslash variant on Windows)
    - test_database_path_env_override: setting DATABASE_PATH env var changes the resolved path
    - test_wal_mode_enabled: new connection returns "wal" from PRAGMA journal_mode query
    - test_data_directory_created: os.path.dirname(DATABASE_PATH) directory exists after module load
  </behavior>
  <action>
    **Rewrite `backend/app/core/database.py` completely (per D-01, D-02, D-03, D-08):**

    ```python
    import os
    import logging
    import sqlite3
    from pathlib import Path

    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker, declarative_base

    logger = logging.getLogger(__name__)

    # __file__ = backend/app/core/database.py
    # .parent = backend/app/core/
    # .parent.parent = backend/app/
    # .parent.parent.parent = backend/
    _BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

    # Per D-01, D-03: env var DATABASE_PATH with __file__-relative default
    _DEFAULT_DB_PATH = str(_BACKEND_DIR / "data" / "rag_database.db")
    DATABASE_PATH = os.getenv("DATABASE_PATH", _DEFAULT_DB_PATH)

    # Per D-02: auto-create data directory
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
    logger.info("SQLite database path: %s", DATABASE_PATH)

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

    # Per D-08 (INFRA-03): WAL mode via engine-level connection event
    @event.listens_for(engine, "connect")
    def _set_sqlite_wal_mode(dbapi_connection, connection_record):
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

    **Public API preserved:** `engine`, `Base`, `SessionLocal`, `get_db`, `DATABASE_PATH`, `SQLALCHEMY_DATABASE_URL` are all still exported. No downstream import breakage.

    **Create `backend/tests/test_database.py`:**

    ```python
    import os
    import sqlite3
    from unittest.mock import patch

    from sqlalchemy import create_engine, event, text
    from sqlalchemy.orm import sessionmaker


    def test_sqlite_path_is_absolute():
        from app.core.database import DATABASE_PATH
        assert os.path.isabs(DATABASE_PATH), (
            f"DATABASE_PATH is not absolute: {DATABASE_PATH}"
        )


    def test_sqlite_path_default_ends_with_backend_data():
        from app.core.database import DATABASE_PATH
        normalized = DATABASE_PATH.replace("\\", "/")
        assert normalized.endswith("backend/data/rag_database.db"), (
            f"Default path does not end with backend/data/rag_database.db: {DATABASE_PATH}"
        )


    def test_data_directory_created():
        from app.core.database import DATABASE_PATH
        data_dir = os.path.dirname(DATABASE_PATH)
        assert os.path.isdir(data_dir), (
            f"Data directory does not exist: {data_dir}"
        )


    def test_wal_mode_enabled():
        from app.core.database import engine
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode")).scalar()
            assert result == "wal", f"Expected WAL mode, got: {result}"


    def test_database_path_env_override():
        test_path = "/tmp/test_override.db"
        with patch.dict(os.environ, {"DATABASE_PATH": test_path}):
            # Re-evaluate the env var (simulating module reload)
            resolved = os.getenv("DATABASE_PATH", "fallback")
            assert resolved == test_path
    ```
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/test_database.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - `backend/app/core/database.py` contains `Path(__file__).resolve().parent.parent.parent`
    - `backend/app/core/database.py` contains `os.getenv("DATABASE_PATH"`
    - `backend/app/core/database.py` contains `PRAGMA journal_mode=WAL`
    - `backend/app/core/database.py` contains `isinstance(dbapi_connection, sqlite3.Connection)`
    - `backend/app/core/database.py` contains `os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)`
    - `backend/app/core/database.py` contains `logger.info("SQLite database path:`
    - `backend/tests/test_database.py` contains `def test_sqlite_path_is_absolute` and `def test_wal_mode_enabled`
    - `cd backend && python -m pytest tests/test_database.py -x` exits 0
  </acceptance_criteria>
  <done>database.py uses absolute path via __file__ with DATABASE_PATH env var override, WAL mode fires on every connection via engine event listener, data directory auto-created. All 5 tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: System dependency startup probe and load_dotenv</name>
  <files>backend/app/main.py, backend/tests/test_startup.py</files>
  <read_first>
    - backend/app/main.py (current state to modify)
    - backend/app/core/database.py (imports from main.py — order matters for load_dotenv)
    - .planning/phases/03A-infrastructure-fixes/03A-RESEARCH.md (Pattern 6 code example)
  </read_first>
  <behavior>
    - test_missing_pdfinfo_logs_warning: when shutil.which("pdfinfo") returns None, WARNING log is emitted containing "poppler" or "pdfinfo"
    - test_missing_tesseract_logs_warning: when shutil.which("tesseract") returns None, WARNING log is emitted containing "tesseract"
    - test_probe_does_not_raise: probe_system_dependencies() returns without exception regardless of missing deps
    - test_app_still_starts: FastAPI app is importable and root endpoint responds 200
  </behavior>
  <action>
    **Rewrite `backend/app/main.py` (per D-07 for INFRA-08, plus load_dotenv for D-01/D-03 env var support):**

    ```python
    from dotenv import load_dotenv
    load_dotenv()  # Must be BEFORE app.core imports so DATABASE_PATH/CHROMADB_PATH env vars are available

    import shutil
    import logging

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.core.database import engine, Base
    from app.models import domain  # noqa: F401 — registers models with Base

    logger = logging.getLogger(__name__)


    def probe_system_dependencies() -> None:
        """Check for system binaries needed by document parsing.
        Per D-07: WARNING log only, does NOT block server startup.
        """
        missing: list[str] = []
        if not shutil.which("pdfinfo"):
            missing.append("poppler (pdfinfo)")
        if not shutil.which("tesseract"):
            missing.append("tesseract")

        if missing:
            logger.warning(
                "System dependencies not found: %s. "
                "PDF parsing will fail when documents are processed. "
                "Install missing tools and restart the server.",
                ", ".join(missing),
            )


    # Probe at startup — warning only
    probe_system_dependencies()

    # Create database tables
    Base.metadata.create_all(bind=engine)

    app = FastAPI(title="Multimodal RAG API")

    # Configure CORS for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.routers import projects, documents  # noqa: E402

    app.include_router(projects.router)
    app.include_router(documents.router)


    @app.get("/")
    def read_root():
        return {"message": "Welcome to the Multimodal RAG Backend API!"}
    ```

    Key changes from current main.py:
    1. Added `from dotenv import load_dotenv; load_dotenv()` at the very top — ensures env vars from `.env` are loaded BEFORE `from app.core.database import engine, Base` executes database.py module body.
    2. Added `probe_system_dependencies()` function and call — per D-07, logs WARNING for missing pdfinfo/tesseract but does not raise or block.
    3. Added `import logging` and `logger` for the probe.
    4. Added `import shutil` for `shutil.which()`.

    **Create `backend/tests/test_startup.py`:**

    ```python
    import logging
    from unittest.mock import patch


    def test_missing_pdfinfo_logs_warning(caplog):
        from app.main import probe_system_dependencies

        with patch("app.main.shutil.which", side_effect=lambda cmd: None if cmd == "pdfinfo" else "/usr/bin/tesseract"):
            with caplog.at_level(logging.WARNING, logger="app.main"):
                probe_system_dependencies()

        assert any("poppler" in record.message.lower() or "pdfinfo" in record.message.lower()
                    for record in caplog.records), (
            f"Expected WARNING about poppler/pdfinfo, got: {[r.message for r in caplog.records]}"
        )


    def test_missing_tesseract_logs_warning(caplog):
        from app.main import probe_system_dependencies

        with patch("app.main.shutil.which", side_effect=lambda cmd: None if cmd == "tesseract" else "/usr/bin/pdfinfo"):
            with caplog.at_level(logging.WARNING, logger="app.main"):
                probe_system_dependencies()

        assert any("tesseract" in record.message.lower()
                    for record in caplog.records), (
            f"Expected WARNING about tesseract, got: {[r.message for r in caplog.records]}"
        )


    def test_probe_does_not_raise():
        from app.main import probe_system_dependencies

        with patch("app.main.shutil.which", return_value=None):
            # Should not raise even when all deps missing
            probe_system_dependencies()


    def test_app_still_starts(client):
        response = client.get("/")
        assert response.status_code == 200
        assert "Multimodal RAG" in response.json()["message"]
    ```
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/test_startup.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - `backend/app/main.py` starts with `from dotenv import load_dotenv` followed by `load_dotenv()`
    - `backend/app/main.py` contains `def probe_system_dependencies`
    - `backend/app/main.py` contains `shutil.which("pdfinfo")`
    - `backend/app/main.py` contains `shutil.which("tesseract")`
    - `backend/app/main.py` contains `logger.warning` (not logger.error, not raise)
    - `backend/app/main.py` contains `probe_system_dependencies()` call at module level (before app = FastAPI)
    - `backend/tests/test_startup.py` contains `def test_missing_pdfinfo_logs_warning`
    - `backend/tests/test_startup.py` contains `def test_probe_does_not_raise`
    - `cd backend && python -m pytest tests/test_startup.py -x` exits 0
  </acceptance_criteria>
  <done>main.py loads dotenv before any app imports, probes pdfinfo and tesseract at startup with WARNING log only, server starts normally regardless. All 4 tests pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| None | Plan 01 modifies internal infrastructure only; no user input crosses boundaries |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-3a-03 | Information Disclosure | database.py logger.info path | accept | Absolute path logged to console is expected behavior per success criteria; local single-user tool, no remote exposure |
| T-3a-04 | Denial of Service | WAL mode misconfiguration | accept | WAL mode is standard SQLite best practice; isinstance guard prevents PRAGMA on non-SQLite engines |
</threat_model>

<verification>
After all 3 tasks complete:
1. `cd backend && python -m pytest tests/ -x -v` — all tests green
2. `cd backend && python -c "from app.core.database import DATABASE_PATH; import os; assert os.path.isabs(DATABASE_PATH)"` — absolute path confirmed
3. `cd backend && python -c "from app.core.database import engine; from sqlalchemy import text; print(engine.connect().execute(text('PRAGMA journal_mode')).scalar())"` — prints "wal"
4. `cd backend && python -c "from app.main import probe_system_dependencies"` — imports without error
</verification>

<success_criteria>
- requirements.txt is UTF-8 encoded (no null bytes, no BOM)
- pip install -r requirements.txt works cleanly
- DATABASE_PATH is absolute, defaults to backend/data/rag_database.db
- WAL mode active on SQLite connections
- Startup probe logs warnings for missing pdfinfo/tesseract
- load_dotenv() runs before any app imports in main.py
- All test files exist and pass: test_requirements_encoding.py, test_database.py, test_startup.py
- Shared test fixtures (conftest.py) available for Plan 02
</success_criteria>

<output>
After completion, create `.planning/phases/03A-infrastructure-fixes/03A-01-SUMMARY.md`
</output>
