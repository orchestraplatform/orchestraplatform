"""Test configuration and fixtures."""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _mock_k8s_startup():
    """Prevent real Kubernetes connections during app startup.

    The server lifespan calls get_k8s_client() on startup. This fixture patches
    it for every test so the test suite runs without a live cluster.
    """
    with patch("api.core.kubernetes.get_k8s_client"):
        yield


@pytest.fixture
def client(_mock_k8s_startup):
    """Create a test client for the FastAPI app."""
    from main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_k8s_client():
    """Mock the Kubernetes CustomObjects API used by WorkshopService.

    WorkshopService.custom_api is a property that calls get_custom_objects_api()
    on each access, so patching the function here intercepts all service calls.
    """
    mock_api = Mock()
    with patch("api.services.workshop_service.get_custom_objects_api", return_value=mock_api):
        yield mock_api
