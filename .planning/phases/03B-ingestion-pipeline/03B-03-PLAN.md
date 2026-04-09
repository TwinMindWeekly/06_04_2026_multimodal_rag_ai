---
phase: 03B-ingestion-pipeline
plan: 03
type: execute
wave: 2
depends_on: ["03B-01", "03B-02"]
files_modified:
  - backend/app/services/document_parser.py
  - backend/tests/test_document_parser.py
  - backend/tests/test_chunking.py
  - backend/tests/test_pipeline.py
autonomous: true
requirements: [PARSE-01, PARSE-02, PARSE-05, CHUNK-01, CHUNK-02, CHUNK-03]

must_haves:
  truths:
    - "DocumentParserService.parse_document() calls unstructured partition() with strategy='auto' and image extraction"
    - "partition() is called with extract_images_in_pdf=True and extract_image_block_output_dir=temp_dir"
    - "Each element's page_number, element_type, and filename are preserved through the pipeline"
    - "RecursiveCharacterTextSplitter uses chunk_size=512, chunk_overlap=64, add_start_index=True"
    - "Image summaries are chunked with same splitter and interleaved at original page position with element_type='image_summary'"
    - "chunk_index is globally unique per document, not per element"
    - "process_and_update_document transitions status: pending -> processing -> completed/failed"
    - "Temp directory is cleaned up in a finally block regardless of success or failure"
    - "Parsing failure marks document status as 'failed'"
    - "Image summarization failure stores placeholder, document still completes"
    - "delete_by_document is called before inserting new vectors (re-processing safety)"
  artifacts:
    - path: "backend/app/services/document_parser.py"
      provides: "DocumentParserService + process_and_update_document rewrite"
      contains: "from unstructured.partition.auto import partition"
    - path: "backend/tests/test_document_parser.py"
      provides: "Tests for PARSE-01, PARSE-02, PARSE-05, pipeline status"
      contains: "test_parse_document_returns_elements"
    - path: "backend/tests/test_chunking.py"
      provides: "Tests for CHUNK-01, CHUNK-02, CHUNK-03"
      contains: "test_chunk_size_within_limit"
    - path: "backend/tests/test_pipeline.py"
      provides: "Integration tests for status transitions and delete-before-insert"
      contains: "test_status_transitions"
  key_links:
    - from: "backend/app/services/document_parser.py"
      to: "unstructured.partition.auto"
      via: "partition() call with strategy='auto'"
      pattern: "partition\\("
    - from: "backend/app/services/document_parser.py"
      to: "backend/app/services/image_processor.py"
      via: "ImageProcessorService().summarize_image()"
      pattern: "image_processor\\.summarize_image"
    - from: "backend/app/services/document_parser.py"
      to: "backend/app/services/vector_store.py"
      via: "vector_store.delete_by_document() then vector_store.insert_documents()"
      pattern: "vector_store\\.(delete_by_document|insert_documents)"
    - from: "backend/app/services/document_parser.py"
      to: "langchain_text_splitters"
      via: "RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)"
      pattern: "RecursiveCharacterTextSplitter"
---

<objective>
Rewrite DocumentParserService with real unstructured.io parsing and wire the full ingestion pipeline: parse -> extract images -> summarize images -> chunk all elements -> embed into ChromaDB.

Purpose: This is the core of Phase 3b. It replaces the stub parser with real document parsing, adds text chunking with metadata, integrates image summarization from Plan 02, and orchestrates the full pipeline with proper status tracking and error handling.

Output: Fully functional ingestion pipeline that processes any PDF/DOCX/PPTX/XLSX upload into metadata-rich chunks in ChromaDB.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/03B-ingestion-pipeline/03B-CONTEXT.md
@.planning/phases/03B-ingestion-pipeline/03B-RESEARCH.md
@.planning/phases/03B-ingestion-pipeline/03B-01-SUMMARY.md
@.planning/phases/03B-ingestion-pipeline/03B-02-SUMMARY.md

