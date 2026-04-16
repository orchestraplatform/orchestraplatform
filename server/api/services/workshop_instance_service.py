"""Service layer for WorkshopInstance (DB records + k8s CRD lifecycle)."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.core.kubernetes import ApiException
from api.models.db.workshop_instance import InstanceEvent, WorkshopInstance
from api.models.schemas.workshop_instance import (
    InstanceUtilization,
    TemplateStats,
    WorkshopInstanceList,
    WorkshopInstanceResponse,
    WorkshopInstanceStatus,
)
from api.models.schemas.workshop_template import WorkshopTemplateResponse
from api.models.workshop import (
    WorkshopCreate,
    WorkshopIngress,
    WorkshopResources,
    WorkshopStorage,
)
from api.services.workshop_service import WorkshopService

logger = logging.getLogger(__name__)
_k8s = WorkshopService()

# SSE polling configuration — adjust here or promote to settings.py for env-var control.
SSE_POLL_FAST_S: int = 5    # interval while any session is in a transitional phase
SSE_POLL_SLOW_S: int = 30   # interval once all sessions have settled
SSE_JITTER_S: int = 5       # max random offset applied to startup delay and each tick

_ACTIVE_PHASES = {"Ready", "Running"}


def _compute_utilization(row: "WorkshopInstance") -> InstanceUtilization:
    """Compute time-in-phase breakdown from a row's pre-loaded events."""
    events = sorted(row.events, key=lambda e: e.recorded_at)
    now = datetime.now(UTC)
    endpoint = row.terminated_at or now

    phase_seconds: dict[str, int] = {}
    for i, event in enumerate(events):
        start = event.recorded_at
        end = events[i + 1].recorded_at if i + 1 < len(events) else endpoint
        secs = max(0, int((end - start).total_seconds()))
        phase_seconds[event.phase] = phase_seconds.get(event.phase, 0) + secs

    active_seconds = sum(
        s for phase, s in phase_seconds.items() if phase in _ACTIVE_PHASES
    )
    total_elapsed = max(0, int((endpoint - row.launched_at).total_seconds()))

    return InstanceUtilization(
        instance_id=row.id,
        k8s_name=row.k8s_name,
        launched_at=row.launched_at,
        terminated_at=row.terminated_at,
        total_elapsed_seconds=total_elapsed,
        active_seconds=active_seconds,
        phase_seconds=phase_seconds,
    )


def _to_response(
    row: WorkshopInstance,
    workshop_name: str | None = None,
) -> WorkshopInstanceResponse:
    return WorkshopInstanceResponse(
        id=row.id,
        workshopId=row.workshop_id,
        workshopName=workshop_name,
        k8sName=row.k8s_name,
        namespace=row.namespace,
        ownerEmail=row.owner_email,
        phase=row.phase,
        url=row.url,
        durationRequested=row.duration_requested,
        launchedAt=row.launched_at,
        expiresAt=row.expires_at,
        terminatedAt=row.terminated_at,
        createdAt=row.created_at,
        updatedAt=row.updated_at,
    )


