"""Test configuration and fixtures."""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from api.core.auth import CurrentUser, get_current_user

# Default test identity used by the `client` fixture
TEST_USER = CurrentUser(email="alice@test.example.com", is_admin=False)
TEST_ADMIN = CurrentUser(email="admin@test.example.com", is_admin=True)

# A minimal mock Workshop CRD returned by the k8s API
MOCK_WORKSHOP_CRD = {
    "apiVersion": "orchestra.io/v1",
    "kind": "Workshop",
    "metadata": {"name": "test-workshop", "namespace": "default"},
    "spec": {
        "name": "test-workshop",
        "owner": "alice@test.example.com",
        "duration": "4h",
        "image": "rocker/rstudio:latest",
    },
    "status": {},
}


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
    """Test client authenticated as the default test user (alice)."""
    from main import app

    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def admin_client(_mock_k8s_startup):
    """Test client authenticated as an admin user."""
    from main import app

    app.dependency_overrides[get_current_user] = lambda: TEST_ADMIN
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_k8s_client():
    """Mock the Kubernetes CustomObjects API used by WorkshopService.

    WorkshopService.custom_api is a property that calls get_custom_objects_api()
    on each access, so patching the function here intercepts all service calls.
    """
    mock_api = Mock()
    with patch("api.services.workshop_service.get_custom_objects_api", return_value=mock_api):
        yield mock_api
