import logging
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.i18n import get_language, t
from app.models.domain import Project, Folder, Document
from app.schemas.domain import SearchResponse, SearchResult, ReindexResponse
from app.services.vector_store import vector_store
from app.services.embeddings import EmbeddingFactory
from app.services.document_parser import process_and_update_document

logger = logging.getLogger(__name__)

router = APIRouter(tags=['search'])


@router.get('/api/search', response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, max_length=1000, description='Search query text'),
    project_id: int = Query(..., description='Project ID to search within'),
    top_k: int = Query(5, ge=1, le=20, description='Number of results'),
    score_threshold: float = Query(0.3, ge=0.0, le=1.0, description='Minimum similarity score'),
    provider: str = Query('local', description='Embedding provider: local/openai/gemini'),
    api_key: str | None = Query(None, description='API key for paid providers'),
    lang: str = Depends(get_language),
):
    """Semantic search endpoint returning Top-K chunks with distances and metadata (SEARCH-01)."""
    try:
        embedding_model = EmbeddingFactory.get_embedding_model(provider=provider, api_key=api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        results = vector_store.similarity_search_mmr(
            query=q,
            top_k=top_k,
            score_threshold=score_threshold,
            project_id=project_id,
            embedding_model=embedding_model,
            provider=provider,
        )
    except ValueError as e:
        # EMBED-04: provider mismatch
        raise HTTPException(status_code=400, detail=str(e))

    return SearchResponse(
        results=[SearchResult(**r) for r in results],
        query=q,
        project_id=project_id,
        result_count=len(results),
    )


@router.post('/api/projects/{project_id}/reindex', response_model=ReindexResponse, status_code=202)
def reindex_project(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    lang: str = Depends(get_language),
):
    """Delete all vectors for a project and re-queue all documents for re-embedding (EMBED-05)."""
    # Verify project exists
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail=t('errors.project_not_found', lang))

    # Delete entire ChromaDB collection for this project
    collection_name = f'project_{project_id}'
    try:
        vector_store.client.delete_collection(collection_name)
    except Exception:
        pass  # Collection may not exist yet

    # Mark all documents in project as pending and queue re-processing
    documents = (
        db.query(Document)
        .join(Folder)
        .filter(Folder.project_id == project_id)
        .all()
    )
    for doc in documents:
        doc.status = 'pending'
    db.commit()

    for doc in documents:
        background_tasks.add_task(process_and_update_document, doc.id)

    return ReindexResponse(
        status='reindex_queued',
        project_id=project_id,
        document_count=len(documents),
    )
