"""Service layer for WorkshopInstance (DB records + k8s CRD lifecycle)."""

import asyncio
import logging
import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from api.models.db.workshop_instance import InstanceEvent, WorkshopInstance
from api.models.schemas.workshop_instance import (
    InstanceSummary,
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
    WorkshopPhase,
    WorkshopResources,
    WorkshopStorage,
)
from api.services.workshop_cluster import K8sWorkshopCluster, WorkshopCluster

logger = logging.getLogger(__name__)

# SSE polling configuration
SSE_POLL_FAST_S: int = 5
SSE_POLL_SLOW_S: int = 30
SSE_JITTER_S: int = 5

_ACTIVE_PHASES = {WorkshopPhase.READY.value, WorkshopPhase.RUNNING.value}
_TRANSITIONAL_PHASES = {
    WorkshopPhase.PENDING.value,
    WorkshopPhase.CREATING.value,
    WorkshopPhase.STARTING.value,
}


# ---------------------------------------------------------------------------
# Instance response builder
# ---------------------------------------------------------------------------


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


def _resolved_spec_dict(workshop: WorkshopCreate) -> dict[str, Any]:
    """Snapshot the resolved launch spec for stamping onto the instance row.

    Uses snake_case sub-keys to match how templates persist resources/storage
    (``model_dump(by_alias=False)``) and the migration backfill.
    """
    return {
        "image": workshop.image,
        "port": workshop.port,
        "duration": workshop.duration,
        "tier": workshop.tier,
        "env": dict(workshop.env),
        "args": list(workshop.args),
        "resources": workshop.resources.model_dump(by_alias=False),
        "storage": workshop.storage.model_dump(by_alias=False)
        if workshop.storage
        else None,
    }


