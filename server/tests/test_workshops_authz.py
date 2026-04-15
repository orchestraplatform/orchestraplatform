"""Ownership isolation tests for the workshop API routes."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from api.core.auth import CurrentUser, get_current_user
from tests.conftest import MOCK_WORKSHOP_CRD, TEST_ADMIN


def _workshop_for(owner: str) -> dict:
    """Return a copy of MOCK_WORKSHOP_CRD with the given owner."""
    return {
        **MOCK_WORKSHOP_CRD,
        "spec": {**MOCK_WORKSHOP_CRD["spec"], "owner": owner},
    }


@pytest.fixture
def bob_client(_mock_k8s_startup):
    """Test client authenticated as bob — a different user from alice."""
    from main import app

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        email="bob@test.example.com", is_admin=False
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def admin_client(_mock_k8s_startup):
    """Test client authenticated as an admin."""
    from main import app

    app.dependency_overrides[get_current_user] = lambda: TEST_ADMIN
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


# ── Ownership isolation ───────────────────────────────────────────────────────

class TestOwnershipIsolation:
    def test_get_own_workshop_succeeds(self, client, mock_k8s_client):
        """Owner can GET their own workshop."""
        mock_k8s_client.get_namespaced_custom_object.return_value = (
            _workshop_for("alice@test.example.com")
        )
        response = client.get("/workshops/test-workshop")
        assert response.status_code == 200
        assert response.json()["owner"] == "alice@test.example.com"

    def test_get_other_users_workshop_returns_404(self, bob_client, mock_k8s_client):
        """Bob cannot see alice's workshop — 404, no existence leak."""
        mock_k8s_client.get_namespaced_custom_object.return_value = (
            _workshop_for("alice@test.example.com")
        )
        response = bob_client.get("/workshops/test-workshop")
        assert response.status_code == 404

    def test_delete_own_workshop_succeeds(self, client, mock_k8s_client):
        """Owner can delete their own workshop."""
        mock_k8s_client.get_namespaced_custom_object.return_value = (
            _workshop_for("alice@test.example.com")
        )
        mock_k8s_client.delete_namespaced_custom_object.return_value = {}
        response = client.delete("/workshops/test-workshop")
        assert response.status_code == 204

    def test_delete_other_users_workshop_returns_404(self, bob_client, mock_k8s_client):
        """Bob cannot delete alice's workshop."""
        mock_k8s_client.get_namespaced_custom_object.return_value = (
            _workshop_for("alice@test.example.com")
        )
        response = bob_client.delete("/workshops/test-workshop")
        assert response.status_code == 404
        # Ensure k8s delete was never called
        mock_k8s_client.delete_namespaced_custom_object.assert_not_called()

    def test_list_shows_only_owner_workshops(self, client, mock_k8s_client):
        """list_workshops passes the owner's email as a label selector filter."""
        mock_k8s_client.list_namespaced_custom_object.return_value = {"items": []}
        client.get("/workshops/")

        call_kwargs = mock_k8s_client.list_namespaced_custom_object.call_args.kwargs
        # The label_selector must include the owner-hash label
        assert "orchestra.io/owner-hash" in call_kwargs.get("label_selector", "")

    def test_status_for_other_users_workshop_returns_404(
        self, bob_client, mock_k8s_client
    ):
        """GET /workshops/{name}/status returns 404 for another user's workshop."""
        mock_k8s_client.get_namespaced_custom_object.return_value = (
            _workshop_for("alice@test.example.com")
        )
        response = bob_client.get("/workshops/test-workshop/status")
        assert response.status_code == 404


# ── Admin bypass ─────────────────────────────────────────────────────────────

class TestAdminBypass:
    def test_admin_can_get_any_workshop(self, admin_client, mock_k8s_client):
        """Admin can GET a workshop belonging to any user."""
        mock_k8s_client.get_namespaced_custom_object.return_value = (
            _workshop_for("alice@test.example.com")
        )
        response = admin_client.get("/workshops/test-workshop")
        assert response.status_code == 200

    def test_admin_list_uses_no_owner_filter(self, admin_client, mock_k8s_client):
        """Admin's list request does NOT filter by owner-hash."""
        mock_k8s_client.list_namespaced_custom_object.return_value = {"items": []}
        admin_client.get("/workshops/")

        call_kwargs = mock_k8s_client.list_namespaced_custom_object.call_args.kwargs
        label_selector = call_kwargs.get("label_selector") or ""
        assert "orchestra.io/owner-hash" not in label_selector

    def test_admin_can_delete_any_workshop(self, admin_client, mock_k8s_client):
        """Admin can delete a workshop belonging to any user."""
        mock_k8s_client.get_namespaced_custom_object.return_value = (
            _workshop_for("alice@test.example.com")
        )
        mock_k8s_client.delete_namespaced_custom_object.return_value = {}
        response = admin_client.delete("/workshops/test-workshop")
        assert response.status_code == 204


# ── Unauthenticated requests ──────────────────────────────────────────────────

class TestUnauthenticatedWorkshopRequests:
    """Verify workshop routes reject requests with no identity."""

    @pytest.fixture
    def anon_client(self, _mock_k8s_startup):
        """Client with NO dependency override and require_authentication=True."""
        from main import app

        app.dependency_overrides.pop(get_current_user, None)
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
        app.dependency_overrides.pop(get_current_user, None)

    def test_list_without_auth_returns_401(self, anon_client):
        response = anon_client.get("/workshops/")
        assert response.status_code == 401

    def test_create_without_auth_returns_401(self, anon_client):
        response = anon_client.post("/workshops/", json={"name": "test"})
        assert response.status_code == 401

    def test_get_without_auth_returns_401(self, anon_client):
        response = anon_client.get("/workshops/anything")
        assert response.status_code == 401
