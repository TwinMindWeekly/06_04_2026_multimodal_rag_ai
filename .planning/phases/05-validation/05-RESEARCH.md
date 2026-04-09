# Phase 5: Validation - Research

**Researched:** 2026-04-09
**Domain:** Python / pytest / FastAPI / ChromaDB integration testing
**Confidence:** HIGH

---

## Summary

Phase 5 cần viết ba nhóm test bao phủ toàn bộ luồng người dùng: E2E upload-to-chat (TEST-01), ChromaDB metadata round-trip (TEST-02), và embedding provider switch + re-index (TEST-03). Tất cả ba test đều có thể viết hoàn toàn tự động với pytest, không cần mock LLM hay API key thật vì codebase đã có fixture `client` (FastAPI TestClient) và pattern mock tốt trong các phase trước.

Điểm khác biệt then chốt so với các test đơn vị hiện có: Phase 5 cần test *tích hợp thật* giữa ChromaDB (dùng `tempfile.mkdtemp()` thay vì collection shared), upload endpoint, search endpoint, và chat endpoint — nhưng vẫn mock LLM để tránh phụ thuộc API key. Pattern VectorStoreService với `PersistentClient(path=tmpdir)` đã được chứng minh hoạt động tốt trong `test_vector_store.py` (17 tests, không có regressions).

**Primary recommendation:** Viết một file `backend/tests/test_e2e_validation.py` với ba class test, mỗi class tương ứng một requirement. Dùng `PersistentClient(path=tmpdir)` cho ChromaDB thật, `_NonClosingSession` wrapper cho session pipeline, mock LLM và `partition` (vì Windows/WSL2 segfault đã documented).

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TEST-01 | E2E test: Upload PDF → verify chunks in ChromaDB → chat query → verify streamed response with citations | Cần: upload endpoint (`POST /api/documents/upload`), pipeline mock, ChromaDB tmpdir, chat endpoint mock LLM — tất cả đều có fixture sẵn |
| TEST-02 | Unit test: ChromaDB metadata round-trip (insert chunk with metadata, query, assert all fields survive) | `VectorStoreService` với `PersistentClient(tmpdir)` — pattern đã có trong `test_vector_store.py` |
| TEST-03 | Integration test: Embedding provider switch triggers re-index, not silent corruption | `reindex` endpoint + provider mismatch guard đã implement trong `search.py` + `vector_store.py` |
</phase_requirements>

---

## Standard Stack

### Core (đã có trong requirements.txt)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=8.0 | Test runner | Đã cài, dùng xuyên suốt dự án |
| pytest-asyncio | >=0.23 | Async test support | Cần cho SSE streaming tests |
| httpx | >=0.27 | FastAPI TestClient + SSE streaming | TestClient dùng httpx nội bộ |
| chromadb | 1.5.7 | Real ChromaDB in tmpdir | `PersistentClient(path=tmpdir)` — pattern đã verify |
| unittest.mock | stdlib | Patch partition, LLM, ImageProcessor | Đã dùng thành công trong toàn bộ test suite |

[VERIFIED: requirements.txt lines 127-129 — pytest>=8.0, pytest-asyncio>=0.23, httpx>=0.27]
[VERIFIED: requirements.txt line 12 — chromadb==1.5.7]

### Fixtures đã có (không cần tạo mới)
| Fixture | File | Purpose |
|---------|------|---------|
| `client` | conftest.py:71 | FastAPI TestClient với in-memory SQLite |
| `test_db` | conftest.py:59 | SQLAlchemy test session, auto-rollback |
| `mock_embeddings` | conftest.py:88 | MagicMock embed (384 dims) |
| `_NonClosingSession` | test_pipeline.py:65 | Ngăn `db.close()` expunge ORM objects |

[VERIFIED: backend/tests/conftest.py — đọc trực tiếp]
[VERIFIED: backend/tests/test_pipeline.py — đọc trực tiếp]

