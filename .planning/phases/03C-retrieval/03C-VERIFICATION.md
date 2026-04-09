---
phase: 03C-retrieval
verified: 2026-04-09T17:30:00Z
status: passed
score: 15/15 must-haves verified
overrides_applied: 0
re_verification: null
gaps: []
deferred: []
human_verification: []
---

# Phase 03C: Retrieval — Verification Report

**Phase Goal:** Query ChromaDB with switchable embedding providers and get ranked, deduplicated results with citations.
**Verified:** 2026-04-09T17:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | EmbeddingFactory.get_embedding_model('local') returns HuggingFaceEmbeddings với all-MiniLM-L6-v2 | VERIFIED | embeddings.py dòng 31-37: `if provider == 'local': return HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2', ...)` — 12/12 test_embeddings pass |
| 2 | EmbeddingFactory.get_embedding_model('openai', api_key='sk-test') returns OpenAIEmbeddings | VERIFIED | embeddings.py dòng 38-39: `elif provider == 'openai': return OpenAIEmbeddings(model='text-embedding-3-small', api_key=api_key)` |
| 3 | EmbeddingFactory.get_embedding_model('gemini', api_key='test') returns _GeminiEmbeddings | VERIFIED | embeddings.py dòng 40-41: `elif provider == 'gemini': return _GeminiEmbeddings(model='models/text-embedding-004', api_key=api_key)` |
| 4 | get_default_embeddings() vẫn hoạt động như lazy singleton | VERIFIED | embeddings.py dòng 47-55: `_default_embeddings = None; def get_default_embeddings(): global _default_embeddings...` |
| 5 | Collection mới được tạo với embedding_provider và embedding_model trong ChromaDB metadata | VERIFIED | vector_store.py dòng 84-91: `get_or_create_collection(name=..., metadata={'embedding_provider': provider, 'embedding_model': model, 'hnsw:space': 'cosine'})` — test_collection_metadata_stored PASS |
| 6 | Collection mới dùng hnsw:space=cosine cho scoring trực quan | VERIFIED | vector_store.py dòng 89: `'hnsw:space': 'cosine'` xác nhận bằng test_collection_metadata_stored |
| 7 | Query collection với provider khác raises lỗi rõ ràng | VERIFIED | vector_store.py dòng 61-68: `_check_provider_match` raises ValueError với 'mismatch' — test_provider_mismatch_raises PASS |
| 8 | Concurrent writes đến cùng project được serialize qua per-project threading.Lock | VERIFIED | vector_store.py dòng 40-49: `_get_project_lock`, dòng 98-104: `with _get_project_lock(project_id): collection.upsert(...)` — test_write_lock_serializes, test_insert_documents_uses_lock PASS |
| 9 | Search results dưới score_threshold bị loại | VERIFIED | vector_store.py dòng 200-204: `sim = 1.0 - dist; if sim >= score_threshold: above_threshold.append(...)` — test_score_threshold_filters PASS |
| 10 | MMR deduplication trả về kết quả đa dạng từ overlapping chunks | VERIFIED | vector_store.py dòng 212-218: `maximal_marginal_relevance(query_arr, list(filtered_embs), ...)` — test_mmr_deduplication PASS |
| 11 | GET /api/search trả về Top-K chunks với content, metadata, similarity, và distance | VERIFIED | search.py dòng 18-52: endpoint đầy đủ, trả về SearchResponse với SearchResult items — test_search_returns_results PASS (11/11 router tests) |
| 12 | GET /api/search với score_threshold cao trả về ít kết quả hơn | VERIFIED | search.py dòng 37: `score_threshold=score_threshold` truyền vào similarity_search_mmr — test_search_score_threshold PASS |
| 13 | POST /api/projects/{id}/reindex trả về 202, xóa collection, queue re-processing | VERIFIED | search.py dòng 55-93: status_code=202, delete_collection, background_tasks — test_reindex_returns_202 PASS |
| 14 | Re-index endpoint đánh dấu tất cả documents của project là pending | VERIFIED | search.py dòng 76-83: `doc.status = 'pending'` cho tất cả docs trong project — test_reindex_marks_documents_pending PASS |
| 15 | Search router được mount trong main.py và có thể truy cập | VERIFIED | main.py dòng 52: `from app.routers import projects, documents, search`, dòng 56: `app.include_router(search.router)` |

**Score:** 15/15 truths verified

---

