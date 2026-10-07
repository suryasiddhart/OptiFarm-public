"""Integration tests for the FarmApp API health endpoint.

These tests verify the API responds correctly when running
with a real database connection.
"""

import pytest
from fastapi.testclient import TestClient

from config.settings import settings
from main import app

client = TestClient(app)


@pytest.mark.integration
class TestHealthEndpoint:
    """Verify the /health endpoint works end-to-end."""

    def test_health_check_returns_ok(self):
        """GET /health should return status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "app" in data
        assert "version" in data

    def test_health_check_has_correct_app_name(self):
        """The app name in health response should match settings."""
        response = client.get("/health")
        data = response.json()
        assert data["app"] == settings.app_name
