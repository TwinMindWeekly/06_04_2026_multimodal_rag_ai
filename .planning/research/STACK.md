# Technology Stack — RAG Pipeline Addition

**Project:** Multimodal RAG AI (Brownfield — Phases 1, 2, 2.5 complete)
**Milestone scope:** Add real document parsing, vector search, and LLM chat to existing React/FastAPI app
**Researched:** 2026-04-09
**Locked constraints:** React 19 + Vite (frontend), FastAPI + SQLAlchemy/SQLite (backend), ChromaDB + LangChain (RAG orchestration), sentence-transformers (local embeddings)

---

## Context: What Is Already In Place

The following are installed and partially wired — this research does NOT re-decide them:

| Component | Installed Version | Status |
|-----------|------------------|--------|
| LangChain | 1.2.15 | Installed, factory pattern stubbed |
| langchain-text-splitters | 1.1.1 | Installed, not yet called |
| ChromaDB | 1.5.7 | Installed, per-project collections designed |
| sentence-transformers | 5.3.0 | Installed, `all-MiniLM-L6-v2` as default |
| unstructured | commented out | Planned but not installed |

This research fills in the six open questions: parsing library, chunking strategy, embedding tradeoffs, ChromaDB characteristics, orchestration layer, and streaming protocol.

---

## 1. Document Parsing

### Recommendation: `unstructured[all-docs]` — stick with the planned choice

**Why:** The project has already designed its parsing interface around unstructured.io's output model (`Element` objects with type, text, metadata). Switching now means rewriting the stub interface, not just swapping a library. The decision is effectively locked by prior design work.

**What unstructured delivers for this project's file types:**

| Format | Extraction quality | System dep required |
|--------|--------------------|---------------------|
| PDF (text) | High — layout-aware, preserves headings | poppler |
| PDF (scanned) | Medium — OCR via tesseract | poppler + tesseract |
| DOCX | High — paragraph, table, heading structure preserved | none |
| PPTX | High — slide text, notes, titles | none |
| XLSX | Medium — cell text extraction, table detection | none |

**Image extraction:** unstructured extracts embedded images from PDF/PPTX as `Image` elements with file paths — this feeds directly into the Gemini Vision summarization step (RAG-05, RAG-06).

**Install command for this project:**
```bash
pip install "unstructured[pdf,docx,pptx,xlsx]"
# System deps (required before pip install):
# Windows: install poppler via conda or pre-built binary; tesseract via UB-Mannheim installer
# The [all-docs] extra pulls in too many optional deps — use format-specific extras
```

**Confidence: HIGH** — unstructured.io is the de-facto standard for multimodal document parsing in Python RAG pipelines. The project interface is already designed around it. No reason to deviate.

### What NOT to use

| Library | Why not |
|---------|---------|
| PyMuPDF (fitz) | PDF-only, no DOCX/PPTX. Good PDF quality but breaks multi-format requirement |
| pdfplumber | PDF-only, better for structured tables but no image extraction |
| python-docx directly | DOCX only, no unified element model |
| docling (IBM) | Newer, promising, but less battle-tested and no XLSX support as of mid-2025 |
| Textract (AWS) | Cloud dependency, breaks local-first constraint |

---

## 2. Text Chunking

### Recommendation: `RecursiveCharacterTextSplitter` — already installed, use it

**Why:** `langchain-text-splitters 1.1.1` is already installed. `RecursiveCharacterTextSplitter` is the correct choice for this project for three concrete reasons:

1. **Document heterogeneity.** The system handles PDF, DOCX, PPTX, XLSX — documents with different structural conventions. A fixed splitter fails on short slides; a semantic splitter adds a second embedding model dependency. Recursive character splitting handles all formats without extra infrastructure.

2. **Deterministic and fast.** No inference step — chunking is pure text manipulation. This keeps the ingestion pipeline latency low (important when users are waiting for upload → ready status).

3. **Citation metadata is preserved.** Each chunk can carry `page_number`, `filename`, `element_type` metadata from unstructured's output — the `add_start_index=True` parameter lets you compute exact character offsets for citations (RAG-09 requirement).

