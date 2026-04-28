"""Service layer for WorkshopInstance (DB records + k8s CRD lifecycle)."""

import asyncio
import logging
import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.core.kubernetes import ApiException, get_custom_objects_api
from api.models.db.workshop import Workshop
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
    WorkshopResponse,
    WorkshopStatus,
    WorkshopCondition,
    WorkshopStorage,
)

logger = logging.getLogger(__name__)

# Kubernetes CRD constants
_K8S_GROUP = "orchestra.io"
_K8S_VERSION = "v1"
_K8S_PLURAL = "workshops"

# SSE polling configuration
SSE_POLL_FAST_S: int = 5
SSE_POLL_SLOW_S: int = 30
SSE_JITTER_S: int = 5

_ACTIVE_PHASES = {"Ready", "Running"}
_TRANSITIONAL_PHASES = {"Pending", "Creating"}


# ---------------------------------------------------------------------------
# K8s CRD helpers (previously WorkshopService)
# ---------------------------------------------------------------------------

def _parse_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None


def _to_kubernetes_crd(
    workshop: WorkshopCreate, owner_email: str, namespace: str
) -> dict[str, Any]:
    """Convert a WorkshopCreate model to a Kubernetes CRD body."""
    crd: dict[str, Any] = {
        "apiVersion": f"{_K8S_GROUP}/{_K8S_VERSION}",
        "kind": "Workshop",
        "metadata": {
            "name": workshop.name,
            "namespace": namespace,
            "labels": {"app": "orchestra-operator", "managed-by": "orchestra-api"},
        },
        "spec": {
            "name": workshop.name,
            "ownerEmail": owner_email,
            "duration": workshop.duration,
            "image": workshop.image,
            "resources": {
                "cpu": workshop.resources.cpu,
                "memory": workshop.resources.memory,
                "cpuRequest": workshop.resources.cpu_request,
                "memoryRequest": workshop.resources.memory_request,
            },
        },
    }
    if workshop.storage:
        crd["spec"]["storage"] = {"size": workshop.storage.size}
        if workshop.storage.storage_class:
            crd["spec"]["storage"]["storageClass"] = workshop.storage.storage_class
    if workshop.ingress:
        crd["spec"]["ingress"] = {}
        if workshop.ingress.host:
            crd["spec"]["ingress"]["host"] = workshop.ingress.host
        if workshop.ingress.annotations:
            crd["spec"]["ingress"]["annotations"] = workshop.ingress.annotations
    return crd


def _from_kubernetes_crd(crd: dict[str, Any]) -> WorkshopResponse:
    """Convert a Kubernetes CRD dict to a WorkshopResponse."""
    metadata = crd.get("metadata", {})
    spec = crd.get("spec", {})
    status = crd.get("status", {})

    workshop_status = None
    if status:
        conditions = [
            WorkshopCondition(
                type=c.get("type"),
                status=c.get("status"),
                reason=c.get("reason"),
                message=c.get("message"),
                last_transition_time=c.get("lastTransitionTime"),
            )
            for c in status.get("conditions", [])
        ]
        workshop_status = WorkshopStatus(
            phase=WorkshopPhase(status.get("phase", "Pending")),
            url=status.get("url"),
            created_at=_parse_datetime(status.get("createdAt")),
            expires_at=_parse_datetime(status.get("expiresAt")),
            conditions=conditions,
        )

    res = spec.get("resources", {})
    storage_spec = spec.get("storage")
    ingress_spec = spec.get("ingress")

    return WorkshopResponse(
        name=metadata.get("name"),
        namespace=metadata.get("namespace"),
        # Support both old "owner" and new "ownerEmail" CRD field names
        owner=spec.get("ownerEmail") or spec.get("owner") or None,
        spec=WorkshopCreate(
            name=spec.get("name"),
            duration=spec.get("duration", "4h"),
            image=spec.get("image", "rocker/rstudio:latest"),
            resources=WorkshopResources(
                cpu=res.get("cpu", "1"),
                memory=res.get("memory", "2Gi"),
                cpuRequest=res.get("cpuRequest", "500m"),
                memoryRequest=res.get("memoryRequest", "1Gi"),
            ),
            storage=WorkshopStorage(
                size=storage_spec.get("size", "10Gi"),
                storageClass=storage_spec.get("storageClass"),
            ) if storage_spec else None,
            ingress=WorkshopIngress(
                host=ingress_spec.get("host"),
                annotations=ingress_spec.get("annotations", {}),
            ) if ingress_spec else None,
        ),
        status=workshop_status,
        created_at=_parse_datetime(metadata.get("creationTimestamp")),
        updated_at=None,
    )


