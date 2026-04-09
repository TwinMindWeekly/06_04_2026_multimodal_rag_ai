---
phase: 03C-retrieval
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/requirements.txt
  - backend/app/services/embeddings.py
  - backend/tests/conftest.py
  - backend/tests/test_embeddings.py
autonomous: true
requirements: [EMBED-01, EMBED-02]
must_haves:
  truths:
    - "EmbeddingFactory.get_embedding_model('local') returns HuggingFaceEmbeddings with all-MiniLM-L6-v2"
    - "EmbeddingFactory.get_embedding_model('openai', api_key='sk-test') returns OpenAIEmbeddings"
    - "EmbeddingFactory.get_embedding_model('gemini', api_key='test') returns _GeminiEmbeddings"
    - "get_default_embeddings() still works as lazy singleton"
    - "All existing tests still pass after conftest pre-mock update"
  artifacts:
    - path: "backend/app/services/embeddings.py"
      provides: "Extended EmbeddingFactory with api_key param + _GeminiEmbeddings wrapper"
      exports: ["EmbeddingFactory", "get_default_embeddings", "_GeminiEmbeddings"]
    - path: "backend/requirements.txt"
      provides: "langchain-openai dependency"
      contains: "langchain-openai==1.1.12"
    - path: "backend/tests/conftest.py"
      provides: "Pre-mock for google.genai to prevent ImportError"
      contains: "google.genai"
    - path: "backend/tests/test_embeddings.py"
      provides: "Tests for all 3 embedding providers"
      contains: "test_openai_embedding_factory"
  key_links:
    - from: "backend/app/services/embeddings.py"
      to: "langchain_openai.OpenAIEmbeddings"
      via: "lazy import inside get_embedding_model"
      pattern: "from langchain_openai import OpenAIEmbeddings"
    - from: "backend/app/services/embeddings.py"
      to: "google.genai.Client"
      via: "_GeminiEmbeddings.embed_documents"
      pattern: "genai\\.Client"
---

<objective>
Extend EmbeddingFactory to support switchable embedding providers (local, OpenAI, Gemini) with API key injection, and fix the test environment so all tests can run.

Purpose: EMBED-01 requires local embedding as default; EMBED-02 requires switchable providers. The current EmbeddingFactory lacks api_key parameter and uses an outdated Gemini model name. Additionally, google-genai is not installed, blocking ALL test collection.

Output: Updated embeddings.py with 3-provider factory, _GeminiEmbeddings wrapper, langchain-openai installed, conftest pre-mock for google.genai, and new tests covering all providers.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/03C-retrieval/03C-RESEARCH.md

<interfaces>
<!-- Current EmbeddingFactory interface (to be extended, not replaced) -->
From backend/app/services/embeddings.py:
```python
class EmbeddingFactory:
    @staticmethod
    def get_embedding_model(provider: str = "local"):
        # Currently: no api_key param, gemini uses langchain_google_genai with wrong model name

_default_embeddings = None

def get_default_embeddings():
    global _default_embeddings
    if _default_embeddings is None:
        _default_embeddings = EmbeddingFactory.get_embedding_model("local")
    return _default_embeddings
```

From backend/tests/conftest.py (pre-mock pattern):
```python
# Lines 1-21: sys.modules pre-mock for unstructured.partition.auto
# Must add google.genai to same pre-mock block
```

