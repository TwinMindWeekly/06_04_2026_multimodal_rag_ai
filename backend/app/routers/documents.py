import os
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.i18n import get_language, t
from app.models.domain import Document, Folder
from app.schemas.domain import DocumentResponse
from app.services.document_parser import process_and_update_document

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    folder_id: int = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    lang: str = Depends(get_language),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    # Check if folder exists if provided
    if folder_id is not None:
        db_folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not db_folder:
            raise HTTPException(status_code=404, detail=t("errors.folder_not_found", lang))

    # Generate unique filename to avoid collisions
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Save to db
    metadata = {
        "original_name": file.filename,
        "size_bytes": len(content),
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
    
    background_tasks.add_task(process_and_update_document, db_document.id, db)

    return db_document

@router.get("/folder/{folder_id}", response_model=List[DocumentResponse])
def get_documents_by_folder(folder_id: int, db: Session = Depends(get_db)):
    return db.query(Document).filter(Document.folder_id == folder_id).all()

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: Session = Depends(get_db), lang: str = Depends(get_language)):
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if not db_document:
        raise HTTPException(status_code=404, detail=t("errors.document_not_found", lang))
        
    # Delete physical file
    if os.path.exists(db_document.file_path):
        os.remove(db_document.file_path)
        
    db.delete(db_document)
    db.commit()
    return None
