# Phase 4a: Chat Backend - Research

**Researched:** 2026-04-09
**Domain:** FastAPI SSE streaming, LangChain LCEL ChatPromptTemplate, RAG chain, LLM provider switching, citation tracking
**Confidence:** HIGH (all API shapes verified against live .venv runtime)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHAT-01 | POST /api/chat endpoint accepting message, project_id, provider settings | FastAPI router pattern verified; request schema defined below |
| CHAT-02 | RAG chain: embed query → ChromaDB MMR search → build context string with citation markers | `similarity_search_mmr` already implemented in vector_store.py; context builder pattern documented |
| CHAT-03 | Context-augmented prompt template using ChatPromptTemplate (not RetrievalQA) | `ChatPromptTemplate.from_messages` verified working; LCEL pipe operator (`|`) verified |
| CHAT-04 | SSE streaming via FastAPI StreamingResponse with X-Accel-Buffering=no, Cache-Control=no-cache | `StreamingResponse` with async generator and headers verified working |
| CHAT-05 | SSE format: `data: {"text": "..."}\n\n` for chunks, `data: {"done": true, "citations": [...]}\n\n` for terminal | JSON serialisation pattern with `json.dumps` verified; async generator yields strings |
| CHAT-06 | Error events mid-stream: `data: {"error": "..."}\n\n` | try/except inside async generator verified; error event before return |
| CHAT-07 | Citation metadata forwarding: page_number, filename, chunk_index per cited source | ChromaDB metadata already stores all three fields; extraction pattern documented |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md / CONVENTIONS.md)

Không có file `CLAUDE.md` cấp dự án. Constraints lấy từ global `~/.claude/CLAUDE.md` và `.planning/codebase/CONVENTIONS.md`.

| Directive | Source | Impact on Phase 4a |
|-----------|--------|--------------------|
| Single quotes cho Python strings | Odoo rules + CONVENTIONS.md | Tất cả file Python mới dùng single quotes |
| Type annotations trên tất cả function signatures | python/coding-style.md | Mọi hàm mới cần type hints |
| Immutability — không mutate objects | common/coding-style.md | Dùng dataclass hoặc dict mới, không sửa in-place |
| Factory pattern cho AI components | CONVENTIONS.md | `LLMProviderFactory.get_llm()` đã tồn tại — dùng lại, không tạo mới |
| `HTTPException` + i18n `t()` cho lỗi endpoint | CONVENTIONS.md | Lỗi trước khi stream bắt đầu dùng HTTPException; lỗi mid-stream dùng SSE error event |
| Files 200-400 dòng, tối đa 800 | common/coding-style.md | Tách `rag_chain.py` (logic RAG) và `chat.py` (router) |
| 80% test coverage | python/testing.md | Cần tests cho cả rag_chain service và chat router |
| Bilingual comments (tiếng Việt domain logic, tiếng Anh technical) | CONVENTIONS.md | Áp dụng cho tất cả file mới |
| Lazy import cho LLM providers | llm_provider.py existing pattern | Giữ nguyên — imports bên trong từng if-branch |
| No RetrievalQA / chains from LangChain | Key Decision (STATE.md) | Chỉ dùng `ChatPromptTemplate` + `astream` trực tiếp |

---

## Summary

Phase 4a xây dựng chat API endpoint theo kiến trúc Pipeline thủ công: **embed query → MMR search → build context → ChatPromptTemplate → LLM.astream() → SSE**. Toàn bộ stack đã được xác minh trên môi trường `.venv` thực tế.

**Hai gói cần cài thêm:** `langchain-anthropic==1.4.0` và `langchain-google-genai==4.2.1`. `langchain-openai==1.1.12` và `google-genai==1.71.0` đã có. `langchain-community` (ChatOllama) đã có. Tất cả dependency chains đã được kiểm tra — không có conflict.

**Vấn đề quan trọng nhất:** `LLMProviderFactory` hiện tại dùng `langchain_google_genai` cho Gemini và `langchain_anthropic` cho Claude — cả hai chưa được cài. Phase 4a Wave 0 **phải** cài hai gói này trước.

