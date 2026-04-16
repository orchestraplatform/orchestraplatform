"""
Integration test fixtures.

These tests require:
  - A running kind cluster with the orchestra-crds chart installed
  - The Orchestra API running against that cluster
  - An oauth2-proxy and mock OIDC provider (Dex) wired in front of the API

Run with: just test-integration
Skip by default: marked with @pytest.mark.integration

To set up locally:
  kind create cluster
  helm install orchestra-crds deploy/charts/orchestra-crds
  just test-integration
"""

import os

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: integration tests requiring a live kind cluster (skipped by default)",
    )


@pytest.fixture(scope="session", autouse=True)
def skip_without_integration_flag():
    """Skip all integration tests unless ORCHESTRA_INTEGRATION_TESTS=1 is set."""
    if not os.environ.get("ORCHESTRA_INTEGRATION_TESTS"):
        pytest.skip(
            "Integration tests skipped. "
            "Set ORCHESTRA_INTEGRATION_TESTS=1 and ensure a kind cluster is running."
        )


# TODO: add fixtures here as integration tests are fleshed out:
#
# @pytest.fixture(scope="session")
# def kind_cluster():
#     """Ensure a kind cluster is available with the orchestra CRDs installed."""
#     subprocess.run(["kind", "create", "cluster", "--name", "orchestra-test"], check=True)
#     subprocess.run(["helm", "install", "orchestra-crds", "deploy/charts/orchestra-crds"], check=True)
#     yield
#     subprocess.run(["kind", "delete", "cluster", "--name", "orchestra-test"], check=True)
#
# @pytest.fixture(scope="session")
# def api_url(kind_cluster):
#     """URL of the Orchestra API server running against the kind cluster."""
#     return os.environ.get("ORCHESTRA_API_URL", "http://localhost:8000")
#
# @pytest.fixture
# def auth_headers_alice():
#     """Headers that simulate alice authenticated via oauth2-proxy."""
#     return {"X-Auth-Request-Email": "alice@test.example.com"}
