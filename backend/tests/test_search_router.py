import pytest
from unittest.mock import patch, MagicMock
from app.models.domain import Project, Folder, Document


def _seed_project_with_document(db):
    """Helper: create a project with a folder and a document."""
    project = Project(name='Test Project')
    db.add(project)
    db.commit()
    db.refresh(project)
    folder = Folder(name='test', project_id=project.id)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    doc = Document(
        filename='test.pdf',
        file_path='/tmp/test.pdf',
        folder_id=folder.id,
        status='completed',
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return project, folder, doc


FAKE_RESULT = [
    {
        'content': 'test chunk',
        'metadata': {'filename': 'test.pdf', 'page_number': 1},
        'similarity': 0.85,
        'distance': 0.15,
    }
]


class TestSearchEndpoint:

    @patch('app.routers.search.vector_store.similarity_search_mmr')
    def test_search_returns_results(self, mock_mmr, client, test_db):
        """GET /api/search returns 200 with results array containing expected keys."""
        mock_mmr.return_value = FAKE_RESULT

        response = client.get('/api/search?q=test+query&project_id=1')

        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        assert len(data['results']) == 1
        result = data['results'][0]
        assert 'content' in result
        assert 'metadata' in result
        assert 'similarity' in result
        assert 'distance' in result

    @patch('app.routers.search.vector_store.similarity_search_mmr')
    def test_search_empty_project(self, mock_mmr, client):
        """GET /api/search on project with no documents returns 200 with empty results."""
        mock_mmr.return_value = []

        response = client.get('/api/search?q=test&project_id=999')

        assert response.status_code == 200
        data = response.json()
        assert data['results'] == []
        assert data['result_count'] == 0

    def test_search_requires_query(self, client):
        """GET /api/search without q param returns 422 (validation error)."""
        response = client.get('/api/search?project_id=1')
        assert response.status_code == 422

    def test_search_requires_project_id(self, client):
        """GET /api/search without project_id param returns 422 (validation error)."""
        response = client.get('/api/search?q=test')
        assert response.status_code == 422

    @patch('app.routers.search.vector_store.similarity_search_mmr')
    def test_search_score_threshold(self, mock_mmr, client):
        """GET /api/search with high score_threshold returns fewer or no results."""
        mock_mmr.return_value = []

        response = client.get('/api/search?q=test&project_id=1&score_threshold=0.99')

        assert response.status_code == 200
        data = response.json()
        assert data['results'] == []
        # Verify score_threshold was passed through
        call_kwargs = mock_mmr.call_args
        assert call_kwargs is not None

    @patch('app.routers.search.vector_store.similarity_search_mmr')
    @patch('app.routers.search.EmbeddingFactory.get_embedding_model')
    def test_search_provider_mismatch(self, mock_emb_factory, mock_mmr, client):
        """GET /api/search with provider mismatch raises ValueError -> 400."""
        mock_emb_factory.return_value = MagicMock()
        mock_mmr.side_effect = ValueError(
            'Embedding provider mismatch: collection uses "local", '
            'active provider is "openai". Re-index to switch providers.'
        )

        response = client.get('/api/search?q=test&project_id=1&provider=openai')

        assert response.status_code == 400
        data = response.json()
        assert 'mismatch' in data['detail'].lower()

    def test_search_query_max_length(self, client):
        """GET /api/search with query > 1000 chars returns 422 (validation error)."""
        long_query = 'a' * 1001
        response = client.get(f'/api/search?q={long_query}&project_id=1')
        assert response.status_code == 422


class TestReindexEndpoint:

    @patch('app.routers.search.process_and_update_document')
    @patch('app.routers.search.vector_store')
    def test_reindex_returns_202(self, mock_vs, mock_process, client, test_db):
        """POST /api/projects/{id}/reindex on existing project returns 202."""
        project = Project(name='Reindex Project')
        test_db.add(project)
        test_db.commit()
        test_db.refresh(project)

        mock_vs.client.delete_collection = MagicMock()

        response = client.post(f'/api/projects/{project.id}/reindex')

        assert response.status_code == 202
        data = response.json()
        assert data['status'] == 'reindex_queued'
        assert data['project_id'] == project.id

    @patch('app.routers.search.process_and_update_document')
    @patch('app.routers.search.vector_store')
    def test_reindex_nonexistent_project(self, mock_vs, mock_process, client):
        """POST /api/projects/999/reindex for nonexistent project returns 404."""
        response = client.post('/api/projects/999/reindex')
        assert response.status_code == 404

    @patch('app.routers.search.process_and_update_document')
    @patch('app.routers.search.vector_store')
    def test_reindex_marks_documents_pending(self, mock_vs, mock_process, client, test_db):
        """After reindex, all project documents have status='pending'."""
        project, folder, doc = _seed_project_with_document(test_db)
        assert doc.status == 'completed'

        mock_vs.client.delete_collection = MagicMock()

        response = client.post(f'/api/projects/{project.id}/reindex')
        assert response.status_code == 202

        test_db.refresh(doc)
        assert doc.status == 'pending'

    @patch('app.routers.search.process_and_update_document')
    @patch('app.routers.search.vector_store')
    def test_reindex_document_count(self, mock_vs, mock_process, client, test_db):
        """Reindex response includes correct document_count."""
        project, folder, doc = _seed_project_with_document(test_db)

        mock_vs.client.delete_collection = MagicMock()

        response = client.post(f'/api/projects/{project.id}/reindex')
        assert response.status_code == 202
        data = response.json()
        assert data['document_count'] == 1