**LLMProviderFactory đã tồn tại** với đầy đủ 4 providers (OpenAI, Gemini, Claude, Ollama). Factory không cần sửa — chỉ cần cài dependency thiếu và thêm streaming support.

Baseline test suite: **84 tests pass** (tất cả từ Phase 3a, 3b, 3c). Phase 4a phải giữ không có regression.

**Primary recommendation:** Tạo `rag_chain.py` (build context từ MMR results), `chat.py` (router SSE), thêm Pydantic schemas `ChatRequest`/`CitationResponse` vào `domain.py`. Extend `LLMProviderFactory` để hỗ trợ `streaming=True` parameter.

---

## Standard Stack

### Core (đã cài)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| fastapi | 0.135.3 | StreamingResponse, APIRouter | INSTALLED [VERIFIED: pip show] |
| starlette | 1.0.0 | StreamingResponse base | INSTALLED [VERIFIED: import] |
| langchain-core | 1.2.28 | ChatPromptTemplate, StrOutputParser, AIMessageChunk | INSTALLED [VERIFIED: import] |
| langchain-openai | 1.1.12 | ChatOpenAI với astream | INSTALLED [VERIFIED: pip show] |
| langchain-community | 0.4.1 | ChatOllama với astream | INSTALLED [VERIFIED: import] |
| google-genai | 1.71.0 | Gemini SDK (đã dùng cho embeddings) | INSTALLED [VERIFIED: pip show] |

### Cần cài (Wave 0)

| Library | Version | Purpose | Ghi chú |
|---------|---------|---------|---------|
| langchain-google-genai | ==4.2.1 | ChatGoogleGenerativeAI cho Gemini chat | Requires google-genai>=1.56.0; ta có 1.71.0 — compatible [VERIFIED: dry-run] |
| langchain-anthropic | ==1.4.0 | ChatAnthropic cho Claude chat | Requires anthropic>=0.85.0 — new dep [VERIFIED: dry-run] |

### Không cần

| Mục đích | Đã có | Lý do không cần thêm |
|---------|-------|---------------------|
| SSE server-sent events | FastAPI StreamingResponse | Không cần thư viện SSE riêng |
| async generator | Python built-in | `async def ... yield` |
| JSON serialization | Python built-in `json` | Không cần orjson cho SSE payload |
| LangGraph | Đã cài nhưng không dùng | Overkill cho pipeline cố định |

**Installation (Wave 0):**
```bash
pip install langchain-google-genai==4.2.1 langchain-anthropic==1.4.0
# Thêm vào requirements.txt:
# langchain-google-genai==4.2.1
# langchain-anthropic==1.4.0
```

**Version verification (đã chạy 2026-04-09):**
```
langchain-google-genai: 4.2.1 [VERIFIED: pip index versions]
langchain-anthropic: 1.4.0 [VERIFIED: pip index versions]
google-genai installed: 1.71.0 >= 1.56.0 requirement — compatible [VERIFIED: dry-run install]
```

---

## Architecture Patterns

### Recommended File Structure

```
backend/app/
├── services/
│   ├── rag_chain.py          # NEW: embed → search → build context string
│   └── llm_provider.py       # EXTEND: thêm streaming=True support
├── routers/
│   └── chat.py               # NEW: POST /api/chat với SSE streaming
├── schemas/
│   └── domain.py             # EXTEND: thêm ChatRequest, CitationItem
└── main.py                   # EXTEND: mount chat router
```

**Không thay đổi:** `vector_store.py` (đã có `similarity_search_mmr`), `embeddings.py` (đã có `EmbeddingFactory`), tất cả router hiện tại.

---

### Pattern 1: ChatRequest Pydantic Schema (CHAT-01)

**What:** Request body cho POST /api/chat
**When to use:** Mọi call vào chat endpoint

