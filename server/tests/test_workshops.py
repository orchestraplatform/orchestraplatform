"""Test workshop API endpoints."""

from tests.conftest import MOCK_WORKSHOP_CRD


# ── CRUD happy paths ──────────────────────────────────────────────────────────

def test_list_workshops_empty(client, mock_k8s_client):
    """Test listing workshops when none exist."""
    mock_k8s_client.list_namespaced_custom_object.return_value = {"items": []}

    response = client.get("/workshops/")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


def test_create_workshop(client, mock_k8s_client):
    """Test creating a workshop."""
    mock_k8s_client.create_namespaced_custom_object.return_value = MOCK_WORKSHOP_CRD

    workshop_data = {
        "name": "test-workshop",
        "duration": "4h",
        "image": "rocker/rstudio:latest",
    }

    response = client.post("/workshops/", json=workshop_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test-workshop"
    assert data["namespace"] == "default"
    assert data["owner"] == "alice@test.example.com"


def test_get_workshop_not_found(client, mock_k8s_client):
    """Test getting a workshop that doesn't exist."""
    from kubernetes.client.rest import ApiException

    mock_k8s_client.get_namespaced_custom_object.side_effect = ApiException(status=404)

    response = client.get("/workshops/nonexistent")
    assert response.status_code == 404


def test_get_workshop_owned_by_other_user_returns_404(client, mock_k8s_client):
    """A workshop owned by another user must appear as 404 (no existence leak)."""
    other_workshop = {
        **MOCK_WORKSHOP_CRD,
        "spec": {**MOCK_WORKSHOP_CRD["spec"], "owner": "bob@test.example.com"},
    }
    mock_k8s_client.get_namespaced_custom_object.return_value = other_workshop

    response = client.get("/workshops/test-workshop")
    assert response.status_code == 404


def test_delete_workshop(client, mock_k8s_client):
    """Test deleting a workshop owned by the current user."""
    mock_k8s_client.get_namespaced_custom_object.return_value = MOCK_WORKSHOP_CRD
    mock_k8s_client.delete_namespaced_custom_object.return_value = {}

    response = client.delete("/workshops/test-workshop")
    assert response.status_code == 204


def test_delete_workshop_owned_by_other_user_returns_404(client, mock_k8s_client):
    """Deleting another user's workshop must return 404."""
    other_workshop = {
        **MOCK_WORKSHOP_CRD,
        "spec": {**MOCK_WORKSHOP_CRD["spec"], "owner": "bob@test.example.com"},
    }
    mock_k8s_client.get_namespaced_custom_object.return_value = other_workshop

    response = client.delete("/workshops/test-workshop")
    assert response.status_code == 404


# ── Status endpoint ───────────────────────────────────────────────────────────

def test_get_workshop_status(client, mock_k8s_client):
    """GET /workshops/{name}/status returns status dict for owned workshop."""
    workshop_with_status = {
        **MOCK_WORKSHOP_CRD,
        "status": {
            "phase": "Ready",
            "url": "https://ws-123.orchestra.localhost",
        },
    }
    mock_k8s_client.get_namespaced_custom_object.return_value = workshop_with_status

    response = client.get("/workshops/test-workshop/status")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-workshop"
    assert data["owner"] == "alice@test.example.com"
    assert data["url"] == "https://ws-123.orchestra.localhost"


def test_get_workshop_status_not_found(client, mock_k8s_client):
    """GET /workshops/{name}/status returns 404 for nonexistent workshop."""
    from kubernetes.client.rest import ApiException

    mock_k8s_client.get_namespaced_custom_object.side_effect = ApiException(status=404)

    response = client.get("/workshops/nonexistent/status")
    assert response.status_code == 404


# ── Validation ────────────────────────────────────────────────────────────────

class TestWorkshopNameValidation:
    def test_invalid_name_uppercase_rejected(self, client):
        """Names with uppercase letters are rejected."""
        response = client.post("/workshops/", json={"name": "MyWorkshop"})
        assert response.status_code == 422

    def test_invalid_name_leading_dash_rejected(self, client):
        """Names starting with a dash are rejected."""
        response = client.post("/workshops/", json={"name": "-workshop"})
        assert response.status_code == 422

    def test_invalid_name_trailing_dash_rejected(self, client):
        """Names ending with a dash are rejected."""
        response = client.post("/workshops/", json={"name": "workshop-"})
        assert response.status_code == 422

    def test_invalid_name_too_long_rejected(self, client):
        """Names exceeding 253 characters are rejected."""
        long_name = "a" * 254
        response = client.post("/workshops/", json={"name": long_name})
        assert response.status_code == 422

    def test_valid_name_with_dashes_accepted(self, client, mock_k8s_client):
        """Names with lowercase letters, digits and dashes are accepted."""
        mock_k8s_client.create_namespaced_custom_object.return_value = {
            **MOCK_WORKSHOP_CRD,
            "metadata": {**MOCK_WORKSHOP_CRD["metadata"], "name": "my-workshop-01"},
            "spec": {**MOCK_WORKSHOP_CRD["spec"], "name": "my-workshop-01"},
        }
        response = client.post("/workshops/", json={"name": "my-workshop-01"})
        assert response.status_code == 201


# ── Pagination ────────────────────────────────────────────────────────────────

class TestPagination:
    def _make_workshop(self, name: str) -> dict:
        return {
            **MOCK_WORKSHOP_CRD,
            "metadata": {**MOCK_WORKSHOP_CRD["metadata"], "name": name},
            "spec": {**MOCK_WORKSHOP_CRD["spec"], "name": name},
        }

    def test_pagination_first_page(self, client, mock_k8s_client):
        """First page returns first `size` items."""
        items = [self._make_workshop(f"ws-{i:02d}") for i in range(10)]
        mock_k8s_client.list_namespaced_custom_object.return_value = {"items": items}

        response = client.get("/workshops/?page=1&size=3")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert len(data["items"]) == 3
        assert data["page"] == 1

    def test_pagination_second_page(self, client, mock_k8s_client):
        """Second page returns the next `size` items."""
        items = [self._make_workshop(f"ws-{i:02d}") for i in range(10)]
        mock_k8s_client.list_namespaced_custom_object.return_value = {"items": items}

        response = client.get("/workshops/?page=2&size=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["page"] == 2

    def test_pagination_last_partial_page(self, client, mock_k8s_client):
        """Last page returns remaining items even if fewer than `size`."""
        items = [self._make_workshop(f"ws-{i:02d}") for i in range(10)]
        mock_k8s_client.list_namespaced_custom_object.return_value = {"items": items}

        response = client.get("/workshops/?page=4&size=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1  # item 10 of 10

    def test_size_over_100_rejected(self, client):
        """size > 100 is rejected by query validation."""
        response = client.get("/workshops/?size=101")
        assert response.status_code == 422
