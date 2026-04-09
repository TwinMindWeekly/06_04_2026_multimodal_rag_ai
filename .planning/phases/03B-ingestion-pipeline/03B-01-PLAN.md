---
phase: 03B-ingestion-pipeline
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/requirements.txt
  - backend/app/models/domain.py
  - backend/app/schemas/domain.py
  - backend/app/core/database.py
  - backend/app/services/vector_store.py
  - backend/tests/test_vector_store.py
autonomous: true
requirements: [CHUNK-02, PARSE-05]

must_haves:
  truths:
    - "Document model has a status column with default 'pending'"
    - "DocumentResponse schema includes status field"
    - "Existing SQLite DB gains status column via ALTER TABLE migration at startup"
    - "VectorStoreService can delete all vectors for a given document_id"
    - "All metadata values are sanitized to ChromaDB-compatible scalar types before insertion"
    - "unstructured and google-generativeai packages are in requirements.txt"
  artifacts:
    - path: "backend/app/models/domain.py"
      provides: "Document.status column"
      contains: "status = Column(String"
    - path: "backend/app/schemas/domain.py"
      provides: "DocumentResponse.status field"
      contains: "status: Optional[str]"
    - path: "backend/app/core/database.py"
      provides: "ALTER TABLE migration for status column"
      contains: "ALTER TABLE documents ADD COLUMN status"
    - path: "backend/app/services/vector_store.py"
      provides: "delete_by_document and _sanitize_metadata methods"
      exports: ["delete_by_document", "_sanitize_metadata"]
    - path: "backend/requirements.txt"
      provides: "New dependencies"
      contains: "unstructured"
  key_links:
    - from: "backend/app/core/database.py"
      to: "backend/app/models/domain.py"
      via: "ALTER TABLE adds column matching Document.status definition"
      pattern: "ALTER TABLE documents ADD COLUMN status"
    - from: "backend/app/services/vector_store.py"
      to: "chromadb"
      via: "collection.delete(where=...) for document removal"
      pattern: "collection\\.delete"
---

<objective>
Add foundational schema changes, new dependencies, and vector store capabilities needed by the ingestion pipeline.

Purpose: The parser rewrite (Plan 03) needs Document.status for pipeline state tracking, delete_by_document() for re-processing safety, and _sanitize_metadata() to prevent ChromaDB rejections. The new packages (unstructured, google-generativeai) must be installable before Plans 02 and 03 can run.

Output: Updated domain model with status column, migration-safe database startup, vector store with delete and sanitize capabilities, requirements.txt with new packages.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/03B-ingestion-pipeline/03B-CONTEXT.md
@.planning/phases/03B-ingestion-pipeline/03B-RESEARCH.md

<interfaces>
<!-- Current Document model from backend/app/models/domain.py -->
```python
class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_path = Column(String)
    folder_id = Column(Integer, ForeignKey("folders.id"))
    metadata_json = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    folder = relationship("Folder", back_populates="documents")
```

<!-- Current DocumentResponse from backend/app/schemas/domain.py -->
```python
class DocumentResponse(DocumentBase):
    id: int
    uploaded_at: datetime
    class Config:
        from_attributes = True
```

<!-- Current VectorStoreService from backend/app/services/vector_store.py -->
```python
class VectorStoreService:
    def __init__(self): ...
    def _get_collection_name(self, project_id: int): ...
    def insert_documents(self, text_chunks: list[str], metadatas: list[dict], project_id: int = None): ...
    def similarity_search(self, query: str, top_k: int = 4, project_id: int = None): ...

vector_store = VectorStoreService()
```

