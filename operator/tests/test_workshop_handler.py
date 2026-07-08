"""Tests for the reconcile glue: the create handler driven through the
OperatorCluster seam with a fake adapter."""

import kopf
import pytest
from fakes import FakeOperatorCluster

from handlers.cleanup import workshop_expiration_timer
from handlers.workshop import workshop_create_handler


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
