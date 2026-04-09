# Phase 3a: Infrastructure Fixes - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 8 known infrastructure blockers so the RAG pipeline (Phases 3b+) has a stable foundation. No new features — only stabilizing existing code paths: absolute DB paths, WAL mode, lazy loading, background task safety, upload validation, encoding fix, and system dependency probes.

</domain>

<decisions>
## Implementation Decisions

### Path Configuration
- **D-01:** ChromaDB and SQLite paths must use env vars (`CHROMADB_PATH`, `DATABASE_PATH`) with `__file__`-relative defaults pointing to `backend/data/` directory.
- **D-02:** Default data directory is `backend/data/` — keeps DB files together, out of the source tree. Directory auto-created at startup if missing.
- **D-03:** Env var names: `CHROMADB_PATH` for ChromaDB persistence, `DATABASE_PATH` for SQLite database.

### Upload Validation
- **D-04:** Validate file extension and Content-Type BEFORE saving to disk. If invalid, return 400 immediately without writing to disk.
- **D-05:** File size limit is 100MB as specified in REQUIREMENTS.md. Return 413 for oversized files.
- **D-06:** Extension whitelist: `.pdf`, `.docx`, `.pptx`, `.xlsx` — case-insensitive check.

### Startup Probes
- **D-07:** Missing poppler/tesseract produces a clear WARNING log at startup but does NOT block server startup. Server runs normally — parsing will fail later when a PDF is uploaded, but the rest of the app works fine.

### Claude's Discretion
- **D-08:** INFRA-03 (SQLite WAL mode) — Enable WAL via `PRAGMA journal_mode=WAL` event listener on engine connect. Standard approach.
- **D-09:** INFRA-04 (Lazy embedding loading) — Replace module-level `default_embeddings` singleton with a lazy-loading pattern (e.g., `_model = None; def get_default_embeddings()` or similar). Model loaded on first call, not at import time.
- **D-10:** INFRA-05 (Background task sessions) — `process_and_update_document` already receives scalar `document_id` and creates its own `SessionLocal()`. Fix: eager-load the `folder` relationship or query `project_id` separately to avoid `DetachedInstanceError` on `db_document.folder.project_id`.
- **D-11:** INFRA-07 (requirements.txt encoding) — Convert from UTF-16 LE to UTF-8. One-time fix.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements
- `.planning/REQUIREMENTS.md` — INFRA-01 through INFRA-08 acceptance criteria
- `.planning/ROADMAP.md` §Phase 3a — Success criteria and estimated scope

### Research
- `.planning/research/SUMMARY.md` §Critical Blockers — 8 blockers with file locations and fix descriptions
- `.planning/research/PITFALLS.md` — Pitfalls #5 (system deps), #10 (concurrent writes), #14 (WAL mode)

### Codebase Maps
- `.planning/codebase/CONVENTIONS.md` — Singleton pattern, factory pattern, error handling conventions
- `.planning/codebase/CONCERNS.md` — Known issues mapped to INFRA requirements

</canonical_refs>

<code_context>
## Existing Code Insights

### Files to Modify
- `backend/app/services/vector_store.py:5` — `CHROMADB_DIR = os.path.join(os.getcwd(), "chroma_db")` → env var + `__file__`-relative default to `backend/data/chroma_db`
- `backend/app/core/database.py:4` — `SQLALCHEMY_DATABASE_URL = "sqlite:///./rag_database.db"` → env var + `__file__`-relative default to `backend/data/rag_database.db`
- `backend/app/services/embeddings.py:28` — `default_embeddings = EmbeddingFactory.get_embedding_model("local")` → lazy-load pattern
- `backend/app/services/document_parser.py:78` — `db_document.folder.project_id` lazy-load risk → eager-load or separate query
- `backend/app/routers/documents.py` — No validation → add extension whitelist + size limit before disk write
- `backend/requirements.txt` — UTF-16 LE → convert to UTF-8

### Established Patterns
- **Factory pattern:** `EmbeddingFactory`, `LLMProviderFactory` — continue using for provider abstraction
- **Singleton pattern:** Module-level instances (`vector_store`, `default_embeddings`) — shift to lazy singletons where needed
- **Dependency injection:** `Depends(get_db)` for DB sessions — keep for request-scoped sessions
- **Error handling:** `HTTPException` with i18n messages via `t()` function — reuse for validation errors
- **Background tasks:** Already use `SessionLocal()` directly — pattern is correct, just needs eager-load fix

### Integration Points
- `database.py` engine is imported by `SessionLocal` users across the app — WAL event must be on the engine itself
- `embeddings.py` `default_embeddings` is imported by `vector_store.py` — lazy pattern must be import-compatible
- `documents.py` upload endpoint is the single entry point for all file uploads

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for all fixes. User confirmed recommended options for all three discussed areas.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03A-infrastructure-fixes*
*Context gathered: 2026-04-09*
