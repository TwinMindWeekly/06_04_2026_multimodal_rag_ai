# Architecture Patterns — RAG Pipeline + Chat API

**Domain:** Multimodal Retrieval-Augmented Generation (brownfield extension)
**Milestone scope:** Add real document parsing, image processing, vector search, and LLM chat to existing React/FastAPI app
**Researched:** 2026-04-09
**Confidence:** HIGH (grounded in actual codebase files, established patterns)

---

## Recommended Architecture

This is a brownfield integration. The skeleton is complete: FastAPI routers, SQLAlchemy models,
ChromaDB PersistentClient, and factory-pattern services for embeddings and LLM providers all
exist and partially work. The task is wiring the ingestion pipeline fully and adding one new
router (chat.py) with SSE streaming.

No new architectural layers are needed. The existing layered architecture
(Router → Service → Data) needs two extension points: a complete ingestion pipeline and a
new chat router.

### Full System Map

```
FRONTEND (React 19 + Vite)
┌─────────────────────────────────────────────────────────────┐
│  Sidebar          ChatArea             SettingsPanel         │
│  (file tree)      (SSE consumer)       (provider/api key)   │
│       │                 │                      │             │
│       └─────────────────┴──────────────────────┘            │
│             axios (HTTP) + fetch ReadableStream (SSE)        │
└─────────────────────────────┬───────────────────────────────┘
                              │ HTTP / SSE
BACKEND (FastAPI)
┌─────────────────────────────▼───────────────────────────────┐
│  API LAYER (Routers)                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ projects.py  │  │ documents.py │  │ chat.py  [NEW]     │ │
│  │  (existing)  │  │  (existing)  │  │ POST /api/chat     │ │
│  └──────────────┘  └──────┬───────┘  └────────┬───────────┘ │
└─────────────────────────────────────────────────────────────┘
                             │                   │
          ┌──────────────────┘                   │
          │  BackgroundTask                       │  async generator
          ▼                                       ▼
┌─────────────────────┐              ┌────────────────────────┐
│ INGESTION SERVICES  │              │ QUERY SERVICES         │
│                     │              │                        │
│ document_parser.py  │              │ chat_service.py [NEW]  │
│ (extend existing)   │              │ (thin adapter)         │
│  unstructured.io    │              │        │               │
│  chunk_by_title     │              │ rag_chain.py [NEW]     │
│        │            │              │  embed → search →      │
│        ▼            │              │  prompt → stream       │
│ image_processor.py  │              └──────────┬─────────────┘
│ [NEW]               │                         │
│  Gemini Vision API  │                         │
│  base64 → summary   │                         │
└──────────┬──────────┘                         │
           │  insert_documents()      similarity_search()
           └──────────────┬──────────────────────┘
                          ▼
              ┌───────────────────────┐
              │ SHARED SERVICES       │
              │                       │
              │ vector_store.py       │
              │ (extend existing)     │
              │                       │
              │ embeddings.py         │
              │ (extend existing)     │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │ DATA LAYER            │
              │                       │
              │ SQLite                │
              │  projects/folders/    │
              │  documents tables     │
              │                       │
              │ ChromaDB              │
              │  project_{id}/        │
              │  collections          │
              │                       │
              │ ./uploads/            │
              │  {uuid}.{ext}         │
              │  extracted_{doc_id}/  │
              └───────────────────────┘
```

---

## Component Boundaries