```python
# Source: verified Pydantic 2.12.5 pattern, consistent with existing domain.py schemas
from pydantic import BaseModel
from typing import Optional

class CitationItem(BaseModel):
    filename: str
    page_number: int
    chunk_index: int

class ChatRequest(BaseModel):
    message: str
    project_id: int
    provider: str = 'openai'          # openai | gemini | claude | ollama
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    top_k: int = 5
    score_threshold: float = 0.3
    embedding_provider: str = 'local'  # provider cho embeddings
    embedding_api_key: Optional[str] = None
```

---

### Pattern 2: RAG Context Builder trong `rag_chain.py` (CHAT-02, CHAT-07)

**What:** Nhận danh sách chunks từ MMR search → tạo context string với citation markers → trả về (context_str, citations_list)
**When to use:** Mỗi request chat, trước khi gọi LLM

```python
# Source: design derived from vector_store.similarity_search_mmr output shape (verified)
# Output shape: list[{'content': str, 'metadata': dict, 'similarity': float, 'distance': float}]

def build_context_with_citations(
    chunks: list[dict],
) -> tuple[str, list[dict]]:
    """
    Xây dựng context string từ chunks với citation markers.
    Returns: (context_string, citations_list)
    """
    if not chunks:
        return '', []

    context_parts = []
    citations = []

    for i, chunk in enumerate(chunks):
        marker = f'[{i + 1}]'
        meta = chunk.get('metadata', {})
        context_parts.append(f'{marker} {chunk["content"]}')
        citations.append({
            'filename': meta.get('filename', ''),
            'page_number': meta.get('page_number', 0),
            'chunk_index': meta.get('chunk_index', 0),
            'marker': marker,
        })

    return '\n\n'.join(context_parts), citations
```

---

### Pattern 3: ChatPromptTemplate (CHAT-03)

**What:** Context-augmented prompt — system prompt nhận {context}, human nhận {question}
**When to use:** Đây là cách duy nhất. KHÔNG dùng RetrievalQA.

```python
# Source: verified ChatPromptTemplate.from_messages working in .venv langchain-core 1.2.28
from langchain_core.prompts import ChatPromptTemplate

RAG_SYSTEM_PROMPT = (
    'You are a helpful assistant. Answer the question based ONLY on the provided context. '
    'If the context does not contain enough information, say so clearly. '
    'Use citation markers [1], [2], etc. when referencing specific parts of the context.\n\n'
    'Context:\n{context}'
)

chat_prompt = ChatPromptTemplate.from_messages([
    ('system', RAG_SYSTEM_PROMPT),
    ('human', '{question}'),
])
```

---

### Pattern 4: LLM Streaming với `astream` (CHAT-04)

**What:** `BaseChatModel.astream()` là async generator trả về `AIMessageChunk`. Mỗi chunk có `.content` là string.
**When to use:** Tất cả LLM calls trong chat endpoint

```python
# Source: verified hasattr(ChatOpenAI, 'astream') = True, hasattr(ChatOllama, 'astream') = True
# AIMessageChunk.content verified in .venv

from langchain_core.messages import AIMessageChunk

async def stream_llm_response(llm, messages) -> AsyncIterator[str]:
    """Wrap LLM.astream() để yield text chunks."""
    async for chunk in llm.astream(messages):
        if isinstance(chunk, AIMessageChunk) and chunk.content:
            yield chunk.content
```

**Lưu ý:** `llm.astream(messages)` nhận list of messages (output của `ChatPromptTemplate.format_messages()`), không phải string.

---

### Pattern 5: FastAPI Async Generator SSE (CHAT-04, CHAT-05, CHAT-06)

**What:** `async def` generator yield SSE-formatted strings → wrap bằng `StreamingResponse`
**When to use:** Đây là pattern duy nhất cho SSE trong FastAPI