**Recommended parameters for this project:**

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,        # tokens ~= chars/4; 512 is sweet spot for all-MiniLM-L6-v2 (max 256 tokens, so this gives ~128 tokens per chunk — safe)
    chunk_overlap=64,      # ~12.5% overlap preserves context across boundaries
    length_function=len,   # character count (fast, no tokenizer needed)
    add_start_index=True,  # enables character-offset citations
    separators=["\n\n", "\n", ". ", " ", ""],  # default recursive order
)
```

**Note on chunk_size vs model context:** `all-MiniLM-L6-v2` has a 256 token max. At ~4 chars/token, 512 chars ≈ 128 tokens — well within limit. If switching to OpenAI `text-embedding-3-small` (8191 token limit), chunks can be made larger (up to ~2000 chars) for better semantic completeness.

**Semantic chunking — why NOT now:**

Semantic chunking (splitting on embedding similarity drops) requires running an embedding model during ingestion. This doubles ingestion time and creates a circular dependency: you need embeddings to decide chunk boundaries, then embeddings again to store chunks. For this project's scope and local-first constraint, it adds complexity without proportional retrieval quality gain. Defer to a future phase if retrieval quality is measured and found lacking.

**Confidence: HIGH** — RecursiveCharacterTextSplitter is the correct default for heterogeneous document RAG. Semantic chunking is a future optimization, not a baseline requirement.

---

## 3. Embedding Models

### Recommendation: Two-tier strategy — local default, switchable to paid

The project already has this designed (RAG-08). This research confirms the specific model choices.

#### Tier 1 — Local default (already installed)

| Model | Library | Dim | Max tokens | Quality | Cost |
|-------|---------|-----|-----------|---------|------|
| `all-MiniLM-L6-v2` | sentence-transformers 5.3.0 | 384 | 256 | Good for English | Free |

**Keep this as the default.** It runs on CPU (torch already installed in CPU mode), requires no API key, and is adequate for development and for users who want fully local operation.

**Limitation to document in code:** Vietnamese text quality is lower with this model — it was trained primarily on English. For a bilingual system, flag this to users in the Settings UI.

#### Tier 2 — Paid upgrade (switchable via Settings UI)

| Provider | Model | Dim | Max tokens | Cost (per 1M tokens) | Notes |
|----------|-------|-----|-----------|---------------------|-------|
| OpenAI | `text-embedding-3-small` | 1536 | 8191 | ~$0.02 | Best cost/quality ratio |
| OpenAI | `text-embedding-3-large` | 3072 | 8191 | ~$0.13 | Overkill for this use case |
| Google | `text-embedding-004` | 768 | 2048 | Free tier available | Good multilingual, matches Gemini stack |
| Ollama | `nomic-embed-text` | 768 | 8192 | Free (local) | Good quality, requires Ollama running |

**Prescriptive recommendation for paid tier:** Use `text-embedding-3-small` for OpenAI users and `text-embedding-004` for Gemini users. Do NOT implement `text-embedding-3-large` — the quality gain over `small` is marginal and the cost is 6.5x higher.

**Critical implementation constraint:** Embeddings must stay consistent within a project collection. Once a project's documents are embedded with model A, you cannot add new documents with model B and search across both — the vector spaces are incompatible. The factory pattern must enforce: switching embedding providers requires re-ingesting all documents in the project.

**Confidence: MEDIUM** — Model names and pricing are from training data (August 2025). Verify current pricing at platform dashboards before communicating costs to users. Model availability is HIGH confidence.

---

## 4. Vector Database (ChromaDB)

### ChromaDB 1.5.7 — use it, but know its limits

The project already uses ChromaDB with a per-project collection design. This research documents the characteristics that matter for implementation decisions.

#### What ChromaDB 1.5.x does well (for this project)

- **Embedded, no server process:** Runs in-process, persists to `./chroma_db/` directory. Zero ops burden, matches local-first constraint perfectly.
- **Per-collection isolation:** One collection per project is the right design — queries cannot bleed across project boundaries.
- **Metadata filtering:** Supports `where` filters on metadata fields (e.g., `{"filename": {"$eq": "report.pdf"}}`). Use this for citation-scoped retrieval.
- **Python-native API:** No REST overhead, direct function calls from FastAPI.

#### Known limitations to design around

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| **Single-process write lock** | Only one writer at a time. Concurrent uploads to the same collection will serialize or fail. | Use FastAPI's background tasks with a per-project lock (asyncio.Lock) to prevent concurrent writes to same collection |
| **No full-text search** | Vector similarity only — no BM25 hybrid search. | For this project's scope this is acceptable. Hybrid search is a future enhancement. |
| **Collection size at scale** | Degrades above ~100K vectors in a single collection on embedded mode. | Not a concern for this project (local-first, single user, typical document = 50-500 chunks) |
| **No built-in re-ranking** | Returns top-K by cosine similarity only. | Implement a simple score-threshold filter (discard chunks below 0.7 similarity) before passing to LLM |
| **Persistence path is CWD-relative** | If the server starts from a different directory, the chroma_db path resolves differently. | Use absolute path: `os.path.join(os.path.dirname(__file__), "../../chroma_db")` |

#### Retrieval pattern for RAG-09

```python
# Correct pattern for this project
collection.query(
    query_embeddings=[query_vector],
    n_results=5,                           # top-5 chunks
    where={"project_id": {"$eq": project_id}},  # project-scoped (if using single collection)
    include=["documents", "metadatas", "distances"]
)
# Filter: only pass chunks where distance < 0.3 (cosine distance, lower = more similar)
```

**Collection design decision:** The project uses one collection per project (not one global collection). This is correct — it avoids the need for metadata filtering on project_id, which would scan the entire global collection. Keep this design.

**Confidence: HIGH** — ChromaDB 1.5.x characteristics are well-documented. The version installed (1.5.7) matches the research baseline.

---

## 5. LLM Orchestration

### Recommendation: Keep LangChain, use it minimally

The project already has LangChain 1.2.15 installed with a factory pattern. This research confirms the right usage boundary.

#### Use LangChain for (HIGH value, LOW risk)

| Use case | LangChain component | Rationale |
|----------|--------------------|-----------| 
| Text splitting | `RecursiveCharacterTextSplitter` | Already installed, stable API |
| Provider abstraction | `langchain-openai`, `langchain-anthropic`, `langchain-google-genai` | Unified `.stream()` interface across all four providers |
| Prompt templates | `ChatPromptTemplate` | Structured prompt construction with variable injection |
| Embeddings | `OpenAIEmbeddings`, `HuggingFaceEmbeddings` | Already in factory pattern |

#### Do NOT use LangChain for (LOW value, HIGH complexity)

| Anti-pattern | Why not |
|-------------|---------|
| `ConversationalRetrievalChain` or `RetrievalQA` | Hides the retrieval logic, makes citations harder to extract, adds magic behavior that breaks when you need control |
| LangChain agents | Overkill — this is a fixed RAG pipeline, not an agent loop |
| LangGraph | Not needed for a single-turn chat with retrieval. Adds significant complexity. |
| LangChain memory / conversation history | Implement conversation history yourself in the FastAPI session — simpler, more controllable |

#### Recommended orchestration pattern (direct, explicit)

```python
# This pattern over any LangChain chain abstraction
async def chat(query: str, project_id: str, settings: Settings):
    # 1. Embed the query
    query_vec = embedding_factory(settings).embed_query(query)

    # 2. Retrieve from ChromaDB
    results = chroma_collection(project_id).query(query_embeddings=[query_vec], n_results=5)

    # 3. Build context string with citations
    context_chunks = build_context(results)  # your function, not LangChain's

    # 4. Construct prompt
    prompt = ChatPromptTemplate.from_messages([...]).format_messages(
        context=context_chunks, question=query
    )

    # 5. Stream from LLM
    llm = llm_factory(settings)
    async for chunk in llm.astream(prompt):
        yield chunk
