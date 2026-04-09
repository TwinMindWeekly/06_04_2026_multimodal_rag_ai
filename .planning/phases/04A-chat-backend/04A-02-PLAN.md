---
phase: 04A-chat-backend
plan: "02"
type: execute
wave: 2
depends_on: ["04A-01"]
files_modified:
  - backend/app/services/rag_chain.py
  - backend/app/routers/chat.py
  - backend/app/main.py
  - backend/tests/test_rag_chain.py
  - backend/tests/test_chat_router.py
autonomous: true
requirements: [CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07]

must_haves:
  truths:
    - "POST /api/chat with valid ChatRequest returns HTTP 200 with text/event-stream content type"
    - "SSE stream contains data: {\"text\": \"...\"} events for each LLM chunk"
    - "SSE stream ends with data: {\"done\": true, \"citations\": [...]} terminal event"
    - "Citations in terminal event contain filename, page_number, chunk_index for each source chunk"
    - "LLM error mid-stream produces data: {\"error\": \"...\"} SSE event instead of silent disconnect"
    - "RAG chain embeds query, searches ChromaDB with MMR, builds context with citation markers"
    - "Prompt uses ChatPromptTemplate (not RetrievalQA) with system+human message pair"
    - "Synchronous ChromaDB call wrapped in asyncio.to_thread to avoid blocking event loop"
  artifacts:
    - path: "backend/app/services/rag_chain.py"
      provides: "build_context_with_citations function + RAG_SYSTEM_PROMPT + chat_prompt template"
      exports: ["build_context_with_citations", "chat_prompt", "RAG_SYSTEM_PROMPT"]
      min_lines: 40
    - path: "backend/app/routers/chat.py"
      provides: "POST /api/chat endpoint with SSE streaming"
      exports: ["router"]
      min_lines: 60
    - path: "backend/app/main.py"
      provides: "chat router mounted"
      contains: "chat"
    - path: "backend/tests/test_rag_chain.py"
      provides: "Unit tests for context builder and prompt template"
      min_lines: 60
    - path: "backend/tests/test_chat_router.py"
      provides: "Integration tests for SSE endpoint"
      min_lines: 80
  key_links:
    - from: "backend/app/routers/chat.py"
      to: "backend/app/services/rag_chain.py"
      via: "import build_context_with_citations, chat_prompt"
      pattern: "from app.services.rag_chain import"
    - from: "backend/app/routers/chat.py"
      to: "backend/app/services/vector_store.py"
      via: "vector_store.similarity_search_mmr call inside asyncio.to_thread"
      pattern: "asyncio.to_thread"
    - from: "backend/app/routers/chat.py"
      to: "backend/app/services/llm_provider.py"
      via: "LLMProviderFactory.get_llm(streaming=True)"
      pattern: "LLMProviderFactory.get_llm"
    - from: "backend/app/routers/chat.py"
      to: "backend/app/services/embeddings.py"
      via: "EmbeddingFactory.get_embedding_model"
      pattern: "EmbeddingFactory.get_embedding_model"
    - from: "backend/app/main.py"
      to: "backend/app/routers/chat.py"
      via: "app.include_router(chat.router)"
      pattern: "include_router.*chat"
---

<objective>
Implement the RAG chain service and SSE-streaming chat endpoint. This is the core Phase 4a deliverable: POST /api/chat that embeds the user query, searches ChromaDB with MMR, builds an augmented prompt with citation markers, streams the LLM response as SSE events, and sends a terminal event with citation metadata.

Purpose: Enable users to chat with their uploaded documents through a streaming API that provides grounded, cited answers.

Output: `rag_chain.py` (context builder + prompt template), `chat.py` (SSE router), updated `main.py` (mount), fully populated test files.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/04A-chat-backend/04A-RESEARCH.md
@.planning/phases/04A-chat-backend/04A-01-SUMMARY.md
@.planning/phases/03C-retrieval/03C-02-SUMMARY.md
@.planning/phases/03C-retrieval/03C-03-SUMMARY.md

<interfaces>
<!-- Key types and contracts the executor needs. -->

From backend/app/schemas/domain.py (created in Plan 01):
```python
class CitationItem(BaseModel):
    filename: str
    page_number: int
    chunk_index: int
    marker: str  # e.g. '[1]', '[2]'

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    project_id: int
    provider: str = 'openai'
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    top_k: int = 5
    score_threshold: float = 0.3
    embedding_provider: str = 'local'
    embedding_api_key: Optional[str] = None
```

