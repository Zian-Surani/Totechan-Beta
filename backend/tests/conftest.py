import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.config.database import get_db, Base
from app.config.settings import settings

# Override settings for testing
settings.database_url = "sqlite+aiosqlite:///./test.db"
settings.pinecone_api_key = "test-key"
settings.openai_api_key = "test-key"

# Test database engine
engine = create_async_engine(
    settings.database_url,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
    echo=False,
)

TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""
    def override_get_db():
        return db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_user_data():
    """Mock user data for testing."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "User"
    }


@pytest.fixture
def mock_document_data():
    """Mock document data for testing."""
    return {
        "title": "Test Document",
        "description": "A test document for unit testing",
        "access_level": "private",
        "tags": "test,document"
    }


@pytest.fixture
def mock_chat_query():
    """Mock chat query for testing."""
    return {
        "query": "What is machine learning?",
        "retrieval_config": {
            "k": 5,
            "rerank": True,
            "threshold": 0.7
        }
    }


# Mock external services
@pytest.fixture
def mock_openai(monkeypatch):
    """Mock OpenAI API calls."""
    class MockOpenAI:
        class ChatCompletion:
            @staticmethod
            async def acreate(*args, **kwargs):
                return {
                    "choices": [{
                        "message": {
                            "content": "This is a test response about machine learning."
                        }
                    }]
                }

        class Embedding:
            @staticmethod
            async def acreate(*args, **kwargs):
                return {
                    "data": [{
                        "embedding": [0.1] * 1536  # Mock embedding vector
                    }]
                }

    monkeypatch.setattr("openai.ChatCompletion.acreate", MockOpenAI.ChatCompletion.acreate)
    monkeypatch.setattr("openai.Embedding.acreate", MockOpenAI.Embedding.acreate)


@pytest.fixture
def mock_pinecone(monkeypatch):
    """Mock Pinecone vector database operations."""
    class MockPinecone:
        class Index:
            def __init__(self, *args, **kwargs):
                pass

            def upsert(self, *args, **kwargs):
                return {"upserted_count": 1}

            def query(self, *args, **kwargs):
                return {
                    "matches": [{
                        "id": "test-doc-1",
                        "score": 0.9,
                        "metadata": {"text": "Test document content about machine learning"}
                    }]
                }

            def delete(self, *args, **kwargs):
                return {"deleted_count": 1}

    monkeypatch.setattr("pinecone.Index", MockPinecone.Index)