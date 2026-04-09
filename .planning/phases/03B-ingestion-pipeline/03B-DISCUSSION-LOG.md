# Phase 3b: Ingestion Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 03B-ingestion-pipeline
**Areas discussed:** Document parsing, Image processing, Chunking & metadata, Pipeline wiring

---

## Document Parsing

| Option | Description | Selected |
|--------|-------------|----------|
| strategy="auto" | Lets unstructured pick best strategy per file type. Best balance of quality and speed. | ✓ |
| strategy="hi_res" always | Forces high-resolution for all documents. Slower, requires poppler+tesseract for everything. | |
| You decide | Claude picks the approach. | |

**User's choice:** strategy="auto"
**Notes:** Aligns with PARSE-01 requirement.

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve all element types | Keeps all types from unstructured (Title, NarrativeText, ListItem, Table, Image, etc.) as element_type metadata. | ✓ |
| Simplify to text/image only | Collapses everything to two types. Simpler but loses structural info. | |
| You decide | Claude decides. | |

**User's choice:** Preserve all element types
**Notes:** Enables richer downstream filtering.

| Option | Description | Selected |
|--------|-------------|----------|
| Extract to temp dir, clean up after | Unstructured extracts images to temp directory. Files deleted after Gemini processing. | ✓ |
| Persist extracted images permanently | Save images alongside uploads permanently. Useful for serving images later. | |
| You decide | Claude decides. | |

**User's choice:** Extract to temp dir, clean up after
**Notes:** Keeps disk clean. No need to serve images in v1.

| Option | Description | Selected |
|--------|-------------|----------|
| Single service, per-type methods | Each file type gets its own parse method inside DocumentParserService. Single class. | ✓ |
| Separate parser classes per type | Separate PdfParser, DocxParser, etc. behind common interface. More extensible. | |
| You decide | Claude decides. | |

**User's choice:** Single service, per-type methods
**Notes:** Simpler structure for 4 file types.

---

## Image Processing

| Option | Description | Selected |
|--------|-------------|----------|
| Gemini SDK direct | Use google-generativeai SDK directly. Simpler, fewer dependencies. | ✓ |
| LangChain Gemini wrapper | Use langchain-google-genai. Consistent with existing LangChain patterns. | |
| You decide | Claude decides. | |

**User's choice:** Gemini SDK direct
**Notes:** Fewer dependencies than LangChain wrapper.

| Option | Description | Selected |
|--------|-------------|----------|
| 3 retries, exponential backoff | tenacity with 2s, 4s, 8s backoff. Matches PARSE-03. | ✓ |
| 1 retry, fixed delay | Single retry with 5s delay. Simpler but less robust. | |
| You decide | Claude decides. | |

**User's choice:** 3 retries, exponential backoff
**Notes:** Matches PARSE-03 requirement.

| Option | Description | Selected |
|--------|-------------|----------|
| Env var, validate on use | GOOGLE_API_KEY checked at image processing time. Missing = placeholder + warning. | ✓ |
| Require at startup | Fail fast at startup if key not set. Blocks server. | |
| You decide | Claude decides. | |

**User's choice:** Env var, validate on use
**Notes:** Doesn't block server startup for users who don't need image summarization.

| Option | Description | Selected |
|--------|-------------|----------|
| Descriptive placeholder | "[Image: unable to process - {filename}]" — searchable, includes context. | ✓ |
| Skip image silently | Empty string, chunk skipped entirely. | |
| You decide | Claude decides. | |

**User's choice:** Descriptive placeholder
**Notes:** Matches PARSE-04 graceful failure requirement.

---

## Chunking & Metadata

| Option | Description | Selected |
|--------|-------------|----------|
| 512/64 as decided | chunk_size=512, chunk_overlap=64. Prior decision confirmed. | ✓ |
| Different parameters | Revisit chunk size parameters. | |

**User's choice:** 512/64 as decided
**Notes:** Confirmed from prior key decision in STATE.md. Safe for all-MiniLM-L6-v2.

| Option | Description | Selected |
|--------|-------------|----------|
| Full schema per CHUNK-02 | document_id, filename, page_number, chunk_index, element_type. | ✓ |
| Extended schema with extra fields | Additional: source_section, heading_context, character_offset. | |
| You decide | Claude decides. | |

**User's choice:** Full schema per CHUNK-02
**Notes:** Matches requirement exactly. Extends current schema which lacks page_number and element_type.

| Option | Description | Selected |
|--------|-------------|----------|
| Chunk like text, interleaved | Image summaries chunked with same splitter, interleaved at original page position. | ✓ |
| Single chunk per image, appended | No splitting, appended after text chunks per page. | |
| You decide | Claude decides. | |

**User's choice:** Chunk like text, interleaved
**Notes:** Preserves position context for better retrieval relevance.

---

## Pipeline Wiring

| Option | Description | Selected |
|--------|-------------|----------|
| Expand existing background task | Expand process_and_update_document() with full pipeline: parse → images → chunk → embed. | ✓ |
| New PipelineOrchestrator class | Separate orchestrator class. More testable but adds abstraction. | |
| You decide | Claude decides. | |

**User's choice:** Expand existing background task
**Notes:** Keeps existing pattern. No new abstraction needed for v1.

| Option | Description | Selected |
|--------|-------------|----------|
| Status column on Document | pending → processing → completed/failed. Enables frontend polling. | ✓ |
| No status tracking | No way to know if processing finished. | |
| You decide | Claude decides. | |

**User's choice:** Status column on Document
**Notes:** Requires adding status column to Document model.

| Option | Description | Selected |
|--------|-------------|----------|
| Fail per-step, continue where possible | Parsing fail = failed. Image fail = placeholder + continue. Embed fail = failed. | ✓ |
| All-or-nothing failure | Any failure marks entire document as failed. | |
| You decide | Claude decides. | |

**User's choice:** Fail per-step, continue where possible
**Notes:** Matches PARSE-04 graceful failure philosophy.

| Option | Description | Selected |
|--------|-------------|----------|
| Delete-then-insert | Delete all existing vectors for document before re-inserting. | ✓ |
| Upsert with stable IDs | Relies on stable IDs. Current code uses random UUIDs so won't deduplicate. | |
| You decide | Claude decides. | |

**User's choice:** Delete-then-insert
**Notes:** Prevents duplicate chunks. Current UUID-based IDs make upsert impractical.

---

## Claude's Discretion

- Exact unstructured partition parameters beyond strategy="auto"
- Gemini Vision prompt wording for image summarization
- Temp directory naming convention and location
- Logging verbosity during pipeline steps

## Deferred Ideas

None — discussion stayed within phase scope.
