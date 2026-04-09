---
phase: 03C-retrieval
plan: "01"
subsystem: embeddings
tags: [embeddings, factory-pattern, langchain, openai, gemini, tdd]
dependency_graph:
  requires: []
  provides: [EmbeddingFactory, _GeminiEmbeddings, get_default_embeddings]
  affects: [backend/app/services/vector_store.py]
tech_stack:
  added: [langchain-openai==1.1.12]
  patterns: [factory-pattern, lazy-singleton, langchain-embeddings-interface]
key_files:
  created: [backend/tests/test_embeddings.py (expanded)]
  modified:
    - backend/app/services/embeddings.py
    - backend/tests/conftest.py
    - backend/requirements.txt
decisions:
  - "google-genai SDK (not langchain_google_genai) for Gemini embeddings — protobuf 6.x compatibility"
  - "Lazy import of google.genai inside embed_documents to keep import-time clean"
  - "Top-level import of OpenAIEmbeddings (not lazy) since langchain-openai is a declared dependency"
  - "Pre-mock google.genai in conftest at module top-level before any app imports"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-09T16:53:10Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 03C Plan 01: Embedding Factory Extension Summary

**One-liner:** Extended EmbeddingFactory to support 3 switchable providers (local/OpenAI/Gemini) with api_key injection, replacing outdated langchain_google_genai with a custom _GeminiEmbeddings wrapper using google-genai SDK.

## What Was Built

- `_GeminiEmbeddings` class implementing the LangChain `Embeddings` interface via the `google-genai` SDK (text-embedding-004 model)
- `EmbeddingFactory.get_embedding_model()` extended with `api_key: str | None = None` parameter
- Three working providers: `local` (HuggingFaceEmbeddings/all-MiniLM-L6-v2), `openai` (OpenAIEmbeddings/text-embedding-3-small), `gemini` (_GeminiEmbeddings/text-embedding-004)
- `google.genai` pre-mock in `conftest.py` preventing ImportError during test collection
- `langchain-openai==1.1.12` added to requirements.txt and installed in venv
- 8 new TDD tests covering all 3 providers (12 total in test_embeddings.py)

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Install langchain-openai + fix conftest google.genai pre-mock | 593b654 | backend/requirements.txt, backend/tests/conftest.py |
| 2 | Extend EmbeddingFactory + _GeminiEmbeddings + tests (TDD) | bc8978d | backend/app/services/embeddings.py, backend/tests/test_embeddings.py |

## Verification Results

- `pytest backend/tests/test_embeddings.py -x -v` → 12/12 passed
- `pytest backend/tests/ -x -q` → 73/73 passed (no regressions)
- `grep "api_key" backend/app/services/embeddings.py` → matches found in _GeminiEmbeddings and EmbeddingFactory
- `grep "langchain_google_genai" backend/app/services/embeddings.py` → no matches (old import removed)
- `grep "embedding-001" backend/app/services/embeddings.py` → no matches (outdated model removed)

## Deviations from Plan

### Auto-fixed Issues

None - plan executed exactly as written.

**Note on test patching:** The plan's `test_openai_embedding_factory` called for patching `app.services.embeddings.OpenAIEmbeddings` (lazy import pattern). The actual implementation uses a top-level import of `OpenAIEmbeddings`, so the patch target `app.services.embeddings.OpenAIEmbeddings` works correctly since the name exists in the module namespace. No deviation was needed.

## Known Stubs

None. All three providers are fully wired with real implementations:
- `local`: HuggingFaceEmbeddings fully operational
- `openai`: OpenAIEmbeddings functional (requires valid API key at runtime)
- `gemini`: _GeminiEmbeddings functional (requires valid GOOGLE_API_KEY at runtime)

## Threat Flags

No new security surface introduced beyond what is in the plan's threat model. API keys flow through function parameters and environment variables only — never logged or persisted.

## Self-Check: PASSED

- [x] `backend/app/services/embeddings.py` exists and contains `_GeminiEmbeddings`, `EmbeddingFactory` with `api_key` param
- [x] `backend/tests/test_embeddings.py` exists with 12 tests
- [x] `backend/tests/conftest.py` contains `google.genai` pre-mock
- [x] `backend/requirements.txt` contains `langchain-openai==1.1.12`
- [x] Commit `593b654` exists (Task 1)
- [x] Commit `bc8978d` exists (Task 2)
