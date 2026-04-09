from pydantic import BaseModel, constr
from typing import Optional, List
from datetime import datetime

class ProjectBase(BaseModel):
    name: str

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class FolderBase(BaseModel):
    name: str
    project_id: int
    parent_id: Optional[int] = None

class FolderCreate(FolderBase):
    pass

class FolderResponse(FolderBase):
    id: int
    
    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    filename: str
    folder_id: Optional[int] = None
    metadata_json: Optional[str] = None
    status: Optional[str] = None

class DocumentCreate(DocumentBase):
    file_path: str

class DocumentResponse(DocumentBase):
    id: int
    uploaded_at: datetime
    status: Optional[str] = None

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    """Single search result with chunk content, metadata, and similarity scores."""
    content: str
    metadata: dict
    similarity: float
    distance: float


class SearchResponse(BaseModel):
    """Response wrapper for search endpoint."""
    results: list[SearchResult]
    query: str
    project_id: int
    result_count: int


class ReindexResponse(BaseModel):
    """Response for reindex endpoint."""
    status: str
    project_id: int
    document_count: int
