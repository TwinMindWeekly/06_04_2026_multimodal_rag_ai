# Roadmap — Multimodal RAG AI

**Project:** Multimodal RAG AI
**Created:** 2026-04-09
**Milestone:** RAG Pipeline + Chat API (v1)
**Source:** REQUIREMENTS.md (38 requirements), research synthesis

---

## Phase Overview

| Phase | Name | Goal | Requirements | Depends On |
|-------|------|------|-------------|------------|
| 3a | Infrastructure Fixes | Stable foundation for RAG pipeline | INFRA-01..08 | — |
| 3b | Ingestion Pipeline | Real document parsing → chunking → ChromaDB | PARSE-01..05, CHUNK-01..03 | 3a |
| 3c | Retrieval | Switchable embeddings + semantic search endpoint | EMBED-01..06, SEARCH-01..03 | 3b |
| 4a | Chat Backend | RAG chain + SSE streaming chat API | CHAT-01..07 | 3c |
| 4b | Chat Frontend | SSE client + citation rendering + settings integration | UI-01..04 | 4a |
| 5 | Validation | E2E testing of full user flow | TEST-01..03 | 4b |

---

## Phase 3a: Infrastructure Fixes

**Goal:** Fix known blockers so the RAG pipeline has a stable foundation.

**Requirements:**
- INFRA-01: Absolute ChromaDB path
- INFRA-02: Configurable SQLite path
- INFRA-03: SQLite WAL mode
- INFRA-04: Lazy embedding model loading
- INFRA-05: Background task session management
- INFRA-06: File upload validation
- INFRA-07: Fix requirements.txt encoding
- INFRA-08: System dependency startup probe

**Plans:** 2 plans

Plans:
- [x] 03A-01-PLAN.md — Fix encoding, test scaffold, absolute SQLite paths, WAL mode, startup probes
- [x] 03A-02-PLAN.md — Lazy-load embeddings, ChromaDB path, eager-load fix, upload validation

**Success criteria:**
- [x] Server starts with absolute DB/ChromaDB paths logged to console
- [x] WAL mode confirmed via `PRAGMA journal_mode` query
- [x] Embedding model NOT loaded until first embedding request
- [x] Upload of .exe file returns 400; upload of 200MB file returns 413
- [x] `pip install -r requirements.txt` works on fresh venv
- [x] Missing poppler/tesseract produces clear warning at startup

**Estimated scope:** 8 requirements, all parallelizable. Touches 6 existing files. **COMPLETE.**

---

## Phase 3b: Ingestion Pipeline

**Goal:** Upload a real PDF/DOCX/PPTX/XLSX and produce properly chunked, metadata-rich vectors in ChromaDB.

**Requirements:**
- PARSE-01: Real document parsing with unstructured.io
- PARSE-02: Image extraction from PDF/PPTX
- PARSE-03: Image summarization via Gemini Vision
- PARSE-04: Graceful image summarization failure
- PARSE-05: Preserve element metadata through pipeline
- CHUNK-01: RecursiveCharacterTextSplitter (512/64)
- CHUNK-02: Chunk metadata schema
- CHUNK-03: Image summaries chunked as text

**Plans:** 3 plans

Plans:
- [ ] 03B-01-PLAN.md — Schema changes, new dependencies, vector store delete/sanitize capabilities
- [ ] 03B-02-PLAN.md — ImageProcessorService with Gemini Vision + tenacity retry
- [ ] 03B-03-PLAN.md — DocumentParserService rewrite with unstructured + chunking + pipeline wiring

**Success criteria:**
- [ ] Upload a 10-page PDF → chunks appear in ChromaDB with page_number metadata
- [ ] Upload a PPTX with images → image summaries embedded as text chunks
- [ ] Upload a DOCX → text properly chunked with overlap
- [ ] Gemini Vision failure → placeholder text stored, document still marked complete
- [ ] ChromaDB metadata includes: document_id, filename, page_number, chunk_index, element_type

**Estimated scope:** 8 requirements. New service: `image_processor.py`. Major rewrite: `document_parser.py`.

**Dependencies:** Phase 3a complete. System deps (poppler, tesseract) installed.

---

## Phase 3c: Retrieval

**Goal:** Query ChromaDB with switchable embedding providers and get ranked, deduplicated results with citations.