class WorkshopInstanceService:
    """Manages WorkshopInstance DB records and k8s CRD lifecycle."""

    async def launch(
        self,
        db: AsyncSession,
        *,
        template: WorkshopTemplateResponse,
        k8s_name: str,
        namespace: str,
        owner_email: str,
        duration: str,
    ) -> WorkshopInstanceResponse:
        """Create a DB record and the corresponding k8s Workshop CRD."""
        # Build WorkshopCreate from template defaults
        res = template.resources
        workshop_create = WorkshopCreate(
            name=k8s_name,
            duration=duration,
            image=template.image,
            resources=WorkshopResources(
                cpu=res.cpu,
                memory=res.memory,
                cpuRequest=res.cpu_request,
                memoryRequest=res.memory_request,
            ),
            storage=(
                WorkshopStorage(
                    size=template.storage.size,
                    storageClass=template.storage.storage_class,
                )
                if template.storage
                else None
            ),
            ingress=WorkshopIngress(),
        )

        # Create k8s CRD first; roll back DB record on failure
        await _k8s.create_workshop(
            workshop_create, owner_email=owner_email, namespace=namespace
        )

        # Insert DB record
        row = WorkshopInstance(
            workshop_id=template.id,
            k8s_name=k8s_name,
            namespace=namespace,
            owner_email=owner_email,
            phase="Pending",
            duration_requested=duration,
            launched_at=datetime.now(UTC),
        )
        db.add(row)
        await db.flush()  # get the id before appending event

        db.add(InstanceEvent(instance_id=row.id, phase="Pending"))
        await db.commit()
        await db.refresh(row)

        logger.info(
            "Launched instance %s (k8s=%s) for %s", row.id, k8s_name, owner_email
        )
        return _to_response(row, workshop_name=template.name)

    async def list_instances(
        self,
        db: AsyncSession,
        *,
        owner_email: str | None = None,
        page: int = 1,
        size: int = 50,
    ) -> tuple[list[WorkshopInstanceResponse], int]:
        """Return a paginated list. If owner_email is None, return all (admin)."""
        query = (
            select(WorkshopInstance)
            .options(selectinload(WorkshopInstance.workshop))
            .where(WorkshopInstance.terminated_at.is_(None))
            .order_by(WorkshopInstance.launched_at.desc())
        )
        if owner_email:
            query = query.where(WorkshopInstance.owner_email == owner_email)

        from sqlalchemy import func

        total_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar_one()

        offset = (page - 1) * size
        result = await db.execute(query.offset(offset).limit(size))
        rows = result.scalars().all()

        # Sync from k8s for instances that haven't settled yet, or have expired.
        now = datetime.now(UTC)
        _TRANSITIONAL = {"Pending", "Creating"}
        for row in rows:
            if row.phase in _TRANSITIONAL or (row.expires_at and row.expires_at <= now):
                await self._sync_from_k8s(db, row)

        items = [_to_response(r, workshop_name=r.workshop.name) for r in rows]
        return items, total

    async def get_instance(
        self, db: AsyncSession, k8s_name: str, namespace: str = "default"
    ) -> WorkshopInstanceResponse | None:
        """Fetch a DB record and sync phase/url from k8s."""
        result = await db.execute(
            select(WorkshopInstance)
            .options(selectinload(WorkshopInstance.workshop))
            .where(
                WorkshopInstance.k8s_name == k8s_name,
                WorkshopInstance.namespace == namespace,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None

        # Sync live status from k8s
        await self._sync_from_k8s(db, row)
        return _to_response(row, workshop_name=row.workshop.name)

    async def terminate(
        self, db: AsyncSession, k8s_name: str, namespace: str = "default"
    ) -> bool:
        """Delete the k8s CRD and mark the DB record as terminated."""
        result = await db.execute(
            select(WorkshopInstance).where(
                WorkshopInstance.k8s_name == k8s_name,
                WorkshopInstance.namespace == namespace,
                WorkshopInstance.terminated_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False

        try:
            await _k8s.delete_workshop(k8s_name, namespace)
        except ApiException as e:
            if e.status != 404:
                raise

        row.terminated_at = datetime.now(UTC)
        row.phase = "Terminating"
        db.add(InstanceEvent(instance_id=row.id, phase="Terminating"))
        await db.commit()
        logger.info("Terminated instance %s (k8s=%s)", row.id, k8s_name)
        return True

    async def get_status(
        self, db: AsyncSession, k8s_name: str, namespace: str = "default"
    ) -> WorkshopInstanceStatus | None:
        """Return lightweight status, syncing from k8s first."""
        result = await db.execute(
            select(WorkshopInstance).where(
                WorkshopInstance.k8s_name == k8s_name,
                WorkshopInstance.namespace == namespace,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        await self._sync_from_k8s(db, row)
        return WorkshopInstanceStatus(
            id=row.id,
            k8sName=row.k8s_name,
            phase=row.phase,
            url=row.url,
            expiresAt=row.expires_at,
        )

    async def get_utilization(
        self, db: AsyncSession, k8s_name: str, namespace: str = "default"
    ) -> InstanceUtilization | None:
        """Return time-in-phase utilization for an instance."""
        result = await db.execute(
            select(WorkshopInstance)
            .options(selectinload(WorkshopInstance.events))
            .where(
                WorkshopInstance.k8s_name == k8s_name,
                WorkshopInstance.namespace == namespace,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _compute_utilization(row)

    async def get_template_stats(
        self, db: AsyncSession, template_id: "uuid.UUID"
    ) -> TemplateStats | None:
        """Return aggregate launch and utilization stats for a template."""
        from sqlalchemy import case, distinct, func

        from api.models.db.workshop import Workshop

        # Verify template exists
        tpl_result = await db.execute(
            select(Workshop).where(Workshop.id == template_id)
        )
        if tpl_result.scalar_one_or_none() is None:
            return None

        agg_result = await db.execute(
            select(
                func.count().label("total"),
                func.sum(
                    case((WorkshopInstance.terminated_at.is_(None), 1), else_=0)
                ).label("active"),
                func.count(distinct(WorkshopInstance.owner_email)).label(
                    "unique_users"
                ),
            ).where(WorkshopInstance.workshop_id == template_id)
        )
        counts = agg_result.one()

        # Active-seconds requires loading events — computed in Python
        instances_result = await db.execute(
            select(WorkshopInstance)
            .options(selectinload(WorkshopInstance.events))
            .where(WorkshopInstance.workshop_id == template_id)
        )
        instances = instances_result.scalars().all()
        total_active_secs = sum(
            _compute_utilization(inst).active_seconds for inst in instances
        )

        return TemplateStats(
            template_id=template_id,
            total_launches=counts.total or 0,
            active_instances=counts.active or 0,
            total_active_seconds=total_active_secs,
            unique_users=counts.unique_users or 0,
        )

    async def get_bulk_launch_counts(
        self, db: AsyncSession
    ) -> list[TemplateStats]:
        """Return total_launches per template in a single grouped query."""
        from sqlalchemy import case, distinct, func

        result = await db.execute(
            select(
                WorkshopInstance.workshop_id,
                func.count().label("total"),
                func.sum(
                    case((WorkshopInstance.terminated_at.is_(None), 1), else_=0)
                ).label("active"),
                func.count(distinct(WorkshopInstance.owner_email)).label("unique_users"),
            ).group_by(WorkshopInstance.workshop_id)
        )
        return [
            TemplateStats(
                template_id=row.workshop_id,
                total_launches=row.total or 0,
                active_instances=row.active or 0,
                total_active_seconds=0,
                unique_users=row.unique_users or 0,
            )
            for row in result.all()
        ]

    async def _sync_from_k8s(self, db: AsyncSession, row: WorkshopInstance) -> None:
        """Pull phase/url/expiresAt from the live k8s CRD and update DB if changed."""
        try:
            k8s_workshop = await _k8s.get_workshop(row.k8s_name, row.namespace)
        except Exception:
            return  # k8s unreachable; leave DB state as-is

        if k8s_workshop is None:
            # CRD is gone — mark as terminated if not already
            if row.terminated_at is None:
                row.terminated_at = datetime.now(UTC)
                row.phase = "Terminated"
                db.add(InstanceEvent(instance_id=row.id, phase="Terminated"))
                await db.commit()
            return

        changed = False
        new_phase = (
            k8s_workshop.status.phase.value if k8s_workshop.status else row.phase
        )
        new_url = k8s_workshop.status.url if k8s_workshop.status else row.url
        new_expires = (
            k8s_workshop.status.expires_at if k8s_workshop.status else row.expires_at
        )

        if new_phase != row.phase:
            db.add(InstanceEvent(instance_id=row.id, phase=new_phase))
            row.phase = new_phase
            changed = True
        if new_url and new_url != row.url:
            row.url = new_url
            changed = True
        if new_expires and new_expires != row.expires_at:
            row.expires_at = new_expires
            changed = True

        if changed:
            await db.commit()

    async def events(
        self,
        db: AsyncSession,
        *,
        owner_email: str | None = None,
    ):
        """Generator for SSE events that yields the current instance list.

        Polls fast (5 s) while any session is transitional, slow (15 s) when
        all are settled.  A random jitter of ±2 s is added to each sleep to
        spread load across connections that started at the same time.
        """
        import asyncio
        import random

        _TRANSITIONAL = {"Pending", "Creating"}

        # Stagger connection startups so a mass-join doesn't produce a
        # synchronised thundering herd on the very first tick.
        await asyncio.sleep(random.uniform(0, SSE_JITTER_S))

        while True:
            items, total = await self.list_instances(db, owner_email=owner_email)
            data = WorkshopInstanceList(items=items, total=total)
            yield data.model_dump_json(by_alias=True)

            has_transitional = any(i.phase in _TRANSITIONAL for i in items)
            base = SSE_POLL_FAST_S if has_transitional else SSE_POLL_SLOW_S
            await asyncio.sleep(base + random.uniform(-SSE_JITTER_S, SSE_JITTER_S))


def get_instance_service() -> WorkshopInstanceService:
    """FastAPI dependency — returns a WorkshopInstanceService instance."""
    return WorkshopInstanceService()
