import pytest
from unittest.mock import AsyncMock, patch
from app.services.embeddings import EmbeddingsService
from app.services.retrieval import RetrievalService
from app.services.document_processor import DocumentProcessor


@pytest.mark.unit
class TestEmbeddingsService:
    """Test embeddings service."""

    @pytest.fixture
    def embeddings_service(self):
        """Create embeddings service instance."""
        return EmbeddingsService()

    @pytest.mark.asyncio
    async def test_generate_embeddings(self, embeddings_service, mock_openai):
        """Test generating embeddings for text."""
        texts = ["This is a test document about machine learning."]

        result = await embeddings_service.generate_embeddings(texts)

        assert len(result) == 1
        assert len(result[0]) == 1536  # OpenAI embedding dimension
        assert all(isinstance(x, float) for x in result[0])

    @pytest.mark.asyncio
    async def test_count_tokens(self, embeddings_service):
        """Test token counting."""
        text = "This is a test document with multiple words."

        result = embeddings_service.count_tokens(text)

        assert isinstance(result, int)
        assert result > 0

    @pytest.mark.asyncio
    async def test_batch_processing(self, embeddings_service, mock_openai):
        """Test batch embedding generation."""
        texts = [
            "First document",
            "Second document",
            "Third document"
        ]

        result = await embeddings_service.generate_embeddings(texts)

        assert len(result) == 3
        assert all(len(embedding) == 1536 for embedding in result)


@pytest.mark.unit
class TestRetrievalService:
    """Test retrieval service."""

    @pytest.fixture
    def retrieval_service(self):
        """Create retrieval service instance."""
        return RetrievalService()

    @pytest.mark.asyncio
    async def test_search_documents(self, retrieval_service, mock_pinecone):
        """Test document search functionality."""
        query = "What is machine learning?"
        filters = {"user_id": "test-user"}

        result = await retrieval_service.search(
            query=query,
            k=5,
            filters=filters
        )

        assert isinstance(result, list)
        assert len(result) > 0
        assert "score" in result[0]
        assert "metadata" in result[0]

    @pytest.mark.asyncio
    async def test_rerank_results(self, retrieval_service):
        """Test result reranking."""
        query = "What is machine learning?"
        results = [
            {"text": "Machine learning is a subset of AI", "score": 0.8},
            {"text": "The weather is nice today", "score": 0.9},
            {"text": "Deep learning uses neural networks", "score": 0.7}
        ]

        result = await retrieval_service.rerank(query, results)

        assert isinstance(result, list)
        assert len(result) == len(results)
        # ML-related documents should be ranked higher
        assert "machine learning" in result[0]["text"].lower() or "neural networks" in result[0]["text"].lower()


@pytest.mark.unit
class TestDocumentProcessor:
    """Test document processor service."""

    @pytest.fixture
    def document_processor(self):
        """Create document processor instance."""
        return DocumentProcessor()

    def test_chunk_text(self, document_processor):
        """Test text chunking functionality."""
        text = "This is a long document that should be split into multiple chunks. " * 50

        chunks = document_processor.chunk_text(
            text=text,
            chunk_size=100,
            overlap=20
        )

        assert len(chunks) > 1
        assert all(len(chunk) > 0 for chunk in chunks)
        # Check overlap
        assert chunks[1].startswith(chunks[0][-20:])

    def test_extract_metadata(self, document_processor):
        """Test metadata extraction."""
        text = """
        Title: Machine Learning Basics
        Author: John Doe
        Date: 2024-01-01

        This document covers the fundamentals of machine learning.
        """

        metadata = document_processor.extract_metadata(text)

        assert metadata["title"] == "Machine Learning Basics"
        assert metadata["author"] == "John Doe"

    def test_process_pdf_content(self, document_processor):
        """Test PDF content processing simulation."""
        # Since we can't process actual PDF in tests, simulate the result
        content = "Sample PDF content for testing purposes."

        result = document_processor.clean_text(content)

        assert isinstance(result, str)
        assert len(result) > 0
        assert not result.isspace()

    def test_clean_text(self, document_processor):
        """Test text cleaning functionality."""
        dirty_text = """
        This   is    a     text     with     extra     spaces.

        And multiple newlines!

        """

        cleaned = document_processor.clean_text(dirty_text)

        assert "  " not in cleaned  # No double spaces
        assert not cleaned.startswith("\n")
        assert not cleaned.endswith("\n")


@pytest.mark.integration
class TestServiceIntegration:
    """Integration tests for services."""

    @pytest.mark.asyncio
    async def test_rag_pipeline(self, document_processor, embeddings_service, retrieval_service, mock_openai, mock_pinecone):
        """Test complete RAG pipeline integration."""
        # Process document
        document_text = "Machine learning is a method of data analysis that automates analytical model building."
        chunks = document_processor.chunk_text(document_text, chunk_size=100, overlap=20)

        # Generate embeddings
        embeddings = await embeddings_service.generate_embeddings(chunks)

        assert len(chunks) == len(embeddings)

        # Search simulation
        query = "What is machine learning?"
        search_results = await retrieval_service.search(query, k=3)

        assert len(search_results) > 0
        assert all("score" in result for result in search_results)