"""
Integration tests: full workshop lifecycle against a real kind cluster.

These tests are skipped by default. See conftest.py for setup instructions.
"""

import pytest

pytestmark = pytest.mark.integration


# TODO: implement once kind cluster + mock OIDC fixtures are in place.
#
# async def test_create_workshop_stamps_owner(api_url, auth_headers_alice):
#     """POST /workshops creates a CR with spec.owner = alice's email."""
#     import httpx
#     async with httpx.AsyncClient() as client:
#         response = await client.post(
#             f"{api_url}/workshops/",
#             json={"name": "integration-test-ws"},
#             headers=auth_headers_alice,
#         )
#     assert response.status_code == 201
#     assert response.json()["owner"] == "alice@test.example.com"
#
#
# async def test_ownership_isolation(api_url, auth_headers_alice, auth_headers_bob):
#     """Alice's workshop is invisible to Bob."""
#     ...
#
#
# async def test_trust_boundary_forged_header_rejected(api_url):
#     """X-Auth-Request-Email sent directly (not through proxy) is rejected."""
#     import httpx
#     async with httpx.AsyncClient() as client:
#         # Simulate attacker sending the header directly to the API
#         # In production the ingress strips this header before it reaches the API.
#         # This test verifies the header-stripping Middleware is in place by
#         # checking that a direct call without a proxy session cookie returns 401.
#         response = await client.get(
#             f"{api_url}/workshops/",
#             headers={"X-Auth-Request-Email": "admin@example.com"},
#         )
#     assert response.status_code == 401