### Không cần cài thêm gì
Tất cả dependencies đã có. Không cần `pytest-mock`, `factory_boy`, hay tool mới nào. [VERIFIED: requirements.txt + conftest.py]

---

## Architecture Patterns

### Pattern 1: ChromaDB Thật Trong tmpdir (Isolation)

**What:** Mỗi test tạo `PersistentClient(path=tempfile.mkdtemp())`, thực hiện thao tác thật, rồi `shutil.rmtree(tmpdir)` trong `finally`.

**When to use:** TEST-02 (metadata round-trip), TEST-03 (provider switch). Không dùng ChromaDB shared toàn suite.

**Why:** Pattern này đã được chứng minh hoạt động trong 11 tests của `test_vector_store.py` (17 tests pass, không regressions). ChromaDB `PersistentClient` trên tmpdir không có side effect giữa các tests.

```python
# Source: backend/tests/test_vector_store.py (đọc trực tiếp)
tmpdir = tempfile.mkdtemp()
try:
    svc = VectorStoreService.__new__(VectorStoreService)
    svc.client = PersistentClient(path=tmpdir)
    # ... test logic ...
    del svc.client  # giải phóng sqlite file lock TRƯỚC khi cleanup
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
```

**CRITICAL:** Phải `del svc.client` trước `shutil.rmtree` để giải phóng SQLite file lock trên Windows. [VERIFIED: test_vector_store.py pattern nhất quán]

### Pattern 2: Mock Partition + ImageProcessor (Windows Segfault Guard)

**What:** `sys.modules` pre-mock trong conftest.py đã chặn import `unstructured.partition.auto`. Trong test, patch `app.services.document_parser.partition` trực tiếp.

**When to use:** TEST-01 — khi test pipeline `process_and_update_document`.

```python
# Source: backend/tests/test_pipeline.py (đọc trực tiếp)
with patch("app.services.document_parser.SessionLocal", return_value=wrapped), \
     patch("app.services.document_parser.partition", return_value=mock_partition_result), \
     patch("app.services.document_parser.vector_store", mock_vs), \
     patch("app.services.document_parser.ImageProcessorService"):
    process_and_update_document(doc_id)
```

**CRITICAL:** Đối với TEST-01 E2E thật, không mock `vector_store` — thay vào đó patch `vector_store` module-level singleton bằng instance dùng chromadb tmpdir.

### Pattern 3: SSE Collection (Chat Endpoint)

**What:** `client.stream('POST', '/api/chat', json={...})` để thu SSE events, `iter_lines()` để parse từng dòng `data: ...`.

**When to use:** TEST-01 — verify chat response có citations.

```python
# Source: backend/tests/test_chat_router.py (đọc trực tiếp)
def _collect_sse_lines(response) -> list[str]:
    lines = []
    for line in response.iter_lines():
        if line.startswith('data:'):
            lines.append(line)
    return lines

with client.stream('POST', '/api/chat', json={'message': 'test', 'project_id': 1}) as response:
    data_lines = _collect_sse_lines(response)
last_payload = json.loads(data_lines[-1][len('data: '):])
assert last_payload.get('done') is True
assert isinstance(last_payload.get('citations'), list)
```

### Pattern 4: _NonClosingSession Wrapper

**What:** Proxy class ngăn `close()` expunge ORM objects khi test chia sẻ session với pipeline.

**When to use:** TEST-01 — khi test E2E và `process_and_update_document` gọi `db.close()` trong finally block.

**Why:** Nếu không dùng, `test_db.refresh(document)` sau pipeline sẽ raise `InvalidRequestError: Instance not persistent`. [VERIFIED: 03B-03-SUMMARY.md — documented as auto-fixed issue]

### Anti-Patterns to Avoid

