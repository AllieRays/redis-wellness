"""Basic tests for the API."""

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns correct info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data


def test_health_check_endpoint():
    """Test health check endpoint."""
    response = client.get("/api/health/check")
    assert response.status_code == 200
    data = response.json()
    assert "redis" in data
    assert "ollama" in data
    assert isinstance(data["redis"], bool)
    assert isinstance(data["ollama"], bool)