| Component | File | Status | Responsibility | Talks To |
|-----------|------|--------|----------------|----------|
| projects router | `routers/projects.py` | existing | Project/folder CRUD | SQLite |
| documents router | `routers/documents.py` | existing | Upload file, spawn BackgroundTask | `document_parser`, SQLite |
| chat router | `routers/chat.py` | NEW | Accept POST /api/chat, return SSE StreamingResponse | `chat_service` |
| document_parser | `services/document_parser.py` | extend | Partition file via unstructured, chunk text, collect image paths | `image_processor`, `vector_store`, SQLite |
| image_processor | `services/image_processor.py` | NEW | Load image as base64, call Gemini Vision, return text summary | Gemini API (external) |
| vector_store | `services/vector_store.py` | extend | insert_documents, similarity_search; expose distances in results | ChromaDB, `embeddings` |
| embeddings | `services/embeddings.py` | extend | Factory for local/OpenAI/Gemini embedding models; singleton | HuggingFace / OpenAI / Google |
| rag_chain | `services/rag_chain.py` | NEW | Embed query → search ChromaDB → build prompt → stream LLM response | `vector_store`, `embeddings`, `llm_provider` |
| chat_service | `services/chat_service.py` | NEW | Validate chat request, extract provider config, delegate to rag_chain | `rag_chain` |
| llm_provider | `services/llm_provider.py` | extend | Factory returning streaming-capable LangChain ChatModel | OpenAI / Gemini / Claude / Ollama |

**Boundary rule:** `image_processor` is invoked only during ingestion, never during query.
`rag_chain` is invoked only during query, never during ingestion. `vector_store` is the single
bridge between both paths and must not carry request-scoped state.

---

## Data Flow

### Path 1: Ingestion (Upload → Parse → Embed → Store)

```
POST /api/documents/upload (multipart form)
  │
  ├─ Save raw file to ./uploads/{uuid}.{ext}
  ├─ INSERT Document row in SQLite (status="processing")
  └─ Spawn BackgroundTask: process_and_update_document(document_id)
       │
       ├─ [Parse] DocumentParserService.parse_document(file_path, document_id)
       │    │
       │    ├─ unstructured.partition(
       │    │     filename=file_path,
       │    │     strategy="hi_res",
       │    │     extract_image_block_types=["Image", "Table"],
       │    │     extract_image_block_output_dir=./uploads/extracted_{doc_id}/
       │    │   ) → List[Element]
       │    │
       │    ├─ chunk_by_title(elements) → List[TextChunk]
       │    │   (each chunk carries: text, page_number, element_type from unstructured metadata)
       │    │
       │    └─ listdir(extracted_{doc_id}/) → List[image_path]
       │
       ├─ [Summarize images] For each image_path:
       │    image_processor.summarize(image_path)
       │      ├─ Read file → base64 encode
       │      ├─ Build Gemini multimodal message:
       │      │    [{ type:"text", text:"Describe this image..." },
       │      │     { type:"image_url", url:"data:image/png;base64,..." }]
       │      ├─ ChatGoogleGenerativeAI("gemini-1.5-pro").invoke(message)
       │      └─ Return: str (image description text)
       │
       ├─ [Merge] text_chunks + image_summaries → all_chunks
       │    Each chunk carries metadata:
       │      { document_id, project_id, filename, chunk_index,
       │        page_number, type: "text"|"image", source_image?: str }
       │
       ├─ [Embed + Store] vector_store.insert_documents(all_chunks, metadatas, project_id)
       │    ├─ embeddings.embed_documents(chunks) → List[vector]
       │    └─ collection.upsert(documents, embeddings, metadatas, ids)
       │
       └─ UPDATE Document row: status="ready", metadata_json={chunk_count, image_count}
```

**Threading note:** BackgroundTask runs in FastAPI's thread pool. It opens its own
`SessionLocal()` DB session (already implemented correctly) and closes in `finally`.
Gemini Vision calls are synchronous in this context — acceptable for a local single-user tool.

### Path 2: Query (Chat Message → Retrieve → Augment → Stream)