- **Shared ChromaDB instance giữa tests:** Dẫn đến provider metadata xung đột khi test TEST-03. Mỗi test phải có tmpdir riêng.
- **Mock toàn bộ VectorStoreService trong TEST-02:** Làm mất giá trị của metadata round-trip test — phải dùng real ChromaDB.
- **Dùng real LLM/API key trong TEST-01:** CI sẽ fail không có key. Mock LLM với `async def mock_astream_ok()` giống `test_chat_router.py`.
- **Quên `del svc.client` trước cleanup:** SQLite file lock trên Windows ngăn `shutil.rmtree`. [VERIFIED: pattern trong mọi test_vector_store.py test]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE parsing trong test | Custom parser | `response.iter_lines()` của httpx | Đã có, đã dùng trong test_chat_router.py |
| Database seeding | Custom ORM helpers | Tái dùng `_seed_project_with_document` pattern từ test_search_router.py | Giữ consistency, giảm boilerplate |
| Async mock LLM | asyncio.Queue custom | `async def mock_astream_ok()` generator | Đơn giản, đã test trong test_chat_router.py |
| Chromadb cleanup | Custom wrapper | `tempfile.mkdtemp()` + `shutil.rmtree(ignore_errors=True)` | OS-controlled, đã proven |

---

## Common Pitfalls

### Pitfall 1: BackgroundTask Chạy Async trong TestClient

**What goes wrong:** `POST /api/documents/upload` queue `process_and_update_document` như BackgroundTask. FastAPI TestClient (sync) chạy background tasks *trong* request lifecycle — nhưng chỉ khi dùng context manager `with TestClient(app) as c`.

**Why it happens:** TestClient với `with` block mới flush background tasks. Nếu test tạo client không dùng `with`, background tasks không chạy.

**How to avoid:** Luôn dùng `with TestClient(app) as c:` (conftest.py đã làm đúng ở dòng 83). Khi cần control background task trong E2E test, gọi `process_and_update_document` trực tiếp sau upload thay vì chờ background.

**Warning signs:** Document vẫn ở status `"pending"` sau upload trong test.

[ASSUMED] — Behavior BackgroundTask trong TestClient dựa trên Starlette test behavior. Cần verify nếu E2E test fail.

### Pitfall 2: Windows SQLite Lock Khi Cleanup ChromaDB

**What goes wrong:** `shutil.rmtree(tmpdir)` fail với `PermissionError` vì ChromaDB PersistentClient giữ file lock trên SQLite.

**Why it happens:** ChromaDB 1.5.7 dùng SQLite làm backend. Trên Windows, file lock không tự release cho đến khi object bị garbage collect.

**How to avoid:** `del svc.client` TRƯỚC `shutil.rmtree`. Dùng `ignore_errors=True` trong rmtree. [VERIFIED: pattern nhất quán trong test_vector_store.py — tất cả 11 tests dùng `del svc.client`]

### Pitfall 3: Provider Metadata Không Bị Ghi Đè Khi get_or_create_collection

**What goes wrong:** ChromaDB `get_or_create_collection` CHỈ set metadata khi tạo collection lần đầu. Re-create với metadata khác không update.

**Why it happens:** ChromaDB design — metadata là immutable sau creation. [VERIFIED: 03C-02-SUMMARY.md: "Use get_or_create_collection metadata param to store provider info on first creation only (ChromaDB behavior verified in RESEARCH.md)"]

**How to avoid:** Trong TEST-03, test đúng flow: (1) insert với provider A, (2) `delete_collection`, (3) reindex với provider B. Không test ghi đè metadata trực tiếp.

**Warning signs:** Test expects provider mismatch nhưng không có — do tạo collection mới trong cùng tmpdir với tên khác.

### Pitfall 4: chunk_index Không Có Trong Metadata Sau Round-Trip

**What goes wrong:** `chunk_index` được assign SAU khi `splitter.create_documents()`, rồi append vào metadata dict. Nếu code thay đổi thứ tự, field này có thể mất.

**Why it happens:** `_build_chunks()` giai đoạn 4 mới assign `chunk_index` — không có trong splitter metadata ban đầu.

**How to avoid:** TEST-02 phải assert tường minh 5 fields: `document_id`, `filename`, `page_number`, `chunk_index`, `element_type`. [VERIFIED: REQUIREMENTS.md CHUNK-02]

