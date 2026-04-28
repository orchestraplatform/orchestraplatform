"""Tests for WorkshopInstanceService lifecycle sync behavior."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.models.db.workshop_instance import InstanceEvent, WorkshopInstance
from api.services.workshop_instance_service import WorkshopInstanceService, _TRANSITIONAL_PHASES


def _instance(**overrides) -> WorkshopInstance:
    now = datetime.now(UTC)
    row = WorkshopInstance(
        id=uuid.uuid4(),
        workshop_id=uuid.uuid4(),
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
    service = WorkshopInstanceService()
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    row = _instance(phase="Running")

    with patch(
        "api.services.workshop_instance_service._k8s_get",
        AsyncMock(return_value=None),
    ):
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
    service = WorkshopInstanceService()
    row = _instance(phase=phase)
    row.workshop = MagicMock()
    row.workshop.name = "Test Workshop"

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
    service = WorkshopInstanceService()
    row = _instance(phase=phase)
    row.workshop = MagicMock()
    row.workshop.name = "Test Workshop"

    total_result = MagicMock()
    total_result.scalar_one.return_value = 1
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [row]

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[total_result, rows_result])

    with patch.object(service, "_sync_from_k8s", AsyncMock()) as mock_sync:
        await service.list_instances(db, owner_email="alice@example.com")

    mock_sync.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_from_k8s_does_not_reterminate_existing_row():
    service = WorkshopInstanceService()
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    terminated_at = datetime.now(UTC) - timedelta(minutes=1)
    row = _instance(phase="Terminated", terminated_at=terminated_at)

    with patch(
        "api.services.workshop_instance_service._k8s_get",
        AsyncMock(return_value=None),
    ):
        await service._sync_from_k8s(db, row)

    assert row.phase == "Terminated"
    assert row.terminated_at == terminated_at
    db.add.assert_not_called()
    db.commit.assert_not_awaited()
