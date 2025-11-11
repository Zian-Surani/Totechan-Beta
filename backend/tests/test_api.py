import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


@pytest.mark.unit
class TestChatAPI:
    """Test chat API endpoints."""

    def test_ask_question_unauthorized(self, client: TestClient, mock_chat_query: dict):
        """Test asking question without authentication."""
        response = client.post("/api/v1/chat/ask", json=mock_chat_query)

        assert response.status_code == 401

    def test_ask_question_invalid_query(self, client: TestClient, auth_headers: dict):
        """Test asking question with invalid query."""
        invalid_query = {"query": ""}  # Empty query

        response = client.post("/api/v1/chat/ask", json=invalid_query, headers=auth_headers)

        assert response.status_code == 422

    @patch('app.routers.chat.RAGService')
    def test_ask_question_success(self, mock_rag_service, client: TestClient, auth_headers: dict, mock_chat_query: dict):
        """Test successful question answering."""
        # Mock RAG service response
        mock_rag_instance = AsyncMock()
        mock_rag_instance.ask_question.return_value = {
            "answer": "Machine learning is a subset of artificial intelligence...",
            "sources": [
                {
                    "document_id": "doc-1",
                    "title": "Introduction to ML",
                    "content": "Machine learning fundamentals...",
                    "score": 0.95
                }
            ],
            "session_id": "session-123"
        }
        mock_rag_service.return_value = mock_rag_instance

        response = client.post("/api/v1/chat/ask", json=mock_chat_query, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "answer" in data["data"]
        assert "sources" in data["data"]
        assert len(data["data"]["sources"]) > 0

    def test_create_session(self, client: TestClient, auth_headers: dict):
        """Test creating a new chat session."""
        session_data = {
            "title": "Test Session",
            "description": "A test chat session"
        }

        response = client.post("/api/v1/chat/sessions", json=session_data, headers=auth_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == session_data["title"]
        assert "id" in data["data"]

    def test_get_sessions(self, client: TestClient, auth_headers: dict):
        """Test retrieving chat sessions."""
        response = client.get("/api/v1/chat/sessions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "sessions" in data["data"]
        assert isinstance(data["data"]["sessions"], list)

    def test_get_session_history(self, client: TestClient, auth_headers: dict):
        """Test retrieving session history."""
        # First create a session
        session_response = client.post("/api/v1/chat/sessions", json={}, headers=auth_headers)
        session_id = session_response.json()["data"]["id"]

        # Get session history
        response = client.get(f"/api/v1/chat/sessions/{session_id}/history", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "messages" in data["data"]


@pytest.mark.unit
class TestDocumentsAPI:
    """Test documents API endpoints."""

    def test_get_documents_unauthorized(self, client: TestClient):
        """Test getting documents without authentication."""
        response = client.get("/api/v1/ingest/documents")

        assert response.status_code == 401

    def test_get_documents_success(self, client: TestClient, auth_headers: dict):
        """Test successfully getting documents."""
        response = client.get("/api/v1/ingest/documents", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "documents" in data["data"]
        assert isinstance(data["data"]["documents"], list)

    def test_upload_document_missing_file(self, client: TestClient, auth_headers: dict, mock_document_data: dict):
        """Test uploading document without file."""
        response = client.post(
            "/api/v1/ingest/upload",
            data=mock_document_data,  # Send as form data, not JSON
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error for missing file

    def test_delete_document_not_found(self, client: TestClient, auth_headers: dict):
        """Test deleting non-existent document."""
        response = client.delete("/api/v1/ingest/documents/nonexistent-id", headers=auth_headers)

        assert response.status_code == 404

    def test_get_ingestion_stats(self, client: TestClient, auth_headers: dict):
        """Test getting ingestion statistics."""
        response = client.get("/api/v1/ingest/stats", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "stats" in data["data"]


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints."""

    def test_complete_chat_workflow(self, client: TestClient, mock_user_data: dict):
        """Test complete chat workflow from registration to question answering."""
        # Register and login
        register_response = client.post("/api/v1/auth/register", json=mock_user_data)
        token = register_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        session_response = client.post("/api/v1/chat/sessions", json={"title": "Test Chat"}, headers=headers)
        session_id = session_response.json()["data"]["id"]

        # Ask question (mocked)
        with patch('app.routers.chat.RAGService') as mock_rag:
            mock_rag_instance = AsyncMock()
            mock_rag_instance.ask_question.return_value = {
                "answer": "Test answer",
                "sources": [],
                "session_id": session_id
            }
            mock_rag.return_value = mock_rag_instance

            query_data = {
                "query": "What is machine learning?",
                "session_id": session_id
            }
            chat_response = client.post("/api/v1/chat/ask", json=query_data, headers=headers)

            assert chat_response.status_code == 200

        # Get session history
        history_response = client.get(f"/api/v1/chat/sessions/{session_id}/history", headers=headers)
        assert history_response.status_code == 200

        # Get all sessions
        sessions_response = client.get("/api/v1/chat/sessions", headers=headers)
        assert sessions_response.status_code == 200
        sessions = sessions_response.json()["data"]["sessions"]
        assert len(sessions) > 0
        assert any(session["id"] == session_id for session in sessions)


# Fixtures
@pytest.fixture
def auth_headers(client: TestClient, mock_user_data: dict):
    """Create authenticated headers for requests."""
    # Register and login user
    register_response = client.post("/api/v1/auth/register", json=mock_user_data)
    token = register_response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}