### Pitfall 5: `document_id` Lưu Là String Trong ChromaDB

**What goes wrong:** `_build_chunks()` set `"document_id": str(document_id)` — dạng string. Test assert `document_id == 1` (int) sẽ fail.

**Why it happens:** ChromaDB metadata chỉ hỗ trợ str/int/float/bool; `document_id` được str-ify bởi `_sanitize_metadata`. [VERIFIED: document_parser.py dòng 162: `"document_id": str(document_id)`]

**How to avoid:** Assert `metadata['document_id'] == '1'` (string), không phải integer.

### Pitfall 6: TEST-01 E2E — Cần Patch vector_store Singleton

**What goes wrong:** `vector_store = VectorStoreService()` là module-level singleton trong `vector_store.py`. Nếu test không redirect nó sang tmpdir client, dữ liệu chạy vào production ChromaDB path.

**Why it happens:** Module-level singleton được tạo khi import, không có dependency injection.

**How to avoid:** Trong TEST-01, tạo `VectorStoreService` với tmpdir client rồi patch:
```python
svc = VectorStoreService.__new__(VectorStoreService)
svc.client = PersistentClient(path=tmpdir)
with patch('app.services.document_parser.vector_store', svc), \
     patch('app.routers.search.vector_store', svc), \
     patch('app.routers.chat.vector_store', svc):
    ...
```

---

## Code Examples

### TEST-01: E2E Upload → ChromaDB → Chat

```python
# Source: Synthesized từ test_pipeline.py + test_chat_router.py + test_search_router.py patterns

import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch
import pytest
from chromadb import PersistentClient
from app.models.domain import Project, Folder, Document
from app.services.vector_store import VectorStoreService
from app.services.document_parser import process_and_update_document


class _NonClosingSession:
    def __init__(self, session):
        self._session = session
    def close(self): pass
    def __getattr__(self, name): return getattr(self._session, name)


def _make_mock_text_element(text="RAG test content about AI.", page_number=1):
    el = MagicMock()
    el.text = text
    el.category = "NarrativeText"
    el.metadata = MagicMock()
    el.metadata.page_number = page_number
    el.metadata.image_path = None
    return el


async def _mock_astream_with_citation(*args, **kwargs):
    for token in ["This", " is", " about", " AI."]:
        chunk = MagicMock()
        chunk.content = token
        yield chunk


class TestE2EUploadToChat:
    """TEST-01: E2E Upload PDF → verify chunks in ChromaDB → chat → citations."""

    def test_upload_to_chat_with_citations(self, client, test_db):
        tmpdir = tempfile.mkdtemp()
        try:
            # 1. Setup: real ChromaDB trong tmpdir
            vs = VectorStoreService.__new__(VectorStoreService)
            vs.client = PersistentClient(path=tmpdir)

            # 2. Setup: project + folder trong DB
            project = Project(name="E2E Project")
            test_db.add(project)
            test_db.commit()
            test_db.refresh(project)
            folder = Folder(name="E2E Folder", project_id=project.id)
            test_db.add(folder)
            test_db.commit()
            test_db.refresh(folder)

            # 3. Upload document (tạo DB record trực tiếp — skip HTTP upload vì BackgroundTask timing)
            import tempfile as tf
            with tf.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(b"%PDF-1.4 fake content")
                tmp_file = f.name

            doc = Document(filename="test.pdf", file_path=tmp_file, folder_id=folder.id, status="pending")
            test_db.add(doc)
            test_db.commit()
            test_db.refresh(doc)
            doc_id = doc.id

            # 4. Run pipeline với ChromaDB thật (tmpdir) thay vì mock vector_store
            mock_partition = [_make_mock_text_element("RAG content about AI research.")]
            wrapped = _NonClosingSession(test_db)

            with patch("app.services.document_parser.SessionLocal", return_value=wrapped), \
                 patch("app.services.document_parser.partition", return_value=mock_partition), \
                 patch("app.services.document_parser.vector_store", vs), \
                 patch("app.services.document_parser.ImageProcessorService"):
                process_and_update_document(doc_id)

            # 5. Verify document completed
            refreshed = test_db.query(Document).filter(Document.id == doc_id).first()
            assert refreshed.status == "completed"

            # 6. Verify chunks in ChromaDB
            collection = vs.client.get_collection(f"project_{project.id}")
            assert collection.count() > 0
            results_raw = collection.get(include=["metadatas"])
            for meta in results_raw["metadatas"]:
                assert "filename" in meta
                assert "document_id" in meta

            # 7. Chat query — mock LLM, real vector search via vs
            mock_emb = MagicMock()
            mock_emb.embed_query.return_value = [0.1] * 384
            mock_llm = MagicMock()
            mock_llm.astream = _mock_astream_with_citation

            with patch("app.routers.chat.vector_store", vs), \
                 patch("app.routers.chat.EmbeddingFactory.get_embedding_model", return_value=mock_emb), \
                 patch("app.routers.chat.LLMProviderFactory.get_llm", return_value=mock_llm):
                with client.stream("POST", "/api/chat", json={
                    "message": "What is this about?",
                    "project_id": project.id,
                    "score_threshold": 0.0,
                }) as response:
                    assert response.status_code == 200
                    data_lines = [l for l in response.iter_lines() if l.startswith("data:")]

            # 8. Verify terminal event has citations
            assert len(data_lines) >= 1
            last = json.loads(data_lines[-1][len("data: "):])
            assert last.get("done") is True
            assert isinstance(last.get("citations"), list)

            del vs.client
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
```

