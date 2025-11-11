import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.unit
class TestAuth:
    """Test authentication endpoints."""

    def test_register_user_success(self, client: TestClient, mock_user_data: dict):
        """Test successful user registration."""
        response = client.post("/api/v1/auth/register", json=mock_user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert data["data"]["user"]["email"] == mock_user_data["email"]
        assert "password" not in data["data"]["user"]

    def test_register_user_duplicate_email(self, client: TestClient, mock_user_data: dict):
        """Test registration with duplicate email."""
        # First registration
        client.post("/api/v1/auth/register", json=mock_user_data)

        # Second registration with same email
        response = client.post("/api/v1/auth/register", json=mock_user_data)

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "already registered" in data["error"]["message"].lower()

    def test_register_user_invalid_email(self, client: TestClient, mock_user_data: dict):
        """Test registration with invalid email."""
        mock_user_data["email"] = "invalid-email"

        response = client.post("/api/v1/auth/register", json=mock_user_data)

        assert response.status_code == 422

    def test_register_user_weak_password(self, client: TestClient, mock_user_data: dict):
        """Test registration with weak password."""
        mock_user_data["password"] = "123"

        response = client.post("/api/v1/auth/register", json=mock_user_data)

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "password" in data["error"]["message"].lower()

    def test_login_success(self, client: TestClient, mock_user_data: dict):
        """Test successful user login."""
        # Register user first
        client.post("/api/v1/auth/register", json=mock_user_data)

        # Login
        login_data = {
            "username": mock_user_data["email"],
            "password": mock_user_data["password"]
        }
        response = client.post("/api/v1/auth/token", data=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "expires_in" in data

    def test_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        response = client.post("/api/v1/auth/token", data=login_data)

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Incorrect email or password"

    def test_get_current_user(self, client: TestClient, mock_user_data: dict):
        """Test getting current user info."""
        # Register and login
        register_response = client.post("/api/v1/auth/register", json=mock_user_data)
        token = register_response.json()["data"]["access_token"]

        # Get current user
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == mock_user_data["email"]

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 401

    def test_protected_route_without_token(self, client: TestClient):
        """Test accessing protected route without token."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401


@pytest.mark.integration
class TestAuthIntegration:
    """Integration tests for authentication."""

    async def test_user_workflow(self, client: TestClient, mock_user_data: dict):
        """Test complete user registration and login workflow."""
        # Register user
        register_response = client.post("/api/v1/auth/register", json=mock_user_data)
        assert register_response.status_code == 201

        token = register_response.json()["data"]["access_token"]
        user_id = register_response.json()["data"]["user"]["id"]

        # Access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["data"]["id"] == user_id

        # Login with credentials
        login_data = {
            "username": mock_user_data["email"],
            "password": mock_user_data["password"]
        }
        login_response = client.post("/api/v1/auth/token", data=login_data)
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()