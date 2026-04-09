import logging
from unittest.mock import patch


def test_missing_pdfinfo_logs_warning(caplog):
    from app.main import probe_system_dependencies

    with patch("app.main.shutil.which", side_effect=lambda cmd: None if cmd == "pdfinfo" else "/usr/bin/tesseract"):
        with caplog.at_level(logging.WARNING, logger="app.main"):
            probe_system_dependencies()

    assert any("poppler" in record.message.lower() or "pdfinfo" in record.message.lower()
                for record in caplog.records), (
        f"Expected WARNING about poppler/pdfinfo, got: {[r.message for r in caplog.records]}"
    )


def test_missing_tesseract_logs_warning(caplog):
    from app.main import probe_system_dependencies

    with patch("app.main.shutil.which", side_effect=lambda cmd: None if cmd == "tesseract" else "/usr/bin/pdfinfo"):
        with caplog.at_level(logging.WARNING, logger="app.main"):
            probe_system_dependencies()

    assert any("tesseract" in record.message.lower()
                for record in caplog.records), (
        f"Expected WARNING about tesseract, got: {[r.message for r in caplog.records]}"
    )


def test_probe_does_not_raise():
    from app.main import probe_system_dependencies

    with patch("app.main.shutil.which", return_value=None):
        # Should not raise even when all deps missing
        probe_system_dependencies()


def test_app_still_starts(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Multimodal RAG" in response.json()["message"]