### TEST-02: ChromaDB Metadata Round-Trip

```python
# Source: Pattern từ test_vector_store.py (test_collection_metadata_stored)

class TestChromaDBMetadataRoundTrip:
    """TEST-02: Insert chunk with full metadata, query, assert all 5 fields survive."""

    def test_metadata_roundtrip_all_fields(self):
        from app.services.vector_store import VectorStoreService, _sanitize_metadata
        from chromadb import PersistentClient

        tmpdir = tempfile.mkdtemp()
        try:
            svc = VectorStoreService.__new__(VectorStoreService)
            svc.client = PersistentClient(path=tmpdir)

            mock_emb = MagicMock()
            mock_emb.embed_documents.return_value = [[0.1] * 384]
            mock_emb.embed_query.return_value = [0.1] * 384

            # Insert với đủ 5 fields theo CHUNK-02
            metadata = {
                "document_id": "42",      # string — per _sanitize_metadata
                "filename": "test.pdf",
                "page_number": 3,
                "chunk_index": 0,
                "element_type": "NarrativeText",
            }
            svc.insert_documents(
                ["Chunk content for round-trip test."],
                [metadata],
                project_id=1,
                embedding_model=mock_emb,
                provider="local",
                model="all-MiniLM-L6-v2",
            )

            # Query và verify metadata survive
            results = svc.similarity_search_mmr(
                query="round-trip test",
                score_threshold=0.0,
                project_id=1,
                embedding_model=mock_emb,
                provider="local",
            )

            assert len(results) == 1
            returned_meta = results[0]["metadata"]
            assert returned_meta["document_id"] == "42"
            assert returned_meta["filename"] == "test.pdf"
            assert returned_meta["page_number"] == 3
            assert returned_meta["chunk_index"] == 0
            assert returned_meta["element_type"] == "NarrativeText"

            del svc.client
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
```

### TEST-03: Embedding Provider Switch Triggers Re-Index

