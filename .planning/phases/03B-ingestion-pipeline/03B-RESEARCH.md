# Phase 3b: Ingestion Pipeline - Research

**Researched:** 2026-04-09
**Domain:** Document parsing (unstructured.io), image summarization (Gemini Vision), text chunking (LangChain), ChromaDB ingestion
**Confidence:** HIGH (all locked decisions verified against installed packages and existing codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Document Parsing**
- D-01: Use `unstructured[pdf,docx,pptx,xlsx]` with `strategy="auto"` — lets unstructured pick best strategy per file type.
- D-02: Preserve all element types from unstructured (Title, NarrativeText, ListItem, Table, Image, etc.) and map to `element_type` metadata on each chunk.
- D-03: Extract images to a temporary directory during processing. Clean up temp files after Gemini summarization. No permanent image storage.
- D-04: Single `DocumentParserService` class with per-type methods (not separate parser classes). Major rewrite of existing stub in `document_parser.py`.

**Image Processing**
- D-05: Use `google-generativeai` SDK directly (not LangChain wrapper) with `gemini-1.5-pro-latest`. New service: `image_processor.py`.
- D-06: Retry with `tenacity`: 3 retries, exponential backoff (2s, 4s, 8s).
- D-07: Gemini API key via `GOOGLE_API_KEY` env var, validated at image processing time (not startup). If missing, store placeholder and log warning.
- D-08: On final failure after retries: `"[Image: unable to process - {filename}]"`. Document still marked complete.

**Chunking and Metadata**
- D-09: RecursiveCharacterTextSplitter with `chunk_size=512`, `chunk_overlap=64`, `add_start_index=True`.
- D-10: Each chunk carries metadata: `document_id`, `filename`, `page_number`, `chunk_index`, `element_type`.
- D-11: Image summaries chunked with same splitter (512/64), stored with `element_type="image_summary"`. Interleaved at original page position, not appended.

**Pipeline Wiring**
- D-12: Expand existing `process_and_update_document()` background task (no new orchestrator class).
- D-13: Add `status` column to Document model: `pending` → `processing` → `completed` or `failed`.
- D-14: Fail per-step, continue where possible. Parsing failure → `failed`. Image summarization failure → placeholder, continue. Embedding failure → `failed`.
- D-15: Delete-then-insert for re-processing: delete all existing vectors for that document before re-inserting.

### Claude's Discretion
- Exact unstructured partition parameters beyond `strategy="auto"`
- Gemini Vision prompt wording for image summarization
- Temp directory naming convention and location
- Logging verbosity during pipeline steps

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PARSE-01 | Parse PDF, DOCX, PPTX, XLSX using `unstructured[pdf,docx,pptx,xlsx]` with `strategy="auto"` | unstructured `partition()` API; strategy param documented |
| PARSE-02 | Extract embedded images from PDF and PPTX as separate elements with file paths | unstructured `extract_images_in_pdf=True` + `extract_image_block_output_dir` params |
| PARSE-03 | Summarize extracted images via Gemini Vision API with retry logic (tenacity, exponential backoff) | google-generativeai `upload_file()` + `generate_content()`; tenacity already in requirements.txt |
| PARSE-04 | On image summarization failure after retries, store placeholder text and continue | tenacity `retry_error_callback`; graceful degradation pattern |
| PARSE-05 | Preserve element metadata (page_number, element_type, filename) through pipeline | unstructured element `.metadata` attribute contains `page_number`; `.category` maps to element_type |
| CHUNK-01 | RecursiveCharacterTextSplitter chunk_size=512, chunk_overlap=64, add_start_index=True | langchain-text-splitters 1.1.1 already installed; `RecursiveCharacterTextSplitter` confirmed |
| CHUNK-02 | Each chunk carries: document_id, filename, page_number, chunk_index, element_type | Extend existing metadata dict in `process_and_update_document()` |
| CHUNK-03 | Image summaries chunked and embedded as text alongside document text chunks | Same splitter applied to summary string; element_type="image_summary"; page-ordered interleaving |
</phase_requirements>

---

## Summary

Phase 3b replaces the stub `DocumentParserService` with real parsing using `unstructured[pdf,docx,pptx,xlsx]`, adds a new `ImageProcessorService` for Gemini Vision summarization, and wires both into the existing `process_and_update_document()` background task. The result is a fully functional ingestion pipeline that produces metadata-rich chunks in ChromaDB.

All locked decisions have been verified against the existing codebase. The key packages — `langchain-text-splitters 1.1.1` (already installed), `tenacity 9.1.4` (already installed), and `google-generativeai` (to be added) — cover all requirements. The `unstructured` package needs to be added to `requirements.txt` with the appropriate extras.

The primary implementation risk is the Windows system dependency chain: `unstructured` requires `poppler` (for PDF image extraction) and `tesseract` (for OCR). These must be installed and added to PATH before any real document processing will work. Phase 3a already added the startup probe (`shutil.which("pdfinfo")`), so missing deps will produce a clear warning rather than a silent crash.

**Primary recommendation:** Implement in this order — (1) add Document.status column + Alembic migration, (2) rewrite `document_parser.py`, (3) create `image_processor.py`, (4) expand `process_and_update_document()`, (5) update `vector_store.py` metadata schema. Each step is independently testable.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| unstructured | latest `[pdf,docx,pptx,xlsx]` | Multi-format document parsing + image extraction | Only library that handles all 4 formats with image extraction in a single API call |
| langchain-text-splitters | 1.1.1 (installed) | `RecursiveCharacterTextSplitter` for chunking | Already installed; deterministic; preserves metadata |
| google-generativeai | latest | Gemini Vision API for image summarization | Direct SDK per D-05; avoids LangChain wrapper overhead |
| tenacity | 9.1.4 (installed) | Retry with exponential backoff for Gemini calls | Already installed; `@retry` decorator with `wait_exponential` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tempfile (stdlib) | built-in | Temp directory for extracted images | Use `tempfile.mkdtemp()` for cross-platform temp dirs |
| pathlib (stdlib) | built-in | Path manipulation | All file path operations |
| logging (stdlib) | built-in | Pipeline step logging | Structured logging per project convention |
| os (stdlib) | built-in | Env var access, file cleanup | `os.getenv("GOOGLE_API_KEY")`, `os.remove()` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| unstructured | PyMuPDF + python-docx + pptx | Would require 3+ separate parsers and no unified element type system |
| google-generativeai direct | langchain-google-genai wrapper | Wrapper adds abstraction but hides retry control and response inspection |
| tenacity | asyncio retry / custom loop | tenacity already installed; cleaner decorator syntax |

### Installation

```bash
# Add to requirements.txt (install in venv)
pip install "unstructured[pdf,docx,pptx,xlsx]" google-generativeai

# System dependencies (Windows — must be on PATH)
# poppler: https://github.com/oschwartz10612/poppler-windows/releases
# tesseract: https://github.com/UB-Mannheim/tesseract/wiki
```

**Version verification:** [ASSUMED] Exact current versions of `unstructured` and `google-generativeai` not verified against PyPI in this session. Pin after install with `pip freeze | grep -E "unstructured|google-generativeai"`.

---

## Architecture Patterns

### Recommended Project Structure Changes

```
backend/app/services/
├── document_parser.py    # MAJOR REWRITE — DocumentParserService + process_and_update_document()
├── image_processor.py    # NEW — ImageProcessorService with Gemini Vision
├── embeddings.py         # NO CHANGE
├── vector_store.py       # MINOR EDIT — metadata schema (page_number, element_type)
└── llm_provider.py       # NO CHANGE

backend/app/models/
└── domain.py             # MINOR EDIT — add Document.status column

backend/app/
└── migrations/           # NEW (if Alembic used) OR manual ALTER TABLE in database.py init
```

### Pattern 1: unstructured partition() Call

**What:** Single entry point for all file types. `strategy="auto"` selects best strategy per file.
**When to use:** Always — do not branch on file extension before calling partition.

```python
# Source: unstructured docs / [ASSUMED from training knowledge]
from unstructured.partition.auto import partition

elements = partition(
    filename=file_path,
    strategy="auto",
    extract_images_in_pdf=True,
    extract_image_block_output_dir=temp_dir,
    extract_image_block_types=["Image", "Table"],
)
```

Each element has:
- `element.text` — extracted text content
- `element.category` — element type string (e.g., `"Title"`, `"NarrativeText"`, `"Image"`, `"Table"`)
- `element.metadata.page_number` — 1-based page number (may be None for some formats)
- `element.metadata.filename` — source filename
- `element.metadata.image_path` — path to extracted image file (for Image elements only)

### Pattern 2: ImageProcessorService with tenacity

**What:** Wraps Gemini Vision API call with retry decorator. Validates API key on call, not startup.
**When to use:** For every Image element extracted from a document.

```python
# Source: tenacity docs, google-generativeai docs — [ASSUMED from training knowledge]
import os
import logging
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_error_callback

logger = logging.getLogger(__name__)

class ImageProcessorService:
    def summarize_image(self, image_path: str, filename: str) -> str:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set — using placeholder for %s", filename)
            return f"[Image: unable to process - {filename}]"
        
        genai.configure(api_key=api_key)
        return self._summarize_with_retry(image_path, filename)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=False,
        retry_error_callback=lambda state: None  # returns None on final failure
    )
    def _call_gemini(self, image_path: str) -> str | None:
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        with open(image_path, "rb") as f:
            image_data = f.read()
        response = model.generate_content([
            "Describe this image concisely for use in a document search system. "
            "Focus on key visual elements, text visible in the image, and subject matter.",
            {"mime_type": "image/png", "data": image_data}
        ])
        return response.text

    def _summarize_with_retry(self, image_path: str, filename: str) -> str:
        result = self._call_gemini(image_path)
        if result is None:
            logger.warning("Gemini Vision failed after retries for %s", filename)
            return f"[Image: unable to process - {filename}]"
        return result
```

### Pattern 3: RecursiveCharacterTextSplitter with metadata propagation

**What:** Splits text while carrying source element metadata onto each child chunk.
**When to use:** For all text elements AND image summaries.

```python
# Source: langchain-text-splitters docs — [ASSUMED from training knowledge]
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,
    add_start_index=True,
)

# For a text element
docs = splitter.create_documents(
    texts=[element.text],
    metadatas=[{
        "document_id": document_id,
        "filename": filename,
        "page_number": element.metadata.page_number or 0,
        "element_type": element.category,
    }]
)
# Each doc.metadata["chunk_index"] must be set after splitting (enumerate)
for i, doc in enumerate(docs):
    doc.metadata["chunk_index"] = i  # global index across all chunks
```

### Pattern 4: Page-ordered interleaving of text + image summary chunks

**What:** Maintain page_number on each chunk so text and image summaries from the same page sort together.
**When to use:** When building the final chunk list before ChromaDB insertion.

```python
# Sort all chunks by page_number, then by element order within page
all_chunks = text_chunks + image_chunks
all_chunks.sort(key=lambda c: (c.metadata.get("page_number", 0),))
# Then assign final global chunk_index
for i, chunk in enumerate(all_chunks):
    chunk.metadata["chunk_index"] = i
```

### Pattern 5: Delete-then-insert for re-processing (D-15)

**What:** Before inserting new vectors for a document, delete all existing ones.
**When to use:** Every time `process_and_update_document()` runs (handles both first upload and re-processing).

```python
# In VectorStoreService — needs a new delete_by_document() method
def delete_by_document(self, document_id: int, project_id: int = None):
    collection_name = self._get_collection_name(project_id)
    try:
        collection = self.client.get_collection(name=collection_name)
        collection.delete(where={"document_id": document_id})
    except Exception:
        pass  # Collection may not exist on first upload
```

### Pattern 6: Document.status column with SQLAlchemy

**What:** Track pipeline state for frontend polling.
**When to use:** Add to domain.py; update in background task at each stage.

```python
# In domain.py — add to Document model
status = Column(String, default="pending", nullable=False)

# In process_and_update_document():
db_document.status = "processing"
db.commit()
# ... pipeline ...
db_document.status = "completed"  # or "failed"
db.commit()
```

**Schema migration note:** Since the project uses SQLAlchemy without Alembic configured, the safest approach is to use `Base.metadata.create_all()` with `checkfirst=True` (existing) OR add a one-time `ALTER TABLE` in `database.py` startup initialization. Document which approach is chosen in the plan.

### Anti-Patterns to Avoid

- **Branching on file extension before partition():** unstructured handles this internally. Pre-branching leads to maintenance burden and misses `strategy="auto"` benefits.
- **Calling genai.configure() at module import:** API key may not be set at startup. Configure only when a summarization call is needed (D-07).
- **Passing full element objects between functions:** Extract text, page_number, element_type, and image_path as plain scalars/dicts at the parse boundary. Keeps services decoupled.
- **Appending image chunks at end of document:** Destroys positional metadata utility. Interleave by page_number (D-11).
- **Reusing the same temp directory across documents:** Race condition risk if two background tasks run concurrently. Use `tempfile.mkdtemp()` per document, clean up in `finally` block.
- **Forgetting to clean up temp images on Gemini failure:** The `finally` block in the pipeline must remove the temp dir regardless of success or failure (D-03).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-format document parsing | Custom PDF/DOCX/PPTX parsers | `unstructured[pdf,docx,pptx,xlsx]` | Image extraction, element typing, metadata extraction all built-in |
| Retry with exponential backoff | `time.sleep()` loop with counter | `tenacity` @retry decorator | Already installed; handles jitter, logging, callback on final failure |
| Text chunking with overlap | Manual substring slicing | `RecursiveCharacterTextSplitter` | Already installed; handles unicode, sentence boundaries, overlap correctly |
| Image MIME type detection | File extension guessing | Read magic bytes or use `imghdr` (stdlib) | Extension can be wrong; unstructured often produces PNG regardless |

**Key insight:** The three most complex sub-problems (parsing, retry, chunking) are all covered by libraries already present in requirements.txt. The only new install is `unstructured` and `google-generativeai`.

---

## Common Pitfalls

### Pitfall 1: element.metadata.page_number is None for some formats

**What goes wrong:** DOCX elements often have `page_number=None` because DOCX has no native page concept. Storing None in ChromaDB metadata causes type inconsistency.
**Why it happens:** unstructured derives page numbers from rendering; DOCX requires a full layout engine for accurate page numbers.
**How to avoid:** Normalize to `page_number = element.metadata.page_number or 0` before storing. Document in chunk metadata that page_number=0 means "unknown page."
**Warning signs:** `TypeError` or ChromaDB rejection when inserting metadata with None values.

### Pitfall 2: ChromaDB rejects non-string/int/float metadata values

**What goes wrong:** ChromaDB `.upsert()` raises if any metadata value is `None`, a list, or a dict.
**Why it happens:** ChromaDB only accepts scalar types (str, int, float, bool) in metadata fields.
**How to avoid:** Sanitize all metadata before insertion: `str(val) if val is not None else ""` for optional fields. Use `int(page_number)` for numeric fields.
**Warning signs:** `ValueError: metadata values must be...` from ChromaDB at ingestion time.

### Pitfall 3: Temp dir not cleaned up on exception

**What goes wrong:** Extracted images accumulate on disk if pipeline fails mid-way.
**Why it happens:** Exception raised before cleanup code runs.
**How to avoid:** Always clean up in a `finally` block — `shutil.rmtree(temp_dir, ignore_errors=True)`.
**Warning signs:** Growing `extracted_*` directories in the uploads folder.

### Pitfall 4: unstructured strategy="hi_res" triggered by PDFs with images — very slow

**What goes wrong:** `strategy="auto"` selects `hi_res` for PDFs with embedded images. This triggers Tesseract OCR on every page, which can take 30+ seconds per page on CPU.
**Why it happens:** `auto` strategy promotes to `hi_res` when images are detected and tesseract is available.
**How to avoid:** This is expected behavior and the correct choice for image-containing PDFs. Set realistic timeout expectations for large files. Log `strategy` used (unstructured exposes this).
**Warning signs:** Background task taking >60 seconds per page — check if hi_res was selected.

### Pitfall 5: google-generativeai upload_file() vs inline bytes

**What goes wrong:** Large images fail if sent as inline base64; small images fail if using File API (Files API has its own lifecycle).
**Why it happens:** Gemini has two image input modes: inline bytes (for small images, <4MB) and File API uploads (for larger files). Mixing them or misapplying causes errors.
**How to avoid:** Use inline bytes (`{"mime_type": "image/png", "data": image_bytes}`) for extracted images — they are typically thumbnails/small PNG exports from unstructured, well under 4MB. [ASSUMED — verify actual extracted image sizes on first test run]
**Warning signs:** `google.api_core.exceptions.InvalidArgument` on Gemini call.

### Pitfall 6: Document.status column migration on existing DB

**What goes wrong:** Adding `status` column to Document model without migrating the existing SQLite DB causes SQLAlchemy to not see the column (it was created before the column existed).
**Why it happens:** `create_all()` does not ALTER existing tables — only creates missing tables.
**How to avoid:** Either (a) use Alembic migration, or (b) delete and recreate the SQLite dev DB, or (c) add an explicit `ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'pending'` in the database startup code.
**Warning signs:** `OperationalError: table documents has no column named status` at runtime.

### Pitfall 7: chunk_index must be globally unique per document, not per element

**What goes wrong:** Assigning `chunk_index` per element (restarting at 0 for each element) creates duplicate indices across elements of the same document.
**Why it happens:** Natural loop pattern resets counter per element.
**How to avoid:** Use a single incrementing counter across all chunks from all elements for the same document. Set `chunk_index` after flattening all chunks from all elements.
**Warning signs:** ChromaDB deduplification silently discarding chunks (upsert with same ID overwrites).

---

## Code Examples

### Minimal DocumentParserService skeleton

```python
# Source: [ASSUMED from training knowledge + existing codebase patterns]
import os
import shutil
import tempfile
import logging
from pathlib import Path
from typing import List

from unstructured.partition.auto import partition

logger = logging.getLogger(__name__)

class DocumentParserService:
    def parse_document(self, file_path: str, document_id: int) -> dict:
        temp_dir = tempfile.mkdtemp(prefix=f"doc_{document_id}_")
        try:
            elements = partition(
                filename=file_path,
                strategy="auto",
                extract_images_in_pdf=True,
                extract_image_block_output_dir=temp_dir,
                extract_image_block_types=["Image", "Table"],
            )
            return {
                "elements": elements,
                "temp_dir": temp_dir,
            }
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
```

### process_and_update_document() expanded skeleton

```python
# Source: existing document_parser.py + D-12, D-13, D-14 decisions
def process_and_update_document(document_id: int):
    db = SessionLocal()
    try:
        db_document = (
            db.query(Document)
            .options(joinedload(Document.folder))
            .filter(Document.id == document_id)
            .first()
        )
        if not db_document:
            return

        db_document.status = "processing"
        db.commit()

        parser = DocumentParserService()
        image_processor = ImageProcessorService()

        try:
            parse_result = parser.parse_document(db_document.file_path, document_id)
        except Exception as e:
            logger.error("Parsing failed for document %d: %s", document_id, e)
            db_document.status = "failed"
            db.commit()
            return

        temp_dir = parse_result["temp_dir"]
        try:
            all_chunks, all_metadatas = _build_chunks(
                elements=parse_result["elements"],
                image_processor=image_processor,
                document_id=document_id,
                filename=db_document.filename,
            )

            proj_id = db_document.folder.project_id if db_document.folder else None

            # D-15: delete existing vectors before re-inserting
            vector_store.delete_by_document(document_id, proj_id)

            if all_chunks:
                vector_store.insert_documents(
                    text_chunks=all_chunks,
                    metadatas=all_metadatas,
                    project_id=proj_id,
                )

            db_document.status = "completed"
            db.commit()

        except Exception as e:
            logger.error("Embedding failed for document %d: %s", document_id, e)
            db_document.status = "failed"
            db.commit()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    finally:
        db.close()
```

### Metadata sanitizer for ChromaDB

```python
# Source: [ASSUMED from ChromaDB constraint knowledge]
def _sanitize_metadata(meta: dict) -> dict:
    """ChromaDB only accepts str/int/float/bool — sanitize before insert."""
    result = {}
    for k, v in meta.items():
        if v is None:
            result[k] = ""
        elif isinstance(v, (str, int, float, bool)):
            result[k] = v
        else:
            result[k] = str(v)
    return result
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyPDF2 + python-docx separate parsers | unstructured unified API | 2022-2023 | Single API for all formats; built-in image extraction |
| LangChain `Document` objects throughout | Plain dict metadata + LangChain splitters only | Project decision | Avoids LangChain abstraction lock-in; metadata stays transparent |
| `genai.upload_file()` (Files API) | Inline bytes for small images | 2024 | Simpler; no file lifecycle management needed for small extracted images |

**Deprecated/outdated:**
- `unstructured` `partition_pdf()`, `partition_docx()` etc. — replaced by unified `partition()` with `strategy` param. [ASSUMED]
- LangChain `UnstructuredFileLoader` — hides element types; use `partition()` directly per D-04.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `partition()` from `unstructured.partition.auto` is the correct import path | Code Examples | Import error on first run; fix is trivial |
| A2 | Extracted images from unstructured are PNG, under 4MB, suitable for inline Gemini bytes API | Pitfall 5 | May need File API for large images; adjust `_call_gemini()` |
| A3 | `strategy="auto"` promotes to `hi_res` for PDFs with images when tesseract is present | Pitfall 4 | Different strategy chosen; image extraction behavior changes |
| A4 | `element.metadata.image_path` holds the extracted image file path for Image elements | Pattern 1 | Need to scan temp_dir directly if attribute name differs |
| A5 | `google-generativeai` inline image format is `{"mime_type": "image/png", "data": bytes}` | Pattern 2 | API call fails; check official SDK docs for correct format |
| A6 | Current `google-generativeai` package supports `gemini-1.5-pro-latest` model name | Standard Stack | Model not found error; check available model names via `genai.list_models()` |
| A7 | ChromaDB `collection.delete(where={"document_id": document_id})` works with integer where clause | Pattern 5 | ChromaDB where clause may require string comparison; cast document_id to str |

**Verification before implementation:** Run a minimal smoke test of `partition()` on a small PDF after installing unstructured. Verify element attributes before writing the full parser. Similarly, call `genai.list_models()` after installing `google-generativeai` to confirm `gemini-1.5-pro-latest` is available.

---

## Open Questions

1. **SQLite migration strategy for Document.status column**
   - What we know: `create_all()` does not ALTER existing tables
   - What's unclear: Whether dev DB will be recreated fresh or needs migration
   - Recommendation: Plan should include an explicit `ALTER TABLE` in database.py startup with `IF NOT EXISTS` guard, or instruct user to delete the dev DB

2. **Exact unstructured element attribute for image file path**
   - What we know: unstructured extracts images to `extract_image_block_output_dir`
   - What's unclear: Whether the path is in `element.metadata.image_path` or requires scanning the temp dir
   - Recommendation: Add a Wave 0 smoke test that prints element attributes for a known PDF with images

3. **ChromaDB where clause type for document_id**
   - What we know: Current metadata stores `document_id` as int
   - What's unclear: Whether ChromaDB `.delete(where={"document_id": int_val})` accepts integers or requires strings
   - Recommendation: Verify in Wave 0; store `document_id` as str in metadata to be safe (consistent with existing `project_id` pattern which stores "none" as string)

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (venv) | All backend | Assumed present | 3.x | — |
| unstructured[pdf,docx,pptx,xlsx] | PARSE-01, PARSE-02 | Not in requirements.txt yet | — | No fallback — must install |
| google-generativeai | PARSE-03 | Not in requirements.txt | — | No fallback — must install |
| tenacity | PARSE-03, PARSE-06 | 9.1.4 (installed) | 9.1.4 | — |
| langchain-text-splitters | CHUNK-01 | 1.1.1 (installed) | 1.1.1 | — |
| poppler (pdfinfo) | PDF image extraction | Unknown — not verified | — | Without it, PDF image extraction silently skipped |
| tesseract | PDF hi_res OCR | Unknown — not verified | — | Without it, strategy degrades to fast (text-only PDFs still work) |
| GOOGLE_API_KEY env var | PARSE-03 | Unknown at research time | — | Missing → placeholder text (D-07, D-08) |

**Missing dependencies with no fallback:**
- `unstructured[pdf,docx,pptx,xlsx]` — must add to requirements.txt and install
- `google-generativeai` — must add to requirements.txt and install

**Missing dependencies with fallback:**
- `poppler` / `pdfinfo` — without it, PDF images not extracted (Phase 3a probe already warns)
- `tesseract` — without it, OCR disabled (documents still parsed, text extracted)
- `GOOGLE_API_KEY` — without it, image summaries replaced with placeholder per D-07/D-08

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ (in requirements.txt) |
| Config file | None detected — Wave 0 must create `backend/pytest.ini` or `pyproject.toml` |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PARSE-01 | `partition()` returns elements for PDF/DOCX/PPTX/XLSX | unit (with fixture files) | `pytest tests/test_document_parser.py::test_parse_pdf -x` | No — Wave 0 |
| PARSE-02 | Image elements extracted to temp dir with file paths | unit | `pytest tests/test_document_parser.py::test_image_extraction -x` | No — Wave 0 |
| PARSE-03 | Gemini call succeeds with valid API key (mocked) | unit (mock genai) | `pytest tests/test_image_processor.py::test_summarize_success -x` | No — Wave 0 |
| PARSE-04 | Gemini failure returns placeholder, not exception | unit (mock to raise) | `pytest tests/test_image_processor.py::test_summarize_failure -x` | No — Wave 0 |
| PARSE-05 | page_number and element_type present in chunk metadata | unit | `pytest tests/test_document_parser.py::test_metadata_preserved -x` | No — Wave 0 |
| CHUNK-01 | Chunks are 512 chars max with 64 overlap | unit | `pytest tests/test_chunking.py::test_chunk_size -x` | No — Wave 0 |
| CHUNK-02 | All required metadata fields present on every chunk | unit | `pytest tests/test_chunking.py::test_chunk_metadata_schema -x` | No — Wave 0 |
| CHUNK-03 | Image summary chunks interleaved at correct page position | unit | `pytest tests/test_chunking.py::test_image_summary_interleaved -x` | No — Wave 0 |
| D-13 | Document.status transitions pending→processing→completed | integration | `pytest tests/test_pipeline.py::test_status_transitions -x` | No — Wave 0 |
| D-15 | Re-processing deletes old vectors before inserting new | integration (mock ChromaDB) | `pytest tests/test_pipeline.py::test_delete_before_insert -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && python -m pytest tests/test_document_parser.py tests/test_image_processor.py tests/test_chunking.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- `backend/tests/__init__.py` — empty file to make tests a package
- `backend/tests/conftest.py` — shared fixtures (sample PDF bytes, mock DB session, mock genai)
- `backend/tests/test_document_parser.py` — covers PARSE-01, PARSE-02, PARSE-05
- `backend/tests/test_image_processor.py` — covers PARSE-03, PARSE-04
- `backend/tests/test_chunking.py` — covers CHUNK-01, CHUNK-02, CHUNK-03
- `backend/tests/test_pipeline.py` — covers D-13, D-15 (integration)
- `backend/pytest.ini` — minimal config: `testpaths = tests`, `asyncio_mode = auto`
- Framework already installed: `pytest>=8.0`, `pytest-asyncio>=0.23`, `httpx>=0.27` in requirements.txt

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth in this phase |
| V3 Session Management | No | Background task, no session |
| V4 Access Control | No | Single-user local tool |
| V5 Input Validation | Yes | File extension whitelist already implemented (Phase 3a) |
| V6 Cryptography | No | API key via env var (not stored) |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via uploaded filename | Tampering | Already mitigated — Phase 3a uses `uuid4()` as stored filename, not user-provided name |
| Temp directory exposure | Information Disclosure | Use `tempfile.mkdtemp()` (OS-controlled permissions); clean up in `finally` |
| GOOGLE_API_KEY in logs | Information Disclosure | Never log API key value; log only "API key present/absent" |
| Malformed PDF causing unstructured crash | Denial of Service | Wrap `partition()` in try/except; set document status to "failed" on exception |
| Image path escaping temp dir | Tampering | unstructured controls image extraction paths; verify `image_path` starts with `temp_dir` prefix before use |

---

## Project Constraints (from CLAUDE.md — global rules)

- **Immutability:** Create new dicts/objects rather than mutating in place — apply when building metadata dicts
- **Error handling:** Handle errors explicitly at every level; never silently swallow; log detailed context server-side
- **Input validation:** Already handled by Phase 3a (extension whitelist, size limit)
- **No hardcoded secrets:** `GOOGLE_API_KEY` via `os.getenv()` — never hardcoded
- **Logging:** Use `logging` module (not `print()`) — project already uses `logger = logging.getLogger(__name__)`
- **File size:** Services should stay under 800 lines; if `document_parser.py` grows large, extract `_build_chunks()` helper to a separate module
- **Type hints:** Add on all new function signatures per project convention (partial usage pattern)

---

## Sources

### Primary (HIGH confidence)
- Existing codebase — `document_parser.py`, `vector_store.py`, `domain.py`, `documents.py`, `requirements.txt` — verified directly
- `.planning/phases/03B-ingestion-pipeline/03B-CONTEXT.md` — locked decisions verified
- `.planning/REQUIREMENTS.md` — requirement IDs and acceptance criteria verified
- `.planning/research/SUMMARY.md` — prior research synthesis verified

### Secondary (MEDIUM confidence)
- `.planning/codebase/STACK.md` — installed package versions verified
- `.planning/codebase/CONVENTIONS.md` — patterns verified against codebase

### Tertiary (LOW confidence — marked ASSUMED in text)
- unstructured API: `partition()` parameter names, element attribute names — training knowledge, needs smoke test validation
- google-generativeai SDK: inline image format, model name string — training knowledge, needs verification after install
- ChromaDB where clause type handling — training knowledge, needs verification

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — packages verified against requirements.txt; only unstructured and google-generativeai are new installs
- Architecture: HIGH — patterns follow existing codebase conventions; integration points mapped exactly
- Pitfalls: MEDIUM — most verified from existing research + codebase patterns; A1-A7 assumptions flagged for smoke test validation

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable libraries; unstructured releases frequently — recheck if major version changes)