<interfaces>
<!-- ImageProcessorService from Plan 02 (backend/app/services/image_processor.py) -->
```python
class ImageProcessorService:
    def summarize_image(self, image_path: str, filename: str) -> str:
        """Returns summary text or placeholder '[Image: unable to process - {filename}]'."""
```

<!-- VectorStoreService from Plan 01 (backend/app/services/vector_store.py) -->
```python
def _sanitize_metadata(meta: dict) -> dict:
    """Sanitize metadata for ChromaDB. None -> '', non-scalar -> str()."""

class VectorStoreService:
    def delete_by_document(self, document_id: int, project_id: int = None) -> None: ...
    def insert_documents(self, text_chunks: list[str], metadatas: list[dict], project_id: int = None): ...

vector_store = VectorStoreService()  # module-level singleton
```

<!-- Document model from Plan 01 (backend/app/models/domain.py) -->
```python
class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_path = Column(String)
    folder_id = Column(Integer, ForeignKey("folders.id"))
    metadata_json = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending", nullable=False)
    folder = relationship("Folder", back_populates="documents")
```

<!-- Current document_parser.py (to be rewritten) -->
```python
class DocumentParserService:
    def __init__(self, extract_images: bool = True): ...
    def parse_document(self, file_path: str, document_id: int): ...
        # STUB — returns mock chunks

def process_and_update_document(document_id: int): ...
    # Calls parser, updates metadata_json, inserts mock chunks into ChromaDB
```

<!-- RecursiveCharacterTextSplitter from langchain_text_splitters (installed 1.1.1) -->
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64, add_start_index=True)
docs = splitter.create_documents(texts=[...], metadatas=[...])
# Each doc has .page_content (str) and .metadata (dict)
```

<!-- Existing conftest.py fixtures available -->
```python
@pytest.fixture test_engine  # In-memory SQLite with Base.metadata.create_all
@pytest.fixture test_db      # Session from test_engine
@pytest.fixture client        # FastAPI TestClient with DB override
@pytest.fixture mock_embeddings  # MagicMock with embed_documents/embed_query
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite DocumentParserService with unstructured parsing + chunking</name>
  <files>backend/app/services/document_parser.py, backend/tests/test_document_parser.py, backend/tests/test_chunking.py</files>
  <read_first>
    - backend/app/services/document_parser.py (current stub to be rewritten)
    - backend/app/services/image_processor.py (Plan 02 output — summarize_image interface)
    - backend/app/services/vector_store.py (Plan 01 output — delete_by_document, _sanitize_metadata)
    - backend/app/models/domain.py (Plan 01 output — Document.status)
    - backend/app/core/database.py (SessionLocal import)
    - backend/tests/conftest.py (existing fixtures)
  </read_first>
  <action>
**backend/app/services/document_parser.py** — FULL REWRITE. Replace entire file contents. The new file has two main components: DocumentParserService class and process_and_update_document() function.

**Imports:**
```python
import os
import json
import shutil
import tempfile
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

from sqlalchemy.orm import joinedload
from langchain_text_splitters import RecursiveCharacterTextSplitter
from unstructured.partition.auto import partition

from app.models.domain import Document
from app.services.vector_store import vector_store
from app.services.image_processor import ImageProcessorService
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)
```

**DocumentParserService class (per D-01, D-02, D-03, D-04):**

```python
class DocumentParserService:
    """Parses documents using unstructured.io with image extraction. Per D-01, D-04."""

    def parse_document(self, file_path: str, document_id: int) -> dict:
        """
        Parse a document file and return structured elements with a temp dir for extracted images.

        Args:
            file_path: absolute path to the uploaded file
            document_id: database ID for temp dir naming

        Returns:
            dict with keys:
                "elements": list of dicts with keys text, category, page_number, image_path (optional)
                "temp_dir": path to temp dir with extracted images (caller must clean up)
        """
        temp_dir = tempfile.mkdtemp(prefix=f"doc_{document_id}_")
        try:
            raw_elements = partition(
                filename=file_path,
                strategy="auto",
                extract_images_in_pdf=True,
                extract_image_block_output_dir=temp_dir,
                extract_image_block_types=["Image", "Table"],
            )

            elements = []
            for el in raw_elements:
                element_dict = {
                    "text": el.text or "",
                    "category": el.category if hasattr(el, "category") else "Unknown",
                    "page_number": getattr(el.metadata, "page_number", None) or 0,
                    "image_path": getattr(el.metadata, "image_path", None),
                }
                elements.append(element_dict)

            return {"elements": elements, "temp_dir": temp_dir}

        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
```

