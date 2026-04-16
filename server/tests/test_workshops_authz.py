"""Ownership isolation and auth tests for workshop instance routes (/instances/)."""

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from api.core.auth import CurrentUser, get_current_user
from api.core.database import get_db
from api.models.schemas.workshop_instance import WorkshopInstanceResponse, WorkshopInstanceStatus
from api.services.workshop_instance_service import get_instance_service
from tests.conftest import TEST_ADMIN

# ── Helpers ───────────────────────────────────────────────────────────────────

NOW = datetime.now(timezone.utc)


def _make_instance(owner: str, k8s_name: str = "test-ws-abc123") -> WorkshopInstanceResponse:
    return WorkshopInstanceResponse(
        id=uuid.uuid4(),
        workshopId=uuid.uuid4(),
        workshopName="Standard RStudio",
        k8sName=k8s_name,
        namespace="default",
        ownerEmail=owner,
        phase="Ready",
        url="http://test-ws-abc123.orchestra.localhost:30080",
        durationRequested="4h",
        launchedAt=NOW,
        expiresAt=None,
        terminatedAt=None,
        createdAt=NOW,
        updatedAt=NOW,
    )


def _make_instance_svc(**overrides) -> MagicMock:
    """Build a MagicMock WorkshopInstanceService with sensible defaults."""
    svc = MagicMock()
    svc.list_instances = AsyncMock(return_value=([], 0))
    svc.get_instance = AsyncMock(return_value=None)
    svc.terminate = AsyncMock(return_value=True)
    svc.get_status = AsyncMock(return_value=None)
    for key, val in overrides.items():
        setattr(svc, key, val)
    return svc


@contextmanager
def _override_instance_svc(**overrides):
    """Override the get_instance_service dependency for the duration of the block."""
    from main import app

    svc = _make_instance_svc(**overrides)
    app.dependency_overrides[get_instance_service] = lambda: svc
    try:
        yield svc
    finally:
        app.dependency_overrides.pop(get_instance_service, None)


@pytest.fixture
def bob_client(_mock_k8s_startup):
    """Client authenticated as bob — a different user from alice."""
    from main import app

    mock_db = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        email="bob@test.example.com", is_admin=False
    )
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


# ── Ownership isolation ───────────────────────────────────────────────────────

class TestOwnershipIsolation:
    def test_get_own_instance_succeeds(self, client):
        instance = _make_instance("alice@test.example.com")
        with _override_instance_svc(get_instance=AsyncMock(return_value=instance)):
            response = client.get("/instances/test-ws-abc123")
        assert response.status_code == 200
        assert response.json()["ownerEmail"] == "alice@test.example.com"

    def test_get_other_users_instance_returns_404(self, bob_client):
        """Bob cannot see alice's instance — 404, no existence leak."""
        alice_instance = _make_instance("alice@test.example.com")
        with _override_instance_svc(get_instance=AsyncMock(return_value=alice_instance)):
            response = bob_client.get("/instances/test-ws-abc123")
        assert response.status_code == 404

    def test_delete_own_instance_succeeds(self, client):
        instance = _make_instance("alice@test.example.com")
        with _override_instance_svc(get_instance=AsyncMock(return_value=instance)):
            response = client.delete("/instances/test-ws-abc123")
        assert response.status_code == 204

    def test_delete_other_users_instance_returns_404(self, bob_client):
        """Bob cannot delete alice's instance — terminate must not be called."""
        alice_instance = _make_instance("alice@test.example.com")
        with _override_instance_svc(
            get_instance=AsyncMock(return_value=alice_instance)
        ) as svc:
            response = bob_client.delete("/instances/test-ws-abc123")
        assert response.status_code == 404
        svc.terminate.assert_not_called()

    def test_list_filters_by_owner_for_non_admin(self, client):
        """Regular user's list call passes owner_email filter to the service."""
        alice_instance = _make_instance("alice@test.example.com")
        captured = {}

        async def fake_list(db, *, owner_email=None, page=1, size=50):
            captured["owner_email"] = owner_email
            return [alice_instance], 1

        with _override_instance_svc(list_instances=AsyncMock(side_effect=fake_list)):
            response = client.get("/instances/")
        assert response.status_code == 200
        assert captured["owner_email"] == "alice@test.example.com"

    def test_status_for_other_users_instance_returns_404(self, bob_client):
        alice_instance = _make_instance("alice@test.example.com")
        status_obj = WorkshopInstanceStatus(
            id=alice_instance.id,
            k8sName="test-ws-abc123",
            phase="Ready",
            url=alice_instance.url,
            expiresAt=None,
        )
        with _override_instance_svc(
            get_instance=AsyncMock(return_value=alice_instance),
            get_status=AsyncMock(return_value=status_obj),
        ):
            response = bob_client.get("/instances/test-ws-abc123/status")
        assert response.status_code == 404


# ── Admin bypass ──────────────────────────────────────────────────────────────

class TestAdminBypass:
    def test_admin_can_get_any_instance(self, admin_client):
        """Admin can GET an instance owned by any user."""
        instance = _make_instance("alice@test.example.com")
        with _override_instance_svc(get_instance=AsyncMock(return_value=instance)):
            response = admin_client.get("/instances/test-ws-abc123")
        assert response.status_code == 200

    def test_admin_list_passes_no_owner_filter(self, admin_client):
        """Admin's list call passes owner_email=None to the service."""
        captured = {}

        async def fake_list(db, *, owner_email=None, page=1, size=50):
            captured["owner_email"] = owner_email
            return [], 0

        with _override_instance_svc(list_instances=AsyncMock(side_effect=fake_list)):
            admin_client.get("/instances/")
        assert captured.get("owner_email") is None

    def test_admin_can_delete_any_instance(self, admin_client):
        """Admin can terminate an instance owned by any user."""
        instance = _make_instance("alice@test.example.com")
        with _override_instance_svc(get_instance=AsyncMock(return_value=instance)):
            response = admin_client.delete("/instances/test-ws-abc123")
        assert response.status_code == 204


# ── Unauthenticated requests ──────────────────────────────────────────────────

class TestUnauthenticatedRequests:
    @pytest.fixture
    def anon_client(self, _mock_k8s_startup):
        from main import app
        from api.core.database import get_db
        from unittest.mock import MagicMock, AsyncMock

        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides[get_db] = lambda: mock_db
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
        app.dependency_overrides.pop(get_db, None)

    def test_list_without_auth_returns_401(self, anon_client):
        assert anon_client.get("/instances/").status_code == 401

    def test_get_without_auth_returns_401(self, anon_client):
        assert anon_client.get("/instances/anything").status_code == 401

    def test_delete_without_auth_returns_401(self, anon_client):
        assert anon_client.delete("/instances/anything").status_code == 401
