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
    owner_hash,
    pvc_name,
    service_name,
    workspace_pvc_name,
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


def _persist_spec(**overrides):
    return _spec(
        templateSlug="rstudio",
        storage={"size": "10Gi", "workspace": {"persist": "per-user"}},
        **overrides,
    )


def test_persistent_workspace_pvc_is_unowned_and_keyed_by_slug_and_owner():
    children = desired_children(_persist_spec(), META, "default")
    expected = workspace_pvc_name("rstudio", "alice@example.com")

    assert children.pvc.metadata.name == expected
    assert expected == f"ws-rstudio-{owner_hash('alice@example.com')}"
    # The ADR-0010 invariant: NO owner-reference, so Kubernetes GC must NOT
    # delete the workspace with the Workshop CR.
    assert children.pvc.metadata.owner_references is None
    # Reaper keys (#87): sweep selector + idle clock, stamped from day one.
    labels = children.pvc.metadata.labels
    assert labels["component"] == "workspace"
    assert labels["orchestra.io/template-slug"] == "rstudio"
    assert labels["orchestra.io/owner-hash"] == owner_hash("alice@example.com")
    assert children.pvc.metadata.annotations["orchestra.io/last-used"]
    # RWO pd-style disk, not an fs share.
    assert children.pvc.spec.access_modes == ["ReadWriteOnce"]


def test_persistent_workspace_mounted_at_data():
    children = desired_children(_persist_spec(), META, "default")
    pod = children.deployment.spec.template.spec

    (volume,) = pod.volumes
    assert volume.persistent_volume_claim.claim_name == children.pvc.metadata.name
    (mount,) = pod.containers[0].volume_mounts
    assert mount.mount_path == "/data"


def test_persistent_workspace_reattaches_across_relaunches():
    """Two launches of the same template by the same owner (different instance
    names/UIDs) must resolve to the SAME PVC — that is the reattach."""
    first = desired_children(_persist_spec(name="rstudio-abc123"), META, "default")
    second_meta = {**META, "name": "rstudio-xyz789", "uid": "6666-7777"}
    second = desired_children(
        _persist_spec(name="rstudio-xyz789"), second_meta, "default"
    )

    assert first.pvc.metadata.name == second.pvc.metadata.name
    assert (
        second.deployment.spec.template.spec.volumes[0].persistent_volume_claim.claim_name
        == first.pvc.metadata.name
    )


def test_persistent_workspace_is_per_owner():
    alice = desired_children(_persist_spec(), META, "default")
    bob = desired_children(_persist_spec(owner="bob@example.com"), META, "default")
    assert alice.pvc.metadata.name != bob.pvc.metadata.name


def test_persistent_workspace_falls_back_to_instance_name_without_slug():
    """A hand-authored CR without templateSlug still persists (keyed by the
    instance name — no cross-relaunch reattach, but never a crash)."""
    spec = _spec(storage={"workspace": {"persist": "per-user"}})
    children = desired_children(spec, META, "default")
    assert children.pvc.metadata.name == workspace_pvc_name(
        "rstudio-abc123", "alice@example.com"
    )
    assert children.pvc.metadata.owner_references is None


def test_ephemeral_storage_stays_owner_referenced():
    """Without a persist declaration the PVC contract is unchanged: per-instance
    name, owner-referenced, GC'd with the Workshop CR."""
    children = desired_children(_spec(storage={"size": "10Gi"}), META, "default")
    assert children.pvc.metadata.name == pvc_name("rstudio-abc123")
    (ref,) = children.pvc.metadata.owner_references
    assert ref.uid == META["uid"]


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


def test_owner_email_from_spec_owner():
    children = desired_children(_spec(owner="new@example.com"), META, "default")
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