def _to_response(row: WorkshopInstance) -> WorkshopInstanceResponse:
    return WorkshopInstanceResponse(
        id=row.id,
        workshopId=row.workshop_id,
        workshopName=row.template_name,
        templateSlug=row.template_slug,
        resolvedSpec=row.resolved_spec,
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


# ---------------------------------------------------------------------------
# WorkshopInstanceService
# ---------------------------------------------------------------------------


class WorkshopInstanceService:
    """Manages WorkshopInstance DB records and k8s CRD lifecycle."""

    def __init__(self, cluster: WorkshopCluster):
        self._cluster = cluster

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
        res = template.resources
        workshop_create = WorkshopCreate(
            name=k8s_name,
            template_slug=template.slug,
            duration=duration,
            image=template.image,
            port=template.port,
            tier=template.tier,
            env=template.env,
            args=template.args,
            resources=WorkshopResources(
                cpu=res.cpu,
                memory=res.memory,
                cpuRequest=res.cpu_request,
                memoryRequest=res.memory_request,
                ephemeralStorage=res.ephemeral_storage,
                ephemeralStorageRequest=res.ephemeral_storage_request,
            ),
            storage=WorkshopStorage(
                size=template.storage.size,
                storageClass=template.storage.storage_class,
                workspace=template.storage.workspace,
            )
            if template.storage
            else None,
            ingress=WorkshopIngress(),
        )

        # Flush all DB work before touching the cluster so DB-side failures
        # (constraints, connection) abort the launch with no Workshop CRD
        # created; the k8s create happens inside the still-open transaction,
        # leaving commit as the only failure point after the CRD exists —
        # compensated below. A create failure propagates with the transaction
        # uncommitted; the get_db session teardown rolls it back.
        row = WorkshopInstance(
            workshop_id=template.id,
            template_slug=template.slug,
            template_name=template.name,
            resolved_spec=_resolved_spec_dict(workshop_create),
            k8s_name=k8s_name,
            namespace=namespace,
            owner_email=owner_email,
            phase=WorkshopPhase.PENDING.value,
            duration_requested=duration,
            launched_at=datetime.now(UTC),
        )
        db.add(row)
        await db.flush()
        db.add(InstanceEvent(instance_id=row.id, phase=WorkshopPhase.PENDING.value))
        await db.flush()

        await self._cluster.create(
            workshop_create, owner_email=owner_email, namespace=namespace
        )

        try:
            await db.commit()
        except Exception:
            # Clear the failed transaction and return the connection to the
            # pool before the (potentially slow) compensating cluster call.
            try:
                await db.rollback()
            except Exception:
                logger.warning(
                    "Rollback after failed commit also failed for %s", k8s_name
                )
            try:
                await self._cluster.delete(k8s_name, namespace)
            except Exception:
                logger.exception(
                    "ORPHANED Workshop CRD %s/%s: commit failed and the "
                    "compensating delete also failed",
                    namespace,
                    k8s_name,
                )
            raise
        await db.refresh(row)

        logger.info(
            "Launched instance %s (k8s=%s) for %s", row.id, k8s_name, owner_email
        )
        return _to_response(row)

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
            .where(WorkshopInstance.terminated_at.is_(None))
            .order_by(WorkshopInstance.launched_at.desc())
        )
        if owner_email:
            query = query.where(WorkshopInstance.owner_email == owner_email)

        total = (
            await db.execute(select(func.count()).select_from(query.subquery()))
        ).scalar_one()
        rows = (
            (await db.execute(query.offset((page - 1) * size).limit(size)))
            .scalars()
            .all()
        )

        now = datetime.now(UTC)
        for row in rows:
            if row.phase in _TRANSITIONAL_PHASES or (
                row.expires_at and row.expires_at <= now
            ):
                await self._sync_from_k8s(db, row)

        return [_to_response(r) for r in rows], total

    async def get_instance(
        self, db: AsyncSession, k8s_name: str, namespace: str = "default"
    ) -> WorkshopInstanceResponse | None:
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
        return _to_response(row)

    async def terminate(
        self, db: AsyncSession, k8s_name: str, namespace: str = "default"
    ) -> bool:
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

        await self._cluster.delete(k8s_name, namespace)

        row.terminated_at = datetime.now(UTC)
        row.phase = WorkshopPhase.TERMINATING.value
        db.add(InstanceEvent(instance_id=row.id, phase=WorkshopPhase.TERMINATING.value))
        await db.commit()
        logger.info("Terminated instance %s (k8s=%s)", row.id, k8s_name)
        return True

    async def extend(
        self,
        db: AsyncSession,
        k8s_name: str,
        namespace: str = "default",
        extra_hours: int = 1,
    ) -> WorkshopInstanceResponse | None:
        """Extend an active instance's expiry by extra_hours."""
        result = await db.execute(
            select(WorkshopInstance).where(
                WorkshopInstance.k8s_name == k8s_name,
                WorkshopInstance.namespace == namespace,
                WorkshopInstance.terminated_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None or row.expires_at is None:
            return None

        new_expires = row.expires_at + timedelta(hours=extra_hours)
        row.expires_at = new_expires

        # Push new expiresAt into the CRD status so the operator picks it up
        try:
            await self._cluster.set_expiry(k8s_name, namespace, new_expires)
        except Exception:
            logger.warning(
                "Could not patch CRD status for %s; DB updated anyway", k8s_name
            )

        await db.commit()
        await db.refresh(row)
        logger.info(
            "Extended instance %s by %dh → %s", k8s_name, extra_hours, new_expires
        )
        return _to_response(row)

    async def get_status(
        self, db: AsyncSession, k8s_name: str, namespace: str = "default"
    ) -> WorkshopInstanceStatus | None:
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
        result = await db.execute(
            select(WorkshopInstance)
            .options(selectinload(WorkshopInstance.events))
            .where(
                WorkshopInstance.k8s_name == k8s_name,
                WorkshopInstance.namespace == namespace,
            )
        )
        row = result.scalar_one_or_none()
        return _compute_utilization(row) if row else None

    async def get_template_stats(
        self, db: AsyncSession, template_id: uuid.UUID
    ) -> TemplateStats | None:
        # Templates live in the file registry (ADR-0006); instances reference
        # them by the same stable id stored in workshop_id.
        from api.services.template_registry import get_registry

        if await get_registry().get_template(template_id=template_id) is None:
            return None

        counts = (
            await db.execute(
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
        ).one()

        instances = (
            (
                await db.execute(
                    select(WorkshopInstance)
                    .options(selectinload(WorkshopInstance.events))
                    .where(WorkshopInstance.workshop_id == template_id)
                )
            )
            .scalars()
            .all()
        )

        return TemplateStats(
            template_id=template_id,
            total_launches=counts.total or 0,
            active_instances=counts.active or 0,
            total_active_seconds=sum(
                _compute_utilization(i).active_seconds for i in instances
            ),
            unique_users=counts.unique_users or 0,
        )

    async def get_instance_summary(self, db: AsyncSession) -> InstanceSummary:
        cutoff = datetime.now(UTC) - timedelta(days=7)
        row = (
            await db.execute(
                select(
                    func.count().label("total"),
                    func.sum(
                        case((WorkshopInstance.launched_at >= cutoff, 1), else_=0)
                    ).label("last_7_days"),
                )
            )
        ).one()
        return InstanceSummary(
            total_launches=row.total or 0, launched_last_7_days=row.last_7_days or 0
        )

    async def get_bulk_launch_counts(self, db: AsyncSession) -> list[TemplateStats]:
        result = await db.execute(
            select(
                WorkshopInstance.workshop_id,
                func.count().label("total"),
                func.sum(
                    case((WorkshopInstance.terminated_at.is_(None), 1), else_=0)
                ).label("active"),
                func.count(distinct(WorkshopInstance.owner_email)).label(
                    "unique_users"
                ),
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
            k8s_workshop = await self._cluster.get(row.k8s_name, row.namespace)
        except Exception:
            return

        if k8s_workshop is None:
            if row.terminated_at is None:
                row.terminated_at = datetime.now(UTC)
                row.phase = WorkshopPhase.TERMINATED.value
                db.add(
                    InstanceEvent(
                        instance_id=row.id, phase=WorkshopPhase.TERMINATED.value
                    )
                )
                await db.commit()
            return

        new_phase = (
            k8s_workshop.status.phase.value if k8s_workshop.status else row.phase
        )
        new_url = k8s_workshop.status.url if k8s_workshop.status else row.url
        new_expires = (
            k8s_workshop.status.expires_at if k8s_workshop.status else row.expires_at
        )

        changed = False
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

    # TODO(scaling): each SSE connection independently polls K8s via _sync_from_k8s
    # for its transitional-phase instances. At ~50+ simultaneous users all launching
    # sessions, this produces redundant parallel K8s API calls. The fix is a single
    # shared background task that polls all active workshops on a common schedule and
    # pushes results into a cache (e.g. asyncio.Queue per subscriber or a broadcast
    # dict). Each SSE stream then reads from the cache instead of hitting K8s itself.
    async def events(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        owner_email: str | None = None,
    ):
        """SSE generator: yields instance list JSON, polling fast while transitional.

        Accepts a session factory rather than a held session so each poll cycle
        opens and closes its own connection. This prevents SSE streams from
        exhausting the connection pool during idle sleep intervals.
        """
        await asyncio.sleep(random.uniform(0, SSE_JITTER_S))
        while True:
            async with session_factory() as db:
                items, total = await self.list_instances(db, owner_email=owner_email)
            yield WorkshopInstanceList(items=items, total=total).model_dump_json(
                by_alias=True
            )
            has_transitional = any(i.phase in _TRANSITIONAL_PHASES for i in items)
            base = SSE_POLL_FAST_S if has_transitional else SSE_POLL_SLOW_S
            await asyncio.sleep(base + random.uniform(-SSE_JITTER_S, SSE_JITTER_S))


def get_instance_service() -> WorkshopInstanceService:
    return WorkshopInstanceService(K8sWorkshopCluster())