```

This pattern gives full control over retrieval, context construction, and citation forwarding. LangChain's value here is only the `ChatPromptTemplate` and the provider-unified `.astream()` interface — two narrow, stable APIs.

#### LlamaIndex — why NOT

LlamaIndex is an alternative orchestration framework. Do not introduce it:
- The project already has LangChain installed and partially wired
- Mixing both frameworks creates import confusion and doubled abstractions
- LlamaIndex's strength is complex retrieval pipelines (hierarchical indexing, query routing) — not needed here
- Migration cost is high, benefit is zero for this scope

**Confidence: HIGH** — LangChain's text splitters and provider adapters are stable. The anti-pattern guidance (avoid high-level chains) is based on consistent community experience with RAG systems requiring citation control.

---

## 6. Streaming Response Protocol

### Recommendation: SSE (Server-Sent Events) — already the right choice (CHAT-04)

The project already specifies SSE in CHAT-04. This research confirms it is correct and documents the implementation pattern.

#### SSE vs WebSocket for this use case

| Criterion | SSE | WebSocket |
|-----------|-----|-----------|
| Protocol | HTTP/1.1 one-way stream | Full-duplex TCP |
| Browser support | Native `EventSource` API, no library needed | Needs `ws` library or native API |
| FastAPI support | `StreamingResponse` built-in | `websockets` package (installed in venv) |
| Reconnection | Automatic (browser handles it) | Manual reconnect logic required |
| Direction | Server → Client only | Bidirectional |
| Use case fit | Chat response streaming (server sends, client reads) | Real-time bidirectional (not needed here) |
| Proxy/load-balancer compatibility | Works with standard HTTP proxies | Requires WebSocket-aware proxy |

Chat is inherently one-directional for streaming: user sends one message (standard POST), server streams the response back. SSE is the correct protocol. WebSocket adds complexity (connection management, reconnect, ping/keep-alive) with no benefit for this interaction pattern.

#### FastAPI SSE implementation pattern

```python
from fastapi.responses import StreamingResponse

