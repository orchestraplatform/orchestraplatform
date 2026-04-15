"""Test workshop API endpoints."""

from tests.conftest import MOCK_WORKSHOP_CRD


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