async def _k8s_create(workshop: WorkshopCreate, owner_email: str, namespace: str) -> WorkshopResponse:
    api = get_custom_objects_api()
    result = api.create_namespaced_custom_object(
        group=_K8S_GROUP, version=_K8S_VERSION, namespace=namespace,
        plural=_K8S_PLURAL, body=_to_kubernetes_crd(workshop, owner_email, namespace),
    )
    logger.info("Created k8s Workshop CRD %s in %s", workshop.name, namespace)
    return _from_kubernetes_crd(result)


async def _k8s_get(name: str, namespace: str) -> WorkshopResponse | None:
    api = get_custom_objects_api()
    try:
        result = api.get_namespaced_custom_object(
            group=_K8S_GROUP, version=_K8S_VERSION, namespace=namespace,
            plural=_K8S_PLURAL, name=name,
        )
        return _from_kubernetes_crd(result)
    except ApiException as e:
        if e.status == 404:
            return None
        raise


async def _k8s_delete(name: str, namespace: str) -> bool:
    api = get_custom_objects_api()
    try:
        api.delete_namespaced_custom_object(
            group=_K8S_GROUP, version=_K8S_VERSION, namespace=namespace,
            plural=_K8S_PLURAL, name=name,
        )
        logger.info("Deleted k8s Workshop CRD %s in %s", name, namespace)
        return True
    except ApiException as e:
        if e.status == 404:
            return False
        raise


async def _k8s_patch_status(name: str, namespace: str, patch: dict[str, Any]) -> None:
    """Patch the status subresource of a Workshop CRD."""
    api = get_custom_objects_api()
    api.patch_namespaced_custom_object_status(
        group=_K8S_GROUP, version=_K8S_VERSION, namespace=namespace,
        plural=_K8S_PLURAL, name=name,
        body={"status": patch},
    )


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

    active_seconds = sum(s for phase, s in phase_seconds.items() if phase in _ACTIVE_PHASES)
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


def _to_response(row: WorkshopInstance, workshop_name: str | None = None) -> WorkshopInstanceResponse:
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


