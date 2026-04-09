import os
import json
from sqlalchemy.orm import Session, joinedload

from app.models.domain import Document
from app.services.vector_store import vector_store


class DocumentParserService:
    def __init__(self, extract_images: bool = True):
        self.extract_images = extract_images

    def parse_document(self, file_path: str, document_id: int):
        """
        Parses a document (PDF, DOCX, PPTX, etc.) using unstructured.
        Extracts both text chunks and images.
        """
        output_dir = os.path.join(os.path.dirname(file_path), f"extracted_{document_id}")
        if self.extract_images:
            os.makedirs(output_dir, exist_ok=True)

        # Stub logic — real parsing implemented in Phase 3b
        text_chunks = [f"[MOCK] This is a chunk extracted from {os.path.basename(file_path)}"]

        extracted_image_paths = []
        if self.extract_images and os.path.exists(output_dir):
            for file in os.listdir(output_dir):
                extracted_image_paths.append(os.path.join(output_dir, file))

        return {
            "text_chunks": text_chunks,
            "images": extracted_image_paths,
            "metadata": {
                "total_chunks": len(text_chunks),
                "total_images": len(extracted_image_paths)
            }
        }


from app.core.database import SessionLocal


def process_and_update_document(document_id: int):
    """
    Background task to parse document immediately after upload.
    Uses own session (SessionLocal) with eager-loaded folder relationship
    to prevent DetachedInstanceError (per D-10, INFRA-05).
    """
    db = SessionLocal()
    try:
        # FIXED: joinedload prevents DetachedInstanceError on folder.project_id
        db_document = (
            db.query(Document)
            .options(joinedload(Document.folder))
            .filter(Document.id == document_id)
            .first()
        )
        if not db_document:
            return None

        parser = DocumentParserService(extract_images=True)
        result = parser.parse_document(db_document.file_path, document_id)

        # Update document metadata
        current_metadata = json.loads(db_document.metadata_json) if db_document.metadata_json else {}
        current_metadata.update(result["metadata"])
        db_document.metadata_json = json.dumps(current_metadata)

        db.commit()

        # Ingest text chunks into Vector DB
        if result.get("text_chunks"):
            # folder relationship is already loaded via joinedload — safe to access
            proj_id = db_document.folder.project_id if db_document.folder else None
            metadatas = []
            for i, chunk in enumerate(result["text_chunks"]):
                metadatas.append({
                    "document_id": document_id,
                    "project_id": proj_id if proj_id is not None else "none",
                    "filename": db_document.filename,
                    "chunk_index": i
                })

            vector_store.insert_documents(
                text_chunks=result["text_chunks"],
                metadatas=metadatas,
                project_id=proj_id
            )

        return result
    finally:
        db.close()