From backend/app/services/llm_provider.py (extended in Plan 01):
```python
class LLMProviderFactory:
    @staticmethod
    def get_llm(provider: str, api_key: str = None, temperature: float = 0.7,
                max_tokens: int = 1000, streaming: bool = True) -> BaseChatModel:
```

From backend/app/services/vector_store.py (existing):
```python
# Module-level singleton:
vector_store = VectorStoreService()

def similarity_search_mmr(
    self, query: str, top_k: int = 5, fetch_k: int = 20,
    score_threshold: float = 0.3, lambda_mult: float = 0.5,
    project_id: int | None = None, embedding_model=None, provider: str = 'local',
) -> list[dict]:
    # Returns: [{'content': str, 'metadata': dict, 'similarity': float, 'distance': float}]
```

From backend/app/services/embeddings.py (existing):
```python
class EmbeddingFactory:
    @staticmethod
    def get_embedding_model(provider: str = 'local', api_key: str | None = None):
```

From backend/app/core/i18n.py:
```python
def get_language(request: Request) -> str:
def t(key: str, lang: str = "en") -> str:
```

From backend/app/main.py (existing pattern):
```python
from app.routers import projects, documents, search  # noqa: E402
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(search.router)
```

From backend/tests/conftest.py (existing fixtures):
```python
@pytest.fixture
def client(test_engine):  # yields TestClient(app)
@pytest.fixture
def test_db(test_engine):  # yields SQLAlchemy session
@pytest.fixture
def mock_embeddings():  # MagicMock with embed_documents/embed_query
```