# ---------------------------------------------------------------------------
# WorkshopInstanceService
# ---------------------------------------------------------------------------

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
            storage=WorkshopStorage(
                size=template.storage.size,
                storageClass=template.storage.storage_class,
            ) if template.storage else None,
            ingress=WorkshopIngress(),
        )

        await _k8s_create(workshop_create, owner_email=owner_email, namespace=namespace)

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
        await db.flush()
        db.add(InstanceEvent(instance_id=row.id, phase="Pending"))
        await db.commit()
        await db.refresh(row)

        logger.info("Launched instance %s (k8s=%s) for %s", row.id, k8s_name, owner_email)
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

        total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (await db.execute(query.offset((page - 1) * size).limit(size))).scalars().all()

        now = datetime.now(UTC)
        for row in rows:
            if row.phase in _TRANSITIONAL_PHASES or (row.expires_at and row.expires_at <= now):
                await self._sync_from_k8s(db, row)

        return [_to_response(r, workshop_name=r.workshop.name) for r in rows], total

    async def get_instance(
        self, db: AsyncSession, k8s_name: str, namespace: str = "default"
    ) -> WorkshopInstanceResponse | None:
        result = await db.execute(
            select(WorkshopInstance)
            .options(selectinload(WorkshopInstance.workshop))
            .where(WorkshopInstance.k8s_name == k8s_name, WorkshopInstance.namespace == namespace)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        await self._sync_from_k8s(db, row)
        return _to_response(row, workshop_name=row.workshop.name)

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

        try:
            await _k8s_delete(k8s_name, namespace)
        except ApiException as e:
            if e.status != 404:
                raise

        row.terminated_at = datetime.now(UTC)
        row.phase = "Terminating"
        db.add(InstanceEvent(instance_id=row.id, phase="Terminating"))
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
            select(WorkshopInstance)
            .options(selectinload(WorkshopInstance.workshop))
            .where(
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
            await _k8s_patch_status(k8s_name, namespace, {"expiresAt": new_expires.isoformat()})
        except Exception:
            logger.warning("Could not patch CRD status for %s; DB updated anyway", k8s_name)

        await db.commit()
        await db.refresh(row)
        logger.info("Extended instance %s by %dh → %s", k8s_name, extra_hours, new_expires)
        return _to_response(row, workshop_name=row.workshop.name)

    async def get_status(
        self, db: AsyncSession, k8s_name: str, namespace: str = "default"
    ) -> WorkshopInstanceStatus | None:
        result = await db.execute(
            select(WorkshopInstance).where(
                WorkshopInstance.k8s_name == k8s_name, WorkshopInstance.namespace == namespace
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        await self._sync_from_k8s(db, row)
        return WorkshopInstanceStatus(
            id=row.id, k8sName=row.k8s_name, phase=row.phase,
            url=row.url, expiresAt=row.expires_at,
        )

    async def get_utilization(
        self, db: AsyncSession, k8s_name: str, namespace: str = "default"
    ) -> InstanceUtilization | None:
        result = await db.execute(
            select(WorkshopInstance)
            .options(selectinload(WorkshopInstance.events))
            .where(WorkshopInstance.k8s_name == k8s_name, WorkshopInstance.namespace == namespace)
        )
        row = result.scalar_one_or_none()
        return _compute_utilization(row) if row else None

    async def get_template_stats(
        self, db: AsyncSession, template_id: uuid.UUID
    ) -> TemplateStats | None:
        if (await db.execute(select(Workshop).where(Workshop.id == template_id))).scalar_one_or_none() is None:
            return None

        counts = (await db.execute(
            select(
                func.count().label("total"),
                func.sum(case((WorkshopInstance.terminated_at.is_(None), 1), else_=0)).label("active"),
                func.count(distinct(WorkshopInstance.owner_email)).label("unique_users"),
            ).where(WorkshopInstance.workshop_id == template_id)
        )).one()

        instances = (await db.execute(
            select(WorkshopInstance)
            .options(selectinload(WorkshopInstance.events))
            .where(WorkshopInstance.workshop_id == template_id)
        )).scalars().all()

        return TemplateStats(
            template_id=template_id,
            total_launches=counts.total or 0,
            active_instances=counts.active or 0,
            total_active_seconds=sum(_compute_utilization(i).active_seconds for i in instances),
            unique_users=counts.unique_users or 0,
        )

    async def get_instance_summary(self, db: AsyncSession) -> InstanceSummary:
        cutoff = datetime.now(UTC) - timedelta(days=7)
        row = (await db.execute(
            select(
                func.count().label("total"),
                func.sum(case((WorkshopInstance.launched_at >= cutoff, 1), else_=0)).label("last_7_days"),
            )
        )).one()
        return InstanceSummary(total_launches=row.total or 0, launched_last_7_days=row.last_7_days or 0)

    async def get_bulk_launch_counts(self, db: AsyncSession) -> list[TemplateStats]:
        result = await db.execute(
            select(
                WorkshopInstance.workshop_id,
                func.count().label("total"),
                func.sum(case((WorkshopInstance.terminated_at.is_(None), 1), else_=0)).label("active"),
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
            k8s_workshop = await _k8s_get(row.k8s_name, row.namespace)
        except Exception:
            return

        if k8s_workshop is None:
            if row.terminated_at is None:
                row.terminated_at = datetime.now(UTC)
                row.phase = "Terminated"
                db.add(InstanceEvent(instance_id=row.id, phase="Terminated"))
                await db.commit()
            return

        new_phase = k8s_workshop.status.phase.value if k8s_workshop.status else row.phase
        new_url = k8s_workshop.status.url if k8s_workshop.status else row.url
        new_expires = k8s_workshop.status.expires_at if k8s_workshop.status else row.expires_at

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

    async def events(self, db: AsyncSession, *, owner_email: str | None = None):
        """SSE generator: yields instance list JSON, polling fast while transitional."""
        await asyncio.sleep(random.uniform(0, SSE_JITTER_S))
        while True:
            items, total = await self.list_instances(db, owner_email=owner_email)
            yield WorkshopInstanceList(items=items, total=total).model_dump_json(by_alias=True)
            has_transitional = any(i.phase in _TRANSITIONAL_PHASES for i in items)
            base = SSE_POLL_FAST_S if has_transitional else SSE_POLL_SLOW_S
            await asyncio.sleep(base + random.uniform(-SSE_JITTER_S, SSE_JITTER_S))


def get_instance_service() -> WorkshopInstanceService:
    return WorkshopInstanceService()