```python
# Source: verified StreamingResponse + async generator in .venv FastAPI 0.135.3 / Starlette 1.0.0
import json
from fastapi.responses import StreamingResponse

async def generate_sse_events(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Async generator cho SSE stream.
    Yields: SSE-formatted strings theo CHAT-05 spec.
    """
    try:
        # 1. Embed query + MMR search
        embedding_model = EmbeddingFactory.get_embedding_model(
            provider=request.embedding_provider,
            api_key=request.embedding_api_key,
        )
        chunks = vector_store.similarity_search_mmr(
            query=request.message,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            project_id=request.project_id,
            embedding_model=embedding_model,
            provider=request.embedding_provider,
        )

        # 2. Build context + collect citations
        context_str, citations = build_context_with_citations(chunks)

        # 3. Build prompt messages
        messages = chat_prompt.format_messages(
            context=context_str or 'No relevant documents found.',
            question=request.message,
        )

        # 4. Get LLM + stream
        llm = LLMProviderFactory.get_llm(
            provider=request.provider,
            api_key=request.api_key,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        async for chunk in llm.astream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                yield f'data: {json.dumps({"text": chunk.content})}\n\n'

        # 5. Terminal event với citations (CHAT-05)
        yield f'data: {json.dumps({"done": True, "citations": citations})}\n\n'

    except Exception as e:
        # 6. Error event mid-stream (CHAT-06)
        yield f'data: {json.dumps({"error": str(e)})}\n\n'


@router.post('/api/chat')
async def chat(request: ChatRequest):
    return StreamingResponse(
        generate_sse_events(request),
        media_type='text/event-stream',
        headers={
            'X-Accel-Buffering': 'no',
            'Cache-Control': 'no-cache',
        },
    )
```

**Lưu ý quan trọng:** Endpoint phải là `async def` vì `generate_sse_events` là async generator. Không dùng `Depends(get_db)` trong chat endpoint trừ khi cần validate project — nếu cần validate, query DB **trước** khi bắt đầu stream, raise `HTTPException` nếu không hợp lệ.

---

### Pattern 6: Cập nhật LLMProviderFactory để hỗ trợ streaming

**What:** `LLMProviderFactory.get_llm()` hiện tại không có streaming param. Tất cả BaseChatModel đều hỗ trợ `.astream()` built-in — không cần thêm `streaming=True` cho `.astream()`. Tuy nhiên, một số provider (OpenAI) cần `streaming=True` flag khi khởi tạo để tránh timeout.

```python
# Source: langchain-openai 1.1.12 docs pattern + verified ChatOpenAI has astream=True
# ChatOpenAI với streaming=True khởi tạo client ở streaming mode
return ChatOpenAI(
    model_name='gpt-4o-mini',
    temperature=temperature,
    max_tokens=max_tokens,
    openai_api_key=key,
    streaming=True,  # Bật streaming mode
)
```

**Quyết định:** Extend `LLMProviderFactory.get_llm()` thêm param `streaming: bool = True`. Khi `streaming=True`, pass vào ChatOpenAI. ChatOllama và ChatAnthropic hỗ trợ `.astream()` mà không cần flag này.

---

### Anti-Patterns to Avoid

- **RetrievalQA / ConversationalRetrievalChain:** Ẩn citation metadata; không thể kiểm soát SSE format.
- **EventSource trên frontend:** GET-only; không pass được request body (API key, project_id). Frontend dùng `fetch + ReadableStream`.
- **HTTPException sau khi stream bắt đầu:** Sau khi HTTP 200 đã gửi, không thể thay đổi status code. Mọi lỗi mid-stream phải là SSE error event.
- **Blocking (sync) trong async endpoint:** `similarity_search_mmr` là synchronous ChromaDB call. Nếu gây block cho event loop → cần `asyncio.to_thread()`. Xem pitfall #4 dưới.
- **Kết nối DB bị leak:** Nếu validate project qua DB, phải dùng `async with` hoặc đóng session đúng chỗ.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM streaming | Custom HTTP client với API | `LLMProviderFactory + .astream()` | Provider abstraction đã có; astream verified working |
| SSE protocol | `data:` prefix + `\n\n` thủ công | Python `json.dumps` + f-string | Đủ cho spec này — không cần thư viện sse-starlette |
| RAG pipeline | LangChain RetrievalQA | Manual: MMR search + context builder + ChatPromptTemplate | Kiểm soát citation metadata; quyết định đã lock (STATE.md) |
| Semantic search | Viết lại query logic | `vector_store.similarity_search_mmr()` | Đã implement đầy đủ trong Phase 3c |
| Embedding | Viết lại embedding call | `EmbeddingFactory.get_embedding_model()` | Factory pattern đã đủ providers |