From backend/locales/en.json (Plan 01 added):
```json
"chat_message_required": "Message is required.",
"chat_provider_error": "Failed to initialize LLM provider.",
"chat_embedding_error": "Failed to initialize embedding provider.",
"chat_stream_error": "An error occurred during response generation."
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: RAG chain service — context builder + prompt template</name>
  <files>backend/app/services/rag_chain.py, backend/tests/test_rag_chain.py</files>
  <read_first>
    - backend/app/services/vector_store.py (lines 148-228 for similarity_search_mmr return format)
    - backend/app/services/llm_provider.py
    - backend/app/schemas/domain.py
    - backend/tests/test_rag_chain.py (scaffold from Plan 01)
    - .planning/phases/04A-chat-backend/04A-RESEARCH.md (Pattern 2: RAG Context Builder, Pattern 3: ChatPromptTemplate)
  </read_first>
  <behavior>
    - build_context_with_citations([]) returns ('', [])
    - build_context_with_citations([{'content': 'hello', 'metadata': {'filename': 'doc.pdf', 'page_number': 1, 'chunk_index': 0}, 'similarity': 0.9, 'distance': 0.1}]) returns context containing '[1] hello' and citations list with one dict having filename='doc.pdf', page_number=1, chunk_index=0, marker='[1]'
    - build_context_with_citations with 3 chunks returns context with [1], [2], [3] markers and 3 citations
    - Missing metadata keys default to '' for filename, 0 for page_number and chunk_index
    - chat_prompt.format_messages(context='ctx', question='q') returns list with system message containing 'ctx' and human message containing 'q'
    - RAG_SYSTEM_PROMPT contains 'citation markers' instruction
    - Module does NOT import RetrievalQA anywhere
  </behavior>
  <action>
1. **Replace scaffold tests in `backend/tests/test_rag_chain.py`** with real test implementations:

   ```python
   """Tests for RAG chain service (CHAT-02, CHAT-03, CHAT-07)."""
   import pytest
   from app.services.rag_chain import build_context_with_citations, chat_prompt, RAG_SYSTEM_PROMPT


   class TestBuildContextWithCitations:
       """CHAT-02, CHAT-07: Context builder from MMR search results."""

       def test_empty_chunks_returns_empty(self):
           context, citations = build_context_with_citations([])
           assert context == ''
           assert citations == []

       def test_single_chunk_produces_marker(self):
           chunks = [{'content': 'hello world', 'metadata': {'filename': 'doc.pdf', 'page_number': 1, 'chunk_index': 0}, 'similarity': 0.9, 'distance': 0.1}]
           context, citations = build_context_with_citations(chunks)
           assert '[1] hello world' in context
           assert len(citations) == 1
           assert citations[0]['filename'] == 'doc.pdf'
           assert citations[0]['page_number'] == 1
           assert citations[0]['chunk_index'] == 0
           assert citations[0]['marker'] == '[1]'

       def test_multiple_chunks_numbered_sequentially(self):
           chunks = [
               {'content': f'chunk {i}', 'metadata': {'filename': f'f{i}.pdf', 'page_number': i, 'chunk_index': i}, 'similarity': 0.8, 'distance': 0.2}
               for i in range(3)
           ]
           context, citations = build_context_with_citations(chunks)
           assert '[1] chunk 0' in context
           assert '[2] chunk 1' in context
           assert '[3] chunk 2' in context
           assert len(citations) == 3

       def test_citation_metadata_forwarded(self):
           chunks = [{'content': 'text', 'metadata': {'filename': 'report.docx', 'page_number': 5, 'chunk_index': 12}, 'similarity': 0.7, 'distance': 0.3}]
           _, citations = build_context_with_citations(chunks)
           c = citations[0]
           assert c['filename'] == 'report.docx'
           assert c['page_number'] == 5
           assert c['chunk_index'] == 12

       def test_missing_metadata_defaults(self):
           chunks = [{'content': 'text', 'metadata': {}, 'similarity': 0.5, 'distance': 0.5}]
           _, citations = build_context_with_citations(chunks)
           c = citations[0]
           assert c['filename'] == ''
           assert c['page_number'] == 0
           assert c['chunk_index'] == 0


   class TestPromptTemplate:
       """CHAT-03: ChatPromptTemplate format verification."""

       def test_prompt_includes_context_and_question(self):
           messages = chat_prompt.format_messages(context='my context here', question='what is this?')
           # System message should contain context
           system_content = messages[0].content
           assert 'my context here' in system_content
           # Human message should contain question
           human_content = messages[1].content
           assert 'what is this?' in human_content

       def test_prompt_no_retrieval_qa(self):
           import app.services.rag_chain as mod
           source = open(mod.__file__).read()
           assert 'RetrievalQA' not in source
   ```

2. Run tests — they MUST fail (RED) because `rag_chain.py` does not exist yet.

3. **Create `backend/app/services/rag_chain.py`:**

   ```python
   """RAG chain service: context building and prompt template (CHAT-02, CHAT-03, CHAT-07).

   Pipeline: embed query -> MMR search -> build_context_with_citations -> ChatPromptTemplate -> LLM.astream()
   This module handles steps 3 (context building) and 4 (prompt template).
   Steps 1-2 and 5 are handled in the chat router.
   """
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


   def build_context_with_citations(
       chunks: list[dict],
   ) -> tuple[str, list[dict]]:
       """Build context string from MMR search results with citation markers.

       Args:
           chunks: Output from vector_store.similarity_search_mmr().
                   Each dict has keys: content, metadata, similarity, distance.

       Returns:
           (context_string, citations_list) where citations_list contains dicts
           with filename, page_number, chunk_index, marker for each chunk.
       """
       if not chunks:
           return '', []

       context_parts: list[str] = []
       citations: list[dict] = []

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

