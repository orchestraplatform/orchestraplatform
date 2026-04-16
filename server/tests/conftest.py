"""Test configuration and fixtures."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from api.core.auth import CurrentUser, get_current_user
from api.core.database import get_db

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
    """Prevent real Kubernetes or DB connections during app startup."""
    with (
        patch("api.core.kubernetes.get_k8s_client"),
        patch("main.get_engine") as mock_engine,
    ):
        # Make the async context manager in lifespan succeed
        mock_conn = AsyncMock()
        mock_engine.return_value.connect.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_engine.return_value.connect.return_value.__aexit__ = AsyncMock(
            return_value=False
        )
        mock_engine.return_value.dispose = AsyncMock()
        yield


def _mock_db_session():
    """Return a mock AsyncSession for use as the get_db dependency override."""
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.fixture
def client(_mock_k8s_startup):
    """Test client authenticated as the default test user (alice)."""
    from main import app

    mock_db = _mock_db_session()
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def admin_client(_mock_k8s_startup):
    """Test client authenticated as an admin user."""
    from main import app

    mock_db = _mock_db_session()
    app.dependency_overrides[get_current_user] = lambda: TEST_ADMIN
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def mock_k8s_client():
    """Mock the Kubernetes CustomObjects API used by WorkshopService."""
    mock_api = Mock()
    with patch(
        "api.services.workshop_service.get_custom_objects_api", return_value=mock_api
    ):
        yield mock_api
