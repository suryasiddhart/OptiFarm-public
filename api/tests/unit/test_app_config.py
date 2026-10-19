"""Unit tests for the API docs switch and the CORS policy (settings read at import)."""

import importlib

import pytest
from fastapi.testclient import TestClient

import config.settings
import main


@pytest.fixture
def client_with(monkeypatch):
    """Build a TestClient for an app created with the given environment."""
    def build(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        importlib.reload(config.settings)
        return TestClient(importlib.reload(main).app)

    yield build
    monkeypatch.undo()
    importlib.reload(config.settings)
    importlib.reload(main)


@pytest.mark.unit
class TestApiDocs:
    def test_enabled_by_default(self, client_with):
        client = client_with()
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200
        assert client.get("/openapi.json").json()["openapi"].startswith("3.")

    def test_disabled_hides_ui_and_schema(self, client_with):
        client = client_with(API_DOCS_ENABLED="false")
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == 404, path
        assert client.get("/health").status_code == 200


@pytest.mark.unit
class TestCors:
    PREFLIGHT = {"Access-Control-Request-Method": "POST",
                 "Access-Control-Request-Headers": "authorization,content-type"}

    def test_no_cross_origin_access_by_default(self, client_with):
        client = client_with()
        response = client.get("/health", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in response.headers
        preflight = client.options("/auth/login",
                                   headers={"Origin": "https://evil.example", **self.PREFLIGHT})
        assert "access-control-allow-origin" not in preflight.headers

    def test_only_listed_origins_without_credentials(self, client_with):
        client = client_with(CORS_ORIGINS="http://localhost:5173, https://admin.example")
        allowed = client.options("/auth/login",
                                 headers={"Origin": "http://localhost:5173", **self.PREFLIGHT})
        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "access-control-allow-credentials" not in allowed.headers

        other = client.get("/health", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in other.headers
