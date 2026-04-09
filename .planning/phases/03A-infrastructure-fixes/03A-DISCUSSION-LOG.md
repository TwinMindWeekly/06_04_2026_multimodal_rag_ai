# Phase 3a: Infrastructure Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 03A-infrastructure-fixes
**Areas discussed:** Path Configuration, Upload Validation, Startup Probes

---

## Path Configuration

| Option | Description | Selected |
|--------|-------------|----------|
| Env vars + __file__ defaults | CHROMADB_PATH and DATABASE_PATH env vars with sensible defaults using __file__-relative paths (e.g., backend/data/chroma_db, backend/data/rag_database.db). Simple, standard Python pattern. | ✓ |
| __file__-relative only | Always resolve relative to the backend/ directory using Path(__file__).resolve(). No env vars needed — deterministic regardless of CWD. | |
| .env config file | Add a .env file with all path settings. Load via python-dotenv (already installed). More configuration surface but centralized. | |

**User's choice:** Env vars + __file__ defaults (Recommended)
**Notes:** None

### Follow-up: Default data directory

| Option | Description | Selected |
|--------|-------------|----------|
| backend/data/ | backend/data/chroma_db and backend/data/rag_database.db — keeps DB files together, out of the source tree | ✓ |
| Backend root | backend/chroma_db and backend/rag_database.db — same as current layout but absolute | |
| Project root data/ | Project root data/ directory — visible from both frontend and backend | |

**User's choice:** backend/data/ (Recommended)
**Notes:** None

---

## Upload Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Validate before save | Check extension + Content-Type before saving. If invalid, return 400 immediately without writing to disk. Fast, saves disk I/O. | ✓ |
| Validate after save | Save file first, then validate. Delete if invalid. Simpler code but wastes I/O on rejected files. | |
| Magic bytes validation | Use python-magic to check actual file bytes (not just extension). More secure but adds a dependency. | |

**User's choice:** Validate before save (Recommended)
**Notes:** None

### Follow-up: File size limit

| Option | Description | Selected |
|--------|-------------|----------|
| 100MB | 100MB as specified in REQUIREMENTS.md (INFRA-06). Covers large PPTX/XLSX files comfortably. | ✓ |
| 50MB | 50MB — tighter limit, faster uploads, less memory pressure during parsing | |
| 200MB | 200MB — generous, handles very large enterprise documents | |

**User's choice:** 100MB (Recommended)
**Notes:** None

---

## Startup Probes

| Option | Description | Selected |
|--------|-------------|----------|
| Warning only | Log a clear WARNING at startup but let the server run. Parsing will fail later when a PDF is uploaded, but the rest of the app works fine. Best for dev experience. | ✓ |
| Warning + degraded mode flag | Log WARNING and set an internal flag. Upload endpoint checks the flag and returns 503 'parsing unavailable' if deps are missing. Fails fast at upload time with a clear message. | |
| Hard fail on startup | Refuse to start the server if system deps are missing. Strictest — guarantees parsing will work but blocks all development if deps aren't installed. | |

**User's choice:** Warning only (Recommended)
**Notes:** None

---

## Claude's Discretion

- INFRA-03 (WAL mode) — standard PRAGMA approach
- INFRA-04 (Lazy embedding) — replace module-level singleton with lazy pattern
- INFRA-05 (Background tasks) — fix eager-load on folder relationship
- INFRA-07 (requirements.txt) — convert UTF-16 to UTF-8

## Deferred Ideas

None — discussion stayed within phase scope.
