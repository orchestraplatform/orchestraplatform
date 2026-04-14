"""Test health endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_health_check(client):
    """Test basic health check endpoint."""
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "orchestra-api"
    assert "timestamp" in data


def test_readiness_check(client):
    """Test readiness endpoint."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "timestamp" in data


def test_liveness_check(client):
    """Test liveness endpoint."""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Orchestra API"
    assert data["version"] == "0.1.0"
    assert "docs_url" in data
