---
phase: 03B-ingestion-pipeline
verified: 2026-04-09T17:00:00Z
status: human_needed
score: 11/11 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Upload a 10-page PDF with embedded images via the API; check ChromaDB for chunks with page_number metadata"
    expected: "Chunks appear in ChromaDB collection with document_id, filename, page_number, chunk_index, element_type all populated"
    why_human: "Cannot run real unstructured.io partition() in test environment (segfault on Windows/WSL2); tests use mocked partition. Only real file upload through running server verifies end-to-end."
  - test: "Upload a PPTX file with images; check that image summary chunks appear in ChromaDB"
    expected: "element_type='image_summary' chunks present with placeholder text (if no GOOGLE_API_KEY) or real Gemini summary (if key set)"
    why_human: "Image extraction path depends on unstructured running in production environment, not mocked test environment."
  - test: "Set GOOGLE_API_KEY and upload a PDF with images; verify Gemini Vision summarization"
    expected: "Image summary chunks contain real descriptive text from Gemini, not placeholder"
    why_human: "Cannot call real Gemini API in automated tests; requires live API key and running server."
---

# Phase 03B: Ingestion Pipeline Verification Report

**Phase Goal:** Upload a real PDF/DOCX/PPTX/XLSX and produce properly chunked, metadata-rich vectors in ChromaDB. Covers: document parsing with unstructured.io, image extraction and summarization via Gemini Vision, text chunking with RecursiveCharacterTextSplitter, and end-to-end pipeline wiring.

**Verified:** 2026-04-09T17:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | PDF/DOCX/PPTX/XLSX parsing via unstructured.io `strategy="auto"` | VERIFIED | `partition(strategy="auto", ...)` at document_parser.py:65; `from unstructured.partition.auto import partition` at line 31 |
| 2 | Image extraction from PDF/PPTX with `extract_images_in_pdf=True` | VERIFIED | `extract_images_in_pdf=True, extract_image_block_output_dir=temp_dir` at document_parser.py:66-67 |
| 3 | ImageProcessorService summarizes images via Gemini Vision with 3-attempt retry | VERIFIED | `@retry(stop=stop_after_attempt(3), wait=wait_exponential(...))` at image_processor.py:59-63; uses `google.genai` SDK v1.71.0 |
| 4 | Image summarization failure returns placeholder, document still completes | VERIFIED | `_summarize_with_retry` catches final exception, returns `PLACEHOLDER_TEMPLATE.format(...)`; test `test_image_failure_does_not_fail_document` passes |
| 5 | Element metadata (page_number, element_type, filename) preserved through pipeline | VERIFIED | `_build_chunks` passes `page_number`, `element_type`, `filename` into splitter metadata; test `test_chunk_metadata_schema` verifies all 5 keys |
| 6 | RecursiveCharacterTextSplitter chunk_size=512, chunk_overlap=64, add_start_index=True | VERIFIED | document_parser.py:114-116 contains exact parameters; test `test_chunk_size_within_limit` verifies enforcement |
| 7 | Each chunk carries metadata: document_id, filename, page_number, chunk_index, element_type | VERIFIED | document_parser.py:163-168 constructs metadata dict with all 5 keys; chunk_index assigned globally at Phase 4 (line 177) |
| 8 | Image summaries chunked and interleaved at original page position | VERIFIED | `intermediate.sort(key=lambda x: x["page_number"])` at line 153; `element_type="image_summary"` at line 137; test `test_image_summary_interleaved` passes |
| 9 | Document status transitions: pending -> processing -> completed/failed | VERIFIED | `db_document.status = "processing"` (line 205), `"completed"` (line 265), `"failed"` (lines 218, 271); 3 pipeline tests verify all transitions |
| 10 | delete_by_document called before insert_documents (re-processing safety) | VERIFIED | `vector_store.delete_by_document(document_id, proj_id)` at line 237 before `vector_store.insert_documents(...)` at line 241; test `test_delete_before_insert` verifies ordering via call_order list |
| 11 | ChromaDB metadata sanitized to scalar types before insertion | VERIFIED | `_sanitize_metadata(m) for m in metadatas` in `insert_documents` at vector_store.py:63; test `test_chunk_metadata_values_are_scalars` verifies all values are str/int/float/bool |

**Score:** 11/11 truths verified

---

### Deferred Items

