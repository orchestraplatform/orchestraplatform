"""Tests for WorkshopInstanceService lifecycle sync behavior."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.models.db.workshop_instance import InstanceEvent, WorkshopInstance
from api.models.schemas.workshop_template import WorkshopTemplateResponse
from api.models.workshop import WorkshopResources, WorkshopStorage
from api.services.workshop_instance_service import (
    _TRANSITIONAL_PHASES,
    WorkshopInstanceService,
)
from tests.fakes import FakeWorkshopCluster


def _instance(**overrides) -> WorkshopInstance:
    now = datetime.now(UTC)
    row = WorkshopInstance(
        id=uuid.uuid4(),
        workshop_id=uuid.uuid4(),
        template_slug="rstudio",
        template_name="Standard RStudio",
        resolved_spec={"image": "rocker/rstudio:latest", "port": 8787},
        k8s_name="rstudio-abc123",
        namespace="default",
        owner_email="alice@example.com",
        phase="Ready",
        duration_requested="4h",
        launched_at=now - timedelta(minutes=10),
        created_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(minutes=5),
    )
    row.url = "http://rstudio-abc123.orchestra.localhost:30080"
    row.expires_at = now + timedelta(hours=1)
    row.terminated_at = None
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


@pytest.mark.asyncio
async def test_sync_from_k8s_marks_missing_crd_terminated():
    service = WorkshopInstanceService(FakeWorkshopCluster())
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    row = _instance(phase="Running")

    await service._sync_from_k8s(db, row)

    assert row.phase == "Terminated"
    assert row.terminated_at is not None
    db.commit.assert_awaited_once()

    event = db.add.call_args.args[0]
    assert isinstance(event, InstanceEvent)
    assert event.phase == "Terminated"
    assert event.instance_id == row.id


@pytest.mark.parametrize("phase", sorted(_TRANSITIONAL_PHASES))
@pytest.mark.asyncio
async def test_list_instances_syncs_transitional_phases(phase: str):
    """_sync_from_k8s must be called for every phase in _TRANSITIONAL_PHASES.

    Regression test: "Starting" was missing from _TRANSITIONAL_PHASES, so
    workshops whose pods were up but not yet marked Ready were never synced
    and stayed frozen in the UI.
    """
    service = WorkshopInstanceService(FakeWorkshopCluster())
    row = _instance(phase=phase)

    total_result = MagicMock()
    total_result.scalar_one.return_value = 1
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [row]

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[total_result, rows_result])

    with patch.object(service, "_sync_from_k8s", AsyncMock()) as mock_sync:
        await service.list_instances(db, owner_email="alice@example.com")

    mock_sync.assert_awaited_once_with(db, row)


@pytest.mark.parametrize("phase", ["Ready", "Running", "Failed"])
@pytest.mark.asyncio
async def test_list_instances_does_not_sync_stable_phases(phase: str):
    """_sync_from_k8s must not be called for stable (non-transitional) phases."""
    service = WorkshopInstanceService(FakeWorkshopCluster())
    row = _instance(phase=phase)

    total_result = MagicMock()
    total_result.scalar_one.return_value = 1
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [row]

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[total_result, rows_result])

    with patch.object(service, "_sync_from_k8s", AsyncMock()) as mock_sync:
        await service.list_instances(db, owner_email="alice@example.com")

    mock_sync.assert_not_awaited()


def _template(**overrides) -> WorkshopTemplateResponse:
    now = datetime.now(UTC)
    data = {
        "id": uuid.uuid4(),
        "name": "Standard RStudio",
        "slug": "rstudio",
        "image": "rocker/rstudio:4.4",
        "defaultDuration": "4h",
        "port": 8787,
        "tier": "large",
        "env": {"DISABLE_AUTH": "false"},
        "args": ["--www-port=8787"],
        "resources": WorkshopResources(),
        "storage": WorkshopStorage(size="20Gi", storageClass="standard"),
        "tags": ["bioconductor"],
        "isActive": True,
        "createdBy": "admin@example.com",
        "createdAt": now,
        "updatedAt": now,
    }
    data.update(overrides)
    return WorkshopTemplateResponse(**data)


def _launch_db(captured: list) -> MagicMock:
    """Mock AsyncSession for launch tests: captures add()ed objects and
    simulates server-side defaults on refresh."""

    def _refresh(obj):
        if isinstance(obj, WorkshopInstance):
            now = datetime.now(UTC)
            obj.id = obj.id or uuid.uuid4()
            obj.created_at = obj.created_at or now
            obj.updated_at = obj.updated_at or now

    db = MagicMock()
    db.add = MagicMock(side_effect=captured.append)
    db.flush = AsyncMock(
        side_effect=lambda: _refresh(captured[0] if captured else None)
    )
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=_refresh)
    return db


@pytest.mark.asyncio
async def test_launch_stamps_template_spec_onto_instance():
    """launch() must denormalize the template onto the instance row so it is
    self-describing and independent of the template row (ADR-0006)."""
    cluster = FakeWorkshopCluster()
    service = WorkshopInstanceService(cluster)
    template = _template()

    captured: list = []
    db = _launch_db(captured)

    resp = await service.launch(
        db,
        template=template,
        k8s_name="rstudio-abc123",
        namespace="default",
        owner_email="alice@example.com",
        duration="2h",
    )

    assert ("default", "rstudio-abc123") in cluster.workshops
    instance = next(o for o in captured if isinstance(o, WorkshopInstance))
    assert instance.workshop_id == template.id
    assert instance.template_slug == "rstudio"
    assert instance.template_name == "Standard RStudio"
    spec = instance.resolved_spec
    assert spec["image"] == "rocker/rstudio:4.4"
    assert spec["port"] == 8787
    assert spec["tier"] == "large"
    assert spec["duration"] == "2h"  # the launch override, not the template default
    assert spec["env"] == {"DISABLE_AUTH": "false"}
    assert spec["args"] == ["--www-port=8787"]
    assert (
        spec["resources"]["cpu_request"] == "500m"
    )  # snake_case, matches template storage
    assert spec["storage"] == {"size": "20Gi", "storage_class": "standard"}

    # Response is built from the stamped fields, not a template join.
    assert resp.template_slug == "rstudio"
    assert resp.workshop_name == "Standard RStudio"
    assert resp.resolved_spec["image"] == "rocker/rstudio:4.4"


@pytest.mark.asyncio
async def test_sync_from_k8s_does_not_reterminate_existing_row():
    service = WorkshopInstanceService(FakeWorkshopCluster())
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    terminated_at = datetime.now(UTC) - timedelta(minutes=1)
    row = _instance(phase="Terminated", terminated_at=terminated_at)

    await service._sync_from_k8s(db, row)

    assert row.phase == "Terminated"
    assert row.terminated_at == terminated_at
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# Launch atomicity: no orphaned Workshop CRDs, no phantom rows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_launch_compensates_on_commit_failure():
    """If the commit fails after the Workshop CRD is created, launch must delete the CRD
    (no orphan) and propagate the failure."""
    cluster = FakeWorkshopCluster()
    service = WorkshopInstanceService(cluster)

    db = _launch_db([])
    db.commit = AsyncMock(side_effect=RuntimeError("db down"))

    with pytest.raises(RuntimeError, match="db down"):
        await service.launch(
            db,
            template=_template(),
            k8s_name="rstudio-abc123",
            namespace="default",
            owner_email="alice@example.com",
            duration="2h",
        )

    assert ("default", "rstudio-abc123") in cluster.deleted
    assert cluster.workshops == {}


@pytest.mark.asyncio
async def test_launch_does_not_commit_when_create_fails():
    """If the CRD create fails, nothing may be committed to the DB."""
    cluster = FakeWorkshopCluster()
    cluster.raise_on_create = RuntimeError("k8s down")
    service = WorkshopInstanceService(cluster)

    db = _launch_db([])

    with pytest.raises(RuntimeError, match="k8s down"):
        await service.launch(
            db,
            template=_template(),
            k8s_name="rstudio-abc123",
            namespace="default",
            owner_email="alice@example.com",
            duration="2h",
        )

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_launch_does_not_create_cr_when_flush_fails():
    """DB-side failures (constraints, connection) must surface before any Workshop CRD
    is created in the cluster."""
    cluster = FakeWorkshopCluster()
    service = WorkshopInstanceService(cluster)

    db = _launch_db([])
    db.flush = AsyncMock(side_effect=RuntimeError("constraint violation"))

    with pytest.raises(RuntimeError, match="constraint violation"):
        await service.launch(
            db,
            template=_template(),
            k8s_name="rstudio-abc123",
            namespace="default",
            owner_email="alice@example.com",
            duration="2h",
        )

    assert cluster.workshops == {}
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_launch_logs_orphan_when_compensating_delete_fails(caplog):
    """The double-failure case must at least leave a loud trace of the orphan."""
    cluster = FakeWorkshopCluster()
    cluster.raise_on_delete = RuntimeError("k8s also down")
    service = WorkshopInstanceService(cluster)

    db = _launch_db([])
    db.commit = AsyncMock(side_effect=RuntimeError("db down"))

    with pytest.raises(RuntimeError, match="db down"):
        await service.launch(
            db,
            template=_template(),
            k8s_name="rstudio-abc123",
            namespace="default",
            owner_email="alice@example.com",
            duration="2h",
        )

    assert any("ORPHANED" in r.message for r in caplog.records)
