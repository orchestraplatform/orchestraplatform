"""Tests for the read-only, registry-backed template routes (ADR-0006).

Templates are git-managed YAML served from the in-memory registry; there are no
create/update/delete endpoints. These tests wire a registry of known templates
into the app and exercise list / get / launch.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from api.core.auth import CurrentUser, get_current_user
from api.core.database import get_db
from api.models.schemas.workshop_instance import WorkshopInstanceResponse
from api.models.schemas.workshop_template import WorkshopTemplateResponse
from api.models.workshop import WorkshopResources
from api.routes.templates import get_template_reader
from api.services.template_registry import TemplateRegistry, stable_template_id
from api.services.workshop_instance_service import get_instance_service

NOW = datetime.now(UTC)


def _template(slug: str, *, enabled: bool = True) -> WorkshopTemplateResponse:
    return WorkshopTemplateResponse(
        id=stable_template_id(slug),
        name=slug.title(),
        slug=slug,
        image=f"example/{slug}:latest",
        defaultDuration="4h",
        port=8787,
        tier="small",
        resources=WorkshopResources(),
        isActive=enabled,
        createdBy="git",
        createdAt=NOW,
        updatedAt=NOW,
    )


_REGISTRY = TemplateRegistry(
    [_template("rstudio"), _template("jupyter", enabled=False)]
)


@pytest.fixture
def client(_mock_k8s_startup):
    from main import app

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        email="alice@test.example.com", is_admin=False
    )
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    app.dependency_overrides[get_template_reader] = lambda: _REGISTRY
    with TestClient(app) as c:
        yield c
    for dep in (get_current_user, get_db, get_template_reader):
        app.dependency_overrides.pop(dep, None)


class TestListAndGet:
    def test_list_returns_active_only_for_user(self, client):
        resp = client.get("/templates/")
        assert resp.status_code == 200
        slugs = [t["slug"] for t in resp.json()["items"]]
        assert slugs == ["rstudio"]  # jupyter is disabled

    def test_get_by_id_found(self, client):
        resp = client.get(f"/templates/{stable_template_id('rstudio')}")
        assert resp.status_code == 200
        assert resp.json()["slug"] == "rstudio"
        assert resp.json()["tier"] == "small"

    def test_get_unknown_id_404(self, client):
        resp = client.get(f"/templates/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestImperativeEndpointsRemoved:
    def test_create_is_gone(self, client):
        # POST /templates/ no longer exists -> 405 Method Not Allowed.
        resp = client.post("/templates/", json={"name": "x", "slug": "x"})
        assert resp.status_code == 405

    def test_delete_is_gone(self, client):
        resp = client.delete(f"/templates/{stable_template_id('rstudio')}")
        assert resp.status_code == 405


class TestLaunch:
    def test_launch_active_template(self, client):
        from main import app

        instance = WorkshopInstanceResponse(
            id=uuid.uuid4(),
            workshopId=stable_template_id("rstudio"),
            workshopName="Rstudio",
            templateSlug="rstudio",
            k8sName="rstudio-abc123",
            namespace="default",
            ownerEmail="alice@test.example.com",
            phase="Pending",
            durationRequested="4h",
            launchedAt=NOW,
            createdAt=NOW,
            updatedAt=NOW,
        )
        svc = AsyncMock()
        svc.launch = AsyncMock(return_value=instance)
        app.dependency_overrides[get_instance_service] = lambda: svc
        try:
            resp = client.post(
                f"/templates/{stable_template_id('rstudio')}/launch", json={}
            )
            assert resp.status_code == 201
            assert resp.json()["templateSlug"] == "rstudio"
        finally:
            app.dependency_overrides.pop(get_instance_service, None)

    def test_launch_disabled_template_404(self, client):
        resp = client.post(
            f"/templates/{stable_template_id('jupyter')}/launch", json={}
        )
        assert resp.status_code == 404
