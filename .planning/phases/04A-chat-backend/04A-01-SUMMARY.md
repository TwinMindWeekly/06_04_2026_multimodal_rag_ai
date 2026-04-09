---
phase: 04A-chat-backend
plan: "01"
subsystem: backend
tags: [schemas, dependencies, streaming, i18n, test-scaffold]
dependency_graph:
  requires: []
  provides:
    - backend/app/schemas/domain.py::ChatRequest
    - backend/app/schemas/domain.py::CitationItem
    - backend/app/services/llm_provider.py::LLMProviderFactory.get_llm(streaming)
  affects:
    - backend/app/routers/chat.py (Plan 02 — imports ChatRequest)
    - backend/app/services/rag_chain.py (Plan 02 — calls LLMProviderFactory.get_llm(streaming=True))
tech_stack:
  added:
    - langchain-google-genai==4.2.1
    - langchain-anthropic==1.4.0
  patterns:
    - Pydantic Field(min_length, max_length) for input validation
    - Factory pattern with streaming param forwarded to LLM constructor
key_files:
  created:
    - backend/tests/test_rag_chain.py
    - backend/tests/test_chat_router.py
  modified:
    - backend/requirements.txt
    - backend/app/schemas/domain.py
    - backend/app/services/llm_provider.py
    - backend/locales/en.json
    - backend/locales/vi.json
decisions:
  - ChatRequest and CitationItem added to domain.py (not new file) to keep schema module cohesive
  - streaming param not passed to ChatGoogleGenerativeAI (astream works natively without it)
  - streaming param not passed to ChatOllama (astream works natively without it)
  - message field validated with Field(min_length=1, max_length=10000) per threat model T-4a-01, T-4a-03
metrics:
  duration: ~8min
  completed: 2026-04-09
  tasks_completed: 2
  files_modified: 7
---

# Phase 4A Plan 01: Chat Foundation — Schemas, Dependencies, and Test Scaffolds Summary

**One-liner:** ChatRequest/CitationItem Pydantic schemas, langchain-anthropic + langchain-google-genai installed, LLMProviderFactory extended with streaming=True, and test scaffolds created for Plan 02.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Install dependencies + Pydantic schemas + i18n keys | 725a161 | requirements.txt, domain.py, en.json, vi.json |
| 2 | Extend LLMProviderFactory with streaming + test scaffolds | 67f7555 | llm_provider.py, test_rag_chain.py, test_chat_router.py |

## What Was Built

### Dependencies
- `langchain-google-genai==4.2.1` — provides `ChatGoogleGenerativeAI` for Gemini chat
- `langchain-anthropic==1.4.0` — provides `ChatAnthropic` for Claude chat
- Both added to `backend/requirements.txt`

### Pydantic Schemas (domain.py)
- `CitationItem` — single citation from RAG context: `filename`, `page_number`, `chunk_index`, `marker`
- `ChatRequest` — POST /api/chat body: `message` (Field min=1, max=10000), `project_id`, `provider`, `api_key`, `temperature`, `max_tokens`, `top_k`, `score_threshold`, `embedding_provider`, `embedding_api_key`
- `provider` and `embedding_provider` are **separate fields** (critical distinction per research Pitfall 7)

### LLMProviderFactory (llm_provider.py)
- Added `streaming: bool = True` parameter to `get_llm()` signature
- `streaming=streaming` forwarded to `ChatOpenAI` and `ChatAnthropic`
- `ChatGoogleGenerativeAI` and `ChatOllama` support `astream()` natively — no streaming param needed

### i18n Keys
Added to both `en.json` and `vi.json`:
- `errors.chat_message_required`
- `errors.chat_provider_error`
- `errors.chat_embedding_error`
- `errors.chat_stream_error`

### Test Scaffolds
- `test_rag_chain.py`: 7 scaffold tests for RAG chain service (TestBuildContextWithCitations, TestPromptTemplate)
- `test_chat_router.py`: 8 scaffold tests for chat router (TestChatEndpoint, TestSSEFormat, TestSSEErrorHandling)
- All tests use `pytest.skip('Implemented in Plan 02')` — Plan 02 will fill bodies

## Verification Results

```
langchain-google-genai: 4.2.1 [VERIFIED]
langchain-anthropic: 1.4.0 [VERIFIED]
from app.schemas.domain import ChatRequest, CitationItem  # OK
streaming in LLMProviderFactory.get_llm signature         # OK (default=True)
pytest backend/tests/: 29 passed, 15 skipped, 0 failures
```

## Deviations from Plan

### Auto-applied decisions

**1. [Rule 2 - Missing field] streaming not forwarded to ChatGoogleGenerativeAI**
- **Found during:** Task 2
- **Issue:** Plan says "pass streaming=streaming to ChatGoogleGenerativeAI() if it supports it" — checked API and it does not accept streaming constructor param in 4.2.1
- **Fix:** Omitted streaming param for Gemini — astream() works natively per LangChain LCEL pattern
- **Files modified:** backend/app/services/llm_provider.py

**2. [Rule 2 - Missing field] worktree path separation**
- **Found during:** Task 1
- **Issue:** Worktree at `.claude/worktrees/agent-abd10fb6` has separate working directory from main repo — edits to `backend/...` needed to target worktree path
- **Fix:** Re-applied all edits targeting worktree path `D:/workspaces/.../worktrees/agent-abd10fb6/backend/...`
- **Files modified:** All Task 1 files

## Known Stubs

None — this plan creates contracts (schemas, factory params) for Plan 02 to implement. No stub data flows to UI.

## Threat Flags

No new security-relevant surfaces introduced beyond those already in the plan's threat model.

## Self-Check: PASSED

- backend/app/schemas/domain.py — ChatRequest class present: YES
- backend/app/schemas/domain.py — CitationItem class present: YES
- backend/app/services/llm_provider.py — streaming param: YES
- backend/tests/test_rag_chain.py — 7 scaffold tests: YES
- backend/tests/test_chat_router.py — 8 scaffold tests: YES
- Commit 725a161 exists: YES
- Commit 67f7555 exists: YES