### Required Artifacts

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `backend/app/services/embeddings.py` | Extended EmbeddingFactory với api_key param + _GeminiEmbeddings wrapper | VERIFIED | 56 dòng, exports EmbeddingFactory, _GeminiEmbeddings, get_default_embeddings. Signature `get_embedding_model(provider: str = 'local', api_key: str | None = None)` |
| `backend/requirements.txt` | langchain-openai dependency | VERIFIED | Dòng 126: `langchain-openai==1.1.12`. pip show xác nhận Version: 1.1.12 |
| `backend/tests/conftest.py` | Pre-mock cho google.genai | VERIFIED | Dòng 8-13: `sys.modules.setdefault('google.genai', _mock_genai)` |
| `backend/tests/test_embeddings.py` | Tests cho tất cả 3 embedding providers | VERIFIED | 12/12 tests pass, bao gồm test_openai_embedding_factory, test_gemini_embedding_factory, test_unsupported_provider_raises |
| `backend/app/services/vector_store.py` | Extended VectorStoreService với provider metadata, mismatch guard, write lock, MMR search | VERIFIED | 231 dòng, exports VectorStoreService, _sanitize_metadata, _get_project_lock. 17/17 vector store tests pass |
| `backend/tests/test_vector_store.py` | Tests cho collection metadata, provider mismatch, write lock, score threshold, MMR | VERIFIED | 17 tests pass bao gồm test_collection_metadata_stored |
| `backend/app/routers/search.py` | Search và reindex endpoints | VERIFIED | 94 dòng, APIRouter với GET /api/search và POST /api/projects/{id}/reindex |
| `backend/app/schemas/domain.py` | SearchResult, SearchResponse, ReindexResponse Pydantic models | VERIFIED | Dòng 50-70: 3 models đầy đủ, importable |
| `backend/app/main.py` | Search router được mount | VERIFIED | Dòng 52 và 56: import và include_router |
| `backend/tests/test_search_router.py` | Integration tests cho search và reindex endpoints | VERIFIED | 11 tests, 100% pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `embeddings.py` | `langchain_openai.OpenAIEmbeddings` | top-level import | WIRED | Dòng 4: `from langchain_openai import OpenAIEmbeddings` — langchain-openai==1.1.12 installed |
| `embeddings.py` | `google.genai.Client` | lazy import trong embed_documents | WIRED | Dòng 15: `from google import genai` — trong _GeminiEmbeddings.embed_documents |
| `vector_store.py` | `chromadb.PersistentClient` | get_or_create_collection với metadata | WIRED | Dòng 84-91: metadata bao gồm embedding_provider, embedding_model, hnsw:space |
| `vector_store.py` | `langchain_core.vectorstores.utils.maximal_marginal_relevance` | import trong similarity_search_mmr | WIRED | Dòng 165: `from langchain_core.vectorstores.utils import maximal_marginal_relevance` |
| `vector_store.py` | `threading.Lock` | _get_project_lock helper | WIRED | Dòng 40-41: `_project_locks: dict[int | None, threading.Lock] = {}`, dòng 44-49: `_get_project_lock` |
| `search.py` | `vector_store.similarity_search_mmr()` | gọi trực tiếp | WIRED | Dòng 35: `results = vector_store.similarity_search_mmr(...)` |
| `search.py` | `EmbeddingFactory.get_embedding_model()` | gọi trực tiếp | WIRED | Dòng 30: `embedding_model = EmbeddingFactory.get_embedding_model(provider=provider, api_key=api_key)` |
| `search.py` | `document_parser.process_and_update_document` | BackgroundTasks trong reindex | WIRED | Dòng 87: `background_tasks.add_task(process_and_update_document, doc.id)` |
| `main.py` | `search.py` | app.include_router | WIRED | Dòng 52, 56: import và include_router(search.router) |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `search.py` GET /api/search | `results` | `vector_store.similarity_search_mmr(query, ...)` | Có — ChromaDB query với embeddings thực | FLOWING |
| `vector_store.py` similarity_search_mmr | `docs`, `distances`, `embeddings_list` | `collection.query(query_embeddings=[query_embedding], include=['documents','metadatas','distances','embeddings'])` | Có — ChromaDB PersistentClient query thực | FLOWING |
| `search.py` POST /api/projects/{id}/reindex | `documents` | `db.query(Document).join(Folder).filter(Folder.project_id == project_id).all()` | Có — SQLAlchemy query thực | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| EmbeddingFactory exports đúng signature | `python -c "from app.services.embeddings import EmbeddingFactory; print(sig)"` | `(provider: str = 'local', api_key: str | None = None)` | PASS |
| VectorStoreService có _check_provider_match và similarity_search_mmr | python check | Cả hai methods tồn tại | PASS |
| Pydantic schemas importable | `python -c "from app.schemas.domain import SearchResult, SearchResponse, ReindexResponse"` | OK | PASS |
| langchain-openai phiên bản đúng | pip show langchain-openai | Version: 1.1.12 | PASS |
| 40/40 phase 03C tests pass | pytest test_embeddings + test_vector_store + test_search_router | 40 passed, 0 failed | PASS |
| 84/84 full suite tests pass | pytest backend/tests/ -q | 84 passed, 25 warnings, 0 failed | PASS |
| langchain_google_genai đã bị xóa | grep langchain_google_genai embeddings.py | No matches found | PASS |
| embedding-001 đã bị xóa | grep embedding-001 embeddings.py | No matches found | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EMBED-01 | 03C-01 | Default embedding: all-MiniLM-L6-v2 via sentence-transformers | SATISFIED | embeddings.py: `HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2', ...)` — default provider='local' |
| EMBED-02 | 03C-01 | Switchable sang OpenAI text-embedding-3-small hoặc Google text-embedding-004 | SATISFIED | embeddings.py: 3 providers hoạt động đầy đủ với api_key injection |
| EMBED-03 | 03C-02 | Store embedding provider name và model ID trong ChromaDB collection metadata | SATISFIED | vector_store.py: get_or_create_collection với metadata={'embedding_provider', 'embedding_model', 'hnsw:space'} |
| EMBED-04 | 03C-02, 03C-03 | Block queries khi provider mismatch; surface clear error | SATISFIED | _check_provider_match raises ValueError — được gọi trong similarity_search_mmr và search router trả về HTTP 400 |
| EMBED-05 | 03C-03 | Re-index endpoint xóa vectors và re-runs embedding pipeline | SATISFIED | POST /api/projects/{id}/reindex: delete_collection + marks pending + background_tasks |
| EMBED-06 | 03C-02 | Serialize ChromaDB writes per collection dùng per-project lock | SATISFIED | _get_project_lock + `with _get_project_lock(project_id): collection.upsert(...)` |
| SEARCH-01 | 03C-02, 03C-03 | Semantic search endpoint trả về Top-K chunks với distances và metadata | SATISFIED | GET /api/search với similarity_search_mmr, trả về SearchResponse với content/metadata/similarity/distance |
| SEARCH-02 | 03C-02 | Score threshold filter: loại chunks dưới similarity threshold | SATISFIED | similarity_search_mmr: `sim = 1.0 - dist; if sim >= score_threshold: above_threshold.append(...)` |
| SEARCH-03 | 03C-02 | MMR để tránh returning overlapping chunks | SATISFIED | maximal_marginal_relevance từ langchain_core được gọi sau threshold filter |