<!-- Current database.py startup from backend/app/core/database.py -->
```python
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
@event.listens_for(engine, "connect")
def _set_sqlite_wal_mode(dbapi_connection, connection_record): ...
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add dependencies + Document.status column + schema + migration</name>
  <files>backend/requirements.txt, backend/app/models/domain.py, backend/app/schemas/domain.py, backend/app/core/database.py</files>
  <read_first>
    - backend/requirements.txt
    - backend/app/models/domain.py
    - backend/app/schemas/domain.py
    - backend/app/core/database.py
  </read_first>
  <action>
**requirements.txt** — Append these two lines at the end (before the pytest lines):
```
unstructured[pdf,docx,pptx,xlsx]
google-generativeai
```

**backend/app/models/domain.py** — Add `status` column to Document class (per D-13):
```python
status = Column(String, default="pending", nullable=False)
```
Place it after `uploaded_at`. Import nothing new (String and Column already imported).

**backend/app/schemas/domain.py** — Add `status` to both `DocumentBase` and `DocumentResponse`:
In `DocumentBase`, add:
```python
status: Optional[str] = None
```
In `DocumentResponse`, add:
```python
status: Optional[str] = None
```
(The `Optional` import is already present.)

**backend/app/core/database.py** — Add a startup migration function that runs ALTER TABLE if the `status` column does not exist. Add this function after the `_set_sqlite_wal_mode` event listener and before `SessionLocal`:

```python
def _migrate_add_status_column(db_engine):
    """One-time migration: add status column to documents table if missing (per D-13, Pitfall 6)."""
    import sqlite3 as _sqlite3
    raw_url = str(db_engine.url).replace("sqlite:///", "")
    if not raw_url or not os.path.exists(raw_url):
        return
    conn = _sqlite3.connect(raw_url)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        if "status" not in columns:
            cursor.execute("ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'pending' NOT NULL")
            conn.commit()
            logger.info("Migrated: added 'status' column to documents table")
    except Exception as e:
        logger.warning("Migration check for status column failed: %s", e)
    finally:
        conn.close()

_migrate_add_status_column(engine)
```

This runs at import time (same as the existing module-level code) and is idempotent.
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/multimodal_rag_ai/backend && python -c "from app.models.domain import Document; assert hasattr(Document, 'status'); print('OK: Document.status exists')" && python -c "from app.schemas.domain import DocumentResponse; f = DocumentResponse.model_fields; assert 'status' in f; print('OK: DocumentResponse.status exists')" && python -c "import ast; tree = ast.parse(open('app/core/database.py').read()); funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]; assert '_migrate_add_status_column' in funcs; print('OK: migration function exists')"</automated>
  </verify>
  <acceptance_criteria>
    - backend/requirements.txt contains line "unstructured[pdf,docx,pptx,xlsx]"
    - backend/requirements.txt contains line "google-generativeai"
    - backend/app/models/domain.py contains `status = Column(String, default="pending", nullable=False)`
    - backend/app/schemas/domain.py DocumentBase contains `status: Optional[str] = None`
    - backend/app/schemas/domain.py DocumentResponse contains `status: Optional[str] = None`
    - backend/app/core/database.py contains function `_migrate_add_status_column`
    - backend/app/core/database.py contains `ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'pending' NOT NULL`
    - backend/app/core/database.py contains `_migrate_add_status_column(engine)` call
  </acceptance_criteria>
  <done>Document model has status column, DocumentResponse exposes it, migration handles existing DBs, new packages listed in requirements.txt</done>
</task>

<task type="auto">
  <name>Task 2: Add delete_by_document and _sanitize_metadata to VectorStoreService</name>
  <files>backend/app/services/vector_store.py, backend/tests/test_vector_store.py</files>
  <read_first>
    - backend/app/services/vector_store.py
    - backend/tests/test_vector_store.py
  </read_first>
  <action>
**backend/app/services/vector_store.py** — Add two new methods to VectorStoreService class and a module-level helper:

1. Add `_sanitize_metadata` as a module-level function (before the class, after imports). Per Pitfall 2 from RESEARCH.md — ChromaDB rejects None, list, dict metadata values:
```python
def _sanitize_metadata(meta: dict) -> dict:
    """Sanitize metadata for ChromaDB: only str/int/float/bool allowed."""
    result = {}
    for k, v in meta.items():
        if v is None:
            result[k] = ""
        elif isinstance(v, (str, int, float, bool)):
            result[k] = v
        else:
            result[k] = str(v)
    return result
```

2. Add `delete_by_document` method to VectorStoreService (after `insert_documents`, before `similarity_search`). Per D-15 — delete-then-insert for re-processing:
```python
def delete_by_document(self, document_id: int, project_id: int = None) -> None:
    """Delete all vectors for a given document_id from the collection. Per D-15."""
    collection_name = self._get_collection_name(project_id)
    try:
        collection = self.client.get_collection(name=collection_name)
        collection.delete(where={"document_id": str(document_id)})
        logger.info("Deleted vectors for document_id=%d from %s", document_id, collection_name)
    except Exception as e:
        logger.debug("No vectors to delete for document_id=%d: %s", document_id, e)
