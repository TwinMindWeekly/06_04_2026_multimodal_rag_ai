# Requirements — Multimodal RAG AI

**Project:** Multimodal RAG AI
**Created:** 2026-04-09
**Source:** PROJECT.md active requirements + research synthesis
**Scope:** v1 milestone (RAG pipeline + Chat API)

---

## Requirement Categories

### INFRA — Infrastructure Fixes (Blockers)

| REQ-ID | Requirement | Source | Priority | Phase |
|--------|-------------|--------|----------|-------|
| INFRA-01 | ChromaDB persistence path must be absolute (not CWD-relative) | CONCERNS #8 | MUST | 3a |
| INFRA-02 | SQLite database path must be configurable via env var with absolute default | CONCERNS #7 | MUST | 3a |
| INFRA-03 | SQLite WAL mode must be enabled at connection init to prevent "database is locked" errors | PITFALLS #14 | MUST | 3a |
| INFRA-04 | Embedding model must lazy-load on first use (not at module import) | CONCERNS #12 | MUST | 3a |
| INFRA-05 | Background tasks must receive scalar IDs only, create own DB session, eager-load relationships | CONCERNS #10 | MUST | 3a |
| INFRA-06 | File upload must validate extension whitelist (pdf, docx, pptx, xlsx) and enforce size limit (100MB) | CONCERNS #5 | MUST | 3a |
| INFRA-07 | requirements.txt must be UTF-8 encoded | CONCERNS #11 | MUST | 3a |
| INFRA-08 | System dependency probe at startup: `shutil.which("pdfinfo")` and `shutil.which("tesseract")` with clear warning log | PITFALLS #5 | MUST | 3a |

### PARSE — Document Parsing

| REQ-ID | Requirement | Source | Priority | Phase |
|--------|-------------|--------|----------|-------|
| PARSE-01 | Parse PDF, DOCX, PPTX, XLSX using `unstructured[pdf,docx,pptx,xlsx]` with `strategy="auto"` | RAG-04 | MUST | 3b |
| PARSE-02 | Extract embedded images from PDF and PPTX as separate elements with file paths | RAG-05 | MUST | 3b |
| PARSE-03 | Summarize extracted images via Gemini Vision API with retry logic (tenacity, exponential backoff) | RAG-06 | MUST | 3b |
| PARSE-04 | On image summarization failure after retries, store placeholder text and continue (do not fail entire document) | PITFALLS #13 | MUST | 3b |
| PARSE-05 | Preserve element metadata from unstructured (page_number, element_type, filename) through the pipeline | ARCHITECTURE | MUST | 3b |

### CHUNK — Text Chunking

| REQ-ID | Requirement | Source | Priority | Phase |
|--------|-------------|--------|----------|-------|
| CHUNK-01 | Chunk text using RecursiveCharacterTextSplitter with chunk_size=512, chunk_overlap=64, add_start_index=True | RAG-07, STACK | MUST | 3b |
| CHUNK-02 | Each chunk must carry metadata: document_id, filename, page_number, chunk_index, element_type | ARCHITECTURE | MUST | 3b |
| CHUNK-03 | Image summaries must be chunked and embedded as text alongside document text chunks | RAG-06 | MUST | 3b |

### EMBED — Embedding & Vector Store

| REQ-ID | Requirement | Source | Priority | Phase |
|--------|-------------|--------|----------|-------|
| EMBED-01 | Default embedding: all-MiniLM-L6-v2 via sentence-transformers (free, local, no API key) | RAG-02, RAG-08 | MUST | 3c |
| EMBED-02 | Switchable to OpenAI text-embedding-3-small or Google text-embedding-004 via Settings UI | RAG-08 | MUST | 3c |
| EMBED-03 | Store embedding provider name and model ID in ChromaDB collection metadata at creation | PITFALLS #2 | MUST | 3c |
| EMBED-04 | Block queries when active embedding provider mismatches collection's recorded provider; surface clear error | PITFALLS #2 | MUST | 3c |
| EMBED-05 | Provide re-index endpoint that deletes all vectors for a project and re-runs full embedding pipeline | STACK | MUST | 3c |
| EMBED-06 | Serialize ChromaDB writes per collection using per-project lock to prevent concurrent write corruption | PITFALLS #10 | MUST | 3c |

### SEARCH — Semantic Search

