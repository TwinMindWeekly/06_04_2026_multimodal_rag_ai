from pydantic import BaseModel, constr, Field
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


class CitationItem(BaseModel):
    """Single citation reference from RAG context (CHAT-07)."""
    filename: str
    page_number: int
    chunk_index: int
    marker: str  # e.g. '[1]', '[2]'


class ChatRequest(BaseModel):
    """Request body for POST /api/chat (CHAT-01).
    provider = LLM provider (openai/gemini/claude/ollama).
    embedding_provider = embedding provider (local/openai/gemini) — separate from LLM provider (Pitfall 7).
    """
    message: str = Field(..., min_length=1, max_length=10000)
    project_id: int
    provider: str = 'openai'
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    top_k: int = 5
    score_threshold: float = 0.3
    embedding_provider: str = 'local'
    embedding_api_key: Optional[str] = None