None.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/services/document_parser.py` | DocumentParserService + process_and_update_document rewrite | VERIFIED | Contains `from unstructured.partition.auto import partition`, `_build_chunks`, `process_and_update_document`; 279 lines |
| `backend/app/services/image_processor.py` | ImageProcessorService class | VERIFIED | Contains `class ImageProcessorService`, `@retry`, `stop_after_attempt(3)`; uses `google.genai` v1.71 SDK |
| `backend/app/services/vector_store.py` | delete_by_document + _sanitize_metadata | VERIFIED | Both methods present and wired; `_sanitize_metadata` applied to all upsert calls |
| `backend/app/models/domain.py` | Document.status column | VERIFIED | `status = Column(String, default="pending", nullable=False)` at line 37 |
| `backend/app/schemas/domain.py` | DocumentResponse.status field | VERIFIED | `status: Optional[str] = None` in both `DocumentBase` (line 36) and `DocumentResponse` (line 44) |
| `backend/app/core/database.py` | ALTER TABLE migration for status column | VERIFIED | `_migrate_add_status_column(engine)` at line 63; runs idempotently at import time |
| `backend/requirements.txt` | New dependencies (unstructured, Gemini SDK) | VERIFIED | `unstructured[pdf,docx,pptx,xlsx]` at line 124; `google-genai>=1.0` at line 125 |
| `backend/tests/test_document_parser.py` | 5 parser tests | VERIFIED | `test_parse_document_returns_elements`, `test_metadata_null_page_number_defaults_to_zero`, etc. — 5 tests PASS |
| `backend/tests/test_chunking.py` | 8 chunking tests | VERIFIED | `test_chunk_size_within_limit`, `test_chunk_metadata_schema`, `test_image_summary_interleaved`, `test_chunk_index_globally_unique` — 8 tests PASS |
| `backend/tests/test_pipeline.py` | 7 pipeline integration tests | VERIFIED | `test_status_transitions_success`, `test_delete_before_insert`, `test_temp_dir_cleaned_on_success`, etc. — 7 tests PASS |
| `backend/tests/test_image_processor.py` | 5 image processor tests | VERIFIED | `test_summarize_success`, `test_summarize_failure_returns_placeholder`, `test_missing_api_key_returns_placeholder`, `test_api_key_not_logged`, `test_retry_count` — 5 tests PASS |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `document_parser.py` | `unstructured.partition.auto` | `partition(strategy="auto")` call | VERIFIED | Line 31: `from unstructured.partition.auto import partition`; line 63-69: real call with all parameters |
| `document_parser.py` | `image_processor.py` | `ImageProcessorService().summarize_image()` | VERIFIED | Line 34: import; line 131: `image_processor.summarize_image(image_path, filename)` |
| `document_parser.py` | `vector_store.py` | `vector_store.delete_by_document()` then `vector_store.insert_documents()` | VERIFIED | Lines 237, 241: delete then insert in sequence |
| `document_parser.py` | `langchain_text_splitters` | `RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)` | VERIFIED | Line 28: import; line 113-117: instantiation with exact parameters |
| `image_processor.py` | `google-genai` (v1.71) | `genai.Client(api_key=...).models.generate_content()` | VERIFIED | Lines 19-20: `from google import genai; from google.genai import types`; line 72-92: real API call |
| `vector_store.py` | `chromadb` | `collection.delete(where={"document_id": str(document_id)})` | VERIFIED | Lines 71-74: `client.get_collection(name=...)` + `collection.delete(where=...)` |
| `database.py` | `Document` model | `ALTER TABLE documents ADD COLUMN status` | VERIFIED | Line 54: `cursor.execute("ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'pending' NOT NULL")` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `document_parser.py / process_and_update_document` | `all_chunks, all_metadatas` | `_build_chunks(elements=parse_result["elements"], ...)` | Yes — consumes real partition() output | FLOWING |
| `document_parser.py / _build_chunks` | `intermediate` list | `element["text"]` + `image_processor.summarize_image(image_path, ...)` | Yes — real text from unstructured elements + real/placeholder image summaries | FLOWING |
| `vector_store.py / insert_documents` | `embeddings` | `get_default_embeddings().embed_documents(text_chunks)` | Yes — lazy-loaded sentence-transformers model | FLOWING |
| `image_processor.py / _call_gemini` | `response.text` | `client.models.generate_content(model="gemini-2.0-flash", ...)` | Yes — real Gemini API call (requires GOOGLE_API_KEY) | FLOWING (with graceful fallback on missing key) |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Document.status has default "pending" | `python -c "from app.models.domain import Document; print(Document.status.default.arg)"` | `pending` | PASS |
| DocumentResponse includes status field | `python -c "from app.schemas.domain import DocumentResponse; print('status' in DocumentResponse.model_fields)"` | `True` | PASS |
| _sanitize_metadata converts None to "" | `python -c "from app.services.vector_store import _sanitize_metadata; print(_sanitize_metadata({'a': None}))"` | `{'a': ''}` | PASS |
| _sanitize_metadata converts list to str | `python -c "from app.services.vector_store import _sanitize_metadata; print(_sanitize_metadata({'b': [1,2]}))"` | `{'b': '[1, 2]'}` | PASS |
| _migrate_add_status_column in database.py | `python -c "import ast; ...assert '_migrate_add_status_column' in funcs"` | `True` | PASS |
| All Phase 03B tests pass (31 tests) | `python -m pytest tests/test_vector_store.py tests/test_image_processor.py tests/test_document_parser.py tests/test_chunking.py tests/test_pipeline.py` | `31 passed` | PASS |
| google.genai SDK available | `python -c "import google.genai; print(google.genai.__version__)"` | `1.71.0` | PASS |
| Real partition() call (import only) | Cannot test — segfaults on WSL2/Windows due to detectron2 C extension | N/A | SKIP (environment limitation, documented in 03B-03-SUMMARY) |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|------------|-------------|--------|----------|
| PARSE-01 | 03B-03 | Parse PDF/DOCX/PPTX/XLSX with `strategy="auto"` | SATISFIED | `partition(filename=..., strategy="auto", ...)` in document_parser.py:63-69 |
| PARSE-02 | 03B-03 | Extract embedded images from PDF/PPTX | SATISFIED | `extract_images_in_pdf=True, extract_image_block_types=["Image","Table"]` in document_parser.py:66-69 |
| PARSE-03 | 03B-02 | Gemini Vision image summarization with retry (tenacity) | SATISFIED | `@retry(stop=stop_after_attempt(3), wait=wait_exponential(...))` in image_processor.py:59-63 |
| PARSE-04 | 03B-02 | Graceful failure: placeholder text on Gemini failure | SATISFIED | `_summarize_with_retry` catches exception, returns `PLACEHOLDER_TEMPLATE.format(filename=filename)` |
| PARSE-05 | 03B-01, 03B-03 | Preserve element metadata (page_number, element_type, filename) | SATISFIED | All 3 metadata fields passed through `_build_chunks`; test `test_chunk_metadata_schema` verifies 5-key schema |
| CHUNK-01 | 03B-03 | RecursiveCharacterTextSplitter (512/64/add_start_index=True) | SATISFIED | document_parser.py:113-117 exact parameters; test `test_chunk_size_within_limit` passes |
| CHUNK-02 | 03B-01, 03B-03 | Chunk metadata: document_id, filename, page_number, chunk_index, element_type | SATISFIED | All 5 keys set in `_build_chunks`; test `test_chunk_metadata_schema` verifies |
| CHUNK-03 | 03B-03 | Image summaries chunked and embedded as text | SATISFIED | Image summaries passed through same splitter with `element_type="image_summary"` |

**Orphaned requirements from REQUIREMENTS.md assigned to Phase 3b:** None — all 8 requirements (PARSE-01 through PARSE-05, CHUNK-01 through CHUNK-03) are claimed in plan frontmatter.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/schemas/domain.py` | 15, 26, 41 | `class Config:` (deprecated Pydantic v1 style) | INFO | PydanticDeprecatedSince20 warning in tests; functional but should migrate to `model_config = ConfigDict(...)` |

