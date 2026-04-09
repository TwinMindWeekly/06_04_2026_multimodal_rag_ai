import os
import json
from sqlalchemy.orm import Session
# from unstructured.partition.auto import partition
# from unstructured.chunking.title import chunk_by_title

from app.models.domain import Document

class DocumentParserService:
    def __init__(self, extract_images: bool = True):
        self.extract_images = extract_images
        
    def parse_document(self, file_path: str, document_id: int):
        """
        Parses a document (PDF, DOCX, PPTX, etc.) using unstructured.
        Extracts both text chunks and images.
        """
        # Define output directory for images
        output_dir = os.path.join(os.path.dirname(file_path), f"extracted_{document_id}")
        if self.extract_images:
            os.makedirs(output_dir, exist_ok=True)
            
        # NOTE: Unstructured requires system dependencies (poppler, tesseract) for hi_res.
        # This is a stub implementation representing the pipeline.
        # In actual execution, uncomment unstructured imports and use:
        # elements = partition(
        #     filename=file_path,
        #     strategy="hi_res",
        #     extract_image_block_types=["Image", "Table"],
        #     extract_image_block_output_dir=output_dir
        # )
        # chunks = chunk_by_title(elements)
        # text_chunks = [chunk.text for chunk in chunks if chunk.text]
        
        # Stub logic
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

def process_and_update_document(document_id: int, db: Session):
    """
    Background task to parse constraints immediately after upload.
    """
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if not db_document:
        return
        
    parser = DocumentParserService(extract_images=True)
    result = parser.parse_document(db_document.file_path, document_id)
    
    # Update document metadata
    current_metadata = json.loads(db_document.metadata_json) if db_document.metadata_json else {}
    current_metadata.update(result["metadata"])
    db_document.metadata_json = json.dumps(current_metadata)
    
    db.commit()
    
    return result
