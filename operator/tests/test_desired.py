"""Tests for the pure desired-state module: names, labels, owner references,
and conditional children — no cluster involved."""

import pytest

from resources.desired import (
    desired_children,
    failed_status,
    ready_status,
    starting_status,
)
from resources.naming import (
    auth_middleware_name,
    deployment_name,
    ingress_name,
    pvc_name,
    service_name,
)


@pytest.fixture(autouse=True)
def clear_settings_cache():
    from config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


META = {
    "name": "rstudio-abc123",
    "uid": "11111111-2222-3333-4444-555555555555",
    "creationTimestamp": "2026-07-08T12:00:00Z",
}


def _spec(**overrides):
    spec = {
        "name": "rstudio-abc123",
        "owner": "alice@example.com",
        "duration": "2h",
        "image": "rocker/rstudio:4.4",
        "port": 8787,
    }
    spec.update(overrides)
    return spec


def test_all_children_named_and_owner_referenced():
    children = desired_children(_spec(storage={"size": "10Gi"}), META, "default")

    assert children.workshop_name == "rstudio-abc123"
    assert children.deployment.metadata.name == deployment_name("rstudio-abc123")
    assert children.service.metadata.name == service_name("rstudio-abc123")
    assert children.ingress["metadata"]["name"] == ingress_name("rstudio-abc123")
    assert children.pvc.metadata.name == pvc_name("rstudio-abc123")

    for typed in (children.pvc, children.deployment, children.service):
        (ref,) = typed.metadata.owner_references
        assert ref.kind == "Workshop"
        assert ref.name == META["name"]
        assert ref.uid == META["uid"]
        assert ref.controller is True

    (ref_dict,) = children.ingress["metadata"]["ownerReferences"]
    assert ref_dict["kind"] == "Workshop"
    assert ref_dict["uid"] == META["uid"]


def test_pvc_only_when_storage_requested():
    children = desired_children(_spec(), META, "default")
    assert children.pvc is None
    assert children.deployment.spec.template.spec.volumes is None


def test_middleware_only_when_oauth2_proxy_configured(monkeypatch):
    from config import get_settings

    children = desired_children(_spec(), META, "default")
    assert children.middleware is None

    monkeypatch.setenv(
        "ORCHESTRA_OAUTH2_PROXY_AUTH_URL", "http://oauth2-proxy/oauth2/auth"
    )
    get_settings.cache_clear()
    children = desired_children(_spec(), META, "default")
    assert children.middleware is not None
    assert children.middleware["metadata"]["name"] == auth_middleware_name(
        "rstudio-abc123"
    )
    assert children.middleware["metadata"]["ownerReferences"]
    # The ingress must route through the per-workshop middleware
    (route,) = children.ingress["spec"]["routes"]
    assert {"name": auth_middleware_name("rstudio-abc123")} in route["middlewares"]


def test_owner_email_dual_field_read():
    children = desired_children(
        _spec(ownerEmail="new@example.com", owner=None), META, "default"
    )
    env = {
        e.name: e.value
        for e in children.deployment.spec.template.spec.containers[1].env
    }
    assert env["ORCHESTRA_OWNER_EMAIL"] == "new@example.com"


def test_url_derivation_follows_entry_points(monkeypatch):
    from config import get_settings

    monkeypatch.setenv("ORCHESTRA_INGRESS_ENTRY_POINTS", '["web"]')
    monkeypatch.setenv("ORCHESTRA_INGRESS_PORT", "30080")
    get_settings.cache_clear()
    children = desired_children(_spec(), META, "default")
    assert children.url.startswith("http://rstudio-abc123.")
    assert children.url.endswith(":30080")

    monkeypatch.setenv("ORCHESTRA_INGRESS_ENTRY_POINTS", '["websecure"]')
    monkeypatch.delenv("ORCHESTRA_INGRESS_PORT")
    get_settings.cache_clear()
    children = desired_children(_spec(), META, "default")
    assert children.url.startswith("https://rstudio-abc123.")


def test_status_builders():
    assert starting_status()["phase"] == "Starting"

    children = desired_children(_spec(), META, "default")
    ready = ready_status(children.url, META["creationTimestamp"], children.expires_at)
    assert ready["phase"] == "Ready"
    assert ready["url"] == children.url
    assert ready["expiresAt"] == children.expires_at.isoformat()
    assert ready["conditions"][0]["status"] == "True"

    failed = failed_status("boom")
    assert failed["phase"] == "Failed"
    assert failed["conditions"][0]["message"] == "boom"