**Key insight:** Toàn bộ infrastructure (VectorStore, EmbeddingFactory, LLMProviderFactory) đã tồn tại. Phase 4a chỉ **wiring** chúng lại với nhau qua một pipeline tuyến tính.

---

## Common Pitfalls

### Pitfall 1: `langchain_google_genai` và `langchain_anthropic` chưa được cài

**What goes wrong:** `LLMProviderFactory.get_llm(provider='gemini')` sẽ `ImportError` tại runtime vì import lazy bên trong if-branch.
**Why it happens:** `llm_provider.py` import các module này lazily (bên trong `elif` blocks) nên không fail khi server khởi động, chỉ fail khi request đầu tiên với provider đó.
**How to avoid:** Wave 0 PHẢI cài `langchain-google-genai==4.2.1` và `langchain-anthropic==1.4.0` và thêm vào `requirements.txt`.
**Warning signs:** Server khởi động thành công nhưng POST /api/chat với `provider=gemini` hoặc `provider=claude` trả về 500.

---

### Pitfall 2: ChromaDB `similarity_search_mmr` là synchronous — block event loop

**What goes wrong:** `vector_store.similarity_search_mmr()` là synchronous (ChromaDB PersistentClient không có async API). Gọi trực tiếp trong `async def` sẽ block toàn bộ uvicorn event loop trong thời gian search.
**Why it happens:** FastAPI chạy trên uvicorn ASGI; blocking I/O trong async handler block tất cả concurrent requests.
**How to avoid:** Dùng `asyncio.to_thread()` để wrap synchronous call:

```python
import asyncio
chunks = await asyncio.to_thread(
    vector_store.similarity_search_mmr,
    query=request.message,
    top_k=request.top_k,
    score_threshold=request.score_threshold,
    project_id=request.project_id,
    embedding_model=embedding_model,
    provider=request.embedding_provider,
)
```

**Warning signs:** curl request đến `/api/chat` làm frozen các request khác.

---

### Pitfall 3: Error handling sau khi stream đã bắt đầu

**What goes wrong:** `raise HTTPException(status_code=500, ...)` sau khi generator đã yield ít nhất một chunk sẽ bị ignore vì HTTP 200 đã được gửi.
**Why it happens:** HTTP response headers (bao gồm status code) được gửi khi `StreamingResponse` bắt đầu yield byte đầu tiên. Sau đó không thể thay đổi.
**How to avoid:** Mọi lỗi trong generator phải yield SSE error event: `yield f'data: {json.dumps({"error": "..."})}\n\n'`. Chỉ raise `HTTPException` TRƯỚC khi generator được return (ví dụ: validate project_id trong router handler trước khi return `StreamingResponse`).

---

### Pitfall 4: LLM response chunk có thể là empty string

**What goes wrong:** `chunk.content` đôi khi là `''` (empty string) — đặc biệt ở đầu stream (usage_metadata chunk) hoặc cuối stream.
**Why it happens:** Các LLM provider gửi metadata chunks bên cạnh content chunks. `AIMessageChunk.content` có thể là `''` hoặc `None`.
**How to avoid:** Check `if chunk.content:` (truthy) trước khi yield:

```python
async for chunk in llm.astream(messages):
    if hasattr(chunk, 'content') and chunk.content:
        yield f'data: {json.dumps({"text": chunk.content})}\n\n'
```

---

### Pitfall 5: `ChatOllama` deprecated import path