| REQ-ID | Requirement | Source | Priority | Phase |
|--------|-------------|--------|----------|-------|
| SEARCH-01 | Semantic search endpoint returning Top-K chunks with distances and metadata | RAG-09 | MUST | 3c |
| SEARCH-02 | Score threshold filter: discard chunks below similarity threshold before passing to LLM | STACK, FEATURES | MUST | 3c |
| SEARCH-03 | MMR (Maximal Marginal Relevance) or deduplication to avoid returning overlapping chunks | PITFALLS #11 | SHOULD | 3c |

### CHAT — Chat API

| REQ-ID | Requirement | Source | Priority | Phase |
|--------|-------------|--------|----------|-------|
| CHAT-01 | POST /api/chat endpoint accepting message, project_id, provider settings | CHAT-01 | MUST | 4a |
| CHAT-02 | RAG chain: embed query → ChromaDB search → build context string with citation markers | CHAT-02 | MUST | 4a |
| CHAT-03 | Context-augmented prompt template using ChatPromptTemplate (not RetrievalQA) | CHAT-02, STACK | MUST | 4a |
| CHAT-04 | SSE streaming via FastAPI StreamingResponse with headers: X-Accel-Buffering=no, Cache-Control=no-cache | CHAT-04 | MUST | 4a |
| CHAT-05 | SSE format: `data: {"text": "..."}\n\n` for chunks, `data: {"done": true, "citations": [...]}\n\n` for terminal event | ARCHITECTURE | MUST | 4a |
| CHAT-06 | Error events mid-stream: `data: {"error": "..."}\n\n` instead of silent connection drop | PITFALLS #7 | MUST | 4a |
| CHAT-07 | Citation metadata forwarding: page_number, filename, chunk_index per cited source | CHAT-03 | MUST | 4a |

### UI — Frontend Chat Integration

| REQ-ID | Requirement | Source | Priority | Phase |
|--------|-------------|--------|----------|-------|
| UI-01 | SSE client using fetch + ReadableStream (NOT EventSource — GET-only limitation) | CHAT-05, STACK | MUST | 4b |
| UI-02 | Parse SSE data events and append text to message buffer incrementally (typing effect) | CHAT-05 | MUST | 4b |
| UI-03 | Render citations from terminal SSE event with filename and page number | CHAT-05 | MUST | 4b |
| UI-04 | Load provider and credential settings from SettingsPanel state into chat request body | CHAT-06 | MUST | 4b |

### TEST — Validation

| REQ-ID | Requirement | Source | Priority | Phase |
|--------|-------------|--------|----------|-------|
| TEST-01 | E2E test: Upload PDF → verify chunks in ChromaDB → chat query → verify streamed response with citations | TEST-01 | MUST | 5 |
| TEST-02 | Unit test: ChromaDB metadata round-trip (insert chunk with metadata, query, assert all fields survive) | PITFALLS #4 | SHOULD | 5 |
| TEST-03 | Integration test: Embedding provider switch triggers re-index, not silent corruption | PITFALLS #2 | SHOULD | 5 |

---

## Out of Scope (v2+)

| Feature | Reason |
|---------|--------|
| OCR for scanned PDFs | `strategy="auto"` handles basic cases; hi_res OCR is a v2 optimization |
| Table extraction / structured parsing | Beyond v1 scope |
| Hybrid search (BM25 + vector) | ChromaDB doesn't support BM25; future enhancement |
| Query rewriting / HyDE | Optimization, not baseline |
| Conversation history / multi-turn | Single-turn RAG is sufficient for v1 |
| text-embedding-3-large | 6.5x cost, marginal quality gain over small |
| Authentication / authorization | Single-user local tool |

---

## Traceability

| PROJECT.md Req | Maps To |
|----------------|---------|
| RAG-04 | PARSE-01 |
| RAG-05 | PARSE-02 |
| RAG-06 | PARSE-03, PARSE-04, CHUNK-03 |
| RAG-07 | CHUNK-01, CHUNK-02 |
| RAG-08 | EMBED-01, EMBED-02, EMBED-03, EMBED-04, EMBED-05 |
| RAG-09 | SEARCH-01, SEARCH-02, SEARCH-03 |
| CHAT-01 | CHAT-01 |
| CHAT-02 | CHAT-02, CHAT-03 |
| CHAT-03 | CHAT-07 |
| CHAT-04 | CHAT-04, CHAT-05, CHAT-06 |
| CHAT-05 | UI-01, UI-02, UI-03 |
| CHAT-06 | UI-04 |
| TEST-01 | TEST-01, TEST-02, TEST-03 |
| CONCERNS #5,7,8,10,11,12 | INFRA-01 through INFRA-08 |

---

*38 requirements total: 35 MUST, 3 SHOULD. All traced to PROJECT.md or research findings.*