**Requirements:**
- EMBED-01: Local embedding default
- EMBED-02: Switchable to OpenAI/Gemini embeddings
- EMBED-03: Store provider in collection metadata
- EMBED-04: Block mismatched provider queries
- EMBED-05: Re-index endpoint
- EMBED-06: Per-project write lock
- SEARCH-01: Top-K semantic search endpoint
- SEARCH-02: Score threshold filtering
- SEARCH-03: MMR/deduplication

**Plans:** 3 plans

Plans:
- [ ] 03C-01-PLAN.md — Install deps, extend EmbeddingFactory with api_key + _GeminiEmbeddings, fix conftest
- [ ] 03C-02-PLAN.md — Collection metadata, provider mismatch check, write lock, MMR search
- [ ] 03C-03-PLAN.md — Search router + reindex endpoint + mount + integration tests

**Success criteria:**
- [ ] Search endpoint returns Top-5 chunks with distances and metadata
- [ ] Low-similarity chunks filtered out
- [ ] Switching embedding provider with existing collection returns clear error message
- [ ] Re-index endpoint deletes and re-embeds all project documents
- [ ] Concurrent uploads to same project do not corrupt collection

**Estimated scope:** 9 requirements. Extends: `embeddings.py`, `vector_store.py`. New: search router or endpoint.

**Dependencies:** Phase 3b complete (documents ingested to search against).

---

## Phase 4a: Chat Backend

**Goal:** POST to /api/chat → get SSE-streamed AI response grounded in project documents with citations.

**Requirements:**
- CHAT-01: POST /api/chat endpoint
- CHAT-02: RAG chain (embed → search → context)
- CHAT-03: Context-augmented prompt template
- CHAT-04: SSE streaming via StreamingResponse
- CHAT-05: SSE data format specification
- CHAT-06: Error events mid-stream
- CHAT-07: Citation metadata forwarding

**Success criteria:**
- [ ] `curl -N -X POST /api/chat` returns streamed SSE events
- [ ] Response text references content from uploaded documents
- [ ] Terminal SSE event contains citations array with filename + page_number
- [ ] Mid-stream LLM error produces error SSE event (not silent disconnect)
- [ ] Works with OpenAI, Gemini, Claude, and Ollama providers

**Estimated scope:** 7 requirements. New: `rag_chain.py`, `chat_service.py`, `chat.py` router.

**Dependencies:** Phase 3c complete (search endpoint working).

---

## Phase 4b: Chat Frontend

**Goal:** User types a question in ChatArea, sees streaming response with citations from their uploaded documents.

**Requirements:**
- UI-01: fetch + ReadableStream SSE client
- UI-02: Incremental text rendering (typing effect)
- UI-03: Citation rendering from terminal event
- UI-04: Dynamic provider/credential loading from Settings

**Success criteria:**
- [ ] User sees text appear word-by-word in ChatArea
- [ ] Citations displayed below response with filename and page number
- [ ] Provider selection in SettingsPanel is used for chat requests
- [ ] API key from SettingsPanel is passed in request body

**Estimated scope:** 4 requirements. Modifies: `ChatArea.jsx`, `SettingsPanel.jsx`. New: SSE client utility.

**Dependencies:** Phase 4a complete (chat API responding).

---

## Phase 5: Validation

**Goal:** Confirm the full user flow works end-to-end.

**Requirements:**
- TEST-01: E2E Upload → Vector → Chat test
- TEST-02: ChromaDB metadata round-trip test
- TEST-03: Embedding provider switch re-index test

**Success criteria:**
- [ ] Automated test: upload PDF → query → receive answer with correct citation
- [ ] Metadata survives ChromaDB insert/query round-trip
- [ ] Provider switch triggers re-index, search works with new embeddings

**Estimated scope:** 3 requirements. New: `backend/tests/` directory with pytest.

**Dependencies:** Phase 4b complete (full stack working).

---

## Milestone Complete When

All 38 requirements implemented and verified:
- User can upload PDF/DOCX/PPTX/XLSX documents
- Documents are parsed, chunked, and embedded in ChromaDB
- Images are extracted and summarized via Gemini Vision
- User can switch embedding providers (with re-index)
- User can chat with AI grounded in their documents
- Responses stream in real-time with citations
- E2E test passes

---

*6 phases, 38 requirements, linear dependency chain with Phase 3a tasks parallelizable.*