```
POST /api/chat
  Body: { query, project_id, provider, api_key, temperature, max_tokens }
  │
  └─ StreamingResponse(event_stream(), media_type="text/event-stream")
       │
       └─ chat_service.stream_response(request)
            │
            ├─ [Step 1: Embed Query]
            │    embeddings.embed_query(query) → query_vector
            │    CRITICAL: Must use same embedding model as ingestion
            │
            ├─ [Step 2: Semantic Search]
            │    vector_store.similarity_search(query_vector, top_k=5, project_id)
            │    → List[{ content: str, metadata: {...}, distance: float }]
            │    Filter: discard chunks where distance > 0.3 (cosine distance)
            │
            ├─ [Step 3: Build Augmented Prompt]
            │    rag_chain.build_prompt(query, retrieved_chunks)
            │    →  "You are a helpful assistant. Answer based on context only.
            │        Context:
            │        [Source: report.pdf, page 3]
            │        {chunk1_text}
            │        [Source: slides.pptx, page 7 - image]
            │        {image_summary_text}
            │        Question: {query}
            │        Answer:"
            │
            ├─ [Step 4: Stream LLM Response]
            │    llm = LLMProviderFactory.get_llm(provider, api_key, streaming=True)
            │    async for token in llm.astream(prompt):
            │        yield SSE event: { type: "token", text: token.content }
            │
            └─ [Step 5: Yield Citations]
                 citations = extract_citations(retrieved_chunks)
                 yield SSE event: { type: "citations", data: [{ filename, page_number, chunk_index, type }] }
                 yield SSE event: { type: "done" }
```

### Citation Metadata Schema (Canonical — must be consistent across ingestion and retrieval)

```python
{
    "filename": str,          # original document filename
    "page_number": int | None, # page number from unstructured metadata (None for XLSX)
    "chunk_index": int,       # position within document
    "type": "text" | "image", # chunk origin
    "source_image": str | None # image filename for type="image" chunks
}
```

This schema must be stored identically in ChromaDB metadata at ingestion time and returned
identically in the SSE citations event. Schema drift between these two sites is the most
common source of broken citation display.

---

## Patterns to Follow

### Pattern 1: SSE Streaming via StreamingResponse

**What:** Return a `StreamingResponse` with `media_type="text/event-stream"` from the chat
endpoint. The response body is an async generator that yields SSE-formatted strings.

**When:** Any endpoint that streams LLM tokens to the frontend.

```python
# backend/app/routers/chat.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    async def event_stream():
        async for event in chat_service.stream_response(request):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # prevents nginx from buffering SSE
        }
    )
```

### Pattern 2: Frontend SSE over POST (fetch + ReadableStream)

**What:** Use `fetch` with `ReadableStream` consumption instead of the native `EventSource` API.

**Why:** `EventSource` only supports GET requests. The chat endpoint is a POST (needs a request
body). `fetch` with streaming body gives identical wire protocol with full POST support.

```javascript
// frontend/src/api/chat.js
export async function streamChat(payload, onToken, onCitations) {
    const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // keep incomplete line in buffer

        for (const line of lines) {
            if (line.startsWith("data: ") && line !== "data: [DONE]") {
                const event = JSON.parse(line.slice(6));
                if (event.type === "token") onToken(event.text);
                if (event.type === "citations") onCitations(event.data);
            }
        }
    }
}
```

### Pattern 3: Direct RAG Chain (no LangChain chain abstraction)

**What:** Implement the retrieval-augment-generate sequence as explicit Python code,
using LangChain only for text splitting, provider-unified `.astream()`, and
`ChatPromptTemplate`.

**Why:** LangChain's high-level chains (`RetrievalQA`, `ConversationalRetrievalChain`) hide
the metadata returned by ChromaDB, making it impossible to extract citation source, page
number, and chunk index. Explicit code gives full control at zero extra complexity.

```python
# backend/app/services/rag_chain.py
from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """You are a helpful assistant. Answer questions based strictly on the
provided context. If the context does not contain enough information, say so clearly.
Do not make up information.

Context:
{context}"""

async def stream_rag_response(
    query: str, retrieved_chunks: list[dict], llm
):
    context = "\n\n".join(
        f"[Source: {c['metadata']['filename']}, page {c['metadata'].get('page_number', '?')}]\n{c['content']}"
        for c in retrieved_chunks
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{question}"),
    ]).format_messages(context=context, question=query)

    async for chunk in llm.astream(prompt):
        yield {"type": "token", "text": chunk.content}
```

### Pattern 4: Background Task DB Session Management

**What:** BackgroundTask functions must open and close their own SQLAlchemy sessions.
They cannot share the request-scoped session injected via `Depends(get_db)`.

**Already implemented correctly** in `document_parser.py`:

```python
def process_and_update_document(document_id: int):
    db = SessionLocal()   # own session
    try:
        # ... all DB operations
        db.commit()
    finally:
        db.close()       # always close
```

Do not change this pattern. Do not pass a `db` session from the router into a BackgroundTask.

### Pattern 5: Embedding Model Singleton

**What:** The embedding model is loaded once at module level. It must NOT be instantiated
per request. `sentence-transformers` model loading takes 2-4 seconds and ~90MB memory.

**Already implemented correctly** in `embeddings.py` (`default_embeddings` module-level singleton).

When adding OpenAI/Gemini embedding providers, apply the same singleton pattern:
one instance per provider per process lifetime, initialized lazily on first use.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Using EventSource for POST Requests

**What goes wrong:** Developer uses `new EventSource('/api/chat')` instead of `fetch`.
`EventSource` sends a GET with no body — the chat message is lost, endpoint returns 405.

**Prevention:** Always use `fetch` + `ReadableStream` for SSE over POST. Document this
explicitly in the frontend API module.

### Anti-Pattern 2: Switching Embedding Models Mid-Project

**What goes wrong:** User ingests documents with `all-MiniLM-L6-v2` (384-dim vectors), then
switches to `text-embedding-3-small` (1536-dim vectors) in Settings. Similarity search runs
a 1536-dim query against 384-dim indexed vectors — ChromaDB returns dimension mismatch error
or silently returns garbage results.

**Prevention:** For this milestone, use a single global embedding model configured at startup
(env var or Settings field that affects all new ingestion). Display a warning in the UI:
"Changing the embedding model requires re-processing all documents." Implement per-project
embedding lock (storing the model name in the Project row) as a future phase.

### Anti-Pattern 3: CWD-Relative ChromaDB Path

**What goes wrong:** `PersistentClient(path="./chroma_db")` resolves relative to wherever
the FastAPI process was started from. If the dev runs the server from `backend/app/` instead
of `backend/`, the data is stored in a different directory and all collections appear empty.

**Prevention:** Use an absolute path anchored to the source file:
```python
import os
CHROMADB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../chroma_db")
```

### Anti-Pattern 4: Missing page_number in ChromaDB Metadata

**What goes wrong:** Citation display in the UI shows `page: null` for all citations.
The page number exists in unstructured's element metadata but is not carried through to
the ChromaDB `metadatas` dict during ingestion.

**Prevention:** Extract `element.metadata.page_number` from each unstructured Element
and include it in the metadata dict passed to `vector_store.insert_documents()`. This
is easy to add during ingestion and impossible to reconstruct later without re-parsing.

### Anti-Pattern 5: LangChain High-Level RAG Chains

**What goes wrong:** Developer uses `RetrievalQA.from_chain_type()` or
`ConversationalRetrievalChain`. The chain abstracts away the ChromaDB query results,
making citation metadata (filename, page_number, chunk_index) inaccessible without
patching internal chain state.

**Prevention:** Use the direct pattern (Pattern 3 above). LangChain's value in this
project is only: text splitting, `ChatPromptTemplate`, and `.astream()` on LLM providers.
Nothing else.

### Anti-Pattern 6: Blocking the Async Event Loop During Image Summarization

**What goes wrong:** If `image_processor.summarize()` is called from an `async def`
context using a synchronous HTTP client, it blocks the FastAPI event loop and freezes
all other requests during Gemini API call latency.

**Prevention:** Image summarization runs inside `process_and_update_document()`, which is
a synchronous function invoked by BackgroundTask in a thread pool — blocking there is fine.
If this is ever refactored into an `async def`, switch to `llm.ainvoke()` (LangChain async).

---

## Suggested Build Order

Build order is determined by dependencies. Each step is independently testable before the next.