4. Run tests again — they MUST pass (GREEN).
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/TwinMindWeekly/06_04_2026_multimodal_rag_ai/backend && .venv/Scripts/python -m pytest tests/test_rag_chain.py -v --no-header --tb=short</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def build_context_with_citations" backend/app/services/rag_chain.py` returns 1
    - `grep -c "ChatPromptTemplate" backend/app/services/rag_chain.py` returns at least 1
    - `grep -c "RetrievalQA" backend/app/services/rag_chain.py` returns 0
    - `grep -c "RAG_SYSTEM_PROMPT" backend/app/services/rag_chain.py` returns at least 1
    - `grep -c "citation markers" backend/app/services/rag_chain.py` returns at least 1
    - All 7 tests in test_rag_chain.py pass
    - `grep "pytest.skip" backend/tests/test_rag_chain.py` returns 0 lines (no more skips)
  </acceptance_criteria>
  <done>
    - build_context_with_citations correctly numbers chunks [1]..[N] and extracts citation metadata
    - chat_prompt formats system message with context and human message with question
    - RAG_SYSTEM_PROMPT instructs LLM to use citation markers and answer from context only
    - No RetrievalQA usage anywhere in rag_chain.py
    - All 7 unit tests pass (TDD RED->GREEN completed)
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Chat router with SSE streaming + mount + integration tests</name>
  <files>backend/app/routers/chat.py, backend/app/main.py, backend/tests/test_chat_router.py</files>
  <read_first>
    - backend/app/services/rag_chain.py (just created in Task 1)
    - backend/app/routers/search.py (existing router pattern reference)
    - backend/app/main.py
    - backend/app/schemas/domain.py
    - backend/tests/test_chat_router.py (scaffold from Plan 01)
    - backend/tests/conftest.py
    - .planning/phases/04A-chat-backend/04A-RESEARCH.md (Pattern 5: AsyncGenerator SSE, Pitfall 2: asyncio.to_thread, Pitfall 3: error after stream, Pitfall 4: empty chunks)
  </read_first>
  <behavior>
    - POST /api/chat with valid JSON returns 200 with content-type text/event-stream
    - Response headers include X-Accel-Buffering: no and Cache-Control: no-cache
    - Stream body contains lines matching `data: {"text": "..."}` pattern
    - Last data line contains `{"done": true, "citations": [...]}`
    - Citations array items have filename, page_number, chunk_index, marker keys
    - LLM failure mid-stream yields `data: {"error": "..."}` event
    - Embedding failure yields `data: {"error": "..."}` event
    - Missing message returns 422
    - Missing project_id returns 422
  </behavior>
  <action>
1. **Replace scaffold tests in `backend/tests/test_chat_router.py`** with real implementations. All LLM and embedding calls MUST be mocked — no real API keys used in tests.

   Key mocking strategy:
   - Mock `app.routers.chat.EmbeddingFactory.get_embedding_model` to return a MagicMock
   - Mock `app.routers.chat.vector_store.similarity_search_mmr` to return a fixed list of chunks
   - Mock `app.routers.chat.LLMProviderFactory.get_llm` to return a MagicMock whose `.astream()` returns an async generator yielding mock AIMessageChunks

   Helper for mock LLM async stream:
   ```python
   async def mock_astream(*args, **kwargs):
       """Simulate LLM streaming with AIMessageChunk-like objects."""
       for text in ['Hello', ' world', '!']:
           chunk = MagicMock()
           chunk.content = text
           yield chunk
   ```

   Tests to implement (replacing the pytest.skip scaffolds):

   **TestChatEndpoint:**
   - `test_chat_returns_200_sse`: POST `/api/chat` with `{"message": "test", "project_id": 1}`, assert status 200, assert `text/event-stream` in content-type. Use `client.stream('POST', '/api/chat', json={...})` context manager.
   - `test_chat_requires_message`: POST `/api/chat` with `{"project_id": 1}` only, assert 422.
   - `test_chat_requires_project_id`: POST `/api/chat` with `{"message": "test"}` only, assert 422.

   **TestSSEFormat:**
   - `test_sse_text_chunks`: Mock LLM to stream ['Hello', ' world'], read lines, assert at least one line contains `"text"` key with string value.
   - `test_sse_terminal_event`: Read all lines, find last `data:` line, parse JSON, assert `done` is True and `citations` is a list.
   - `test_sse_headers`: Assert response headers contain `X-Accel-Buffering: no` and `Cache-Control: no-cache`.

   **TestSSEErrorHandling:**
   - `test_sse_error_event_on_llm_failure`: Mock LLM `.astream()` to raise `Exception('LLM crashed')`, read lines, assert one line contains `"error"` key.
   - `test_sse_error_event_on_embedding_failure`: Mock `EmbeddingFactory.get_embedding_model` to raise `ValueError('bad provider')`, read lines, assert one line contains `"error"` key.

   Important: Use `@patch` decorators targeting `app.routers.chat.X` (not the original module path) since chat.py will import these at module level.

2. Run tests — they MUST fail (RED) because `chat.py` router does not exist yet.

