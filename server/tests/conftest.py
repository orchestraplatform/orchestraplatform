"""Test configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_k8s_client():
    """Mock Kubernetes client for testing."""
    with patch('api.core.kubernetes.get_custom_objects_api') as mock:
        mock_api = Mock()
        mock.return_value = mock_api
        yield mock_api