@router.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    async def event_stream():
        async for chunk in chat_pipeline(request):
            # SSE format: "data: {payload}\n\n"
            text = chunk.content if hasattr(chunk, "content") else str(chunk)
            yield f"data: {json.dumps({'text': text})}\n\n"

        # Send citations after stream completes
        yield f"data: {json.dumps({'citations': get_citations(), 'done': True})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disables nginx buffering if behind nginx
        }
    )
```

#### Frontend SSE parsing pattern (CHAT-05)

```javascript
// Use fetch + ReadableStream over EventSource — gives POST support
// EventSource only supports GET, which cannot carry the chat request body
const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(chatRequest),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const lines = decoder.decode(value).split("\n");
    for (const line of lines) {
        if (line.startsWith("data: ")) {
            const payload = JSON.parse(line.slice(6));
            if (payload.done) {
                // render citations
            } else {
                // append payload.text to message buffer
            }
        }
    }
}
```

**Why fetch over EventSource:** `EventSource` is GET-only. The chat request requires a POST body (message, project_id, provider settings). Use `fetch` with `ReadableStream` — same wire protocol, full POST support.

**Confidence: HIGH** — SSE with FastAPI `StreamingResponse` is the established pattern for LLM chat streaming in Python backends. The fetch-based frontend approach is standard for SSE over POST.

---

## Installation Commands

### Document parsing (new dependency)

```bash
# Install unstructured with format-specific extras (lighter than [all-docs])
pip install "unstructured[pdf,docx,pptx,xlsx]"

# Windows system dependencies:
# poppler: download from https://github.com/oschwartz10612/poppler-windows/releases
#   Add bin/ to PATH
# tesseract: download from https://github.com/UB-Mannheim/tesseract/wiki
#   Add install dir to PATH
# pytesseract (Python wrapper):
pip install pytesseract pillow

# Verify unstructured can find system deps:
python -c "from unstructured.partition.pdf import partition_pdf; print('OK')"
```

### LLM provider packages (confirm installed)

```bash
# These should already be present via langchain extras — verify:
pip install langchain-openai langchain-anthropic langchain-google-genai

# Ollama provider (via langchain-community, already installed):
# Requires Ollama running locally: https://ollama.ai
```

### No new packages needed for

- Text chunking — `langchain-text-splitters` already installed
- ChromaDB — already installed at 1.5.7
- sentence-transformers — already installed at 5.3.0
- SSE streaming — `StreamingResponse` is in FastAPI core

---

## Alternatives Considered

| Category | Recommended | Alternative Considered | Why Not |
|----------|-------------|----------------------|---------|
| Document parsing | unstructured[pdf,docx,pptx,xlsx] | docling (IBM) | Less mature, no XLSX, interface mismatch with existing stub |
| Document parsing | unstructured | PyMuPDF + python-docx separately | No unified element model, breaks RAG-05 image extraction |
| Chunking | RecursiveCharacterTextSplitter | Semantic chunking | Doubles ingestion latency, adds model dependency, no citation advantage |
| Chunking | RecursiveCharacterTextSplitter | Fixed-size token chunking | Doesn't respect sentence/paragraph boundaries, citation quality worse |
| Embeddings (paid) | text-embedding-3-small | text-embedding-3-large | 6.5x cost, marginal quality gain at this scale |
| Orchestration | LangChain (narrow use) + direct Python | LlamaIndex | Already installed, no migration benefit, LlamaIndex complexity overkill |
| Orchestration | LangChain (narrow use) + direct Python | LangChain RetrievalQA chain | Hides citation metadata, less controllable |
| Streaming | SSE via StreamingResponse | WebSocket | Bidirectional not needed, SSE simpler, no reconnect code required |
| Vector DB | ChromaDB (keep) | Qdrant, Weaviate | External server required, breaks local-first constraint |

---

## Sources

- Project files: `.planning/PROJECT.md`, `.planning/codebase/STACK.md` (HIGH confidence — direct observation)
- unstructured.io library characteristics: training data verified against known stable API (MEDIUM confidence — verify system dep install steps on target Windows environment)
- LangChain 1.x API: training data (MEDIUM confidence — API surface for text splitters and provider adapters has been stable; verify `.astream()` signature against installed version)
- ChromaDB 1.5.x embedded mode behavior: training data (MEDIUM confidence — 1.5.7 is installed, behavior consistent with known 1.x embedded API)
- SSE over HTTP/FastAPI StreamingResponse: training data (HIGH confidence — stable pattern, no known breaking changes)
- Embedding model pricing: training data as of August 2025 (LOW confidence on exact pricing — verify current rates at platform dashboards before surfacing to users)