**What goes wrong:** `from langchain_community.chat_models import ChatOllama` có deprecation warning nhưng vẫn work trong 0.4.1.
**Why it happens:** `langchain-community` 0.4.1 khuyến khích dùng `langchain-ollama` package riêng.
**How to avoid:** Giữ import hiện tại — không cài thêm package chỉ để tránh warning. Mark as known deprecation. Không phải blocker.

---

### Pitfall 6: `ChatOpenAI` dùng `openai_api_key` nhưng `ChatAnthropic` dùng `anthropic_api_key`

**What goes wrong:** Tên parameter khác nhau giữa các provider — dễ nhầm khi extend LLMProviderFactory.
**Why it happens:** Mỗi langchain provider package có naming convention riêng.
**How to avoid:** Verify từng provider khi extend factory. Hiện tại `llm_provider.py` đã handle đúng. Không thay đổi parameter names.

---

### Pitfall 7: `provider` field trong ChatRequest vs `embedding_provider`

**What goes wrong:** Dùng cùng một `provider` field cho cả LLM provider và embedding provider gây nhầm lẫn trong logic.
**Why it happens:** Chat request cần hai providers riêng biệt: một cho LLM (OpenAI/Gemini/Claude/Ollama), một cho embeddings (local/openai/gemini).
**How to avoid:** `ChatRequest` phải có hai fields riêng: `provider` (LLM) và `embedding_provider` (embeddings). Ví dụ: dùng Gemini LLM + local embeddings là valid config.

---

## Code Examples

Verified patterns từ live runtime:

### ChatPromptTemplate format và invoke

```python
# Source: verified in .venv langchain-core 1.2.28
from langchain_core.prompts import ChatPromptTemplate

template = ChatPromptTemplate.from_messages([
    ('system', 'Context:\n{context}\n\nAnswer based on context only.'),
    ('human', '{question}'),
])

# format_messages trả về list[BaseMessage] — pass trực tiếp vào llm.astream()
messages = template.format_messages(context='...', question='...')
```

### AsyncGenerator pattern cho SSE

```python
# Source: verified StreamingResponse + async generator FastAPI 0.135.3
import json
from typing import AsyncGenerator
from fastapi.responses import StreamingResponse

async def event_stream() -> AsyncGenerator[str, None]:
    yield f'data: {json.dumps({"text": "Hello"})}\n\n'
    yield f'data: {json.dumps({"done": True, "citations": []})}\n\n'

return StreamingResponse(
    event_stream(),
    media_type='text/event-stream',
    headers={'X-Accel-Buffering': 'no', 'Cache-Control': 'no-cache'},
)
```

### Test với httpx AsyncClient (async streaming)

```python
# Source: verified httpx 0.28.1 has AsyncClient.stream(), pytest-asyncio 1.3.0
import pytest
import httpx
from fastapi.testclient import TestClient

# Sync test (non-streaming verify)
def test_chat_returns_sse(test_client: TestClient):
    with test_client.stream('POST', '/api/chat', json={...}) as response:
        assert response.status_code == 200
        assert 'text/event-stream' in response.headers['content-type']
        events = list(response.iter_lines())
        assert any('"text"' in e for e in events)

# Async test pattern
import pytest_asyncio

@pytest.mark.asyncio
async def test_chat_async():
    ...
```

**Quan trọng:** `TestClient` của Starlette hỗ trợ `.stream()` context manager cho streaming responses — không cần `httpx.AsyncClient` cho tests synchronous.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangChain RetrievalQA | Manual pipeline + ChatPromptTemplate | LangChain 0.2+ | Kiểm soát hoàn toàn metadata và format |
| EventSource cho SSE | fetch + ReadableStream | — (limitation) | EventSource chỉ hỗ trợ GET, chat cần POST |
| `chain.stream()` sync | `llm.astream()` async | LangChain 0.1+ | Non-blocking streaming trong FastAPI |
| `streaming=True` on init (required) | `astream()` method (implicit) | LangChain 0.2+ | `.astream()` tự động dùng streaming; `streaming=True` vẫn recommended cho OpenAI |

