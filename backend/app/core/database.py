import os
import logging
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

# __file__ = backend/app/core/database.py
# .parent = backend/app/core/
# .parent.parent = backend/app/
# .parent.parent.parent = backend/
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

# Per D-01, D-03: env var DATABASE_PATH with __file__-relative default
_DEFAULT_DB_PATH = str(_BACKEND_DIR / "data" / "rag_database.db")
DATABASE_PATH = os.getenv("DATABASE_PATH", _DEFAULT_DB_PATH)

# Per D-02: auto-create data directory
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
logger.info("SQLite database path: %s", DATABASE_PATH)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)


# Per D-08 (INFRA-03): WAL mode via engine-level connection event
@event.listens_for(engine, "connect")
def _set_sqlite_wal_mode(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def _migrate_add_status_column(db_engine):
    """One-time migration: add status column to documents table if missing (per D-13, Pitfall 6)."""
    import sqlite3 as _sqlite3
    raw_url = str(db_engine.url).replace("sqlite:///", "")
    if not raw_url or not os.path.exists(raw_url):
        return
    conn = _sqlite3.connect(raw_url)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        if "status" not in columns:
            cursor.execute("ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'pending' NOT NULL")
            conn.commit()
            logger.info("Migrated: added 'status' column to documents table")
    except Exception as e:
        logger.warning("Migration check for status column failed: %s", e)
    finally:
        conn.close()


_migrate_add_status_column(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
