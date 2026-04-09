# Feature Landscape — Multimodal RAG AI

**Domain:** Document-grounded RAG chat system
**Researched:** 2026-04-09
**Confidence:** HIGH (grounded in PROJECT.md active requirements + domain analysis)

---

## Feature Categories

### Category 1: Document Ingestion Pipeline

| Feature | Table Stakes? | This Project | Priority |
|---------|--------------|--------------|----------|
| Multi-format parsing (PDF, DOCX, PPTX, XLSX) | Yes | RAG-04 | v1 |
| Text chunking with overlap | Yes | RAG-07 | v1 |
| Image extraction from documents | Differentiator | RAG-05 | v1 |
| Image summarization via Vision AI | Differentiator | RAG-06 | v1 |
| Background processing with status updates | Yes | BE-04 (done) | v1 |
| File type validation and size limits | Yes | Missing | v1 |
| OCR for scanned PDFs | Nice-to-have | Via unstructured hi_res | v2 |
| Table extraction and structured parsing | Nice-to-have | Not planned | v2 |

### Category 2: Vector Store & Retrieval

| Feature | Table Stakes? | This Project | Priority |
|---------|--------------|--------------|----------|
| Per-project vector isolation | Yes | RAG-01 (done) | v1 |
| Top-K similarity search | Yes | RAG-09 | v1 |
| Citation metadata (page, filename) | Yes | CHAT-03 | v1 |
| Score threshold filtering | Table Stakes | Not explicit | v1 |
| MMR (Maximal Marginal Relevance) dedup | Differentiator | Not explicit | v1 |
| Switchable embedding providers | Differentiator | RAG-08 | v1 |
| Re-index on provider switch | Required | Not explicit | v1 |
| Hybrid search (BM25 + vector) | Advanced | Not planned | v2 |
| Query rewriting / HyDE | Advanced | Not planned | v2 |

### Category 3: Chat & LLM Integration

| Feature | Table Stakes? | This Project | Priority |
|---------|--------------|--------------|----------|
| Multi-provider LLM support | Differentiator | LLM-01 (done) | v1 |
| Context-augmented prompting | Yes | CHAT-02 | v1 |
| SSE streaming responses | Yes | CHAT-04 | v1 |
| Citation rendering in UI | Yes | CHAT-05 | v1 |
| Dynamic provider/credential loading | Yes | CHAT-06 | v1 |
| Conversation history / memory | Nice-to-have | Not planned | v2 |
| Multi-turn context carry | Nice-to-have | Not planned | v2 |
| Image input in chat | Differentiator | CHAT-01 | v1 |

### Category 4: Infrastructure & Quality

| Feature | Table Stakes? | This Project | Priority |
|---------|--------------|--------------|----------|
| Absolute paths for DB/ChromaDB | Required fix | CONCERNS #7, #8 | v1 |
| SQLite WAL mode | Required fix | Not explicit | v1 |
| Lazy embedding model loading | Performance fix | CONCERNS #12 | v1 |
| File upload validation | Security fix | CONCERNS #5 | v1 |
| E2E testing | Yes | TEST-01 | v1 |
| System dep startup probe | Required | Not explicit | v1 |

### Category 5: UI Enhancements

| Feature | Table Stakes? | This Project | Priority |
|---------|--------------|--------------|----------|
| Document processing status indicator | Yes | Not explicit | v1 |
| Re-index button on provider switch | Required UX | Not explicit | v1 |
| Embedding provider warning (Vietnamese) | Nice-to-have | Not explicit | v2 |

---

## Critical Path (Dependency Chain)

```
System deps (poppler/tesseract)
    ↓
Fix absolute paths (DB + ChromaDB)
    ↓
Real document parsing (RAG-04)
    ↓
Image extraction (RAG-05) ──→ Image summarization (RAG-06)
    ↓                              ↓
Text chunking (RAG-07) ←──────────┘
    ↓
Embedding + store in ChromaDB (RAG-08)
    ↓
Semantic search endpoint (RAG-09)
    ↓
Chat API endpoint (CHAT-01)
    ↓
Context-augmented prompting (CHAT-02)
    ↓
Citation forwarding (CHAT-03)
    ↓
SSE streaming (CHAT-04)
    ↓
Frontend SSE + citations (CHAT-05)
    ↓
Dynamic provider loading (CHAT-06)
    ↓
E2E testing (TEST-01)
```

The critical path is **linear** — each step depends on the previous one. Only RAG-05/RAG-06 (image extraction + summarization) can be partially parallelized with RAG-07 (text chunking).

---

## v1 MVP Recommendation

**Must ship (13 features):** RAG-04 through RAG-09, CHAT-01 through CHAT-06, TEST-01, plus infrastructure fixes (absolute paths, WAL mode, lazy loading, file validation, startup probe).

**Defer to v2 (5 features):** OCR for scanned PDFs (auto strategy handles basic cases), table extraction, hybrid search, query rewriting, conversation history/multi-turn.

**Anti-features (never build):**
- LangChain RetrievalQA chains — hides citation metadata
- EventSource for SSE — GET-only, cannot POST
- Multiple embedding models in same collection — incompatible vector spaces
- Semantic chunking at ingestion — doubles latency, circular dependency

---

## Sources

- `.planning/PROJECT.md` — Active requirements (13 items)
- `.planning/codebase/CONCERNS.md` — 13 known issues mapped to features
- Domain analysis of RAG system table stakes vs differentiators
