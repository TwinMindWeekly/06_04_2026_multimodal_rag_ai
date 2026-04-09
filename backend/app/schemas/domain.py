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

class DocumentCreate(DocumentBase):
    file_path: str

class DocumentResponse(DocumentBase):
    id: int
    uploaded_at: datetime
    
    class Config:
        from_attributes = True