```
Step 1: image_processor.py [NEW]
  No dependencies on other new components.
  Input: image file path. Output: text summary string.
  Test: unit test with a sample PNG, mock Gemini API.

Step 2: Extend document_parser.py [EXTEND]
  Depends on: image_processor (step 1)
  Wire real unstructured.partition() — uncomment the commented-out code.
  Call image_processor.summarize() for each extracted image path.
  Merge text chunks + image summaries into single all_chunks list.
  Ensure page_number is extracted from element.metadata.page_number.
  Test: integration test with sample PDF/DOCX files.

Step 3: Extend vector_store.py [EXTEND — minor]
  Depends on: updated metadata schema from step 2.
  Ensure similarity_search returns distances alongside documents.
  Add distance-based filtering (discard results with distance > 0.3).
  Verify metadata includes: filename, page_number, chunk_index, type.
  Test: unit test with ChromaDB in-memory mode (PersistentClient with temp dir).

Step 4: Extend embeddings.py [EXTEND]
  Add OpenAI (text-embedding-3-small) and Google (text-embedding-004) providers.
  Maintain singleton pattern per provider.
  All providers must implement embed_documents() and embed_query().
  Test: unit tests with mocked API clients.

Step 5: Extend llm_provider.py [EXTEND]
  Add streaming=True parameter to factory.
  Ensure all providers return a model that supports .astream().
  Test: unit tests with mocked LangChain models.

Step 6: rag_chain.py [NEW]
  Depends on: vector_store (step 3), embeddings (step 4), llm_provider (step 5).
  build_prompt(query, retrieved_chunks) -> formatted string.
  stream_rag_response(query, chunks, llm) -> AsyncIterator[dict].
  Test: integration test calling ChromaDB + mock LLM, verify SSE event shape.

Step 7: chat_service.py [NEW]
  Depends on: rag_chain (step 6).
  Thin adapter: validate ChatRequest, instantiate providers, delegate to rag_chain.
  Test: unit test with mocked rag_chain.

Step 8: chat.py router [NEW]
  Depends on: chat_service (step 7).
  POST /api/chat -> StreamingResponse with text/event-stream.
  Register in main.py: app.include_router(chat_router, prefix="/api").
  Test: httpx async client test streaming the full SSE response.

Step 9: Frontend SSE client [EXTEND]
  Depends on: chat.py router live (step 8).
  fetch() + ReadableStream parser in ChatArea component.
  Parse token events (append to message buffer) and citations event (render sources).
  Test: manual E2E with a real uploaded document.
```

Steps 1-5 can be developed and tested in parallel. Steps 6-7 depend on 3-5.
Step 8 depends on 7. Step 9 depends on 8.

---

## Scalability Considerations

| Concern | Current scale (local, 1 user) | Future concern |
|---------|-------------------------------|----------------|
| Ingestion speed | BackgroundTask thread pool is fine | Many large PDFs with many images need a task queue (Celery, ARQ) |
| Gemini Vision calls per document | Sequential, 1 API call per image | Cache summaries in Document.metadata_json to avoid re-processing on re-upload |
| ChromaDB write concurrency | Single writer, sequential uploads acceptable | Multiple concurrent uploads to same collection need per-project asyncio.Lock |
| Embedding model memory | One singleton ~90MB at startup | Multiple embedding model singletons — add a model registry with lazy loading |
| SSE connection lifetime | FastAPI handles single long-lived response correctly | For multi-user, add connection timeout and max concurrent SSE stream limits |
| ChromaDB collection size | Typical document = 50-500 chunks; no concern | Degrades above ~100K vectors in embedded mode; move to ChromaDB server mode |

---

## Sources

- Existing codebase: `backend/app/services/document_parser.py`, `vector_store.py`,
  `embeddings.py`, `llm_provider.py` (HIGH confidence — direct file reads)
- `.planning/PROJECT.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/INTEGRATIONS.md`
  (HIGH confidence — authoritative project context)
- `.planning/research/STACK.md` (HIGH confidence — verified stack decisions from parallel research)
- FastAPI StreamingResponse + SSE pattern: established, stable FastAPI core feature
  (HIGH confidence)
- LangChain `.astream()` interface: consistent across langchain-openai, langchain-anthropic,
  langchain-google-genai (MEDIUM confidence — verify against installed versions in requirements.txt)
- Gemini Vision multimodal message format: base64 image URL pattern
  (MEDIUM confidence — verify current SDK docs for exact message structure)
