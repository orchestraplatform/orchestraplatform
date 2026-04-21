"""Tests for workshop handler helpers, specifically deployment readiness polling."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from kubernetes.client.rest import ApiException

from handlers.workshop import _wait_for_deployment_ready


def _make_deployment(available_replicas: int | None) -> MagicMock:
    """Return a mock V1Deployment with the given available_replicas."""
    dep = MagicMock()
    dep.status.available_replicas = available_replicas
    return dep


class TestWaitForDeploymentReady:
    async def test_returns_true_when_immediately_ready(self):
        """If the deployment already has a replica available, return True right away."""
        mock_api = MagicMock()
        mock_api.read_namespaced_deployment.return_value = _make_deployment(1)

        result = await _wait_for_deployment_ready(
            mock_api, "ws-deployment", "default", timeout=10, poll_interval=1
        )
        assert result is True

    async def test_returns_true_after_one_retry(self):
        """First call returns 0 replicas, second returns 1."""
        mock_api = MagicMock()
        mock_api.read_namespaced_deployment.side_effect = [
            _make_deployment(0),
            _make_deployment(1),
        ]

        result = await _wait_for_deployment_ready(
            mock_api, "ws-deployment", "default", timeout=10, poll_interval=0
        )
        assert result is True
        assert mock_api.read_namespaced_deployment.call_count == 2

    async def test_returns_false_on_timeout(self):
        """Deployment never becomes ready; function returns False after timeout."""
        mock_api = MagicMock()
        mock_api.read_namespaced_deployment.return_value = _make_deployment(0)

        result = await _wait_for_deployment_ready(
            mock_api, "ws-deployment", "default", timeout=2, poll_interval=1
        )
        assert result is False

    async def test_api_exception_is_tolerated_and_retried(self):
        """Transient ApiException should be caught and retried."""
        api_error = ApiException(status=500, reason="Internal Server Error")
        mock_api = MagicMock()
        mock_api.read_namespaced_deployment.side_effect = [
            api_error,
            _make_deployment(1),
        ]

        result = await _wait_for_deployment_ready(
            mock_api, "ws-deployment", "default", timeout=10, poll_interval=0
        )
        assert result is True
        assert mock_api.read_namespaced_deployment.call_count == 2

    async def test_none_available_replicas_is_treated_as_zero(self):
        """None available_replicas (field absent) should not be treated as ready."""
        mock_api = MagicMock()
        mock_api.read_namespaced_deployment.side_effect = [
            _make_deployment(None),
            _make_deployment(1),
        ]

        result = await _wait_for_deployment_ready(
            mock_api, "ws-deployment", "default", timeout=10, poll_interval=0
        )
        assert result is True
        assert mock_api.read_namespaced_deployment.call_count == 2