**Tất cả 9 requirements được thỏa mãn. Không có orphaned requirements.**

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/app/schemas/domain.py` | 15,26,41 | `class Config` (Pydantic V1 style) trong ProjectResponse, FolderResponse, DocumentResponse | Info | Cảnh báo deprecation Pydantic V2 — không ảnh hưởng đến chức năng, chỉ là code cũ từ các phases trước, ngoài phạm vi phase 03C |

Không có blocker anti-patterns trong code mới của phase 03C. Các models mới (SearchResult, SearchResponse, ReindexResponse) sử dụng Pydantic V2 syntax đúng cách.

---

### Human Verification Required

Không có items cần human verification. Tất cả can be verified programmatically.

---

### Gaps Summary

Không có gaps. Tất cả 15 must-have truths đã được xác minh:

- **EmbeddingFactory (EMBED-01, EMBED-02):** 3 providers (local/openai/gemini) với api_key injection hoạt động đầy đủ. _GeminiEmbeddings wrapper sử dụng google-genai SDK (không phải langchain_google_genai cũ). 12/12 embedding tests pass.
- **VectorStoreService (EMBED-03, EMBED-04, EMBED-06, SEARCH-02, SEARCH-03):** Collection metadata được lưu khi tạo. Provider mismatch raises ValueError rõ ràng. Per-project threading.Lock serializes writes. Score threshold filtering và MMR deduplication hoạt động đúng. 17/17 vector store tests pass.
- **Search Router (EMBED-05, SEARCH-01):** GET /api/search và POST /api/projects/{id}/reindex đầy đủ chức năng. Được mount trong main.py. 11/11 router tests pass.
- **Full test suite:** 84/84 tests pass, không có regressions.

---

_Verified: 2026-04-09T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
