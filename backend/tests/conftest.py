import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite://"


@pytest.fixture
def test_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
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