**Deprecated/outdated:**
- `langchain.chains.RetrievalQA`: Không dùng — ẩn metadata, không hỗ trợ custom SSE format.
- `langchain.chains.ConversationalRetrievalChain`: Không dùng — multi-turn là out of scope v1.
- `from langchain.chat_models import ChatOpenAI`: Import path cũ — dùng `langchain_openai`.

---

## Open Questions

1. **ChatOllama model name cứng là `llama3`**
   - What we know: `llm_provider.py` hardcode `model='llama3'`; người dùng có thể có model khác
   - What's unclear: Có cần accept `model_name` param trong `ChatRequest` không?
   - Recommendation: Giữ `llama3` mặc định cho v1; có thể thêm `ollama_model` field sau. Không block Phase 4a.

2. **Context window limit khi nhiều chunks**
   - What we know: Top-k mặc định = 5 chunks × ~512 chars = ~2560 chars context
   - What's unclear: LLM context window đủ không với chunks + system prompt + response?
   - Recommendation: gpt-4o-mini có 128K context — đủ. Không phải vấn đề cho v1.

3. **`langchain_google_genai` version mới nhất (4.2.1) với `google_api_key` param**
   - What we know: `llm_provider.py` dùng `google_api_key=key` — cần verify parameter name trong v4.x
   - What's unclear: v4.x có thể đổi param name sang `api_key`
   - Recommendation: Wave 0 sau khi install phải verify: `ChatGoogleGenerativeAI.__init__` signature.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| FastAPI | SSE endpoint | ✓ | 0.135.3 | — |
| langchain-core | ChatPromptTemplate, astream | ✓ | 1.2.28 | — |
| langchain-openai | ChatOpenAI provider | ✓ | 1.1.12 | — |
| langchain-community | ChatOllama provider | ✓ | 0.4.1 | — |
| google-genai | Gemini SDK (base) | ✓ | 1.71.0 | — |
| langchain-google-genai | ChatGoogleGenerativeAI | ✗ | — | Install 4.2.1 (verified compatible) |
| langchain-anthropic | ChatAnthropic | ✗ | — | Install 1.4.0 (verified compatible) |
| pytest-asyncio | Async tests | ✓ | 1.3.0 | — |
| httpx | Test streaming client | ✓ | 0.28.1 | — |

**Missing dependencies với fallback:**
- `langchain-google-genai`: Install Wave 0 — dry-run confirmed no conflicts.
- `langchain-anthropic`: Install Wave 0 — dry-run confirmed no conflicts, adds `anthropic` and `docstring-parser` as new deps.