```
Note: `document_id` is cast to `str()` in the where clause because ChromaDB metadata will store document_id as string (per Pitfall 2 and Open Question 3 from RESEARCH.md — store as str for safe where-clause matching).

3. Update `insert_documents` to sanitize metadata before upsert. Replace the `collection.upsert(...)` call's `metadatas` parameter:
Change: `metadatas=metadatas,`
To: `metadatas=[_sanitize_metadata(m) for m in metadatas],`

**backend/tests/test_vector_store.py** — Add tests for the new methods. Read the existing file first, then append these test functions:

```python
def test_sanitize_metadata_removes_none():
    from app.services.vector_store import _sanitize_metadata
    result = _sanitize_metadata({"a": None, "b": "hello", "c": 42})
    assert result == {"a": "", "b": "hello", "c": 42}


def test_sanitize_metadata_converts_non_scalar():
    from app.services.vector_store import _sanitize_metadata
    result = _sanitize_metadata({"a": [1, 2], "b": {"nested": True}})
    assert result["a"] == "[1, 2]"
    assert result["b"] == "{'nested': True}"


def test_delete_by_document_no_collection_no_error():
    """delete_by_document should not raise if the collection does not exist."""
    from app.services.vector_store import VectorStoreService
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        from chromadb import PersistentClient
        svc = VectorStoreService.__new__(VectorStoreService)
        svc.client = PersistentClient(path=tmpdir)
        # Should not raise — collection doesn't exist
        svc.delete_by_document(document_id=999, project_id=1)
```
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/multimodal_rag_ai/backend && python -m pytest tests/test_vector_store.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - backend/app/services/vector_store.py contains `def _sanitize_metadata(meta: dict) -> dict:`
    - backend/app/services/vector_store.py contains `def delete_by_document(self, document_id: int, project_id: int = None) -> None:`
    - backend/app/services/vector_store.py contains `collection.delete(where={"document_id": str(document_id)})`
    - backend/app/services/vector_store.py insert_documents contains `_sanitize_metadata(m) for m in metadatas`
    - backend/tests/test_vector_store.py contains `test_sanitize_metadata_removes_none`
    - backend/tests/test_vector_store.py contains `test_sanitize_metadata_converts_non_scalar`
    - backend/tests/test_vector_store.py contains `test_delete_by_document_no_collection_no_error`
    - `python -m pytest tests/test_vector_store.py -x` exits 0
  </acceptance_criteria>
  <done>VectorStoreService has delete_by_document() for re-processing safety and all metadata is sanitized before ChromaDB insertion. Tests pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Parsed metadata -> ChromaDB | Metadata from unstructured elements inserted into ChromaDB; must be scalar-sanitized |
| Startup migration -> SQLite | ALTER TABLE runs on existing DB; static SQL, no user input |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-3b-01 | Tampering | _sanitize_metadata | mitigate | Sanitize all metadata values to str/int/float/bool before ChromaDB insert; None becomes empty string |
| T-3b-02 | Denial of Service | _migrate_add_status_column | accept | Static SQL with PRAGMA table_info guard; no user input; runs once at startup; wrapped in try/except |
</threat_model>

<verification>
- `python -c "from app.models.domain import Document; print(Document.status.default.arg)"` outputs `pending`
- `python -m pytest tests/test_vector_store.py -x -q` exits 0
- `grep -c "unstructured" requirements.txt` returns 1
- `grep -c "google-generativeai" requirements.txt` returns 1
</verification>

<success_criteria>
- Document.status column exists with default "pending"
- DocumentResponse schema includes status field
- ALTER TABLE migration runs safely on existing and new databases
- VectorStoreService.delete_by_document() removes vectors by document_id
- _sanitize_metadata() converts all values to ChromaDB-compatible scalar types
- New packages (unstructured, google-generativeai) listed in requirements.txt
- All existing + new tests pass
</success_criteria>

<output>
After completion, create `.planning/phases/03B-ingestion-pipeline/03B-01-SUMMARY.md`
</output>
