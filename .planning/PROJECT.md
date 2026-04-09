# Multimodal RAG AI

## What This Is

A web-based Retrieval-Augmented Generation (RAG) system that lets users upload documents (PDF, DOCX, PPTX, XLSX), extract and vectorize their content, and chat with an AI that uses those documents as context. Supports multiple LLM providers (OpenAI, Gemini, Claude, Ollama) with bilingual UI (English/Vietnamese).

## Core Value

Users can upload documents and get accurate, citation-backed AI answers grounded in their own content — not hallucinated from general training data.

## Requirements

### Validated

<!-- Shipped and confirmed working (Phase 1, 2, 2.5 complete) -->

- ✓ **UI-01**: Modern React UI with Sidebar, Chat Area, Settings Panel — Phase 1
- ✓ **UI-02**: Dark mode with Glassmorphism design system — Phase 1
- ✓ **UI-03**: Bilingual UI (EN/VI) with i18next switcher — Phase 1
- ✓ **UI-04**: Project tree view with nested folders in Sidebar — Phase 1
- ✓ **UI-05**: Chat interface with markdown rendering, typing animation, citation display — Phase 1
- ✓ **UI-06**: Settings panel for provider selection (OpenAI/Gemini/Claude/Ollama), API key, temperature, max tokens — Phase 1
- ✓ **BE-01**: FastAPI backend with CRUD APIs for Projects, Folders, Documents — Phase 2
- ✓ **BE-02**: SQLite database with SQLAlchemy ORM (projects, folders, documents tables) — Phase 2
- ✓ **BE-03**: Backend i18n middleware (Accept-Language header, EN/VI error messages) — Phase 2
- ✓ **BE-04**: Document upload with UUID filenames and background processing — Phase 2
- ✓ **BE-05**: Document parsing pipeline (stubbed with unstructured.io interface) — Phase 2
- ✓ **INT-01**: Frontend-backend integration via axios with language interceptor — Phase 2.5
- ✓ **INT-02**: Real file upload with progress, tree view data fetching from API — Phase 2.5
- ✓ **INT-03**: Error handling with toast/alert for 404/500 responses — Phase 2.5
- ✓ **RAG-01**: ChromaDB vector store with per-project collections — Phase 3 (partial)
- ✓ **RAG-02**: Embedding factory (local sentence-transformers default) — Phase 3 (partial)
- ✓ **RAG-03**: Data ingestion pipeline (upload → parse → embed → ChromaDB) — Phase 3 (partial)
- ✓ **LLM-01**: LLM provider factory (OpenAI/Gemini/Claude/Ollama) — Phase 4 (partial)

### Active

<!-- Current scope — building toward these -->

- [ ] **RAG-04**: Real document parsing with unstructured.io (PDF, DOCX, PPTX, XLSX extraction)
- [ ] **RAG-05**: Image extraction from structured documents (PDF/PPTX)
- [ ] **RAG-06**: Image summarization via Gemini 1.5 Pro Vision
- [ ] **RAG-07**: Text chunking with RecursiveCharacterTextSplitter
- [ ] **RAG-08**: Switchable embedding providers (local default, OpenAI/Gemini upgrade)
- [ ] **RAG-09**: Semantic search endpoint (Top-K retrieval with citations)
- [ ] **CHAT-01**: Chat API endpoint (/api/chat) accepting text + image
- [ ] **CHAT-02**: Context-augmented prompt engineering with retrieved chunks
- [ ] **CHAT-03**: Citation metadata forwarding (page number, filename)
- [ ] **CHAT-04**: SSE streaming response (real-time typing effect)
- [ ] **CHAT-05**: Frontend SSE parsing and citation rendering
- [ ] **CHAT-06**: Dynamic provider/credential loading from Settings UI
- [ ] **TEST-01**: End-to-end user flow testing (Upload → Vector → Chat)

### Out of Scope

- Real-time collaborative editing — not a document editor
- User authentication/accounts — single-user local tool for now
- Cloud deployment/scaling — local-first development
- Mobile app — web-only
- Fine-tuning models — uses pre-trained models via API

## Context

- **Brownfield project:** Phases 1, 2, 2.5 complete. Phase 3 and 4 partially started.
- **Tech stack locked:** React 19 + Vite (frontend), FastAPI + SQLAlchemy/SQLite (backend), ChromaDB + LangChain (RAG)
- **Document parsing decision:** Unstructured.io with system dependencies (poppler, tesseract) for highest quality extraction
- **Embedding strategy:** Both local (sentence-transformers, free) and paid (OpenAI/Gemini) — switchable by user
- **Image RAG:** Gemini Vision for image summarization, embedded as text into ChromaDB
- **Priority:** RAG pipeline (Phase 3) first, then Chat API (Phase 4)

## Constraints

- **Tech stack**: React/Vite frontend, FastAPI/Python backend — already built, cannot change
- **Database**: SQLite (relational) + ChromaDB (vector) — both local, no external DB server
- **AI/ML**: Must support offline/local operation (sentence-transformers, Ollama) as well as cloud providers
- **Language**: UI and backend errors must support EN/VI bilingual output
- **Protocol**: Must follow AI_AGENT_PROTOCOL.md enterprise guidelines (docs-first, approval workflow, conventional commits)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Unstructured.io for parsing | Highest quality multi-format extraction, already planned | — Pending |
| Local + paid embeddings (switchable) | Free local default for development, paid upgrade for quality | — Pending |
| Gemini Vision for image summarization | Best multimodal understanding, user already has Gemini in stack | — Pending |
| Collection-per-project in ChromaDB | Isolates vector data, enables project-scoped search | ✓ Good |
| Factory pattern for LLM/Embedding providers | Runtime switching without code changes | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-09 after initialization*