```python
# Source: Pattern từ test_search_router.py (test_reindex_marks_documents_pending)
# + test_vector_store.py (test_similarity_search_mmr_provider_check)

class TestProviderSwitchReindex:
    """TEST-03: Switch provider -> re-index -> search works, no silent corruption."""

    def test_provider_switch_without_reindex_raises_mismatch(self, client, test_db):
        """Before re-index: querying with different provider raises 400 mismatch."""
        tmpdir = tempfile.mkdtemp()
        try:
            vs = VectorStoreService.__new__(VectorStoreService)
            vs.client = PersistentClient(path=tmpdir)

            # Insert với provider 'local'
            mock_emb = MagicMock()
            mock_emb.embed_documents.return_value = [[0.1] * 384]
            vs.insert_documents(
                ["Content here."],
                [{"document_id": "1", "filename": "a.pdf", "page_number": 1, "chunk_index": 0, "element_type": "Text"}],
                project_id=1,
                embedding_model=mock_emb,
                provider="local",
                model="all-MiniLM-L6-v2",
            )

            # Query với provider 'openai' phải raise ValueError
            mock_emb2 = MagicMock()
            mock_emb2.embed_query.return_value = [0.2] * 384
            import pytest
            with pytest.raises(ValueError, match="mismatch"):
                vs.similarity_search_mmr(
                    query="test",
                    project_id=1,
                    embedding_model=mock_emb2,
                    provider="openai",
                )

            del vs.client
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_reindex_endpoint_marks_pending_and_allows_new_provider(self, client, test_db):
        """POST /api/projects/{id}/reindex marks documents pending (router test)."""
        project = Project(name="Switch Provider Project")
        test_db.add(project)
        test_db.commit()
        test_db.refresh(project)
        folder = Folder(name="f", project_id=project.id)
        test_db.add(folder)
        test_db.commit()
        test_db.refresh(folder)
        doc = Document(filename="doc.pdf", file_path="/tmp/doc.pdf", folder_id=folder.id, status="completed")
        test_db.add(doc)
        test_db.commit()
        test_db.refresh(doc)

        with patch("app.routers.search.process_and_update_document"), \
             patch("app.routers.search.vector_store") as mock_vs:
            mock_vs.client.delete_collection = MagicMock()
            response = client.post(f"/api/projects/{project.id}/reindex")

        assert response.status_code == 202
        test_db.refresh(doc)
        assert doc.status == "pending"
        # delete_collection phải được gọi để xóa old provider metadata
        mock_vs.client.delete_collection.assert_called_once_with(f"project_{project.id}")
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | Không có `pytest.ini` — chạy từ `backend/` directory |
| Quick run command | `cd backend && python -m pytest tests/test_e2e_validation.py -v` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEST-01 | Upload PDF → chunks in ChromaDB → chat → SSE citations | integration | `pytest tests/test_e2e_validation.py::TestE2EUploadToChat -v` | ❌ Wave 0 |
| TEST-02 | Metadata round-trip qua ChromaDB | unit | `pytest tests/test_e2e_validation.py::TestChromaDBMetadataRoundTrip -v` | ❌ Wave 0 |
| TEST-03 | Provider switch raises mismatch; reindex endpoint marks pending | integration | `pytest tests/test_e2e_validation.py::TestProviderSwitchReindex -v` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_e2e_validation.py -v`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green trước `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_e2e_validation.py` — covers TEST-01, TEST-02, TEST-03

*(Tất cả infrastructure test (conftest.py, fixtures, framework) đã có — không cần tạo thêm)*

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pytest | All tests | ✓ (in requirements.txt) | >=8.0 | — |
| chromadb | TEST-01, TEST-02, TEST-03 | ✓ | 1.5.7 | — |
| httpx | SSE streaming tests | ✓ | >=0.27 | — |
| langchain_openai | embeddings.py import | ✗ trong test env hiện tại | — | Mock via `sys.modules` hoặc cài đủ deps |

**Chú ý môi trường:**
- Test hiện tại KHÔNG chạy được trong shell hiện tại vì `langchain_openai` không được cài trong Python env hiện tại (`ModuleNotFoundError`). [VERIFIED: bash output khi chạy pytest]
- Giả định: Test suite chạy được trong môi trường dev đầy đủ (venv với requirements.txt). Phaser cần verify môi trường trước khi execute.

---

## Security Domain

Áp dụng cho phase này ở mức tối thiểu — đây là test-only code:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | no | Test code không nhận user input |
| V6 Cryptography | no | Không có crypto operations |

