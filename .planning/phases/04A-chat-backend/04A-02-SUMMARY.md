---
phase: 04A-chat-backend
plan: "02"
subsystem: backend
tags: [rag, chat, sse, streaming, llm, chromadb, citations]
dependency_graph:
  requires:
    - backend/app/schemas/domain.py::ChatRequest (Plan 01)
    - backend/app/schemas/domain.py::CitationItem (Plan 01)
    - backend/app/services/llm_provider.py::LLMProviderFactory.get_llm(streaming) (Plan 01)
    - backend/app/services/vector_store.py::similarity_search_mmr
    - backend/app/services/embeddings.py::EmbeddingFactory
  provides:
    - backend/app/services/rag_chain.py::build_context_with_citations
    - backend/app/services/rag_chain.py::chat_prompt
    - backend/app/services/rag_chain.py::RAG_SYSTEM_PROMPT
    - backend/app/routers/chat.py::router (POST /api/chat)
  affects:
    - backend/app/main.py (chat router mounted)
tech_stack:
  added: []
  patterns:
    - LCEL ChatPromptTemplate (system + human pair, no RetrievalQA)
    - AsyncGenerator SSE streaming with StreamingResponse
    - asyncio.to_thread for synchronous ChromaDB calls
    - Citation markers [1]..[N] embedded in context string
    - Error-as-SSE-event pattern (no silent disconnect, no HTTPException mid-stream)
key_files:
  created:
    - backend/app/services/rag_chain.py
    - backend/app/routers/chat.py
  modified:
    - backend/app/main.py
    - backend/tests/test_rag_chain.py
    - backend/tests/test_chat_router.py
    - backend/app/schemas/domain.py
decisions:
  - ChatPromptTemplate used directly (not RetrievalQA) for full control over context formatting
  - asyncio.to_thread wraps synchronous similarity_search_mmr to avoid blocking uvicorn event loop (T-4a-06)
  - Error mid-stream yields SSE error event instead of HTTPException — client can always parse the stream
  - LLM error message forwarded directly to error SSE event; logger.exception logs full traceback server-side (T-4a-04)
  - context_str falls back to 'No relevant documents found.' when MMR returns empty (CHAT-05 correctness)
metrics:
  duration: ~15min
  completed: 2026-04-09
  tasks_completed: 2
  files_modified: 6
---

# Phase 4A Plan 02: RAG Chain + SSE Chat Endpoint Summary

**One-liner:** RAG chain with citation-marker context builder and ChatPromptTemplate, plus POST /api/chat that streams LLM output as SSE events with a terminal citation event.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | RAG chain service — context builder + prompt template | e9c4e64 | rag_chain.py, test_rag_chain.py, domain.py (bug fix) |
| 2 | Chat router with SSE streaming + mount + integration tests | 1b2c238 | chat.py, main.py, test_chat_router.py |

## What Was Built

### RAG Chain Service (`rag_chain.py`)

- `build_context_with_citations(chunks)` — numbers each chunk `[1]...[N]`, extracts `filename`, `page_number`, `chunk_index` from metadata, returns `(context_str, citations_list)`. Missing metadata fields default to `''` / `0`.
- `RAG_SYSTEM_PROMPT` — instructs LLM to answer from context only and use citation markers.
- `chat_prompt` — `ChatPromptTemplate.from_messages([('system', RAG_SYSTEM_PROMPT), ('human', '{question}')])`. Pure LCEL, no RetrievalQA.

### Chat Router (`chat.py`)

- `POST /api/chat` — accepts `ChatRequest`, returns `StreamingResponse(media_type='text/event-stream')`.
- SSE headers: `X-Accel-Buffering: no`, `Cache-Control: no-cache`.
- Pipeline:
  1. `EmbeddingFactory.get_embedding_model(provider, api_key)` — get embedding model.
  2. `asyncio.to_thread(vector_store.similarity_search_mmr, ...)` — MMR search (sync -> async).
  3. `build_context_with_citations(chunks)` — build context + citations.
  4. `chat_prompt.format_messages(context, question)` — format prompt.
  5. `LLMProviderFactory.get_llm(provider, streaming=True)` — get streaming LLM.
  6. `async for chunk in llm.astream(messages)` — stream `data: {"text": "..."}` events.
  7. Terminal event: `data: {"done": true, "citations": [...]}`.
  8. Exception handler: `data: {"error": "..."}` — never silent disconnect.

### main.py Updated

- Import: `from app.routers import projects, documents, search, chat`
- Mount: `app.include_router(chat.router)`

## Verification Results

```
tests/test_rag_chain.py: 7 passed
tests/test_chat_router.py: 8 passed
Full suite: 99 passed, 0 failures, 0 regressions
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restored missing Search schemas from domain.py**
- **Found during:** Task 1, when running initial tests (conftest import failed)
- **Issue:** Plan 01 commit `725a161` rewrote `domain.py` and dropped `SearchResult`, `SearchResponse`, `ReindexResponse` that were added in commit `32f13ac` (Phase 03C). The `search.py` router imports these at module level, causing `ImportError` when conftest loaded `app.main`.
- **Fix:** Re-added all three schema classes to `domain.py` using definitions from commit `32f13ac`.
- **Files modified:** `backend/app/schemas/domain.py`
- **Commit:** e9c4e64

### Scope boundary

No out-of-scope issues deferred.

## Known Stubs

None — `build_context_with_citations` wires real MMR results to real citations. The SSE stream flows real LLM output to the client. No hardcoded or placeholder data flows to the UI.

## Threat Flags

No new security-relevant surfaces beyond those in the plan's threat model:
- `POST /api/chat` trust boundary already documented in threat model (T-4a-01 through T-4a-07).
- All mitigations implemented: `max_length=10000` (T-4a-01/03), `asyncio.to_thread` (T-4a-06), `logger.exception` + generic error string (T-4a-04), `project_id` integer only (T-4a-07).

## Self-Check: PASSED

- `backend/app/services/rag_chain.py` exists: YES
- `backend/app/routers/chat.py` exists: YES
- `backend/app/main.py` contains `chat` (import + include_router): YES (count=2)
- `backend/tests/test_rag_chain.py` has 0 pytest.skip: YES
- `backend/tests/test_chat_router.py` has 0 pytest.skip: YES
- Commit e9c4e64 exists: YES
- Commit 1b2c238 exists: YES
- Full suite: 99 passed, 0 failures: YES
