---
phase: 04A-chat-backend
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/requirements.txt
  - backend/app/schemas/domain.py
  - backend/app/services/llm_provider.py
  - backend/locales/en.json
  - backend/locales/vi.json
  - backend/tests/test_rag_chain.py
  - backend/tests/test_chat_router.py
autonomous: true
requirements: [CHAT-01, CHAT-02, CHAT-03, CHAT-07]

must_haves:
  truths:
    - "langchain-google-genai and langchain-anthropic are installed and importable"
    - "ChatRequest schema validates message, project_id, provider, embedding_provider as separate fields"
    - "CitationItem schema carries filename, page_number, chunk_index"
    - "LLMProviderFactory.get_llm() accepts streaming param and passes it to ChatOpenAI"
    - "Test scaffolds exist for test_rag_chain.py and test_chat_router.py"
  artifacts:
    - path: "backend/requirements.txt"
      provides: "langchain-google-genai and langchain-anthropic entries"
      contains: "langchain-google-genai"
    - path: "backend/app/schemas/domain.py"
      provides: "ChatRequest, CitationItem Pydantic models"
      contains: "class ChatRequest"
    - path: "backend/app/services/llm_provider.py"
      provides: "streaming=True support in LLMProviderFactory"
      contains: "streaming"
    - path: "backend/tests/test_rag_chain.py"
      provides: "Test scaffold for RAG chain service"
    - path: "backend/tests/test_chat_router.py"
      provides: "Test scaffold for chat router"
  key_links:
    - from: "backend/app/schemas/domain.py"
      to: "backend/app/routers/chat.py (Plan 02)"
      via: "ChatRequest import"
      pattern: "class ChatRequest"
    - from: "backend/app/services/llm_provider.py"
      to: "backend/app/services/rag_chain.py (Plan 02)"
      via: "LLMProviderFactory.get_llm(streaming=True)"
      pattern: "streaming"
---

<objective>
Install missing LLM provider dependencies, create Pydantic schemas for chat API, extend LLMProviderFactory with streaming support, add i18n error keys for chat, and create test scaffolds.

Purpose: Establish all contracts and dependencies that Plan 02 (RAG chain + chat router) will build against. Without this, Plan 02 cannot import schemas or instantiate LLM providers.

Output: Updated requirements.txt, ChatRequest/CitationItem schemas, LLMProviderFactory with streaming, i18n keys, empty test files with initial test cases.
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

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From backend/app/schemas/domain.py (existing):
```python
class SearchResult(BaseModel):
    content: str
    metadata: dict
    similarity: float
    distance: float

class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    project_id: int
    result_count: int
```

From backend/app/services/llm_provider.py (existing):
```python
class LLMProviderFactory:
    @staticmethod
    def get_llm(provider: str, api_key: str = None, temperature: float = 0.7, max_tokens: int = 1000) -> BaseChatModel:
        # providers: openai, gemini, claude, ollama
        # lazy imports inside each if-branch
```

From backend/app/services/vector_store.py (existing):
```python
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
        # providers: local, openai, gemini
```

From backend/app/core/i18n.py (existing):
```python
def t(key: str, lang: str = "en") -> str:
    # Translate dotted key e.g. 'errors.chat_project_required'
```

From backend/locales/en.json (existing keys):
```json
{
  "errors": {
    "project_not_found": "Project not found.",
    "folder_not_found": "Folder not found.",
    "document_not_found": "Document not found.",
    "internal_error": "An internal server error occurred.",
    "invalid_file_type": "Invalid file type. Allowed types: PDF, DOCX, PPTX, XLSX.",
    "file_too_large": "File too large. Maximum size is 100MB."
  }
}
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
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Install dependencies + Pydantic schemas + i18n keys</name>
  <files>backend/requirements.txt, backend/app/schemas/domain.py, backend/locales/en.json, backend/locales/vi.json</files>
  <read_first>
    - backend/requirements.txt
    - backend/app/schemas/domain.py
    - backend/locales/en.json
    - backend/locales/vi.json
  </read_first>
  <action>
1. Install missing LLM provider packages:
   ```bash
   D:/workspaces/projects/TwinMindWeekly/06_04_2026_multimodal_rag_ai/backend/.venv/Scripts/python -m pip install langchain-google-genai==4.2.1 langchain-anthropic==1.4.0
   ```

2. Append to end of `backend/requirements.txt` (before any blank trailing line):
   ```
   langchain-google-genai==4.2.1
   langchain-anthropic==1.4.0
   ```

3. Add to `backend/app/schemas/domain.py` — append AFTER the existing `ReindexResponse` class. Use single quotes per project convention:

   ```python
   class CitationItem(BaseModel):
       """Single citation reference from RAG context (CHAT-07)."""
       filename: str
       page_number: int
       chunk_index: int
       marker: str  # e.g. '[1]', '[2]'


   class ChatRequest(BaseModel):
       """Request body for POST /api/chat (CHAT-01).
       provider = LLM provider (openai/gemini/claude/ollama).
       embedding_provider = embedding provider (local/openai/gemini) — separate from LLM provider (Pitfall 7).
       """
       message: str  # max_length enforced via Field below
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

   Also add Field import at top of file: `from pydantic import BaseModel, constr, Field`
   Then replace `message: str` with:
   ```python
       message: str = Field(..., min_length=1, max_length=10000)
   ```

