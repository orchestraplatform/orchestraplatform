"""Tests for the reconcile glue: the create handler driven through the
OperatorCluster seam with a fake adapter."""

from datetime import UTC, datetime, timedelta

import kopf
import kubernetes.client as k8s
import pytest
from fakes import FakeOperatorCluster

from handlers.cleanup import (
    reap_idle_workspaces,
    workshop_delete_stamps_workspace,
    workshop_expiration_timer,
)
from handlers.workshop import workshop_create_handler
from resources.naming import workspace_pvc_name
from resources.pvc import LAST_USED_ANNOTATION


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
SPEC = {"name": "rstudio-abc123", "owner": "alice@example.com", "duration": "2h"}


def _memo(cluster) -> kopf.Memo:
    memo = kopf.Memo()
    memo.cluster = cluster
    return memo


async def _run_create(cluster, patch=None):
    patch = patch if patch is not None else {}
    await workshop_create_handler(
        spec=SPEC,
        meta=META,
        patch=patch,
        namespace="default",
        name="rstudio-abc123",
        memo=_memo(cluster),
    )
    return patch


@pytest.mark.asyncio
async def test_create_applies_children_and_reports_ready():
    cluster = FakeOperatorCluster(ready=True)
    patch = await _run_create(cluster)

    (children, namespace) = cluster.applied[0]
    assert namespace == "default"
    assert children.workshop_name == "rstudio-abc123"

    status = patch["status"]
    assert status["phase"] == "Ready"
    assert status["url"] == children.url
    assert status["expiresAt"] == children.expires_at.isoformat()
    assert status["createdAt"] == META["creationTimestamp"]


@pytest.mark.asyncio
async def test_create_requeues_while_pod_not_ready():
    cluster = FakeOperatorCluster(ready=False)
    patch = {}
    with pytest.raises(kopf.TemporaryError):
        await _run_create(cluster, patch)

    assert patch["status"]["phase"] == "Starting"
    assert cluster.applied  # children were still applied before the requeue


@pytest.mark.asyncio
async def test_create_failure_marks_failed_and_is_permanent():
    cluster = FakeOperatorCluster()
    cluster.raise_on_apply = RuntimeError("quota exceeded")
    patch = {}
    with pytest.raises(kopf.PermanentError):
        await _run_create(cluster, patch)

    status = patch["status"]
    assert status["phase"] == "Failed"
    assert "quota exceeded" in status["conditions"][0]["message"]


# ---------------------------------------------------------------------------
# Expiration timer
# ---------------------------------------------------------------------------


async def _run_timer(cluster, status):
    await workshop_expiration_timer(
        spec={},
        status=status,
        namespace="default",
        name="rstudio-abc123",
        memo=_memo(cluster),
    )


@pytest.mark.asyncio
async def test_timer_deletes_expired_workshop():
    cluster = FakeOperatorCluster()
    cluster.workshops.add(("default", "rstudio-abc123"))
    await _run_timer(cluster, {"expiresAt": "2020-01-01T00:00:00+00:00"})
    assert ("default", "rstudio-abc123") in cluster.deleted


@pytest.mark.asyncio
async def test_timer_leaves_unexpired_workshop():
    cluster = FakeOperatorCluster()
    await _run_timer(cluster, {"expiresAt": "2099-01-01T00:00:00+00:00"})
    assert cluster.deleted == []


@pytest.mark.asyncio
async def test_timer_skips_when_no_expiry_set():
    cluster = FakeOperatorCluster()
    await _run_timer(cluster, {})
    assert cluster.deleted == []


@pytest.mark.asyncio
async def test_timer_tolerates_delete_failure():
    cluster = FakeOperatorCluster()
    cluster.raise_on_delete = RuntimeError("apiserver down")
    # Must not raise — the timer retries on its own 30s cadence.
    await _run_timer(cluster, {"expiresAt": "2020-01-01T00:00:00+00:00"})


# ---------------------------------------------------------------------------
# Persistent workspace reclamation (ADR-0010 decision E / #87)
# ---------------------------------------------------------------------------

WORKSPACE_SPEC = {
    **SPEC,
    "templateSlug": "rstudio",
    "storage": {"size": "10Gi", "workspace": {"persist": "per-user"}},
}


async def _run_delete(cluster, spec):
    await workshop_delete_stamps_workspace(
        spec=spec, namespace="default", name="rstudio-abc123", memo=_memo(cluster)
    )


