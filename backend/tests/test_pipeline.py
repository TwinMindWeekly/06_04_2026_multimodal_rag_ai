"""
Integration tests for process_and_update_document() pipeline orchestration.

Covers:
  - Status transitions: pending -> processing -> completed/failed
  - delete_by_document called before insert_documents (D-15)
  - Image summarization failure resilience (D-14)
  - Temp directory cleanup on success and failure (D-03, T-3b-07)
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, call, patch

import pytest

from app.models.domain import Document, Folder, Project


def _make_mock_text_element(text: str = "Document content here.", page_number: int = 1):
    """Create a mock unstructured text element."""
    el = MagicMock()
    el.text = text
    el.category = "NarrativeText"
    el.metadata = MagicMock()
    el.metadata.page_number = page_number
    el.metadata.image_path = None
    return el


def _make_mock_image_element(page_number: int = 2, image_path: str = "/tmp/img.png"):
    """Create a mock unstructured image element."""
    el = MagicMock()
    el.text = ""
    el.category = "Image"
    el.metadata = MagicMock()
    el.metadata.page_number = page_number
    el.metadata.image_path = image_path
    return el


def _create_test_document(test_db, tmp_file_path: str, status: str = "pending") -> Document:
    """Helper: insert Project, Folder, and Document into test DB. Returns Document."""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.flush()

    folder = Folder(name="Test Folder", project_id=project.id)
    test_db.add(folder)
    test_db.flush()

    document = Document(
        filename="test_document.pdf",
        file_path=tmp_file_path,
        folder_id=folder.id,
        status=status,
    )
    test_db.add(document)
    test_db.commit()
    test_db.refresh(document)
    return document


class _NonClosingSession:
    """
    Wraps a SQLAlchemy session to prevent close() from expunging test data.

    process_and_update_document() calls db.close() in a finally block.
    In tests we share the same session for setup and verification, so we
    intercept close() to avoid expunging all ORM objects mid-test.
    """

    def __init__(self, session):
        self._session = session

    def close(self):
        # Do NOT close — the test fixture owns the session lifecycle
        pass

    def __getattr__(self, name):
        return getattr(self._session, name)


class TestStatusTransitions:
    """Tests for D-13: pipeline status state machine."""

    def test_status_transitions_success(self, test_db):
        """Successful pipeline: pending -> processing -> completed."""
        from app.services.document_parser import process_and_update_document

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake content")
            tmp_path = f.name

        try:
            document = _create_test_document(test_db, tmp_path)
            doc_id = document.id

            mock_partition_result = [_make_mock_text_element()]
            mock_vs = MagicMock()
            wrapped = _NonClosingSession(test_db)

            with patch("app.services.document_parser.SessionLocal", return_value=wrapped), \
                 patch("app.services.document_parser.partition", return_value=mock_partition_result), \
                 patch("app.services.document_parser.vector_store", mock_vs), \
                 patch("app.services.document_parser.ImageProcessorService"):
                process_and_update_document(doc_id)

            refreshed = test_db.query(Document).filter(Document.id == doc_id).first()
            assert refreshed.status == "completed", f"Expected 'completed', got '{refreshed.status}'"

        finally:
            os.unlink(tmp_path)

    def test_status_failed_on_parse_error(self, test_db):
        """partition() raises -> document.status='failed'."""
        from app.services.document_parser import process_and_update_document

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"not a real pdf")
            tmp_path = f.name

        try:
            document = _create_test_document(test_db, tmp_path)
            doc_id = document.id
            wrapped = _NonClosingSession(test_db)

            with patch("app.services.document_parser.SessionLocal", return_value=wrapped), \
                 patch("app.services.document_parser.partition", side_effect=RuntimeError("bad file")), \
                 patch("app.services.document_parser.vector_store"):
                process_and_update_document(doc_id)

            refreshed = test_db.query(Document).filter(Document.id == doc_id).first()
            assert refreshed.status == "failed", f"Expected 'failed', got '{refreshed.status}'"

        finally:
            os.unlink(tmp_path)

    def test_status_failed_on_embedding_error(self, test_db):
        """insert_documents() raises -> document.status='failed'."""
        from app.services.document_parser import process_and_update_document

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF fake")
            tmp_path = f.name

        try:
            document = _create_test_document(test_db, tmp_path)
            doc_id = document.id

            mock_partition_result = [_make_mock_text_element("Some content.")]
            mock_vs = MagicMock()
            mock_vs.insert_documents.side_effect = Exception("chroma error")
            wrapped = _NonClosingSession(test_db)

            with patch("app.services.document_parser.SessionLocal", return_value=wrapped), \
                 patch("app.services.document_parser.partition", return_value=mock_partition_result), \
                 patch("app.services.document_parser.vector_store", mock_vs), \
                 patch("app.services.document_parser.ImageProcessorService"):
                process_and_update_document(doc_id)

            refreshed = test_db.query(Document).filter(Document.id == doc_id).first()
            assert refreshed.status == "failed", f"Expected 'failed', got '{refreshed.status}'"

        finally:
            os.unlink(tmp_path)


class TestDeleteBeforeInsert:
    """Tests for D-15: delete_by_document called before insert_documents."""

    def test_delete_before_insert(self, test_db):
        """delete_by_document must be called before insert_documents."""
        from app.services.document_parser import process_and_update_document

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF fake")
            tmp_path = f.name

        try:
            document = _create_test_document(test_db, tmp_path)
            doc_id = document.id

            mock_partition_result = [_make_mock_text_element("Some content to embed.")]
            mock_vs = MagicMock()

            # Track call order
            call_order = []
            mock_vs.delete_by_document.side_effect = lambda *a, **kw: call_order.append("delete")
            mock_vs.insert_documents.side_effect = lambda *a, **kw: call_order.append("insert")
            wrapped = _NonClosingSession(test_db)

            with patch("app.services.document_parser.SessionLocal", return_value=wrapped), \
                 patch("app.services.document_parser.partition", return_value=mock_partition_result), \
                 patch("app.services.document_parser.vector_store", mock_vs), \
                 patch("app.services.document_parser.ImageProcessorService"):
                process_and_update_document(doc_id)

            assert "delete" in call_order, "delete_by_document was not called"
            assert "insert" in call_order, "insert_documents was not called"
            assert call_order.index("delete") < call_order.index("insert"), \
                "delete_by_document must be called before insert_documents"

        finally:
            os.unlink(tmp_path)


class TestImageFailureResilience:
    """Tests for D-14: image summarization failure should not fail the document."""

    def test_image_failure_does_not_fail_document(self, test_db):
        """Image summarization returning placeholder -> document still completes."""
        from app.services.document_parser import process_and_update_document

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF fake")
            tmp_path = f.name

        try:
            document = _create_test_document(test_db, tmp_path)
            doc_id = document.id

            # One text element + one image element
            mock_partition_result = [
                _make_mock_text_element("Normal text content."),
                _make_mock_image_element(page_number=1, image_path="/tmp/fake.png"),
            ]
            mock_vs = MagicMock()

            # Image processor returns placeholder (simulates Gemini failure)
            mock_image_processor = MagicMock()
            mock_image_processor.summarize_image.return_value = "[Image: unable to process - test_document.pdf]"

            wrapped = _NonClosingSession(test_db)

            with patch("app.services.document_parser.SessionLocal", return_value=wrapped), \
                 patch("app.services.document_parser.partition", return_value=mock_partition_result), \
                 patch("app.services.document_parser.vector_store", mock_vs), \
                 patch("app.services.document_parser.ImageProcessorService", return_value=mock_image_processor):
                process_and_update_document(doc_id)

            refreshed = test_db.query(Document).filter(Document.id == doc_id).first()
            assert refreshed.status == "completed", \
                f"Image failure should not fail document, got status='{refreshed.status}'"

        finally:
            os.unlink(tmp_path)


class TestTempDirCleanup:
    """Tests for D-03, T-3b-07: temp directory cleanup in finally block."""

    def test_temp_dir_cleaned_on_success(self, test_db):
        """Temp dir is removed after successful pipeline execution."""
        from app.services.document_parser import process_and_update_document

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF fake")
            tmp_path = f.name

        try:
            document = _create_test_document(test_db, tmp_path)
            doc_id = document.id

            created_dirs = []
            original_mkdtemp = tempfile.mkdtemp

            def capture_mkdtemp(**kwargs):
                d = original_mkdtemp(**kwargs)
                created_dirs.append(d)
                return d

            mock_partition_result = [_make_mock_text_element("Content.")]
            mock_vs = MagicMock()
            wrapped = _NonClosingSession(test_db)

            with patch("app.services.document_parser.SessionLocal", return_value=wrapped), \
                 patch("app.services.document_parser.partition", return_value=mock_partition_result), \
                 patch("app.services.document_parser.vector_store", mock_vs), \
                 patch("app.services.document_parser.ImageProcessorService"), \
                 patch("app.services.document_parser.tempfile.mkdtemp", side_effect=capture_mkdtemp):
                process_and_update_document(doc_id)

            assert len(created_dirs) >= 1, "No temp dir was created"
            for d in created_dirs:
                assert not os.path.exists(d), \
                    f"Temp dir {d} was not cleaned up after successful pipeline"

        finally:
            os.unlink(tmp_path)

    def test_temp_dir_cleaned_on_failure(self, test_db):
        """Temp dir is removed even when embedding fails."""
        from app.services.document_parser import process_and_update_document

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF fake")
            tmp_path = f.name

        try:
            document = _create_test_document(test_db, tmp_path)
            doc_id = document.id

            created_dirs = []
            original_mkdtemp = tempfile.mkdtemp

            def capture_mkdtemp(**kwargs):
                d = original_mkdtemp(**kwargs)
                created_dirs.append(d)
                return d

            mock_partition_result = [_make_mock_text_element("Content.")]
            mock_vs = MagicMock()
            mock_vs.insert_documents.side_effect = Exception("embedding failure")
            wrapped = _NonClosingSession(test_db)

            with patch("app.services.document_parser.SessionLocal", return_value=wrapped), \
                 patch("app.services.document_parser.partition", return_value=mock_partition_result), \
                 patch("app.services.document_parser.vector_store", mock_vs), \
                 patch("app.services.document_parser.ImageProcessorService"), \
                 patch("app.services.document_parser.tempfile.mkdtemp", side_effect=capture_mkdtemp):
                process_and_update_document(doc_id)

            assert len(created_dirs) >= 1, "No temp dir was created"
            for d in created_dirs:
                assert not os.path.exists(d), \
                    f"Temp dir {d} was not cleaned up after pipeline failure"

        finally:
            os.unlink(tmp_path)
