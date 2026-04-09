import os
import uuid
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.i18n import get_language, t
from app.models.domain import Document, Folder
from app.schemas.domain import DocumentResponse
from app.services.document_parser import process_and_update_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Per D-06: extension whitelist (case-insensitive)
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}

# Per D-05: 100MB file size limit
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024

# Per D-04: Content-Type secondary validation
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    folder_id: int = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    lang: str = Depends(get_language),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    # --- VALIDATION BEFORE DISK WRITE (per D-04) ---

    # 1. Extension check (per D-06: case-insensitive)
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=t("errors.invalid_file_type", lang)
        )

    # 2. Content-Type check (defense in depth)
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=t("errors.invalid_file_type", lang)
        )

    # 3. Size check: read into memory up to limit+1 to detect oversized (per D-05)
    content = await file.read(MAX_FILE_SIZE_BYTES + 1)
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=t("errors.file_too_large", lang)
        )

    # --- VALIDATION PASSED — write to disk ---

    # Check if folder exists if provided
    if folder_id is not None:
        db_folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not db_folder:
            raise HTTPException(status_code=404, detail=t("errors.folder_not_found", lang))

    # Generate unique filename to avoid collisions
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Write validated content to disk (already in memory from size check)
    with open(file_path, "wb") as buffer:
        buffer.write(content)

    file_size = len(content)

    # Save to db
    metadata = {
        "original_name": file.filename,
        "size_bytes": file_size,
        "content_type": file.content_type
    }

    db_document = Document(
        filename=file.filename,
        file_path=file_path,
        folder_id=folder_id,
        metadata_json=json.dumps(metadata)
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    background_tasks.add_task(process_and_update_document, db_document.id)

    return db_document


@router.get("/folder/{folder_id}", response_model=List[DocumentResponse])
def get_documents_by_folder(folder_id: int, db: Session = Depends(get_db)):
    return db.query(Document).filter(Document.folder_id == folder_id).all()


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: Session = Depends(get_db), lang: str = Depends(get_language)):
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if not db_document:
        raise HTTPException(status_code=404, detail=t("errors.document_not_found", lang))

    try:
        if os.path.exists(db_document.file_path):
            os.remove(db_document.file_path)
    except Exception as e:
        logger.warning("Failed to delete physical file %s: %s", db_document.file_path, e)

    db.delete(db_document)
    db.commit()
    return None
