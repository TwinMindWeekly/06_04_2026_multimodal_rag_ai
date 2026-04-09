"""
Tests for DocumentParserService.parse_document().

Covers: PARSE-01 (unstructured partition call), PARSE-02 (element type preservation),
PARSE-05 (metadata preservation), and error handling.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


def _make_mock_element(
    text: str = "Some text",
    category: str = "NarrativeText",
    page_number: int = 1,
    image_path: str = None,
) -> MagicMock:
    """Helper: create a mock unstructured element with the expected attribute structure."""
    el = MagicMock()
    el.text = text
    el.category = category
    el.metadata = MagicMock()
    el.metadata.page_number = page_number
    el.metadata.image_path = image_path
    return el


class TestParseDocument:
    """Unit tests for DocumentParserService.parse_document()."""

    def test_parse_document_returns_elements(self):
        """parse_document returns dict with 'elements' list and 'temp_dir' key."""
        from app.services.document_parser import DocumentParserService

        mock_elements = [
            _make_mock_element(text="Hello world", category="NarrativeText", page_number=1),
            _make_mock_element(text="", category="Image", page_number=2, image_path="/tmp/img.png"),
        ]

        with patch("app.services.document_parser.partition", return_value=mock_elements):
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(b"%PDF-1.4 fake")
                tmp_path = f.name
            try:
                service = DocumentParserService()
                result = service.parse_document(tmp_path, document_id=1)
            finally:
                os.unlink(tmp_path)
                # clean up temp_dir from result
                import shutil
                shutil.rmtree(result.get("temp_dir", ""), ignore_errors=True)

        assert "elements" in result
        assert "temp_dir" in result
        assert len(result["elements"]) == 2

        text_el = result["elements"][0]
        assert text_el["text"] == "Hello world"
        assert text_el["category"] == "NarrativeText"

    def test_image_extraction_paths(self):
        """Image element with metadata.image_path is preserved in the element dict."""
        from app.services.document_parser import DocumentParserService

        mock_img_element = _make_mock_element(
            text="",
            category="Image",
            page_number=1,
            image_path="/tmp/doc_1_xyz/image-001.png",
        )

        with patch("app.services.document_parser.partition", return_value=[mock_img_element]):
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(b"%PDF-1.4 fake")
                tmp_path = f.name
            try:
                service = DocumentParserService()
                result = service.parse_document(tmp_path, document_id=1)
            finally:
                os.unlink(tmp_path)
                import shutil
                shutil.rmtree(result.get("temp_dir", ""), ignore_errors=True)

        assert len(result["elements"]) == 1
        el = result["elements"][0]
        assert el["image_path"] == "/tmp/doc_1_xyz/image-001.png"
        assert el["category"] == "Image"

    def test_metadata_preserved_page_number(self):
        """Element with metadata.page_number=3 produces element dict with page_number=3."""
        from app.services.document_parser import DocumentParserService

        mock_el = _make_mock_element(text="Page 3 content", category="Title", page_number=3)

        with patch("app.services.document_parser.partition", return_value=[mock_el]):
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(b"%PDF fake")
                tmp_path = f.name
            try:
                service = DocumentParserService()
                result = service.parse_document(tmp_path, document_id=5)
            finally:
                os.unlink(tmp_path)
                import shutil
                shutil.rmtree(result.get("temp_dir", ""), ignore_errors=True)

        assert result["elements"][0]["page_number"] == 3

    def test_metadata_null_page_number_defaults_to_zero(self):
        """Element with metadata.page_number=None produces page_number=0 in element dict."""
        from app.services.document_parser import DocumentParserService

        mock_el = _make_mock_element(text="No page info", category="NarrativeText", page_number=None)

        with patch("app.services.document_parser.partition", return_value=[mock_el]):
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
                f.write(b"fake docx content")
                tmp_path = f.name
            try:
                service = DocumentParserService()
                result = service.parse_document(tmp_path, document_id=2)
            finally:
                os.unlink(tmp_path)
                import shutil
                shutil.rmtree(result.get("temp_dir", ""), ignore_errors=True)

        assert result["elements"][0]["page_number"] == 0

    def test_parse_failure_cleans_temp_dir(self):
        """When partition() raises, the temp_dir created by parse_document is cleaned up."""
        from app.services.document_parser import DocumentParserService
        import shutil

        created_dirs = []
        original_mkdtemp = tempfile.mkdtemp

        def capture_mkdtemp(**kwargs):
            d = original_mkdtemp(**kwargs)
            created_dirs.append(d)
            return d

        with patch("app.services.document_parser.partition", side_effect=RuntimeError("bad file")):
            with patch("tempfile.mkdtemp", side_effect=capture_mkdtemp):
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(b"%PDF fake")
                    tmp_path = f.name
                try:
                    service = DocumentParserService()
                    with pytest.raises(RuntimeError, match="bad file"):
                        service.parse_document(tmp_path, document_id=99)
                finally:
                    os.unlink(tmp_path)

        # All temp dirs created during the call should be cleaned up
        for d in created_dirs:
            assert not os.path.exists(d), f"Temp dir {d} was not cleaned up after parse failure"