4. Add chat-specific error keys to `backend/locales/en.json` under the "errors" object:
   ```json
   "chat_message_required": "Message is required.",
   "chat_provider_error": "Failed to initialize LLM provider.",
   "chat_embedding_error": "Failed to initialize embedding provider.",
   "chat_stream_error": "An error occurred during response generation."
   ```

5. Add chat-specific error keys to `backend/locales/vi.json` under the "errors" object:
   ```json
   "chat_message_required": "Tin nhan khong duoc de trong.",
   "chat_provider_error": "Khong the khoi tao nha cung cap LLM.",
   "chat_embedding_error": "Khong the khoi tao nha cung cap embedding.",
   "chat_stream_error": "Da xay ra loi trong qua trinh tao phan hoi."
   ```
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/TwinMindWeekly/06_04_2026_multimodal_rag_ai/backend && .venv/Scripts/python -c "from app.schemas.domain import ChatRequest, CitationItem; print('OK'); from langchain_google_genai import ChatGoogleGenerativeAI; print('genai OK'); from langchain_anthropic import ChatAnthropic; print('anthropic OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "langchain-google-genai" backend/requirements.txt` returns 1
    - `grep -c "langchain-anthropic" backend/requirements.txt` returns 1
    - `grep -c "class ChatRequest" backend/app/schemas/domain.py` returns 1
    - `grep -c "class CitationItem" backend/app/schemas/domain.py` returns 1
    - `grep -c "embedding_provider" backend/app/schemas/domain.py` returns at least 1
    - `grep -c "max_length=10000" backend/app/schemas/domain.py` returns 1
    - `grep -c "chat_stream_error" backend/locales/en.json` returns 1
    - `grep -c "chat_stream_error" backend/locales/vi.json` returns 1
  </acceptance_criteria>
  <done>
    - ChatRequest and CitationItem importable from app.schemas.domain
    - langchain-google-genai and langchain-anthropic installed and importable
    - i18n keys for chat errors exist in both en.json and vi.json
    - message field has min_length=1, max_length=10000 validation
    - provider and embedding_provider are separate fields in ChatRequest
  </done>
</task>

<task type="auto">
  <name>Task 2: Extend LLMProviderFactory with streaming + create test scaffolds</name>
  <files>backend/app/services/llm_provider.py, backend/tests/test_rag_chain.py, backend/tests/test_chat_router.py</files>
  <read_first>
    - backend/app/services/llm_provider.py
    - backend/tests/conftest.py
    - backend/app/services/vector_store.py (lines 148-228 for similarity_search_mmr signature)
  </read_first>
  <action>
1. Modify `backend/app/services/llm_provider.py`:
   - Add `streaming: bool = True` parameter to `get_llm()` method signature (after max_tokens)
   - In the `openai` branch, pass `streaming=streaming` to `ChatOpenAI()` constructor
   - In the `gemini` branch, pass `streaming=streaming` to `ChatGoogleGenerativeAI()` if it supports it (check after install — if not supported, skip; astream works without it)
   - In the `claude` branch: `ChatAnthropic` supports astream natively — no streaming param needed, but add `streaming=streaming` if accepted
   - In the `ollama` branch: `ChatOllama` — no change needed, astream works natively
   - Keep all existing parameter names (openai_api_key, google_api_key, anthropic_api_key) — these are correct per the installed package versions
   - Update docstring to mention streaming parameter

2. Create `backend/tests/test_rag_chain.py` — test scaffold for RAG chain service (Plan 02 will implement the service):
   ```python
   """Tests for RAG chain service (CHAT-02, CHAT-03, CHAT-07).
   Scaffold created in Plan 01; test bodies filled in Plan 02.
   """
   import pytest
   from unittest.mock import MagicMock, patch


   class TestBuildContextWithCitations:
       """CHAT-02, CHAT-07: Context builder from MMR search results."""

       def test_empty_chunks_returns_empty(self):
           """Empty input produces empty context string and empty citations list."""
           pytest.skip('Implemented in Plan 02')

       def test_single_chunk_produces_marker(self):
           """Single chunk produces [1] marker in context and one citation."""
           pytest.skip('Implemented in Plan 02')

       def test_multiple_chunks_numbered_sequentially(self):
           """N chunks produce [1]..[N] markers in context and N citations."""
           pytest.skip('Implemented in Plan 02')

       def test_citation_metadata_forwarded(self):
           """filename, page_number, chunk_index extracted from chunk metadata (CHAT-07)."""
           pytest.skip('Implemented in Plan 02')

       def test_missing_metadata_defaults(self):
           """Missing metadata fields default to empty string / 0."""
           pytest.skip('Implemented in Plan 02')


   class TestPromptTemplate:
       """CHAT-03: ChatPromptTemplate format verification."""

       def test_prompt_includes_context_and_question(self):
           """Formatted messages contain context in system and question in human."""
           pytest.skip('Implemented in Plan 02')

       def test_prompt_no_retrieval_qa(self):
           """Prompt uses ChatPromptTemplate, not RetrievalQA."""
           pytest.skip('Implemented in Plan 02')
   ```

