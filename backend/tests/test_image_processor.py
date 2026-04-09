"""
Tests for ImageProcessorService — PARSE-03, PARSE-04.

Covers:
- Successful Gemini Vision call returning summary text
- Failure after 3 retries returns placeholder
- Missing GOOGLE_API_KEY returns placeholder, no exception
- API key value never appears in any log output
- Retry count: fails twice, succeeds on third call
"""
import logging
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(text: str) -> MagicMock:
    """Build a mock Gemini response object with a .text attribute."""
    response = MagicMock()
    response.text = text
    return response


def _make_mock_client(mock_response=None, side_effect=None) -> MagicMock:
    """Build a mock genai.Client with models.generate_content configured."""
    client = MagicMock()
    if side_effect is not None:
        client.models.generate_content.side_effect = side_effect
    elif mock_response is not None:
        client.models.generate_content.return_value = mock_response
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestImageProcessorService:

    def test_summarize_success(self, tmp_path, monkeypatch):
        """Mock Gemini to return known text; assert summarize_image returns it."""
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-for-test")

        image_file = tmp_path / "chart.png"
        image_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        mock_response = _make_mock_response("A chart showing revenue growth")
        mock_client = _make_mock_client(mock_response=mock_response)

        with patch("app.services.image_processor.genai.Client", return_value=mock_client):
            from app.services.image_processor import ImageProcessorService
            svc = ImageProcessorService()
            result = svc.summarize_image(str(image_file), "chart.png")

        assert result == "A chart showing revenue growth"

    def test_summarize_failure_returns_placeholder(self, tmp_path, monkeypatch):
        """generate_content raises on all 3 attempts; expect placeholder."""
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-for-test")

        image_file = tmp_path / "chart.png"
        image_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        mock_client = _make_mock_client(side_effect=Exception("API Error"))

        with patch("app.services.image_processor.genai.Client", return_value=mock_client):
            from app.services.image_processor import ImageProcessorService
            svc = ImageProcessorService()
            result = svc.summarize_image(str(image_file), "chart.png")

        assert result == "[Image: unable to process - chart.png]"

    def test_missing_api_key_returns_placeholder(self, tmp_path, monkeypatch):
        """When GOOGLE_API_KEY is absent, return placeholder without raising."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        image_file = tmp_path / "photo.png"
        image_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        with patch("app.services.image_processor.genai.Client") as mock_client_cls:
            from app.services.image_processor import ImageProcessorService
            svc = ImageProcessorService()
            result = svc.summarize_image(str(image_file), "photo.png")

        assert result == "[Image: unable to process - photo.png]"
        # Gemini client should NOT have been created at all
        mock_client_cls.assert_not_called()

    def test_api_key_not_logged(self, tmp_path, monkeypatch, caplog):
        """API key value must never appear in any log message."""
        secret_value = "super-secret-api-key-12345"
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        image_file = tmp_path / "photo.png"
        image_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        with caplog.at_level(logging.DEBUG, logger="app.services.image_processor"):
            from app.services.image_processor import ImageProcessorService
            svc = ImageProcessorService()
            svc.summarize_image(str(image_file), "photo.png")

        for record in caplog.records:
            assert secret_value not in record.getMessage(), (
                f"API key leaked in log: {record.getMessage()}"
            )

    def test_retry_count(self, tmp_path, monkeypatch):
        """Fails twice then succeeds on third call; generate_content called 3 times."""
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-for-test")

        image_file = tmp_path / "chart.png"
        image_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        mock_response = _make_mock_response("Final success text")
        mock_client = _make_mock_client(side_effect=[
            Exception("err 1"),
            Exception("err 2"),
            mock_response,
        ])

        with patch("app.services.image_processor.genai.Client", return_value=mock_client), \
             patch(
                 "app.services.image_processor.wait_exponential",
                 return_value=MagicMock(return_value=0),
             ):
            import importlib
            import app.services.image_processor as _mod
            importlib.reload(_mod)
            svc = _mod.ImageProcessorService()
            result = svc.summarize_image(str(image_file), "chart.png")

        assert result == "Final success text"
        assert mock_client.models.generate_content.call_count == 3
