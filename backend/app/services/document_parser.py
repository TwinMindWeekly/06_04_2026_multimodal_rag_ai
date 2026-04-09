"""
DocumentParserService — parses documents using unstructured.io with image extraction.

Design decisions implemented:
  D-01: DocumentParserService with strategy="auto" for unstructured partition()
  D-02: Preserve all element types (Title, NarrativeText, ListItem, Table, Image, etc.)
  D-03: Extract images to temp dir; clean up in finally block after summarization
  D-04: Single DocumentParserService class (not separate parser classes)
  D-09: RecursiveCharacterTextSplitter with chunk_size=512, chunk_overlap=64
  D-10: Each chunk carries: document_id, filename, page_number, chunk_index, element_type
  D-11: Image summaries interleaved at original page position (not appended)
  D-12: process_and_update_document orchestrates full pipeline
  D-13: Status transitions: pending -> processing -> completed/failed
  D-14: Parsing failure -> 'failed'; image failure -> placeholder, continue
  D-15: delete_by_document before insert_documents (re-processing safety)

Threat mitigations:
  T-3b-06: partition() wrapped in try/except; parsing failure -> document.status='failed'
  T-3b-07: tempfile.mkdtemp() for OS-controlled permissions; shutil.rmtree() in finally
"""

import json
import logging
import shutil
import tempfile
from typing import Any, Dict, List, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.orm import joinedload
from unstructured.partition.auto import partition

from app.core.database import SessionLocal
from app.models.domain import Document
from app.services.image_processor import ImageProcessorService
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


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

        Raises:
            Exception: any exception from unstructured partition() propagates to caller
        """
        # T-3b-07: OS-controlled permissions via tempfile.mkdtemp
        temp_dir = tempfile.mkdtemp(prefix=f"doc_{document_id}_")
        try:
            # D-01: strategy="auto" lets unstructured pick best strategy per file type
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
                    # D-02: preserve element type (Title, NarrativeText, Image, etc.)
                    "category": el.category if hasattr(el, "category") else "Unknown",
                    # Default to 0 if page_number is None (handles non-paginated docs)
                    "page_number": getattr(el.metadata, "page_number", None) or 0,
                    "image_path": getattr(el.metadata, "image_path", None),
                }
                elements.append(element_dict)

            return {"elements": elements, "temp_dir": temp_dir}

        except Exception:
            # T-3b-07: clean up temp dir on parse failure
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise


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

    Args:
        elements: list of element dicts from parse_document()
        image_processor: ImageProcessorService instance for image summarization
        document_id: used for chunk metadata
        filename: used for chunk metadata and image placeholders

    Returns:
        (text_chunks, metadatas) -- parallel lists ready for VectorStoreService.insert_documents()
    """
    # D-09: chunk_size=512, chunk_overlap=64, add_start_index=True
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

        # Handle Image elements -- summarize via Gemini Vision, then treat summary as text
        # D-14: summarize_image() never raises; returns placeholder on failure
        if category == "Image" and el.get("image_path"):
            image_path = el["image_path"]
            summary = image_processor.summarize_image(image_path, filename)
            if summary:
                intermediate.append({
                    "text": summary,
                    "page_number": page_num,
                    # D-11: element_type="image_summary" for interleaved image content
                    "element_type": "image_summary",
                })
            continue

        # Skip empty text elements
        if not text.strip():
            continue

        # D-02: preserve original element type
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
        # D-10: metadata schema: document_id, filename, page_number, element_type
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
    # chunk_index is 0-based, sequential across all elements in document
    for i, meta in enumerate(all_metadatas):
        meta["chunk_index"] = i

    return all_chunks, all_metadatas


def process_and_update_document(document_id: int) -> None:
    """
    Background task: parse document -> extract images -> summarize -> chunk -> embed.

    Status transitions per D-13: pending -> processing -> completed/failed.
    Delete-before-insert per D-15.
    Per-step failure handling per D-14.
    Temp dir cleanup in finally per D-03, T-3b-07.
    """
    db = SessionLocal()
    try:
        db_document = (
            db.query(Document)
            # joinedload prevents DetachedInstanceError on folder.project_id
            .options(joinedload(Document.folder))
            .filter(Document.id == document_id)
            .first()
        )
        if not db_document:
            logger.warning("Document %d not found -- skipping processing", document_id)
            return

        # D-13: transition to processing
        db_document.status = "processing"
        db.commit()

        parser = DocumentParserService()
        image_processor = ImageProcessorService()

        # Step 1: Parse document
        # D-14: parsing failure -> document.status='failed', pipeline stops for this doc
        # T-3b-06: partition() wrapped in try/except; malformed file -> 'failed' not crash
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
            # D-14: image summarization failures produce placeholders internally, not exceptions
            all_chunks, all_metadatas = _build_chunks(
                elements=parse_result["elements"],
                image_processor=image_processor,
                document_id=document_id,
                filename=db_document.filename,
            )

            # Step 4: Determine project_id from eagerly-loaded folder relationship
            proj_id = db_document.folder.project_id if db_document.folder else None

            # D-15: delete existing vectors before re-inserting (re-processing safety)
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

            # Update document metadata with ingestion statistics
            current_metadata = (
                json.loads(db_document.metadata_json) if db_document.metadata_json else {}
            )
            updated_metadata = {
                **current_metadata,
                "total_chunks": len(all_chunks),
                "total_images": sum(
                    1 for m in all_metadatas if m.get("element_type") == "image_summary"
                ),
            }
            db_document.metadata_json = json.dumps(updated_metadata)

            # D-13: transition to completed
            db_document.status = "completed"
            db.commit()

        except Exception as e:
            # D-14: embedding/chunking failure -> document.status='failed'
            logger.error("Processing failed for document %d: %s", document_id, e)
            db_document.status = "failed"
            db.commit()
        finally:
            # D-03, T-3b-07: always clean up temp dir regardless of success or failure
            shutil.rmtree(temp_dir, ignore_errors=True)

    finally:
        db.close()
