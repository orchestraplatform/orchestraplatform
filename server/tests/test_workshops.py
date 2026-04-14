"""Test workshop API endpoints."""

from unittest.mock import Mock
import pytest


def test_list_workshops_empty(client, mock_k8s_client):
    """Test listing workshops when none exist."""
    # Mock empty response from Kubernetes
    mock_k8s_client.list_namespaced_custom_object.return_value = {"items": []}
    
    response = client.get("/api/v1/workshops/")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


def test_create_workshop(client, mock_k8s_client):
    """Test creating a workshop."""
    # Mock successful creation
    mock_workshop = {
        "apiVersion": "orchestra.io/v1",
        "kind": "Workshop",
        "metadata": {"name": "test-workshop", "namespace": "default"},
        "spec": {"name": "test-workshop", "duration": "4h"},
        "status": {}
    }
    mock_k8s_client.create_namespaced_custom_object.return_value = mock_workshop
    
    workshop_data = {
        "name": "test-workshop",
        "duration": "4h",
        "image": "rocker/rstudio:latest"
    }
    
    response = client.post("/api/v1/workshops/", json=workshop_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test-workshop"
    assert data["namespace"] == "default"


def test_get_workshop_not_found(client, mock_k8s_client):
    """Test getting a workshop that doesn't exist."""
    from kubernetes.client.rest import ApiException
    
    # Mock 404 response
    mock_k8s_client.get_namespaced_custom_object.side_effect = ApiException(status=404)
    
    response = client.get("/api/v1/workshops/nonexistent")
    assert response.status_code == 404


def test_delete_workshop(client, mock_k8s_client):
    """Test deleting a workshop."""
    # Mock successful deletion
    mock_k8s_client.delete_namespaced_custom_object.return_value = {}
    
    response = client.delete("/api/v1/workshops/test-workshop")
    assert response.status_code == 204