**Không có threat mới:** Test files không introduce network endpoints hay auth paths mới.

**Lưu ý:** Các tests không được hardcode API key. Mock LLM và embedding models để tránh phụ thuộc credential. [VERIFIED: pattern trong test_chat_router.py]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | BackgroundTask trong TestClient flush trong `with TestClient(app) as c:` block | Common Pitfalls #1 | TEST-01 có thể dùng direct `process_and_update_document` call — không blocking |
| A2 | Phase 4a, 4b đã hoàn thành và `chat.py`, `rag_chain.py`, `llm_provider.py` tồn tại | Code Examples TEST-01 | Đã verify `chat.py` và `rag_chain.py` exist — LLMProviderFactory cần verify |

---

## Open Questions

1. **LLMProviderFactory location**
   - What we know: `chat.py` import từ `app.services.llm_provider`
   - What's unclear: File này chưa đọc trực tiếp trong session này
   - Recommendation: Planner kiểm tra `backend/app/services/llm_provider.py` tồn tại — nếu có, TEST-01 mock `app.routers.chat.LLMProviderFactory.get_llm` như trong `test_chat_router.py`

2. **TEST-01 — Sync vs Async vector search**
   - What we know: `chat.py` dùng `asyncio.to_thread(vector_store.similarity_search_mmr, ...)` (dòng 44-50)
   - What's unclear: Khi patch `app.routers.chat.vector_store` bằng instance có tmpdir, `asyncio.to_thread` vẫn hoạt động bình thường
   - Recommendation: Không có issue — `asyncio.to_thread` chỉ là wrapper, không ảnh hưởng đến mock behavior

3. **Số lượng chunks từ fake document**
   - What we know: `_make_mock_text_element` return text ngắn → `RecursiveCharacterTextSplitter(512)` → 1 chunk
   - What's unclear: Cần ít nhất 1 chunk trong ChromaDB để `similarity_search_mmr` không return `[]`
   - Recommendation: Dùng text đủ dài (>64 chars) và `score_threshold=0.0` trong TEST-01 để đảm bảo search trả về kết quả

---

## Sources

### Primary (HIGH confidence)
- `backend/tests/conftest.py` — fixtures, pre-mock pattern, TestClient setup
- `backend/tests/test_pipeline.py` — `_NonClosingSession` pattern, pipeline mock
- `backend/tests/test_vector_store.py` — ChromaDB tmpdir pattern, provider mismatch tests
- `backend/tests/test_search_router.py` — reindex endpoint tests, `_seed_project_with_document`
- `backend/tests/test_chat_router.py` — SSE streaming test pattern, `_collect_sse_lines`
- `backend/app/services/vector_store.py` — `_sanitize_metadata`, `document_id` as string
- `backend/app/services/document_parser.py` — `_build_chunks` metadata schema
- `.planning/phases/03B-ingestion-pipeline/03B-03-SUMMARY.md` — `_NonClosingSession` rationale
- `.planning/phases/03C-retrieval/03C-02-SUMMARY.md` — ChromaDB metadata behavior
- `backend/requirements.txt` — dependency versions

### Secondary (MEDIUM confidence)
- `.planning/phases/03C-retrieval/03C-03-SUMMARY.md` — reindex endpoint behavior
- `.planning/phases/04A-chat-backend/04A-02-SUMMARY.md` — file không tìm thấy (phase 4a chưa execute)

### Tertiary (LOW confidence)
- Behavior BackgroundTask trong Starlette TestClient (A1 trong Assumptions Log)

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — verified từ requirements.txt và conftest.py
- Architecture Patterns: HIGH — verified từ 4 test files hiện có
- Code Examples: HIGH — synthesized từ verified patterns, không có assumptions mới
- Pitfalls: HIGH — 4/6 pitfalls verified trực tiếp từ code; 2 inferred từ Windows behavior

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (30 ngày — ChromaDB và pytest API ổn định)