**Module-level helper — _build_chunks (per D-09, D-10, D-11, Pitfall 7):**

```python
def _build_chunks(
    elements: List[Dict[str, Any]],
    image_processor: ImageProcessorService,
    document_id: int,
    filename: str,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Chunk all parsed elements (text + image summaries) into final text chunks with metadata.

    Image summaries are interleaved at their original page position per D-11.
    chunk_index is globally unique per document per Pitfall 7.

    Returns:
        (text_chunks, metadatas) — parallel lists ready for VectorStoreService.insert_documents()
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=64,
        add_start_index=True,
    )

    # Phase 1: Process elements into (text, metadata) pairs, preserving page order
    intermediate: List[Dict[str, Any]] = []

    for el in elements:
        text = el["text"]
        category = el["category"]
        page_num = el["page_number"]

        # Handle Image elements — summarize via Gemini, then treat summary as text
        if category == "Image" and el.get("image_path"):
            image_path = el["image_path"]
            summary = image_processor.summarize_image(image_path, filename)
            if summary:
                intermediate.append({
                    "text": summary,
                    "page_number": page_num,
                    "element_type": "image_summary",
                })
            continue

        # Skip empty text elements
        if not text.strip():
            continue

        intermediate.append({
            "text": text,
            "page_number": page_num,
            "element_type": category,
        })

    # Phase 2: Sort by page_number to interleave image summaries at correct position (D-11)
    intermediate.sort(key=lambda x: x["page_number"])

    # Phase 3: Chunk each intermediate item and collect with metadata
    all_chunks: List[str] = []
    all_metadatas: List[Dict[str, Any]] = []

    for item in intermediate:
        docs = splitter.create_documents(
            texts=[item["text"]],
            metadatas=[{
                "document_id": str(document_id),
                "filename": filename,
                "page_number": item["page_number"],
                "element_type": item["element_type"],
            }],
        )
        for doc in docs:
            all_chunks.append(doc.page_content)
            all_metadatas.append(dict(doc.metadata))

    # Phase 4: Assign globally unique chunk_index per document (Pitfall 7)
    for i, meta in enumerate(all_metadatas):
        meta["chunk_index"] = i

    return all_chunks, all_metadatas
```

**process_and_update_document function (per D-12, D-13, D-14, D-15):**

