"""Basic health-check test (no database access)."""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


@pytest.mark.unit
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "version" in data