3. **Create `backend/app/routers/chat.py`:**

   ```python
   """POST /api/chat — SSE streaming chat endpoint (CHAT-01, CHAT-04, CHAT-05, CHAT-06).

   Pipeline: validate request -> embed query -> MMR search -> build context ->
   ChatPromptTemplate -> LLM.astream() -> SSE events -> terminal citation event.
   """
   import asyncio
   import json
   import logging
   from typing import AsyncGenerator

   from fastapi import APIRouter
   from fastapi.responses import StreamingResponse

   from app.schemas.domain import ChatRequest
   from app.services.embeddings import EmbeddingFactory
   from app.services.llm_provider import LLMProviderFactory
   from app.services.rag_chain import build_context_with_citations, chat_prompt
   from app.services.vector_store import vector_store

   logger = logging.getLogger(__name__)

   router = APIRouter(tags=['chat'])


   async def _generate_sse_events(request: ChatRequest) -> AsyncGenerator[str, None]:
       """Async generator that yields SSE-formatted events.

       CHAT-05 format:
         data: {"text": "..."}\n\n          — for each LLM chunk
         data: {"done": true, "citations": [...]}\n\n  — terminal event
       CHAT-06 format:
         data: {"error": "..."}\n\n        — on any error mid-stream
       """
       try:
           # 1. Get embedding model (CHAT-02 step 1)
           embedding_model = EmbeddingFactory.get_embedding_model(
               provider=request.embedding_provider,
               api_key=request.embedding_api_key,
           )

           # 2. MMR search — synchronous ChromaDB call, wrap in to_thread (Pitfall 2)
           chunks = await asyncio.to_thread(
               vector_store.similarity_search_mmr,
               query=request.message,
               top_k=request.top_k,
               score_threshold=request.score_threshold,
               project_id=request.project_id,
               embedding_model=embedding_model,
               provider=request.embedding_provider,
           )

           # 3. Build context with citation markers (CHAT-02, CHAT-07)
           context_str, citations = build_context_with_citations(chunks)

           # 4. Format prompt (CHAT-03)
           messages = chat_prompt.format_messages(
               context=context_str or 'No relevant documents found.',
               question=request.message,
           )

           # 5. Get LLM with streaming (CHAT-04)
           llm = LLMProviderFactory.get_llm(
               provider=request.provider,
               api_key=request.api_key,
               temperature=request.temperature,
               max_tokens=request.max_tokens,
               streaming=True,
           )

           # 6. Stream LLM response as SSE text events (CHAT-05)
           async for chunk in llm.astream(messages):
               if hasattr(chunk, 'content') and chunk.content:
                   yield f'data: {json.dumps({"text": chunk.content})}\n\n'

           # 7. Terminal event with citations (CHAT-05, CHAT-07)
           yield f'data: {json.dumps({"done": True, "citations": citations})}\n\n'

       except Exception as e:
           # CHAT-06: Error event mid-stream — do NOT raise HTTPException
           logger.exception('Chat stream error: %s', e)
           yield f'data: {json.dumps({"error": str(e)})}\n\n'


   @router.post('/api/chat')
   async def chat(request: ChatRequest) -> StreamingResponse:
       """POST /api/chat — RAG-augmented chat with SSE streaming (CHAT-01, CHAT-04)."""
       return StreamingResponse(
           _generate_sse_events(request),
           media_type='text/event-stream',
           headers={
               'X-Accel-Buffering': 'no',
               'Cache-Control': 'no-cache',
           },
       )
   ```

4. **Update `backend/app/main.py`** — add chat router import and mount:
   - Change the import line to include chat: `from app.routers import projects, documents, search, chat  # noqa: E402`
   - Add after the last include_router: `app.include_router(chat.router)`

5. Run tests again — they MUST pass (GREEN).