```python
def process_and_update_document(document_id: int) -> None:
    """
    Background task: parse document -> extract images -> summarize -> chunk -> embed.

    Status transitions per D-13: pending -> processing -> completed/failed.
    Delete-before-insert per D-15.
    Per-step failure handling per D-14.
    Temp dir cleanup in finally per D-03.
    """
    db = SessionLocal()
    try:
        db_document = (
            db.query(Document)
            .options(joinedload(Document.folder))
            .filter(Document.id == document_id)
            .first()
        )
        if not db_document:
            logger.warning("Document %d not found — skipping processing", document_id)
            return

        # D-13: transition to processing
        db_document.status = "processing"
        db.commit()

        parser = DocumentParserService()
        image_processor = ImageProcessorService()

        # Step 1: Parse document (D-14: parsing failure -> status='failed')
        try:
            parse_result = parser.parse_document(db_document.file_path, document_id)
        except Exception as e:
            logger.error("Parsing failed for document %d: %s", document_id, e)
            db_document.status = "failed"
            db.commit()
            return

        temp_dir = parse_result["temp_dir"]
        try:
            # Step 2+3: Build chunks (includes image summarization)
            # D-14: image summarization failures produce placeholders, not exceptions
            all_chunks, all_metadatas = _build_chunks(
                elements=parse_result["elements"],
                image_processor=image_processor,
                document_id=document_id,
                filename=db_document.filename,
            )

            # Step 4: Determine project_id
            proj_id = db_document.folder.project_id if db_document.folder else None

            # D-15: delete existing vectors before re-inserting
            vector_store.delete_by_document(document_id, proj_id)

            # Step 5: Embed chunks into ChromaDB
            if all_chunks:
                vector_store.insert_documents(
                    text_chunks=all_chunks,
                    metadatas=all_metadatas,
                    project_id=proj_id,
                )
                logger.info(
                    "Ingested %d chunks for document %d (%s)",
                    len(all_chunks), document_id, db_document.filename,
                )

            # Update document metadata
            current_metadata = json.loads(db_document.metadata_json) if db_document.metadata_json else {}
            updated_metadata = {
                **current_metadata,
                "total_chunks": len(all_chunks),
                "total_images": sum(1 for m in all_metadatas if m.get("element_type") == "image_summary"),
            }
            db_document.metadata_json = json.dumps(updated_metadata)

            # D-13: transition to completed
            db_document.status = "completed"
            db.commit()

        except Exception as e:
            # D-14: embedding/chunking failure -> status='failed'
            logger.error("Processing failed for document %d: %s", document_id, e)
            db_document.status = "failed"
            db.commit()
        finally:
            # D-03: always clean up temp dir
            shutil.rmtree(temp_dir, ignore_errors=True)

    finally:
        db.close()
```

**backend/tests/test_document_parser.py** — REWRITE to test real parser. Replace the 3 existing tests (which tested joinedload pattern via source inspection — those are no longer relevant after the rewrite).

