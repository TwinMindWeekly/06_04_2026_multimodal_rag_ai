import inspect


def test_background_task_uses_joinedload():
    """document_parser.py must use joinedload(Document.folder) to prevent DetachedInstanceError."""
    from app.services import document_parser
    source = inspect.getsource(document_parser)
    assert "joinedload(Document.folder)" in source, (
        "document_parser.py must use joinedload(Document.folder)"
    )


def test_joinedload_imported():
    """joinedload must be imported from sqlalchemy.orm."""
    from app.services import document_parser
    source = inspect.getsource(document_parser)
    assert "from sqlalchemy.orm" in source and "joinedload" in source, (
        "document_parser.py must import joinedload from sqlalchemy.orm"
    )


def test_process_document_handles_missing_document(test_db):
    """process_and_update_document with nonexistent ID returns None without error."""
    from app.services.document_parser import process_and_update_document
    result = process_and_update_document(99999)
    assert result is None
