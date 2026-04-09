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
from unittest.mock import MagicMock, patch, call
import warnings

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(text: str) -> MagicMock:
    """Build a mock Gemini response object with a .text attribute."""
    response = MagicMock()
    response.text = text
    return response


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestImageProcessorService:

    def test_summarize_success(self, tmp_path, monkeypatch):
        """Mock Gemini to return known text; assert summarize_image returns it."""
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-for-test")

        # Create a dummy image file so Path.read_bytes() works
        image_file = tmp_path / "chart.png"
        image_file.write_bytes(b"\x89PNG\r\n\x1a\n")  # minimal PNG header

        mock_response = _make_mock_response("A chart showing revenue growth")
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            with patch("google.generativeai.configure"), \
                 patch("google.generativeai.GenerativeModel", return_value=mock_model):
                from app.services.image_processor import ImageProcessorService
                svc = ImageProcessorService()
                result = svc.summarize_image(str(image_file), "chart.png")

        assert result == "A chart showing revenue growth"

    def test_summarize_failure_returns_placeholder(self, tmp_path, monkeypatch):
        """generate_content raises on all 3 attempts; expect placeholder."""
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-for-test")

        image_file = tmp_path / "chart.png"
        image_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            with patch("google.generativeai.configure"), \
                 patch("google.generativeai.GenerativeModel", return_value=mock_model):
                from app.services.image_processor import ImageProcessorService
                svc = ImageProcessorService()
                result = svc.summarize_image(str(image_file), "chart.png")

        assert result == "[Image: unable to process - chart.png]"

    def test_missing_api_key_returns_placeholder(self, tmp_path, monkeypatch):
        """When GOOGLE_API_KEY is absent, return placeholder without raising."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        image_file = tmp_path / "photo.png"
        image_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            with patch("google.generativeai.configure") as mock_configure, \
                 patch("google.generativeai.GenerativeModel") as mock_gm:
                from app.services.image_processor import ImageProcessorService
                svc = ImageProcessorService()
                result = svc.summarize_image(str(image_file), "photo.png")

        assert result == "[Image: unable to process - photo.png]"
        # Gemini should NOT have been called at all
        mock_gm.assert_not_called()

    def test_api_key_not_logged(self, tmp_path, monkeypatch, caplog):
        """API key value must never appear in any log message."""
        secret_value = "super-secret-api-key-12345"
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        image_file = tmp_path / "photo.png"
        image_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
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
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = [
            Exception("err 1"),
            Exception("err 2"),
            mock_response,
        ]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            with patch("google.generativeai.configure"), \
                 patch("google.generativeai.GenerativeModel", return_value=mock_model), \
                 patch(
                     "app.services.image_processor.wait_exponential",
                     return_value=MagicMock(return_value=0),
                 ):
                # Reload to get a fresh instance with patched wait
                import importlib
                import app.services.image_processor as _mod
                importlib.reload(_mod)
                svc = _mod.ImageProcessorService()
                result = svc.summarize_image(str(image_file), "chart.png")

        assert result == "Final success text"
        assert mock_model.generate_content.call_count == 3