3. Create `backend/tests/test_chat_router.py` — test scaffold for chat router (Plan 02 will implement):
   ```python
   """Tests for POST /api/chat SSE endpoint (CHAT-01, CHAT-04, CHAT-05, CHAT-06, CHAT-07).
   Scaffold created in Plan 01; test bodies filled in Plan 02.
   """
   import pytest
   from unittest.mock import MagicMock, patch, AsyncMock


   class TestChatEndpoint:
       """CHAT-01: POST /api/chat accepts ChatRequest."""

       def test_chat_returns_200_sse(self, client):
           """POST /api/chat returns 200 with text/event-stream content-type (CHAT-04)."""
           pytest.skip('Implemented in Plan 02')

       def test_chat_requires_message(self, client):
           """Missing message field returns 422."""
           pytest.skip('Implemented in Plan 02')

       def test_chat_requires_project_id(self, client):
           """Missing project_id returns 422."""
           pytest.skip('Implemented in Plan 02')


   class TestSSEFormat:
       """CHAT-05: SSE data format specification."""

       def test_sse_text_chunks(self, client):
           """Stream contains data: {"text": "..."} events."""
           pytest.skip('Implemented in Plan 02')

       def test_sse_terminal_event(self, client):
           """Stream ends with data: {"done": true, "citations": [...]} event (CHAT-05, CHAT-07)."""
           pytest.skip('Implemented in Plan 02')

       def test_sse_headers(self, client):
           """Response has X-Accel-Buffering=no and Cache-Control=no-cache (CHAT-04)."""
           pytest.skip('Implemented in Plan 02')


   class TestSSEErrorHandling:
       """CHAT-06: Error events mid-stream."""

       def test_sse_error_event_on_llm_failure(self, client):
           """LLM error produces data: {"error": "..."} SSE event."""
           pytest.skip('Implemented in Plan 02')

       def test_sse_error_event_on_embedding_failure(self, client):
           """Embedding provider error produces SSE error event."""
           pytest.skip('Implemented in Plan 02')
   ```
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/TwinMindWeekly/06_04_2026_multimodal_rag_ai/backend && .venv/Scripts/python -m pytest tests/test_rag_chain.py tests/test_chat_router.py -v --no-header 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "streaming" backend/app/services/llm_provider.py` returns at least 2 (param + usage)
    - `grep -c "streaming: bool" backend/app/services/llm_provider.py` returns 1
    - File `backend/tests/test_rag_chain.py` exists with at least 7 test methods
    - File `backend/tests/test_chat_router.py` exists with at least 8 test methods
    - `D:/workspaces/projects/TwinMindWeekly/06_04_2026_multimodal_rag_ai/backend/.venv/Scripts/python -m pytest tests/ -q --tb=short` shows 0 failures (skips are OK)
  </acceptance_criteria>
  <done>
    - LLMProviderFactory.get_llm() accepts streaming: bool = True parameter
    - ChatOpenAI constructed with streaming=True when streaming param is True
    - test_rag_chain.py has 7 scaffold tests (all pytest.skip for Plan 02)
    - test_chat_router.py has 8 scaffold tests (all pytest.skip for Plan 02)
    - Full test suite runs with 0 failures (84 existing + new skipped tests)
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client -> POST /api/chat | User-supplied message, provider, api_key enter the system |
| chat router -> LLM provider | API key forwarded to external service |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-4a-01 | Tampering | ChatRequest.message | mitigate | Pydantic Field(max_length=10000) prevents unbounded input (this plan, Task 1) |
| T-4a-02 | Information Disclosure | ChatRequest.api_key | accept | Single-user local tool; api_key in request body, not logged. Accepted per REQUIREMENTS.md |
| T-4a-03 | Denial of Service | ChatRequest.message | mitigate | max_length=10000 on message field limits LLM token cost (this plan, Task 1) |
| T-4a-04 | Information Disclosure | LLM error details | mitigate | Plan 02 will catch exceptions and yield generic SSE error event; log details server-side only |
</threat_model>

<verification>
1. `pip show langchain-google-genai` shows version 4.2.1
2. `pip show langchain-anthropic` shows version 1.4.0
3. `python -c "from app.schemas.domain import ChatRequest, CitationItem"` succeeds
4. `python -c "from app.services.llm_provider import LLMProviderFactory; import inspect; sig = inspect.signature(LLMProviderFactory.get_llm); assert 'streaming' in sig.parameters"` succeeds
5. `pytest tests/ -q` — 0 failures, all existing tests pass, new scaffold tests skip
</verification>

<success_criteria>
- Two new pip packages installed and in requirements.txt
- ChatRequest and CitationItem schemas importable with correct fields
- LLMProviderFactory supports streaming parameter
- i18n error keys for chat exist in both locales
- Test scaffolds created (will be populated in Plan 02)
- Full test suite: 0 failures
</success_criteria>

<output>
After completion, create `.planning/phases/04A-chat-backend/04A-01-SUMMARY.md`
</output>
