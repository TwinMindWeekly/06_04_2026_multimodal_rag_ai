import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Pre-mock google.genai to prevent ImportError in environments without the package.
# image_processor.py does 'from google import genai' at import time.
# ---------------------------------------------------------------------------
if 'google.genai' not in sys.modules:
    _mock_google = MagicMock()
    _mock_genai = MagicMock()
    sys.modules.setdefault('google', _mock_google)
    sys.modules.setdefault('google.genai', _mock_genai)
    _mock_google.genai = _mock_genai

# ---------------------------------------------------------------------------
# Pre-mock unstructured.partition.auto BEFORE any app module is imported.
#
# unstructured.partition.image imports detectron2/torch which causes a
# segmentation fault on Windows (WSL2) when loaded natively. Since all tests
# mock `partition` anyway, we replace the module at the sys.modules level so
# the real C-extension is never loaded.
#
# This must be done at conftest import time (module top-level), before pytest
# collects test modules that transitively import document_parser.py.
# ---------------------------------------------------------------------------
if "unstructured.partition.auto" not in sys.modules:
    _mock_unstructured = MagicMock()
    _mock_partition_auto = MagicMock()
    _mock_partition_auto.partition = MagicMock(return_value=[])
    sys.modules.setdefault("unstructured", _mock_unstructured)
    sys.modules.setdefault("unstructured.partition", MagicMock())
    sys.modules.setdefault("unstructured.partition.auto", _mock_partition_auto)

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite://"


@pytest.fixture
def test_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def test_db(test_engine):
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(test_engine):
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_embeddings():
    mock = MagicMock()
    mock.embed_documents.return_value = [[0.1] * 384]
    mock.embed_query.return_value = [0.1] * 384
    return mock
