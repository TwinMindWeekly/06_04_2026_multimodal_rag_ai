import io
import pytest
from unittest.mock import patch


def test_invalid_extension_exe_returns_400(client):
    file_content = b"fake exe content"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("malware.exe", io.BytesIO(file_content), "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Invalid" in response.json()["detail"] or "invalid" in response.json()["detail"].lower()


def test_invalid_extension_txt_returns_400(client):
    file_content = b"some text"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("readme.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert response.status_code == 400


def test_valid_extension_pdf_accepted(client):
    """A valid .pdf upload should not be rejected by validation (may fail later for other reasons)."""
    file_content = b"%PDF-1.4 fake pdf content"
    with patch("app.routers.documents.process_and_update_document"):
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")},
        )
    # Should not be 400 or 413 — validation passed
    assert response.status_code != 400
    assert response.status_code != 413


def test_valid_extension_case_insensitive(client):
    """Uppercase .PDF should be accepted."""
    file_content = b"%PDF-1.4 fake pdf content"
    with patch("app.routers.documents.process_and_update_document"):
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.PDF", io.BytesIO(file_content), "application/pdf")},
        )
    assert response.status_code != 400


def test_oversized_file_returns_413(client):
    """File larger than 100MB must return 413."""
    from app.routers.documents import MAX_FILE_SIZE_BYTES

    oversized_content = b"x" * (MAX_FILE_SIZE_BYTES + 1)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("huge.pdf", io.BytesIO(oversized_content), "application/pdf")},
    )
    assert response.status_code == 413


def test_allowed_extensions_constant():
    """ALLOWED_EXTENSIONS must contain exactly the 4 whitelisted types."""
    from app.routers.documents import ALLOWED_EXTENSIONS
    assert ALLOWED_EXTENSIONS == {".pdf", ".docx", ".pptx", ".xlsx"}


def test_max_file_size_constant():
    """MAX_FILE_SIZE_BYTES must be 100MB."""
    from app.routers.documents import MAX_FILE_SIZE_BYTES
    assert MAX_FILE_SIZE_BYTES == 100 * 1024 * 1024
