# Research Summary — Multimodal RAG AI

**Project:** Multimodal RAG AI (Brownfield — adding RAG pipeline + Chat API)
**Synthesized:** 2026-04-09
**Research files:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md

---

## Executive Summary

The remaining work (Phase 3: RAG pipeline, Phase 4: Chat API) requires **no new architectural layers** — the existing Router → Service → Data pattern accommodates everything. Two new services, one router, and frontend SSE wiring complete the milestone. The critical path is linear (parse → chunk → embed → search → chat → stream), and all infrastructure dependencies are already installed except `unstructured[pdf,docx,pptx,xlsx]` and its system dependencies (poppler, tesseract).

---

## Key Decisions (Confirmed by Research)

| Decision | Confidence | Rationale |
|----------|-----------|-----------|
| **unstructured.io for parsing** | HIGH | Interface already designed around it; best multi-format support; image extraction built-in |
| **RecursiveCharacterTextSplitter** | HIGH | Already installed (langchain-text-splitters 1.1.1); deterministic, fast, preserves citation metadata |
| **chunk_size=512, overlap=64** | HIGH | Safe for all-MiniLM-L6-v2 (256-token limit ≈ 1024 chars); ~128 tokens per chunk |
| **Local + paid embeddings (switchable)** | HIGH | all-MiniLM-L6-v2 default; text-embedding-3-small (OpenAI) or text-embedding-004 (Gemini) upgrade |
| **Re-ingestion on provider switch** | HIGH | Vector spaces are incompatible across models; must store provider in collection metadata |
| **LangChain narrow usage only** | HIGH | Use text splitters + provider adapters + ChatPromptTemplate; avoid RetrievalQA/chains |
| **SSE via StreamingResponse** | HIGH | fetch + ReadableStream on frontend (NOT EventSource — GET-only limitation) |
| **Gemini Vision for image summarization** | MEDIUM | Best multimodal understanding; rate limit risk at 15 RPM free tier |
| **ChromaDB per-project collections** | HIGH | Already implemented; correct isolation model |

---

## Critical Blockers (Fix Before Phase 3)

These must be resolved before any real document processing begins:

| # | Issue | File | Fix |
|---|-------|------|-----|
| 1 | ChromaDB path is CWD-relative | `vector_store.py:5` | Use `__file__`-relative or env var absolute path |
| 2 | SQLite path is hardcoded | `database.py:4` | Use env var with `__file__`-relative default |
| 3 | SQLite WAL mode not enabled | `database.py` | Add `PRAGMA journal_mode=WAL` on connection init |
| 4 | Embedding model loaded at import time | `embeddings.py:28` | Lazy-initialize on first use |
| 5 | Background task passes ORM objects | `document_parser.py` | Pass `document_id: int` only; fresh SessionLocal in task |
| 6 | No file upload validation | `documents.py` | Add size limit + extension whitelist |
| 7 | requirements.txt UTF-16 encoding | `requirements.txt` | Convert to UTF-8 |
| 8 | System deps not verified at startup | N/A | Add `shutil.which("pdfinfo")` probe at boot |

---

## Architecture: New Components Needed

| Component | Type | Purpose |
|-----------|------|---------|
| `image_processor.py` | New service | Gemini Vision image summarization |
| `rag_chain.py` | New service | Query pipeline: embed → search → build context |
| `chat_service.py` | New service | Thin adapter: prompt engineering + LLM streaming |
| `chat.py` | New router | `/api/chat` POST endpoint with SSE streaming |

**No changes needed to:** `main.py` structure, `models/domain.py`, `schemas/domain.py` (just add chat schemas), existing router patterns.

**Extend existing:** `document_parser.py` (real unstructured calls), `vector_store.py` (distances in search), `embeddings.py` (lazy load + providers), `llm_provider.py` (streaming=True).

---

## Build Order (Dependency-Driven)

```
Phase 3a: Infrastructure Fixes (parallelizable)
├── Fix absolute paths (DB + ChromaDB)
├── Enable SQLite WAL mode
├── Lazy-load embedding model
├── Fix background task session management
├── Add file upload validation
├── Install unstructured + system deps
└── Fix requirements.txt encoding

Phase 3b: Ingestion Pipeline (sequential)
├── Real document parsing (unstructured.io)
├── Image extraction from PDF/PPTX
├── Image summarization (Gemini Vision)
├── Text chunking (RecursiveCharacterTextSplitter)
└── Store chunks + metadata in ChromaDB

Phase 3c: Retrieval (sequential)
├── Switchable embedding providers + re-index logic
└── Semantic search endpoint (Top-K + score filter + MMR)

Phase 4a: Chat Backend (sequential)
├── RAG chain (embed query → search → build context)
├── Context-augmented prompt engineering
├── Chat API endpoint with SSE streaming
└── Citation metadata forwarding

Phase 4b: Chat Frontend (sequential)
├── fetch + ReadableStream SSE client
├── Citation rendering in ChatArea
└── Dynamic provider/credential loading from Settings

Phase 5: Validation
└── E2E testing (Upload → Vector → Chat)
```

---

## Top 5 Pitfalls to Avoid

1. **Chunk size exceeding embedding model limit** — all-MiniLM-L6-v2 silently truncates at 256 tokens. Use chunk_size=512 chars (≈128 tokens).

2. **Embedding provider switch without re-indexing** — vectors from different models live in incompatible spaces. Store provider in collection metadata; block mismatched queries.

3. **DetachedInstanceError in background tasks** — Never pass ORM objects to background tasks. Pass scalar IDs, open fresh session in task.

4. **EventSource for SSE** — GET-only. Chat needs POST. Use fetch + ReadableStream.

5. **Unstructured system deps missing at runtime** — pip install succeeds without poppler/tesseract; failure surfaces only when first PDF is processed in background task with no user-visible error.

---

## What NOT to Build

| Anti-pattern | Why |
|-------------|-----|
| LangChain RetrievalQA / ConversationalRetrievalChain | Hides citation metadata; breaks when you need control |
| LangGraph | Overkill for fixed RAG pipeline |
| LlamaIndex | Already have LangChain; mixing doubles abstractions |
| Semantic chunking | Doubles ingestion latency; circular model dependency |
| text-embedding-3-large | 6.5x cost over text-embedding-3-small; marginal quality gain |
| WebSocket for chat streaming | Bidirectional not needed; SSE is simpler |
| Multiple embedding models in same collection | Incompatible vector spaces |

---

## Open Questions for Implementation

1. **Windows poppler/tesseract paths** — Exact install + PATH registration steps need validation on the dev machine before writing parsing code.
2. **Ollama async streaming** — Verify `ChatOllama.astream()` works with installed `langchain-community` version.
3. **Vietnamese retrieval quality** — all-MiniLM-L6-v2 is English-trained; smoke test with Vietnamese queries once pipeline runs; consider `paraphrase-multilingual-MiniLM-L12-v2` as fallback.
4. **Gemini Vision rate limits** — Free tier is 15 RPM; batch image processing needs retry logic with backoff.
5. **Image summary caching** — Re-upload triggers re-summarization at API cost; consider caching in `Document.metadata_json`.

---

*This summary synthesizes findings from 4 research dimensions. Individual research files contain full detail, code examples, and confidence assessments.*
