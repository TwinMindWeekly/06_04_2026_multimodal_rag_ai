---
phase: 04A-chat-backend
verified: 2026-04-09T00:00:00Z
status: human_needed
score: 13/13 must-haves verified (automated); 2 ROADMAP success criteria require human testing
overrides_applied: 0
human_verification:
  - test: "Gửi POST /api/chat với API key thực của OpenAI, yêu cầu câu hỏi về tài liệu đã upload"
    expected: "Response stream có SSE events với text chunks trích dẫn nội dung từ tài liệu, terminal event có citations array có filename và page_number thực"
    why_human: "Cần API key thực và tài liệu đã được ingested vào ChromaDB — không thể mock trong automated test"
  - test: "Thử lần lượt với provider=gemini, provider=claude, provider=ollama (với key/URL tương ứng)"
    expected: "Mỗi provider trả về SSE stream hợp lệ với text và citations"
    why_human: "Multi-provider smoke test cần real credentials — không thể verify programmatically"
---

# Phase 4A: Chat Backend — Verification Report

**Phase Goal:** POST to /api/chat -> get SSE-streamed AI response grounded in project documents with citations.
**Verified:** 2026-04-09
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /api/chat với ChatRequest hợp lệ trả về HTTP 200 với content-type text/event-stream | VERIFIED | test_chat_returns_200_sse PASSED; router.routes = [({'POST'}, '/api/chat')] |
| 2 | SSE stream chứa `data: {"text": "..."}` events cho mỗi LLM chunk | VERIFIED | test_sse_text_chunks PASSED; chat.py dòng 73: `yield f'data: {json.dumps({"text": chunk.content})}'` |
| 3 | SSE stream kết thúc với `data: {"done": true, "citations": [...]}` terminal event | VERIFIED | test_sse_terminal_event PASSED; chat.py dòng 76: terminal event được yield sau vòng lặp astream |
| 4 | Citations trong terminal event chứa filename, page_number, chunk_index, marker cho mỗi source chunk | VERIFIED | test_citation_metadata_forwarded PASSED; build_context_with_citations() extract đầy đủ từ metadata |
| 5 | LLM error mid-stream tạo ra `data: {"error": "..."}` SSE event thay vì silent disconnect | VERIFIED | test_sse_error_event_on_llm_failure PASSED; chat.py dòng 78-81: except block yields error event |
| 6 | RAG chain embeds query, tìm kiếm ChromaDB với MMR, xây dựng context với citation markers [1]..[N] | VERIFIED | build_context_with_citations() spot-check PASSED; asyncio.to_thread wraps similarity_search_mmr |
| 7 | Prompt dùng ChatPromptTemplate (KHÔNG phải RetrievalQA) với cặp system+human messages | VERIFIED | test_prompt_no_retrieval_qa PASSED; grep "RetrievalQA" rag_chain.py = 0 |
| 8 | Synchronous ChromaDB call được wrap trong asyncio.to_thread | VERIFIED | chat.py dòng 42: `chunks = await asyncio.to_thread(vector_store.similarity_search_mmr, ...)` |
| 9 | langchain-google-genai và langchain-anthropic được cài và importable | VERIFIED | `from langchain_google_genai import ChatGoogleGenerativeAI` OK; `from langchain_anthropic import ChatAnthropic` OK |
| 10 | ChatRequest schema validate message, project_id, provider, embedding_provider là các field riêng biệt | VERIFIED | domain.py: ChatRequest có embedding_provider và provider là 2 field độc lập |
| 11 | CitationItem schema chứa filename, page_number, chunk_index, marker | VERIFIED | domain.py dòng 71-76: CitationItem đầy đủ các field |
| 12 | LLMProviderFactory.get_llm() chấp nhận streaming param và truyền cho ChatOpenAI/ChatAnthropic | VERIFIED | streaming=True trong signature; ChatOpenAI và ChatAnthropic nhận streaming=streaming |
| 13 | Chat router được mount trong main.py | VERIFIED | main.py dòng 52-57: `from app.routers import ... chat` và `app.include_router(chat.router)` |

**Score automated:** 13/13 truths verified

### Deferred Items

