"""Tests for workshop template API endpoints (/workshops/)."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from api.models.schemas.workshop_template import (
    WorkshopResourceDefaults,
    WorkshopTemplateResponse,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

TEMPLATE_ID = uuid.uuid4()
NOW = datetime.now(timezone.utc)

MOCK_TEMPLATE = WorkshopTemplateResponse(
    id=TEMPLATE_ID,
    name="Standard RStudio",
    slug="rstudio",
    description="Default RStudio environment",
    image="rocker/rstudio:latest",
    defaultDuration="4h",
    resources=WorkshopResourceDefaults(),
    storage=None,
    isActive=True,
    createdBy="admin@test.example.com",
    createdAt=NOW,
    updatedAt=NOW,
)


def _patch_template_svc(**overrides):
    """Return a context-manager that patches WorkshopTemplateService methods."""
    defaults = {
        "list_templates": AsyncMock(return_value=([MOCK_TEMPLATE], 1)),
        "get_template": AsyncMock(return_value=MOCK_TEMPLATE),
        "get_template_by_slug": AsyncMock(return_value=None),
        "create_template": AsyncMock(return_value=MOCK_TEMPLATE),
        "update_template": AsyncMock(return_value=MOCK_TEMPLATE),
        "archive_template": AsyncMock(return_value=True),
    }
    defaults.update(overrides)
    return patch.multiple(
        "api.routes.workshops.template_service", **defaults
    )


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_templates_returns_200(client):
    with _patch_template_svc():
        response = client.get("/workshops/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "rstudio"


def test_list_templates_empty(client):
    with _patch_template_svc(list_templates=AsyncMock(return_value=([], 0))):
        response = client.get("/workshops/")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_list_without_auth_returns_401(client):
    """Unauthenticated requests are rejected before reaching the service."""
    from main import app
    from api.core.auth import get_current_user
    from fastapi import HTTPException

    app.dependency_overrides[get_current_user] = lambda: (_ for _ in ()).throw(
        HTTPException(status_code=401)
    )
    try:
        response = client.get("/workshops/")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ── Create (admin only) ───────────────────────────────────────────────────────

def test_create_template_as_admin_returns_201(admin_client):
    payload = {
        "name": "Standard RStudio",
        "slug": "rstudio",
        "image": "rocker/rstudio:latest",
        "defaultDuration": "4h",
        "resources": {},
    }
    with _patch_template_svc():
        response = admin_client.post("/workshops/", json=payload)
    assert response.status_code == 201
    assert response.json()["slug"] == "rstudio"


def test_create_template_as_non_admin_returns_403(client):
    payload = {"name": "Test", "slug": "test", "image": "img:latest"}
    with _patch_template_svc():
        response = client.post("/workshops/", json=payload)
    assert response.status_code == 403


def test_create_template_duplicate_slug_returns_409(admin_client):
    with _patch_template_svc(
        get_template_by_slug=AsyncMock(return_value=MOCK_TEMPLATE)
    ):
        response = admin_client.post(
            "/workshops/",
            json={"name": "Dupe", "slug": "rstudio", "image": "img:latest"},
        )
    assert response.status_code == 409


# ── Slug validation ───────────────────────────────────────────────────────────

class TestTemplateSlugValidation:
    def test_uppercase_slug_rejected(self, admin_client):
        response = admin_client.post(
            "/workshops/", json={"name": "X", "slug": "MySlug", "image": "img:latest"}
        )
        assert response.status_code == 422

    def test_leading_dash_slug_rejected(self, admin_client):
        response = admin_client.post(
            "/workshops/", json={"name": "X", "slug": "-bad", "image": "img:latest"}
        )
        assert response.status_code == 422

    def test_trailing_dash_slug_rejected(self, admin_client):
        response = admin_client.post(
            "/workshops/", json={"name": "X", "slug": "bad-", "image": "img:latest"}
        )
        assert response.status_code == 422

    def test_slug_over_40_chars_rejected(self, admin_client):
        long_slug = "a" * 41
        response = admin_client.post(
            "/workshops/", json={"name": "X", "slug": long_slug, "image": "img:latest"}
        )
        assert response.status_code == 422

    def test_valid_slug_accepted(self, admin_client):
        with _patch_template_svc():
            response = admin_client.post(
                "/workshops/",
                json={"name": "Valid", "slug": "my-rstudio-01", "image": "img:latest"},
            )
        assert response.status_code == 201


# ── Get ───────────────────────────────────────────────────────────────────────

def test_get_template_returns_200(client):
    with _patch_template_svc():
        response = client.get(f"/workshops/{TEMPLATE_ID}")
    assert response.status_code == 200
    assert response.json()["id"] == str(TEMPLATE_ID)


def test_get_template_not_found_returns_404(client):
    with _patch_template_svc(get_template=AsyncMock(return_value=None)):
        response = client.get(f"/workshops/{uuid.uuid4()}")
    assert response.status_code == 404


# ── Update (admin only) ───────────────────────────────────────────────────────

def test_update_template_as_admin_returns_200(admin_client):
    with _patch_template_svc():
        response = admin_client.put(
            f"/workshops/{TEMPLATE_ID}", json={"name": "Renamed"}
        )
    assert response.status_code == 200


def test_update_template_as_non_admin_returns_403(client):
    with _patch_template_svc():
        response = client.put(f"/workshops/{TEMPLATE_ID}", json={"name": "X"})
    assert response.status_code == 403


# ── Archive (admin only) ──────────────────────────────────────────────────────

def test_archive_template_as_admin_returns_204(admin_client):
    with _patch_template_svc():
        response = admin_client.delete(f"/workshops/{TEMPLATE_ID}")
    assert response.status_code == 204


def test_archive_template_as_non_admin_returns_403(client):
    with _patch_template_svc():
        response = client.delete(f"/workshops/{TEMPLATE_ID}")
    assert response.status_code == 403


def test_archive_template_not_found_returns_404(admin_client):
    with _patch_template_svc(archive_template=AsyncMock(return_value=False)):
        response = admin_client.delete(f"/workshops/{uuid.uuid4()}")
    assert response.status_code == 404


# ── Pagination ────────────────────────────────────────────────────────────────

class TestPagination:
    def _make_templates(self, n: int) -> list[WorkshopTemplateResponse]:
        return [
            WorkshopTemplateResponse(
                id=uuid.uuid4(),
                name=f"Template {i}",
                slug=f"tmpl-{i:02d}",
                description=None,
                image="rocker/rstudio:latest",
                defaultDuration="4h",
                resources=WorkshopResourceDefaults(),
                storage=None,
                isActive=True,
                createdBy="admin@test.example.com",
                createdAt=NOW,
                updatedAt=NOW,
            )
            for i in range(n)
        ]

    def test_size_over_100_rejected(self, client):
        response = client.get("/workshops/?size=101")
        assert response.status_code == 422

    def test_pagination_params_forwarded(self, client):
        templates = self._make_templates(10)
        page3 = templates[6:9]
        with _patch_template_svc(
            list_templates=AsyncMock(return_value=(page3, 10))
        ):
            response = client.get("/workshops/?page=3&size=3")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert data["page"] == 3
        assert len(data["items"]) == 3