New tests:
1. `test_parse_document_returns_elements` — Mock `partition` to return 2 fake elements (NarrativeText + Image). Assert result has "elements" list with correct category, page_number, text fields. Assert "temp_dir" key exists.
2. `test_image_extraction_paths` — Mock `partition` to return an Image element with `metadata.image_path` set. Assert element dict has `image_path` key containing the path.
3. `test_metadata_preserved_page_number` — Mock `partition` to return element with `metadata.page_number=3`. Assert parsed element dict has `page_number=3`.
4. `test_metadata_null_page_number_defaults_to_zero` — Mock `partition` to return element with `metadata.page_number=None`. Assert parsed element dict has `page_number=0`.
5. `test_parse_failure_cleans_temp_dir` — Mock `partition` to raise RuntimeError. Assert the temp dir created inside parse_document is cleaned up (doesn't exist after exception).

Use `unittest.mock.patch("app.services.document_parser.partition")` to mock unstructured. Create mock elements with `MagicMock()` setting `.text`, `.category`, `.metadata.page_number`, `.metadata.image_path`.

**backend/tests/test_chunking.py** — NEW file. Tests for _build_chunks function:

1. `test_chunk_size_within_limit` — Create intermediate text longer than 512 chars. Call `_build_chunks` with mock image_processor (never called for text elements). Assert every returned chunk has `len(chunk) <= 512`.
2. `test_chunk_overlap` — Create text where overlap is expected. Verify chunks share overlapping content.
3. `test_chunk_metadata_schema` — Call `_build_chunks` and assert every metadata dict has all 5 required keys: `document_id`, `filename`, `page_number`, `chunk_index`, `element_type`.
4. `test_chunk_metadata_values_are_scalars` — Assert every value in every metadata dict is str, int, float, or bool (ChromaDB-compatible).
5. `test_image_summary_interleaved` — Provide elements: [page 1 text, page 2 image, page 2 text, page 3 text]. Mock image_processor to return "Image description". Assert the image_summary chunk appears between page 1 and page 3 chunks (sorted by page_number). Assert its element_type is "image_summary".
6. `test_chunk_index_globally_unique` — Provide 3 elements with multiple chunks each. Assert chunk_index values are [0, 1, 2, 3, ...] with no duplicates and no gaps.
7. `test_empty_text_elements_skipped` — Provide an element with `text=""`. Assert it produces no chunks.
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/multimodal_rag_ai/backend && python -m pytest tests/test_document_parser.py tests/test_chunking.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - backend/app/services/document_parser.py contains `from unstructured.partition.auto import partition`
    - backend/app/services/document_parser.py contains `strategy="auto"`
    - backend/app/services/document_parser.py contains `extract_images_in_pdf=True`
    - backend/app/services/document_parser.py contains `extract_image_block_output_dir=temp_dir`
    - backend/app/services/document_parser.py contains `RecursiveCharacterTextSplitter(` with `chunk_size=512, chunk_overlap=64, add_start_index=True`
    - backend/app/services/document_parser.py contains `def _build_chunks(`
    - backend/app/services/document_parser.py contains `"element_type": "image_summary"` for image summary chunks
    - backend/app/services/document_parser.py contains `intermediate.sort(key=lambda x: x["page_number"])` for page-ordered interleaving
    - backend/app/services/document_parser.py contains `meta["chunk_index"] = i` for global chunk indexing
    - backend/app/services/document_parser.py contains `shutil.rmtree(temp_dir, ignore_errors=True)` in a finally block
    - backend/tests/test_document_parser.py contains `test_parse_document_returns_elements`
    - backend/tests/test_document_parser.py contains `test_metadata_null_page_number_defaults_to_zero`
    - backend/tests/test_chunking.py contains `test_chunk_size_within_limit`
    - backend/tests/test_chunking.py contains `test_chunk_metadata_schema`
    - backend/tests/test_chunking.py contains `test_image_summary_interleaved`
    - backend/tests/test_chunking.py contains `test_chunk_index_globally_unique`
    - `python -m pytest tests/test_document_parser.py tests/test_chunking.py -x` exits 0
  </acceptance_criteria>
  <done>DocumentParserService rewritten with real unstructured parsing, image extraction, and _build_chunks with RecursiveCharacterTextSplitter (512/64). All metadata preserved. Tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Wire process_and_update_document pipeline + integration tests</name>
  <files>backend/tests/test_pipeline.py</files>
  <read_first>
    - backend/app/services/document_parser.py (Task 1 output — process_and_update_document)
    - backend/app/services/vector_store.py (Plan 01 output — delete_by_document)
    - backend/app/models/domain.py (Plan 01 output — Document.status)
    - backend/tests/conftest.py (test_db fixture)
  </read_first>
  <action>
Note: process_and_update_document() is already implemented in Task 1 above within document_parser.py. This task creates the integration test file to verify the pipeline wiring.

**backend/tests/test_pipeline.py** — NEW file with integration tests for the pipeline orchestration:

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from app.models.domain import Document, Folder, Project
```

1. `test_status_transitions_success(test_db)` — Insert a Project, Folder, and Document into test DB with status="pending". Mock `partition` to return 1 text element. Mock `vector_store.insert_documents` and `vector_store.delete_by_document`. Patch `app.services.document_parser.SessionLocal` to return test_db session. Call `process_and_update_document(document.id)`. Assert `db_document.status == "completed"`.

2. `test_status_failed_on_parse_error(test_db)` — Same setup but mock `partition` to raise `RuntimeError("bad file")`. Call `process_and_update_document`. Assert `db_document.status == "failed"`.

3. `test_status_failed_on_embedding_error(test_db)` — Mock `partition` to succeed, but mock `vector_store.insert_documents` to raise `Exception("chroma error")`. Call pipeline. Assert `db_document.status == "failed"`.

4. `test_delete_before_insert(test_db)` — Mock `partition` to return elements. Mock `vector_store.delete_by_document` and `vector_store.insert_documents`. Call pipeline. Assert `vector_store.delete_by_document` was called BEFORE `vector_store.insert_documents` (use `call_args_list` ordering or `mock_calls`).

5. `test_image_failure_does_not_fail_document(test_db)` — Mock `partition` to return 1 text element + 1 Image element. Mock `ImageProcessorService.summarize_image` to return placeholder. Call pipeline. Assert `db_document.status == "completed"` (not "failed").

6. `test_temp_dir_cleaned_on_success(test_db)` — Mock `partition`, capture the temp_dir path from `tempfile.mkdtemp`. After pipeline completes, assert the temp_dir no longer exists on disk.

7. `test_temp_dir_cleaned_on_failure(test_db)` — Mock `partition` to succeed but mock embedding to fail. Assert temp_dir is cleaned up even on failure.

For all tests: create a real small file on disk (e.g., write b"fake pdf content" to a temp file with .pdf extension) so `file_path` is valid. Use `patch("app.services.document_parser.SessionLocal")` to inject the test_db session. Use `patch("app.services.document_parser.partition")` to avoid real unstructured calls. Use `patch("app.services.document_parser.vector_store")` to avoid real ChromaDB calls.
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/multimodal_rag_ai/backend && python -m pytest tests/test_pipeline.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - backend/tests/test_pipeline.py contains `test_status_transitions_success`
    - backend/tests/test_pipeline.py contains `test_status_failed_on_parse_error`
    - backend/tests/test_pipeline.py contains `test_status_failed_on_embedding_error`
    - backend/tests/test_pipeline.py contains `test_delete_before_insert`
    - backend/tests/test_pipeline.py contains `test_image_failure_does_not_fail_document`
    - backend/tests/test_pipeline.py contains `test_temp_dir_cleaned_on_success`
    - backend/tests/test_pipeline.py contains `test_temp_dir_cleaned_on_failure`
    - `python -m pytest tests/test_pipeline.py -x` exits 0
  </acceptance_criteria>
  <done>Full pipeline integration tests covering status transitions, delete-before-insert ordering, image failure resilience, and temp directory cleanup. 7 tests pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Uploaded file -> unstructured partition() | User-uploaded file parsed by unstructured; malformed files could crash partition |
| unstructured image extraction -> disk | Images extracted to temp dir on local filesystem |
| image_path from temp_dir -> Gemini API | Only paths within temp_dir should be read and sent to API |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-3b-06 | Denial of Service | partition() | mitigate | Wrap partition() in try/except; on failure set document.status="failed", pipeline continues to next document |
| T-3b-07 | Information Disclosure | temp_dir | mitigate | Use tempfile.mkdtemp() for OS-controlled permissions; clean up in finally block via shutil.rmtree(temp_dir, ignore_errors=True) |
| T-3b-08 | Tampering | image_path | accept | Image paths are generated by unstructured into a temp_dir we control; not user-supplied. Path traversal risk is minimal for local single-user tool. |
| T-3b-09 | Denial of Service | Large file + hi_res strategy | accept | strategy="auto" may select hi_res for image-heavy PDFs (30+ seconds/page). Acceptable for local tool; no timeout enforced in v1. |
</threat_model>

<verification>
- `cd backend && python -m pytest tests/test_document_parser.py tests/test_chunking.py tests/test_pipeline.py -x -q` all pass
- `grep "from unstructured.partition.auto import partition" backend/app/services/document_parser.py` returns match
- `grep "chunk_size=512" backend/app/services/document_parser.py` returns match
- `grep "element_type.*image_summary" backend/app/services/document_parser.py` returns match
- `grep "status.*completed" backend/app/services/document_parser.py` returns match
</verification>

<success_criteria>
- DocumentParserService calls unstructured partition() with strategy="auto" and image extraction enabled
- _build_chunks produces chunks with chunk_size=512, chunk_overlap=64, add_start_index=True
- Every chunk metadata has: document_id, filename, page_number, chunk_index, element_type
- Image summaries interleaved at original page position with element_type="image_summary"
- chunk_index globally unique per document (no duplicates across elements)
- process_and_update_document transitions status correctly: processing -> completed/failed
- delete_by_document called before insert_documents
- Temp directory cleaned up in finally block on both success and failure
- Parsing failure sets status to "failed"
- Image summarization failure stores placeholder, document still completes
- 19+ tests pass across 3 test files (5 parser + 7 chunking + 7 pipeline)
</success_criteria>

<output>
After completion, create `.planning/phases/03B-ingestion-pipeline/03B-03-SUMMARY.md`
</output>