def _ws_pvc(name, last_used_days_ago=None, namespace="default"):
    annotations = {}
    if last_used_days_ago is not None:
        stamp = datetime.now(UTC) - timedelta(days=last_used_days_ago)
        annotations[LAST_USED_ANNOTATION] = stamp.isoformat()
    return k8s.V1PersistentVolumeClaim(
        metadata=k8s.V1ObjectMeta(
            name=name,
            namespace=namespace,
            # The full label set the real adapter's WORKSPACE_PVC_SELECTOR
            # (component=workspace + orchestra.io/owner-hash) lists by.
            labels={
                "component": "workspace",
                "orchestra.io/owner-hash": "abc123def456",
            },
            annotations=annotations,
        )
    )


@pytest.mark.asyncio
async def test_delete_stamps_last_used_on_workspace_pvc():
    cluster = FakeOperatorCluster()
    await _run_delete(cluster, WORKSPACE_SPEC)
    expected = workspace_pvc_name("rstudio", "alice@example.com")
    assert cluster.stamped == [("default", expected)]


@pytest.mark.asyncio
async def test_delete_skips_stamp_for_ephemeral_storage():
    cluster = FakeOperatorCluster()
    await _run_delete(cluster, SPEC)
    assert cluster.stamped == []


@pytest.mark.asyncio
async def test_delete_stamp_failure_does_not_raise():
    class ExplodingCluster(FakeOperatorCluster):
        async def stamp_pvc_last_used(self, name, namespace):
            raise RuntimeError("apiserver down")

    # Best-effort: a failed stamp must never block Workshop deletion.
    await _run_delete(ExplodingCluster(), WORKSPACE_SPEC)


@pytest.mark.asyncio
async def test_reap_deletes_idle_unmounted_workspace():
    cluster = FakeOperatorCluster()
    cluster.pvcs[("default", "ws-idle")] = _ws_pvc("ws-idle", last_used_days_ago=45)
    await reap_idle_workspaces(cluster)
    assert cluster.deleted_pvcs == [("default", "ws-idle")]


@pytest.mark.asyncio
async def test_reap_keeps_recently_used_workspace():
    cluster = FakeOperatorCluster()
    cluster.pvcs[("default", "ws-fresh")] = _ws_pvc("ws-fresh", last_used_days_ago=1)
    await reap_idle_workspaces(cluster)
    assert cluster.deleted_pvcs == []


@pytest.mark.asyncio
async def test_reap_keeps_mounted_workspace_even_if_idle():
    cluster = FakeOperatorCluster()
    cluster.pvcs[("default", "ws-live")] = _ws_pvc("ws-live", last_used_days_ago=45)
    cluster.mounted.add(("default", "ws-live"))
    await reap_idle_workspaces(cluster)
    assert cluster.deleted_pvcs == []


@pytest.mark.asyncio
async def test_reap_keeps_workspace_without_parseable_annotation():
    cluster = FakeOperatorCluster()
    cluster.pvcs[("default", "ws-odd")] = _ws_pvc("ws-odd")  # no annotation
    await reap_idle_workspaces(cluster)
    assert cluster.deleted_pvcs == []


@pytest.mark.asyncio
async def test_reap_continues_past_a_failed_delete():
    class FlakyDeleteCluster(FakeOperatorCluster):
        async def delete_pvc(self, name, namespace):
            if name == "ws-bad":
                raise RuntimeError("apiserver down")
            await super().delete_pvc(name, namespace)

    cluster = FlakyDeleteCluster()
    cluster.pvcs[("default", "ws-bad")] = _ws_pvc("ws-bad", last_used_days_ago=45)
    cluster.pvcs[("default", "ws-idle")] = _ws_pvc("ws-idle", last_used_days_ago=45)
    await reap_idle_workspaces(cluster)
    assert ("default", "ws-idle") in cluster.deleted_pvcs


@pytest.mark.asyncio
async def test_reap_ttl_is_configurable(monkeypatch):
    monkeypatch.setenv("ORCHESTRA_WORKSPACE_IDLE_TTL_DAYS", "1")
    cluster = FakeOperatorCluster()
    cluster.pvcs[("default", "ws-2d")] = _ws_pvc("ws-2d", last_used_days_ago=2)
    await reap_idle_workspaces(cluster)
    assert cluster.deleted_pvcs == [("default", "ws-2d")]
