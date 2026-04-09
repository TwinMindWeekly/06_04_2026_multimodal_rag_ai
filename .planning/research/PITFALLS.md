# Domain Pitfalls: Multimodal RAG AI

**Domain:** Multimodal RAG pipeline added to existing FastAPI/React app
**Researched:** 2026-04-09
**Confidence:** HIGH (confirmed against known codebase issues in CONCERNS.md + domain knowledge)

---

## Critical Pitfalls

Mistakes that cause silent data corruption, retrieval failures, or rewrites.

---

### Pitfall 1: Chunking Size Mismatch With Embedding Model Context Window

**What goes wrong:** Chunks are sized to what "feels right" (e.g., 1000 chars) without checking the embedding model's actual token limit. `all-MiniLM-L6-v2` has a 256-token limit (roughly 800-900 characters). Chunks larger than this are silently truncated by the model — the tail of the chunk is discarded with no error. The embedding is produced for only the first 256 tokens, but the full chunk text is stored in ChromaDB. Retrieval returns chunks whose stored text does not match what was actually embedded.

**Why it happens:** LangChain's `RecursiveCharacterTextSplitter` works in characters, not tokens. `chunk_size=1000` looks reasonable but is ~25% over the model's hard limit.

**Consequences:** Retrieved chunks appear relevant to the query vector but their stored text contains irrelevant tail content. Answer quality degrades silently — no exception is raised anywhere.

**Prevention:**
- Size chunks to stay within 80% of the embedding model's token limit to leave headroom for tokenizer differences.
- For `all-MiniLM-L6-v2`: `chunk_size=512`, `chunk_overlap=64` (characters), which maps to roughly 150-180 tokens.
- For OpenAI `text-embedding-3-small`: limit is 8191 tokens; `chunk_size=1500` chars is safe.
- Add a token-count assertion in the chunking pipeline as a fast-fail guard.

**Warning signs:** Retrieval returns chunks but answers ignore content from the second half of documents. Embedding time per chunk is suspiciously uniform regardless of chunk length variation.

**Phase:** RAG-07 (chunking implementation) — must be resolved before any embedding work.

---

### Pitfall 2: Embedding Model Mismatch Between Indexing and Querying

**What goes wrong:** Documents are indexed with one embedding model (e.g., `all-MiniLM-L6-v2`, 384 dimensions), then a user switches to OpenAI embeddings in settings (1536 dimensions). The query vector dimension does not match the stored vectors. ChromaDB raises a dimension mismatch error at query time, or — worse — silently returns garbage similarity scores if the collection was created without dimension enforcement.

**Why it happens:** This project's ChromaDB uses per-project collections (RAG-01, good isolation), but the collection is created once at first document upload and its embedding dimension is fixed at creation. If the user changes the embedding provider in Settings, the collection is now dimensionally incompatible.

**Consequences:** The entire project's vector store becomes unusable after a provider switch. No data is lost from SQLite, but all vectors must be re-embedded to recover.

**Prevention:**
- Store the embedding provider name and model ID in the ChromaDB collection metadata at creation time.
- At query time, assert that the active embedding config matches the collection's recorded config. If mismatched, surface a clear error: "This project was indexed with X. Re-index to switch to Y."
- Add a re-index endpoint that deletes all vectors for a project and re-runs the full embedding pipeline.
- Never allow the embedding factory to silently fall back to a different model.

**Warning signs:** User changes Settings provider; subsequent queries return `InvalidDimensionException` or zero results.

**Phase:** RAG-08 (switchable embeddings) — design the re-index path before exposing provider switching in UI.

---

### Pitfall 3: ChromaDB Persistence Path Is CWD-Relative

**What goes wrong:** `os.path.join(os.getcwd(), "chroma_db")` resolves to different directories depending on where the FastAPI process is started. Running `uvicorn` from `/backend` creates `chroma_db` there; running from `/` creates it at root. On restart from a different directory, ChromaDB finds no existing data and starts fresh, appearing to have lost all indexed documents.

**Why it happens:** Already confirmed in CONCERNS.md item #8. A CWD-relative path is silent and context-sensitive.

**Consequences:** Intermittent "no documents indexed" bugs that are hard to reproduce. In the worst case, a developer starts the server from a different shell directory and silently creates a second empty ChromaDB store, causing confusion about which store is active.