Không có deferred items — tất cả requirements CHAT-01..07 được implemented trong phase này.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/services/rag_chain.py` | context builder + prompt template (>=40 lines) | VERIFIED | 53 lines; exports build_context_with_citations, chat_prompt, RAG_SYSTEM_PROMPT |
| `backend/app/routers/chat.py` | POST /api/chat SSE endpoint (>=60 lines) | VERIFIED | 94 lines; exports router; StreamingResponse với text/event-stream |
| `backend/app/main.py` | chat router mounted | VERIFIED | dòng 52: import chat; dòng 57: app.include_router(chat.router) |
| `backend/app/schemas/domain.py` | ChatRequest, CitationItem Pydantic models | VERIFIED | cả hai class hiện diện với đầy đủ fields |
| `backend/app/services/llm_provider.py` | streaming=True support | VERIFIED | streaming: bool = True trong get_llm() signature |
| `backend/tests/test_rag_chain.py` | Unit tests (>=60 lines) | VERIFIED | 67 lines; 7 tests, 0 skips, 7/7 PASSED |
| `backend/tests/test_chat_router.py` | Integration tests (>=80 lines) | VERIFIED | 150 lines; 8 tests, 0 skips, 8/8 PASSED |
| `backend/requirements.txt` | langchain-google-genai + langchain-anthropic | VERIFIED | 1 entry mỗi loại trong file |
| `backend/locales/en.json` | chat_* i18n keys | VERIFIED | 4 keys: chat_message_required, chat_provider_error, chat_embedding_error, chat_stream_error |
| `backend/locales/vi.json` | chat_* i18n keys (Vietnamese) | VERIFIED | 4 keys tương ứng trong tiếng Việt |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/routers/chat.py` | `backend/app/services/rag_chain.py` | `from app.services.rag_chain import build_context_with_citations, chat_prompt` | VERIFIED | dòng 17 trong chat.py |
| `backend/app/routers/chat.py` | `backend/app/services/vector_store.py` | `asyncio.to_thread(vector_store.similarity_search_mmr, ...)` | VERIFIED | dòng 42-50 trong chat.py |
| `backend/app/routers/chat.py` | `backend/app/services/llm_provider.py` | `LLMProviderFactory.get_llm(streaming=True)` | VERIFIED | dòng 62-68 trong chat.py |
| `backend/app/routers/chat.py` | `backend/app/services/embeddings.py` | `EmbeddingFactory.get_embedding_model` | VERIFIED | dòng 36-39 trong chat.py |
| `backend/app/main.py` | `backend/app/routers/chat.py` | `app.include_router(chat.router)` | VERIFIED | dòng 52 + 57 trong main.py |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `chat.py` → SSE stream | `chunks` | `vector_store.similarity_search_mmr()` | YES — queries ChromaDB với embedding model thực | FLOWING |
| `chat.py` → SSE stream | `citations` | `build_context_with_citations(chunks)` | YES — extract từ chunk metadata thực | FLOWING |
| `chat.py` → SSE text events | `chunk.content` | `llm.astream(messages)` | YES — streamed từ LLM thực (mock trong tests, real trong production) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| build_context_with_citations([]) = ('', []) | Python import + assert | OK | PASS |
| Single chunk tạo ra [1] marker | Python import + assert | OK | PASS |
| chat_prompt format_messages chứa context và question | Python import + assert | OK | PASS |
| RAG_SYSTEM_PROMPT chứa 'citation markers' | grep count = 2 | OK | PASS |
| POST /api/chat registered trong app | router.routes check | ({'POST'}, '/api/chat') | PASS |
| Full test suite 99 passed, 0 failures | pytest tests/ -q | 99 passed, 25 warnings | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CHAT-01 | 04A-01, 04A-02 | POST /api/chat endpoint accepting message, project_id, provider settings | SATISFIED | ChatRequest schema + router.post('/api/chat') |
| CHAT-02 | 04A-02 | RAG chain: embed query -> ChromaDB search -> build context with citation markers | SATISFIED | _generate_sse_events() full pipeline; asyncio.to_thread wraps search |
| CHAT-03 | 04A-02 | ChatPromptTemplate (not RetrievalQA) | SATISFIED | chat_prompt = ChatPromptTemplate.from_messages([...]); RetrievalQA count = 0 |
| CHAT-04 | 04A-02 | SSE streaming via StreamingResponse với X-Accel-Buffering=no, Cache-Control=no-cache | SATISFIED | chat.py dòng 87-93: StreamingResponse với headers đúng |
| CHAT-05 | 04A-02 | SSE format: text chunks + terminal done event | SATISFIED | test_sse_text_chunks + test_sse_terminal_event PASSED |
| CHAT-06 | 04A-02 | Error events mid-stream thay vì silent disconnect | SATISFIED | except block yields `data: {"error": "..."}` |
| CHAT-07 | 04A-01, 04A-02 | Citation metadata: page_number, filename, chunk_index | SATISFIED | CitationItem schema + build_context_with_citations() extract metadata |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/app/schemas/domain.py` | 15,26,40 | `class Config:` deprecated Pydantic V2 style | Info | Pydantic deprecation warning; chỉ ảnh hưởng ProjectResponse, FolderResponse, DocumentResponse — không thuộc scope phase 4A |

Không có anti-pattern nào trong các file thuộc scope phase 4A (rag_chain.py, chat.py, test_rag_chain.py, test_chat_router.py).

### Human Verification Required

**1. End-to-end với real LLM providers**

**Test:** Gửi POST request đến /api/chat với real OpenAI API key và project có tài liệu đã được ingested:
```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the main topic of this document?", "project_id": 1, "provider": "openai", "api_key": "sk-..."}'
```
**Expected:** Stream SSE events với text chunks trích dẫn nội dung thực từ tài liệu; terminal event có `citations` array với `filename` và `page_number` thực.
**Why human:** Cần API key thực + ChromaDB đã được populated với document chunks từ Phase 3b/3c.

**2. Multi-provider smoke test**

**Test:** Thử provider=gemini, provider=claude, provider=ollama với credentials tương ứng
**Expected:** Mỗi provider trả về SSE stream hợp lệ (không crash, có text events)
**Why human:** Cần real API keys/running Ollama instance — không thể mock được tất cả behavior trong automated tests.

### Gaps Summary

Không có gaps kỹ thuật. Tất cả 13 truths đã được verified bằng automated tests và code inspection. Hai ROADMAP success criteria còn lại ("Response text references content from uploaded documents" và "Works with OpenAI, Gemini, Claude, and Ollama providers") là behavioral checks cần real credentials và running infrastructure — chúng không thể được verified programmatically mà không có API keys thực.

---

_Verified: 2026-04-09T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
