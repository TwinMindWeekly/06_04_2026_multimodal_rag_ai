# Phase 3b: Ingestion Pipeline - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Upload a real PDF/DOCX/PPTX/XLSX and produce properly chunked, metadata-rich vectors in ChromaDB. Covers: document parsing with unstructured.io, image extraction and summarization via Gemini Vision, text chunking with RecursiveCharacterTextSplitter, and end-to-end pipeline wiring. Image search, retrieval endpoints, and embedding provider switching are Phase 3c.

</domain>

<decisions>
## Implementation Decisions

### Document Parsing
- **D-01:** Use `unstructured[pdf,docx,pptx,xlsx]` with `strategy="auto"` — lets unstructured pick the best strategy per file type (hi_res for PDFs with images, fast for plain text).
- **D-02:** Preserve all element types from unstructured (Title, NarrativeText, ListItem, Table, Image, etc.) and map them to `element_type` metadata on each chunk.
- **D-03:** Extract images to a temporary directory during processing. Clean up temp files after Gemini summarization completes (or fails). No permanent image storage.
- **D-04:** Single `DocumentParserService` class with per-type methods (not separate parser classes). Major rewrite of existing stub in `document_parser.py`.

### Image Processing
- **D-05:** Use `google-generativeai` SDK directly (not LangChain wrapper) with `gemini-1.5-pro-latest` for image summarization. New service: `image_processor.py`.
- **D-06:** Retry with `tenacity`: 3 retries, exponential backoff (2s, 4s, 8s). Matches PARSE-03 requirement.
- **D-07:** Gemini API key via `GOOGLE_API_KEY` env var, validated at image processing time (not at startup). If missing when an image is encountered, store placeholder and log warning.
- **D-08:** On final failure after retries, store descriptive placeholder: `"[Image: unable to process - {filename}]"`. Document still marked complete per PARSE-04.

### Chunking & Metadata
- **D-09:** RecursiveCharacterTextSplitter with `chunk_size=512`, `chunk_overlap=64`, `add_start_index=True`. Confirmed from prior decision (safe for all-MiniLM-L6-v2 256-token limit).
- **D-10:** Each chunk carries metadata per CHUNK-02: `document_id`, `filename`, `page_number`, `chunk_index`, `element_type`. Extends current schema which lacks `page_number` and `element_type`.
- **D-11:** Image summaries chunked with the same splitter (512/64) and stored with `element_type="image_summary"`. Interleaved with text chunks at their original page position, not appended.

### Pipeline Wiring
- **D-12:** Expand existing `process_and_update_document()` background task to orchestrate: parse → extract images → summarize images → chunk all elements → embed into ChromaDB. No new orchestrator class.
- **D-13:** Add `status` column to Document model: `'pending'` → `'processing'` → `'completed'` or `'failed'`. Enables frontend polling.
- **D-14:** Fail per-step, continue where possible. Parsing failure → document marked `'failed'`. Image summarization failure → placeholder text, continue. Embedding failure → document marked `'failed'`.
- **D-15:** Re-processing a document: delete all existing vectors for that document in ChromaDB before re-inserting. Prevents duplicate chunks.

### Claude's Discretion
- Exact unstructured partition parameters beyond `strategy="auto"`
- Gemini Vision prompt wording for image summarization
- Temp directory naming convention and location
- Logging verbosity during pipeline steps

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements
- `.planning/REQUIREMENTS.md` — PARSE-01 through PARSE-05, CHUNK-01 through CHUNK-03 acceptance criteria
- `.planning/ROADMAP.md` §Phase 3b — Success criteria, estimated scope, dependencies

### Prior Phase Context
- `.planning/phases/03A-infrastructure-fixes/03A-CONTEXT.md` — Infrastructure decisions (ChromaDB path, lazy loading, eager-load fix, upload validation) that this phase builds on

### Research
- `.planning/research/SUMMARY.md` — Research synthesis including parsing strategy and chunking rationale
- `.planning/codebase/CONVENTIONS.md` — Factory pattern, singleton pattern, error handling conventions
- `.planning/codebase/STACK.md` — Current dependency versions (LangChain 1.2.15, ChromaDB 1.5.7, sentence-transformers 5.3.0)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/embeddings.py` — `EmbeddingFactory` + `get_default_embeddings()` lazy singleton: ready to use, no changes needed for 3b
- `backend/app/services/vector_store.py` — `VectorStoreService` with `insert_documents()` and `similarity_search()`: needs metadata schema expansion (add `page_number`, `element_type`)
- `backend/app/routers/documents.py` — Upload endpoint with validation (extension whitelist, size limit): already wired to `process_and_update_document()` background task
- `backend/app/core/i18n.py` — `t()` function for i18n error messages: reuse for any new user-facing errors

### Established Patterns
- **Factory pattern:** `EmbeddingFactory`, `LLMProviderFactory` — continue using for provider abstraction
- **Lazy singleton:** `get_default_embeddings()` with global guard — same pattern for any new singletons
- **Background tasks:** `SessionLocal()` with `try/finally` and `joinedload` — extend this pattern for expanded pipeline
- **Error handling:** `HTTPException` with i18n `t()` messages — reuse for validation errors

### Integration Points
- `document_parser.py:62` — `parser.parse_document()` called from `process_and_update_document()`: return value must change from mock to real parsed elements
- `vector_store.py:33` — `insert_documents()` receives `text_chunks` and `metadatas`: metadata dict schema needs `page_number` and `element_type` fields
- `documents.py:106` — `background_tasks.add_task(process_and_update_document, db_document.id)`: existing wiring stays, but background task logic expands significantly
- `models/domain.py` — `Document` model: needs `status` column added (`pending`/`processing`/`completed`/`failed`)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User confirmed recommended options for all discussed areas.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03B-ingestion-pipeline*
*Context gathered: 2026-04-09*