**Prevention:**
- Use `__file__`-relative or env-var-based absolute paths: `Path(__file__).parent.parent / "chroma_db"`.
- Expose `CHROMA_DB_PATH` as an environment variable with a sensible default.
- Apply the same fix to `sqlite:///./rag_database.db` (CONCERNS.md item #7) at the same time.
- Log the resolved absolute path at server startup so it is visible in console output.

**Warning signs:** "Document shows as processed but search returns nothing" after server restart from a different directory.

**Phase:** Phase 3 (RAG pipeline) — fix before any real documents are indexed.

---

### Pitfall 4: ChromaDB Metadata Filtering Silently Fails on Non-String Types

**What goes wrong:** ChromaDB metadata values must be `str`, `int`, `float`, or `bool`. Storing `None`, `list`, `dict`, or `datetime` objects in metadata causes either a silent drop of the field or a runtime error at add time. Additionally, metadata filter operators (`$eq`, `$in`, `$gte`) only work on indexed metadata keys that were present at document-add time — a key added to some chunks but not others cannot be reliably filtered.

**Why it happens:** Python dicts accept anything; the ChromaDB client does not validate types until the gRPC/HTTP call is made.

**Consequences:** Citation metadata (page number, filename, section) is lost or un-filterable. Semantic search returns results but citation rendering has missing fields.

**Prevention:**
- Define a strict `ChunkMetadata` TypedDict or Pydantic model: `document_id: str`, `page: int`, `filename: str`, `chunk_index: int`.
- Sanitize before insertion: convert `None` to `""`, coerce types explicitly.
- All chunks must include the same metadata keys. Missing keys break `$where` filters.
- Write a unit test that inserts a known document and asserts all metadata fields survive a round-trip query.

**Warning signs:** Citation display shows "undefined" or empty page numbers despite the metadata being set during ingestion.

**Phase:** RAG-03 (ingestion pipeline) and RAG-09 (semantic search) — enforce schema at ingestion.

---

### Pitfall 5: Unstructured.io System Dependencies Not Present on Target Machine

**What goes wrong:** `unstructured[all-docs]` requires `poppler` (for PDF page rendering), `tesseract-ocr` (for OCR), `libmagic`, and `pandoc`. On Windows (the confirmed dev OS), none of these are installed via `pip`. The `unstructured` Python package installs without error even when system deps are missing; the failure happens at runtime when a PDF is first processed.

**Why it happens:** Python packaging cannot enforce OS-level binary dependencies. The current code already has unstructured imports commented out (CONCERNS.md item #1) precisely because of this.

**Consequences:** The parser raises `FileNotFoundError` or `PDFPageCountError` at document processing time, the background task fails silently, and the document is marked as "failed" with no useful message to the user.

**Prevention:**
- On Windows: install `poppler` via `conda install poppler` or via the pre-built binary from `poppler-windows`. Add `tesseract` via the official UB Mannheim installer. Add both to PATH.
- Provide a `scripts/setup_deps.ps1` (Windows) and `scripts/setup_deps.sh` (Linux/Mac) that checks for and installs system dependencies.
- At application startup, run a dependency probe: `shutil.which("pdfinfo")` for poppler and `shutil.which("tesseract")`. Log a clear warning if either is missing before any upload is possible.
- Use `partition_pdf(filename, strategy="fast")` first and fall back to `strategy="hi_res"` (which requires OCR) only when needed.

**Warning signs:** Document upload succeeds (HTTP 200) but document status never leaves "processing". Background task logs show `poppler not found` or similar.

**Phase:** RAG-04 (real document parsing) — resolve system deps before writing any parsing code.

---

### Pitfall 6: Background Task DB Session Detached Instance Error

**What goes wrong:** FastAPI background tasks run after the HTTP response is returned. The SQLAlchemy `Session` from the request is closed before the background task accesses it. Accessing `db_document.folder.project_id` (line 81 of `document_parser.py`, confirmed in CONCERNS.md item #10) triggers a lazy load on a closed session, raising `sqlalchemy.orm.exc.DetachedInstanceError`.

**Why it happens:** SQLAlchemy's default lazy loading defers relationship queries. The relationship is not populated while the session is open during the request, and by the time the background task runs, the session is gone.

**Consequences:** Document processing silently crashes. The document stays in "processing" state forever. ChromaDB vectors are never written. The user sees no error.

**Prevention:**
- In the background task function, do NOT pass the request's `db` session. Create a fresh `SessionLocal()` scoped to the task, and close it in a `finally` block.
- Before passing any ORM object to the background task, extract all needed scalar values (IDs, paths) while the request session is still open: pass `document_id: int` not the ORM object.
- The background task then does its own `db.query(Document).options(joinedload(Document.folder).joinedload(Folder.project)).filter(Document.id == document_id).first()` with eager loading.
- Never pass SQLAlchemy ORM objects across session boundaries.

**Warning signs:** `DetachedInstanceError` in background task logs; documents permanently stuck in "processing" status.

**Phase:** RAG-03 (ingestion pipeline) — fix the existing background task pattern before adding real parsing.

---

### Pitfall 7: SSE Streaming Breaks Due to Missing Headers or Buffering

**What goes wrong:** FastAPI `StreamingResponse` with `media_type="text/event-stream"` works in isolation but fails in production-like setups. Three common failure modes: (1) Nginx or any reverse proxy buffers the entire response body before forwarding, defeating streaming. (2) The browser's `EventSource` API rejects SSE if the `Content-Type` is not exactly `text/event-stream` with no extra parameters. (3) LLM provider `async` generators are not properly awaited, causing the generator to yield all chunks at once after completion rather than incrementally.

**Why it happens:** SSE is HTTP-level streaming and every layer in the stack must opt in. FastAPI does not set `X-Accel-Buffering: no` automatically. Frontend `EventSource` does not support custom headers (Authorization), which matters when adding auth later.

**Consequences:** The streaming endpoint returns HTTP 200 but the frontend receives all text at once at the end — the "typing effect" does not work. Alternatively, the connection hangs until timeout if an exception occurs mid-stream without proper error event emission.

**Prevention:**
- Set response headers explicitly: `X-Accel-Buffering: no`, `Cache-Control: no-cache`, `Connection: keep-alive`.
- Format each SSE chunk correctly: `data: {json}\n\n` — two newlines are required as the message terminator.
- Send a terminal event when the stream ends: `data: [DONE]\n\n` so the frontend knows to close the connection.
- Wrap the generator in a `try/except` and emit `data: {"error": "..."}\n\n` on failure — never let an unhandled exception silently drop the connection.
- For LLM provider streaming, verify the provider's async generator actually yields incrementally (test with `curl --no-buffer`).
- On the frontend, use `fetch()` with `ReadableStream` instead of `EventSource` — `EventSource` cannot send POST bodies or custom headers, which are needed to pass provider credentials.

**Warning signs:** `curl -N http://localhost:8000/api/chat` returns all text at once after a delay; typing effect does not appear in browser.

**Phase:** CHAT-04 (SSE streaming) — test with `curl --no-buffer` before connecting the frontend.

---

### Pitfall 8: Embedding Model Loaded at Import Time — OOM on Cold Start

**What goes wrong:** `default_embeddings = EmbeddingFactory.get_embedding_model("local")` at module import time (confirmed in CONCERNS.md item #12) loads the 80MB+ `all-MiniLM-L6-v2` model into RAM immediately when the backend starts, regardless of whether any embedding is needed. Combined with ChromaDB's own memory footprint and SQLAlchemy connection pool, cold start RAM usage exceeds 500MB before any user request arrives.

**Why it happens:** Module-level singleton initialization is a common shortcut that becomes a problem when the object is expensive to construct.

**Consequences:** On machines with limited RAM (common for a local-first tool), the server is slow to start or OOM-kills. If multiple embedding models are pre-loaded (local + OpenAI fallback), this multiplies. Also makes unit testing painful — every test that imports the module triggers a 3-5 second model download/load.

**Prevention:**
- Use lazy initialization: wrap in a `functools.cached_property` or a `get_default_embeddings()` function that initializes on first call.
- Never instantiate expensive resources at module scope.
- For testing, allow the embedding model to be overridden via dependency injection or an env var `EMBEDDING_MODEL=mock`.

**Warning signs:** Server startup takes >5 seconds; RAM usage shown in logs is >400MB before the first request; tests that import `embeddings.py` are slow.

**Phase:** RAG-08 (switchable embeddings) — fix lazy loading before adding additional providers.

---

### Pitfall 9: Large File Upload Blocks the Event Loop

**What goes wrong:** FastAPI is async but `await file.read()` on a large upload (50MB+ PDF) reads the entire file into memory in one synchronous chunk inside the async handler. This blocks the Python event loop for the duration of the read, preventing other concurrent requests from being served.

**Why it happens:** `UploadFile.read()` is a coroutine that wraps a sync file read. The underlying I/O is not truly non-blocking for large payloads.

**Consequences:** Uploading a large document makes all other API endpoints unresponsive for seconds. On a single-user local tool this is tolerable, but it also means RAM spikes to 2× the file size (once for the upload buffer, once for the write).

**Prevention:**
- Stream large files in chunks using `file.read(chunk_size)` in a loop and write to disk incrementally.
- Move the file-write operation to `asyncio.get_event_loop().run_in_executor(None, sync_write_fn)` to keep it off the event loop.
- Enforce a file size limit at the upload endpoint (e.g., 100MB max) with a clear HTTP 413 error. This is already identified as missing in CONCERNS.md item #5.
- Store only the file path in the DB immediately; all heavy processing (parsing, embedding) happens in the background task.

**Warning signs:** UI freezes during upload; other API calls (project list, etc.) time out while a large file is uploading.

**Phase:** RAG-04 (real parsing) — fix upload handling before wiring in unstructured.io processing.

---

### Pitfall 10: ChromaDB Collection Corruption on Concurrent Writes

**What goes wrong:** ChromaDB's local persistence mode (DuckDB+Parquet in older versions, SQLite in newer) is not safe for concurrent writes from multiple threads. If two background tasks simultaneously embed chunks from two documents in the same project (same collection), writes can corrupt the collection index.

**Why it happens:** FastAPI's background tasks run in a thread pool. Multiple uploads triggered in quick succession will spawn concurrent background tasks. Each calls `collection.add(...)` on the same ChromaDB collection without locking.

**Consequences:** ChromaDB collection becomes inconsistent. Queries return incorrect results or raise internal errors. Recovery requires deleting and re-indexing the entire collection.

**Prevention:**
- Serialize ChromaDB writes per collection using an `asyncio.Lock` keyed by `project_id` (a `dict[str, asyncio.Lock]`).
- Alternatively, process background tasks for a given project sequentially using a per-project queue.
- For the current single-user local tool scope, a global `threading.Lock` around all ChromaDB write operations is a simple safe choice.

**Warning signs:** Indexing multiple documents simultaneously results in fewer chunks in ChromaDB than expected; queries return `IndexError` or zero results after bulk uploads.

**Phase:** RAG-03 (ingestion pipeline) — add write serialization before any concurrent upload testing.

---

## Moderate Pitfalls

### Pitfall 11: Chunk Overlap Creates Duplicate Retrieval Results

**What goes wrong:** With `chunk_overlap=200` characters, adjacent chunks share 200 characters of content. A semantic query retrieves Top-K chunks; if the query maps to a boundary region, multiple overlapping chunks are returned. The LLM receives nearly identical content multiple times, wasting context window space and producing redundant citations.

**Prevention:** After retrieval, deduplicate chunks by checking if the start of one chunk is contained within the text of a previous chunk. Alternatively, use MMR (Maximal Marginal Relevance) retrieval in LangChain's ChromaDB wrapper, which penalizes redundant results by design.

**Phase:** RAG-09 (semantic search) — add deduplication in the retrieval post-processing step.

---

### Pitfall 12: requirements.txt UTF-16 Encoding Breaks pip on Linux/Mac

**What goes wrong:** Already confirmed in CONCERNS.md item #11. `pip install -r requirements.txt` silently fails or raises `UnicodeDecodeError` on non-Windows systems because pip expects UTF-8.

**Prevention:** Convert the file: `python -c "open('requirements.txt', 'w').write(open('requirements.txt', encoding='utf-16').read())"`. Verify with `file requirements.txt` (should report ASCII/UTF-8). Add a CI check or pre-commit hook that asserts requirements files are UTF-8.

**Phase:** Pre-phase — fix before any new dependency is added.

---

### Pitfall 13: Gemini Vision API Rate Limits During Batch Image Summarization

**What goes wrong:** A PPTX with 50 image slides triggers 50 sequential Gemini Vision API calls during ingestion. Free-tier Gemini has 15 RPM (requests per minute) rate limits. The batch fails partway through, leaving the document partially indexed with some image summaries and some gaps.

**Prevention:**
- Add exponential backoff with jitter around Vision API calls using `tenacity`.
- Process images in small batches (e.g., 5 at a time) with a delay between batches.
- If an image summary fails after retries, store a placeholder text (`"[Image: summary unavailable]"`) and continue — do not fail the entire document.
- Log which images succeeded and which failed so re-processing is possible without re-running the whole document.

**Phase:** RAG-06 (image summarization) — design retry logic before wiring Gemini Vision into the pipeline.

---

### Pitfall 14: SQLite WAL Mode Conflicts With Background Task Writes

**What goes wrong:** SQLAlchemy's default SQLite configuration uses synchronous journal mode. Background tasks write document status updates (`processing` → `completed` / `failed`) while the main request thread may be reading. Under concurrent access, this can produce `database is locked` errors.

**Prevention:**
- Enable WAL mode: add `connect_args={"check_same_thread": False}` and execute `PRAGMA journal_mode=WAL` on connection init. FastAPI SQLite apps consistently need this.
- Already partially mitigated if background tasks use their own `SessionLocal()` (see Pitfall 6), but WAL mode removes the shared-lock contention entirely.

**Phase:** Phase 3 start — verify WAL mode is enabled before background tasks are activated.

---

## Minor Pitfalls

### Pitfall 15: SSE EventSource Cannot Send POST Requests

**What goes wrong:** The browser's native `EventSource` API only supports GET requests. The chat endpoint needs to receive a POST body (message, project ID, provider settings). Teams commonly try to use `EventSource` for streaming and only discover this constraint when implementing auth or request bodies.

**Prevention:** Use `fetch()` with `ReadableStream` on the frontend. The pattern is well-established: `const response = await fetch('/api/chat', {method: 'POST', body: JSON.stringify(payload)}); const reader = response.body.getReader();`. This supports POST, custom headers, and is compatible with React 19's concurrent rendering.

**Phase:** CHAT-05 (frontend SSE parsing) — implement with `fetch` + `ReadableStream` from the start, not `EventSource`.

---

### Pitfall 16: Unstructured.io "hi_res" Strategy Is Extremely Slow

**What goes wrong:** `partition_pdf(filename, strategy="hi_res")` triggers full OCR on every page even when the PDF has selectable text. A 20-page PDF can take 2-3 minutes to parse with this strategy.

**Prevention:** Use `strategy="auto"` (default) which applies OCR only to pages that need it. For PDFs with selectable text, `strategy="fast"` is sufficient and takes seconds. Expose strategy as a configurable option rather than hardcoding.

**Phase:** RAG-04 (document parsing) — default to `"auto"` strategy.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| RAG-04: Real document parsing | System deps missing (poppler/tesseract) silently fail at runtime | Startup probe: `shutil.which("pdfinfo")` |
| RAG-07: Text chunking | Chunk size exceeds embedding model token limit (silent truncation) | Size to 80% of model limit; add token assertion |
| RAG-08: Switchable embeddings | Provider switch invalidates existing collection vectors | Store provider in collection metadata; force re-index on switch |
| RAG-03: Ingestion pipeline | Background task accesses detached ORM object | Pass only IDs to background tasks; open fresh DB session |
| RAG-03: Ingestion pipeline | Concurrent writes corrupt ChromaDB collection | Per-project asyncio.Lock on all collection.add() calls |
| CHAT-04: SSE streaming | Proxy buffering defeats streaming; wrong Content-Type | Set X-Accel-Buffering: no; test with curl --no-buffer |
| CHAT-05: Frontend streaming | EventSource cannot POST | Use fetch() + ReadableStream |
| RAG-06: Image summarization | Gemini Vision rate limit fails batch midway | Tenacity retry + placeholder on failure |
| RAG-08: Embedding lazy load | 500MB+ RAM at cold start | Lazy-initialize embedding model on first use |
| Phase 3 start | SQLite locked errors from concurrent background writes | Enable WAL mode at DB init |

---

## Sources

- Project codebase: `.planning/PROJECT.md` (architecture, tech decisions, active requirements)
- Confirmed known issues: `.planning/codebase/CONCERNS.md` (items #1, #5, #7, #8, #10, #11, #12)
- `all-MiniLM-L6-v2` token limit: 256 tokens (SBERT documentation, HIGH confidence)
- ChromaDB metadata type constraints: ChromaDB official docs, HIGH confidence
- FastAPI SSE pattern: FastAPI official docs + Starlette `StreamingResponse` docs, HIGH confidence
- SQLAlchemy `DetachedInstanceError` on background tasks: SQLAlchemy docs, HIGH confidence
- Unstructured.io system deps: unstructured.io official installation docs, HIGH confidence
- Gemini API rate limits (free tier 15 RPM): Google AI documentation, MEDIUM confidence (subject to change)