6. Run full test suite to verify no regressions: `cd backend && .venv/Scripts/python -m pytest tests/ -q --tb=short`
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/TwinMindWeekly/06_04_2026_multimodal_rag_ai/backend && .venv/Scripts/python -m pytest tests/test_chat_router.py tests/test_rag_chain.py -v --no-header --tb=short && .venv/Scripts/python -m pytest tests/ -q --tb=short</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def chat" backend/app/routers/chat.py` returns at least 1
    - `grep -c "StreamingResponse" backend/app/routers/chat.py` returns at least 1
    - `grep -c "text/event-stream" backend/app/routers/chat.py` returns at least 1
    - `grep -c "X-Accel-Buffering" backend/app/routers/chat.py` returns 1
    - `grep -c "Cache-Control" backend/app/routers/chat.py` returns 1
    - `grep -c "asyncio.to_thread" backend/app/routers/chat.py` returns 1
    - `grep -c '"error"' backend/app/routers/chat.py` returns at least 1 (error SSE event)
    - `grep -c '"done"' backend/app/routers/chat.py` returns at least 1 (terminal event)
    - `grep -c "chat" backend/app/main.py` returns at least 2 (import + include_router)
    - `grep "pytest.skip" backend/tests/test_chat_router.py` returns 0 lines (no more skips)
    - All 8 tests in test_chat_router.py pass
    - All 7 tests in test_rag_chain.py pass
    - Full suite (84 baseline + 15 new) runs with 0 failures
  </acceptance_criteria>
  <done>
    - POST /api/chat endpoint returns SSE stream with text chunks and terminal citation event
    - SSE headers: X-Accel-Buffering=no, Cache-Control=no-cache, content-type=text/event-stream
    - Error mid-stream yields SSE error event (not silent disconnect, not HTTPException)
    - ChromaDB sync call wrapped in asyncio.to_thread
    - Chat router mounted in main.py
    - 8 integration tests pass for chat router
    - 7 unit tests pass for rag chain
    - Full test suite: 0 failures, no regressions
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client -> POST /api/chat | User-supplied message, provider config, api_key cross trust boundary |
| chat router -> EmbeddingFactory | embedding_provider + embedding_api_key forwarded |
| chat router -> LLMProviderFactory | provider + api_key forwarded to external LLM service |
| chat router -> vector_store | project_id used to derive collection_name (integer only) |
| LLM response -> SSE stream | LLM output forwarded to client (could contain unexpected content) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-4a-01 | Tampering | ChatRequest.message | mitigate | Pydantic Field(max_length=10000) enforced in Plan 01 schema |
| T-4a-02 | Information Disclosure | api_key in request body | accept | Single-user local tool; no server-side logging of request body |
| T-4a-03 | Denial of Service | Unbounded message length | mitigate | max_length=10000 on message field (Plan 01) |
| T-4a-04 | Information Disclosure | LLM error details in SSE | mitigate | Catch all exceptions in _generate_sse_events, yield generic error string, log full detail server-side with logger.exception |
| T-4a-05 | Tampering | Prompt injection via message | accept | System prompt is fixed; context comes only from project documents; no code execution. Accepted for v1 single-user local tool |
| T-4a-06 | Denial of Service | Blocking event loop | mitigate | vector_store.similarity_search_mmr wrapped in asyncio.to_thread() to prevent blocking uvicorn event loop |
| T-4a-07 | Information Disclosure | project_id used for collection name | mitigate | project_id is integer from Pydantic schema; collection_name = f'project_{int}' — no user-controlled string injection |
</threat_model>

<verification>
1. `curl -N -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"message": "what is in the document?", "project_id": 1, "provider": "openai", "api_key": "sk-test"}' | head -20` — returns SSE events with `data:` prefix
2. `pytest tests/test_chat_router.py tests/test_rag_chain.py -v` — 15 tests pass
3. `pytest tests/ -q` — full suite passes with 0 failures
4. `grep -c "include_router.*chat" backend/app/main.py` — returns 1
5. `python -c "from app.routers.chat import router; print(router.routes)"` — shows POST /api/chat route
</verification>

<success_criteria>
- POST /api/chat endpoint accepts ChatRequest and returns SSE-streamed response
- SSE stream: text chunks as `data: {"text": "..."}\n\n`, terminal event as `data: {"done": true, "citations": [...]}\n\n`
- Mid-stream errors yield `data: {"error": "..."}\n\n` (never silent disconnect)
- RAG chain: embed query -> MMR search -> context with [1]..[N] markers -> ChatPromptTemplate -> LLM.astream()
- Citations contain filename, page_number, chunk_index per source chunk
- Works with all 4 providers (OpenAI, Gemini, Claude, Ollama) when configured
- asyncio.to_thread wraps synchronous ChromaDB call
- 15 new tests pass (7 unit + 8 integration), full suite 0 failures
</success_criteria>

<output>
After completion, create `.planning/phases/04A-chat-backend/04A-02-SUMMARY.md`
</output>