No blockers or stubs found. All "placeholder" references in code are intentional graceful-failure return values per D-08 and PARSE-04, not stubs.

**Note on Gemini SDK deviation:** Plan 03B-01 specified `google-generativeai` (old SDK), but implementation uses `google-genai>=1.0` (new SDK) with `from google import genai; genai.Client(api_key=...)`. This is a valid deviation — the old SDK emits a `FutureWarning` indicating all support has ended, and the new SDK provides the same functionality. Requirements.txt correctly lists `google-genai>=1.0`. All 5 image processor tests pass with the new SDK interface.

---

### Human Verification Required

#### 1. End-to-End PDF Upload with Real Chunks in ChromaDB

**Test:** Start the backend server; upload a 10-page PDF via the API (`POST /api/documents/upload`); query ChromaDB directly or through the `/api/search` endpoint.
**Expected:** Chunks appear in ChromaDB with `page_number` metadata matching the PDF's actual page numbers, `document_id` matching the DB record, and `element_type` set to the unstructured element types (NarrativeText, Title, etc.).
**Why human:** The test suite mocks `partition()` entirely due to a segfault when importing `unstructured.partition.auto` on Windows/WSL2 (detectron2/torch C-extension incompatibility). Real parsing can only be verified by running the server in its production environment.

#### 2. PPTX with Images — Image Summary Chunks

**Test:** Upload a PPTX file containing at least one image slide. Check that the resulting ChromaDB vectors include chunks with `element_type="image_summary"`.
**Expected:** If `GOOGLE_API_KEY` is not set: image chunks contain `"[Image: unable to process - {filename}]"`. If key is set: image chunks contain meaningful Gemini Vision descriptions.
**Why human:** Requires real unstructured.io image extraction (not mocked) and optionally a live Gemini API key.

#### 3. Gemini Vision Integration (Live API Key)

**Test:** Set `GOOGLE_API_KEY` to a valid key; upload a PDF with embedded images; inspect the image summary chunks in ChromaDB.
**Expected:** Image summary chunks contain concise, descriptive text from Gemini (not the placeholder string). Document status reaches "completed".
**Why human:** Cannot call live Gemini API in automated tests; requires real credentials.

---

### Gaps Summary

No gaps found. All 11 observable truths are VERIFIED. All 8 requirements (PARSE-01..05, CHUNK-01..03) are SATISFIED. All 31 automated tests pass. The `human_needed` status is due to 3 end-to-end behaviors that require a running server with real unstructured.io execution (blocked by environment-level segfault on WSL2/Windows during test collection).

---

_Verified: 2026-04-09T17:00:00Z_
_Verifier: Claude (gsd-verifier)_