From langchain_core.embeddings (interface to implement for _GeminiEmbeddings):
```python
class Embeddings(ABC):
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Install langchain-openai + fix conftest pre-mock for google.genai</name>
  <files>backend/requirements.txt, backend/tests/conftest.py</files>
  <read_first>
    - backend/requirements.txt
    - backend/tests/conftest.py
  </read_first>
  <action>
1. Install langchain-openai and google-genai into the venv:
   ```
   D:/workspaces/projects/TwinMindWeekly/06_04_2026_multimodal_rag_ai/backend/.venv/Scripts/python -m pip install langchain-openai==1.1.12 google-genai
   ```

2. Add `langchain-openai==1.1.12` as a new line at the end of `backend/requirements.txt` (after the existing `google-genai>=1.0` line).

3. In `backend/tests/conftest.py`, extend the sys.modules pre-mock block (lines 15-21) to also mock google.genai. Add BEFORE the `if "unstructured.partition.auto" not in sys.modules:` block:
   ```python
   # Pre-mock google.genai to prevent ImportError in environments without the package.
   # image_processor.py does 'from google import genai' at import time.
   if 'google.genai' not in sys.modules:
       _mock_google = MagicMock()
       _mock_genai = MagicMock()
       sys.modules.setdefault('google', _mock_google)
       sys.modules.setdefault('google.genai', _mock_genai)
       _mock_google.genai = _mock_genai
   ```
   Place this block AFTER `from unittest.mock import MagicMock` (line 2) and BEFORE the existing unstructured pre-mock block (line 15).

4. Verify all existing tests still pass:
   ```
   D:/workspaces/projects/TwinMindWeekly/06_04_2026_multimodal_rag_ai/backend/.venv/Scripts/python -m pytest backend/tests/ -x -q
   ```
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/TwinMindWeekly/06_04_2026_multimodal_rag_ai && backend/.venv/Scripts/python -m pip show langchain-openai | findstr Version && backend/.venv/Scripts/python -m pip show google-genai | findstr Version && backend/.venv/Scripts/python -m pytest backend/tests/ -x -q</automated>
  </verify>
  <acceptance_criteria>
    - grep "langchain-openai==1.1.12" backend/requirements.txt returns a match
    - grep "google.genai" backend/tests/conftest.py returns a match
    - grep "sys.modules.setdefault.*google.genai" backend/tests/conftest.py returns a match
    - pip show langchain-openai shows Version: 1.1.12
    - pip show google-genai shows a version >= 1.0
    - pytest backend/tests/ -x -q shows all tests passed (0 failures)
  </acceptance_criteria>
  <done>langchain-openai==1.1.12 and google-genai installed; conftest pre-mocks both google.genai and unstructured; all existing tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extend EmbeddingFactory with api_key + _GeminiEmbeddings wrapper + tests</name>
  <files>backend/app/services/embeddings.py, backend/tests/test_embeddings.py</files>
  <read_first>
    - backend/app/services/embeddings.py
    - backend/tests/test_embeddings.py
    - backend/app/services/vector_store.py (consumer of embeddings — ensure no breakage)
  </read_first>
  <behavior>
    - test_factory_local_returns_huggingface: EmbeddingFactory.get_embedding_model('local') returns HuggingFaceEmbeddings with model_name='all-MiniLM-L6-v2'
    - test_factory_local_is_default: EmbeddingFactory.get_embedding_model() (no args) returns local model
    - test_openai_embedding_factory: EmbeddingFactory.get_embedding_model('openai', api_key='sk-test') returns OpenAIEmbeddings instance with model='text-embedding-3-small'
    - test_gemini_embedding_factory: EmbeddingFactory.get_embedding_model('gemini', api_key='test-key') returns _GeminiEmbeddings instance with _model='models/text-embedding-004'
    - test_gemini_embeddings_embed_documents: _GeminiEmbeddings.embed_documents(['text']) calls genai.Client and returns list of float lists
    - test_gemini_embeddings_embed_query: _GeminiEmbeddings.embed_query('text') returns single float list
    - test_unsupported_provider_raises: EmbeddingFactory.get_embedding_model('invalid') raises ValueError containing 'Unsupported embedding provider'
    - test_gemini_api_key_from_env: _GeminiEmbeddings with api_key=None reads GOOGLE_API_KEY from env
  </behavior>
  <action>
1. **Write tests first** in `backend/tests/test_embeddings.py`. Keep all 4 existing tests. Add 8 new tests below them:

   - `test_factory_local_returns_huggingface`: Patch `HuggingFaceEmbeddings`, call `EmbeddingFactory.get_embedding_model('local')`, assert called with `model_name='all-MiniLM-L6-v2'`.
   - `test_factory_local_is_default`: Patch `HuggingFaceEmbeddings`, call `EmbeddingFactory.get_embedding_model()`, assert HuggingFaceEmbeddings was called.
   - `test_openai_embedding_factory`: Patch `langchain_openai.OpenAIEmbeddings` at `app.services.embeddings.OpenAIEmbeddings` (after lazy import), call `EmbeddingFactory.get_embedding_model('openai', api_key='sk-test')`. Assert `OpenAIEmbeddings` called with `model='text-embedding-3-small'` and `api_key='sk-test'`.
   - `test_gemini_embedding_factory`: Call `EmbeddingFactory.get_embedding_model('gemini', api_key='test-key')`. Assert returned instance is `_GeminiEmbeddings` with `_model == 'models/text-embedding-004'` and `_api_key == 'test-key'`.
   - `test_gemini_embeddings_embed_documents`: Create `_GeminiEmbeddings(api_key='k')`. Patch `google.genai.Client` to return mock with `models.embed_content` returning mock result with `embeddings = [MagicMock(values=[0.1, 0.2])]`. Call `embed_documents(['hello'])`. Assert returns `[[0.1, 0.2]]`.
   - `test_gemini_embeddings_embed_query`: Same setup, call `embed_query('hello')`, assert returns `[0.1, 0.2]`.
   - `test_unsupported_provider_raises`: `with pytest.raises(ValueError, match='Unsupported embedding provider')`: call `EmbeddingFactory.get_embedding_model('invalid')`.
   - `test_gemini_api_key_from_env`: Patch `os.getenv` to return `'env-key'` for `GOOGLE_API_KEY`. Create `_GeminiEmbeddings(api_key=None)`. Assert `_api_key == 'env-key'`.

2. Run tests — they should FAIL (RED phase).

3. **Implement** in `backend/app/services/embeddings.py`:

   a. Add `import os` at the top (after existing imports).
   
   b. Add `from langchain_core.embeddings import Embeddings` import.

   c. Create `_GeminiEmbeddings` class BEFORE `EmbeddingFactory`:
      ```python
      class _GeminiEmbeddings(Embeddings):
          """Thin LangChain-compatible wrapper around google-genai SDK for text-embedding-004."""

          def __init__(self, model: str = 'models/text-embedding-004', api_key: str | None = None):
              self._model = model
              self._api_key = api_key or os.getenv('GOOGLE_API_KEY')

          def embed_documents(self, texts: list[str]) -> list[list[float]]:
              from google import genai
              client = genai.Client(api_key=self._api_key)
              result = client.models.embed_content(model=self._model, contents=texts)
              return [e.values for e in result.embeddings]

          def embed_query(self, text: str) -> list[float]:
              return self.embed_documents([text])[0]
      ```

   d. Modify `EmbeddingFactory.get_embedding_model` signature to accept `api_key`:
      ```python
      @staticmethod
      def get_embedding_model(provider: str = 'local', api_key: str | None = None):
      ```

   e. Update the `openai` branch:
      ```python
      elif provider == 'openai':
          from langchain_openai import OpenAIEmbeddings
          return OpenAIEmbeddings(model='text-embedding-3-small', api_key=api_key)
      ```

   f. Update the `gemini` branch (replace langchain_google_genai with _GeminiEmbeddings):
      ```python
      elif provider == 'gemini':
          return _GeminiEmbeddings(model='models/text-embedding-004', api_key=api_key)
      ```

   g. Remove the old `from langchain_google_genai import GoogleGenerativeAIEmbeddings` import (it was lazy inside the elif, so just replace the elif body).

   h. Use single quotes consistently per project convention.

4. Run tests — they should PASS (GREEN phase).
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/TwinMindWeekly/06_04_2026_multimodal_rag_ai && backend/.venv/Scripts/python -m pytest backend/tests/test_embeddings.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - grep "def get_embedding_model.*provider.*api_key" backend/app/services/embeddings.py returns a match
    - grep "class _GeminiEmbeddings" backend/app/services/embeddings.py returns a match
    - grep "models/text-embedding-004" backend/app/services/embeddings.py returns a match
    - grep "text-embedding-3-small" backend/app/services/embeddings.py returns a match
    - grep "from langchain_openai import OpenAIEmbeddings" backend/app/services/embeddings.py returns a match
    - grep "from google import genai" backend/app/services/embeddings.py returns a match
    - grep "test_openai_embedding_factory" backend/tests/test_embeddings.py returns a match
    - grep "test_gemini_embedding_factory" backend/tests/test_embeddings.py returns a match
    - grep "test_gemini_embeddings_embed_documents" backend/tests/test_embeddings.py returns a match
    - grep "test_unsupported_provider_raises" backend/tests/test_embeddings.py returns a match
    - pytest backend/tests/test_embeddings.py -x -v shows all tests passed (0 failures)
    - grep "langchain_google_genai" backend/app/services/embeddings.py returns NO match (old import removed)
    - grep "embedding-001" backend/app/services/embeddings.py returns NO match (outdated model removed)
  </acceptance_criteria>
  <done>EmbeddingFactory accepts api_key parameter. Three providers work: local (HuggingFaceEmbeddings/all-MiniLM-L6-v2), openai (OpenAIEmbeddings/text-embedding-3-small), gemini (_GeminiEmbeddings/text-embedding-004). All 12 embedding tests pass. Old langchain_google_genai and models/embedding-001 references removed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| caller -> EmbeddingFactory | API keys passed from caller; must not be logged |
| _GeminiEmbeddings -> google.genai | External API call with API key |
| EmbeddingFactory -> langchain_openai | External API call with API key |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-3c-01 | Information Disclosure | EmbeddingFactory | mitigate | Never log api_key values; only log provider name. Follow image_processor.py established pattern. |
| T-3c-02 | Denial of Service | _GeminiEmbeddings.embed_documents | accept | No retry logic here (search is user-initiated, not background); caller handles errors. Single-user local tool. |
| T-3c-03 | Spoofing | EmbeddingFactory.get_embedding_model | accept | No authentication boundary; single-user local tool per REQUIREMENTS.md out-of-scope. |
</threat_model>

<verification>
1. `backend/.venv/Scripts/python -m pytest backend/tests/test_embeddings.py -x -v` — all 12 tests pass
2. `backend/.venv/Scripts/python -m pytest backend/tests/ -x -q` — full suite green (no regressions)
3. `grep "api_key" backend/app/services/embeddings.py` — api_key param present in factory and _GeminiEmbeddings
4. `grep "langchain_google_genai" backend/app/services/embeddings.py` — returns nothing (old import removed)
</verification>

<success_criteria>
- EmbeddingFactory.get_embedding_model() supports 3 providers with api_key injection
- _GeminiEmbeddings implements LangChain Embeddings interface using google-genai SDK
- Outdated models/embedding-001 replaced with models/text-embedding-004
- langchain-openai==1.1.12 installed and in requirements.txt
- google-genai installed and conftest pre-mocks it for test isolation
- All existing + 8 new embedding tests pass
- Full test suite green (no regressions from conftest changes)
</success_criteria>

<output>
After completion, create `.planning/phases/03C-retrieval/03C-01-SUMMARY.md`
</output>