**Missing dependencies blocking execution:** Cả hai đều blocking nếu user chọn Gemini hoặc Claude provider. OpenAI và Ollama providers sẽ work ngay.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | none — xem Wave 0 |
| Quick run command | `pytest backend/tests/test_chat_router.py -x -q` |
| Full suite command | `pytest backend/tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHAT-01 | POST /api/chat nhận ChatRequest | integration | `pytest backend/tests/test_chat_router.py::test_chat_returns_200 -x` | ❌ Wave 0 |
| CHAT-02 | RAG chain embed → search → context | unit | `pytest backend/tests/test_rag_chain.py::test_build_context -x` | ❌ Wave 0 |
| CHAT-03 | ChatPromptTemplate format đúng | unit | `pytest backend/tests/test_rag_chain.py::test_prompt_format -x` | ❌ Wave 0 |
| CHAT-04 | StreamingResponse trả về text/event-stream | integration | `pytest backend/tests/test_chat_router.py::test_sse_content_type -x` | ❌ Wave 0 |
| CHAT-05 | SSE format data: {...}\n\n | integration | `pytest backend/tests/test_chat_router.py::test_sse_format -x` | ❌ Wave 0 |
| CHAT-06 | Error event mid-stream | integration | `pytest backend/tests/test_chat_router.py::test_sse_error_event -x` | ❌ Wave 0 |
| CHAT-07 | Citations trong terminal event | integration | `pytest backend/tests/test_chat_router.py::test_sse_citations -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/test_chat_router.py backend/tests/test_rag_chain.py -q`
- **Per wave merge:** `pytest backend/tests/ -q` (84 baseline + new tests)
- **Phase gate:** Full suite green trước `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_chat_router.py` — covers CHAT-01, CHAT-04, CHAT-05, CHAT-06, CHAT-07
- [ ] `backend/tests/test_rag_chain.py` — covers CHAT-02, CHAT-03
- [ ] Install: `pip install langchain-google-genai==4.2.1 langchain-anthropic==1.4.0`
- [ ] Verify `ChatGoogleGenerativeAI` constructor param name trong v4.x
- [ ] Add `langchain-google-genai==4.2.1` và `langchain-anthropic==1.4.0` vào `requirements.txt`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user local tool (per REQUIREMENTS.md) |
| V3 Session Management | no | Stateless SSE; không có session |
| V4 Access Control | no | Single-user — no multi-user isolation needed |
| V5 Input Validation | yes | Pydantic `ChatRequest` validation; `message` field cần max_length |
| V6 Cryptography | no | API keys truyền qua request body (HTTPS assumed locally) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key exposure trong request body | Information Disclosure | Accepted per REQUIREMENTS.md (single-user local tool); không log request body |
| Prompt injection qua `message` field | Tampering | System prompt cố định; context chỉ từ project documents; không execute user content |
| Unbounded `message` length | DoS | Add `max_length=10000` hoặc tương tự vào `ChatRequest.message` field |
| LLM provider error details leaked | Information Disclosure | Catch exceptions, yield generic SSE error message, log full detail server-side |

**Threat flag tương tự Phase 3c:** `api_key` trong request body visible ở server access logs — accepted per single-user local tool scope.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ChatGoogleGenerativeAI(google_api_key=key)` param name đúng trong v4.2.1 | Standard Stack / LLMProviderFactory | Cần đổi param name; sửa 1 dòng |
| A2 | `ChatAnthropic(anthropic_api_key=key)` param name đúng trong 1.4.0 | Standard Stack / LLMProviderFactory | Cần đổi sang `api_key`; sửa 1 dòng |
| A3 | `ChatOllama.astream()` hoạt động với `langchain-community 0.4.1` (đã test offline) | Environment Availability | Ollama provider không stream; cần fallback |

**Nếu table rỗng:** Tất cả claims đã được verified hoặc cited — không cần user confirm.
(A1, A2, A3 là LOW risk và có fix rõ ràng)

---

## Sources

### Primary (HIGH confidence)
- `.venv` runtime verification — tất cả imports và API shapes test trực tiếp
- `backend/app/services/llm_provider.py` — existing factory code
- `backend/app/services/vector_store.py` — `similarity_search_mmr` output shape
- `backend/app/services/embeddings.py` — EmbeddingFactory API
- `backend/app/routers/search.py` — existing router pattern

### Secondary (MEDIUM confidence)
- `pip index versions langchain-google-genai` — version 4.2.1 latest [VERIFIED 2026-04-09]
- `pip install langchain-google-genai==4.2.1 --dry-run` — compatibility với google-genai 1.71.0 [VERIFIED]
- `pip install langchain-anthropic==1.4.0 --dry-run` — compatibility check [VERIFIED]

### Tertiary (LOW confidence)
- `ChatGoogleGenerativeAI(google_api_key=...)` param name trong v4.x — [ASSUMED từ training + cần verify sau install]
- `ChatAnthropic(anthropic_api_key=...)` param name trong 1.4.0 — [ASSUMED từ training + cần verify sau install]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — tất cả packages verified với pip, imports tested
- Architecture: HIGH — pattern dựa trên existing code trong cùng codebase
- Pitfalls: HIGH — verified qua live testing (ChromaDB sync blocking, empty chunks, etc.)
- Missing packages A1/A2: MEDIUM — dry-run confirmed installable nhưng constructor params chưa verify

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (30 ngày — stack ổn định)
**Baseline tests:** 84/84 passing tại thời điểm research
