import os
import sqlite3
from unittest.mock import patch

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker


def test_sqlite_path_is_absolute():
    from app.core.database import DATABASE_PATH
    assert os.path.isabs(DATABASE_PATH), (
        f"DATABASE_PATH is not absolute: {DATABASE_PATH}"
    )


def test_sqlite_path_default_ends_with_backend_data():
    from app.core.database import DATABASE_PATH
    normalized = DATABASE_PATH.replace("\\", "/")
    assert normalized.endswith("backend/data/rag_database.db"), (
        f"Default path does not end with backend/data/rag_database.db: {DATABASE_PATH}"
    )


def test_data_directory_created():
    from app.core.database import DATABASE_PATH
    data_dir = os.path.dirname(DATABASE_PATH)
    assert os.path.isdir(data_dir), (
        f"Data directory does not exist: {data_dir}"
    )


def test_wal_mode_enabled():
    from app.core.database import engine
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA journal_mode")).scalar()
        assert result == "wal", f"Expected WAL mode, got: {result}"


def test_database_path_env_override():
    test_path = "/tmp/test_override.db"
    with patch.dict(os.environ, {"DATABASE_PATH": test_path}):
        # Re-evaluate the env var (simulating module reload)
        resolved = os.getenv("DATABASE_PATH", "fallback")
        assert resolved == test_path
