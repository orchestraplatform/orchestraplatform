"""Service layer for WorkshopInstance (DB records + k8s CRD lifecycle)."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.core.kubernetes import ApiException
from api.models.db.workshop_instance import InstanceEvent, WorkshopInstance
from api.models.schemas.workshop_instance import (
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
            ingress=WorkshopIngress() if template.ingress else None,
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
            launched_at=datetime.now(timezone.utc),
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

        row.terminated_at = datetime.now(timezone.utc)
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

    async def _sync_from_k8s(self, db: AsyncSession, row: WorkshopInstance) -> None:
        """Pull phase/url/expiresAt from the live k8s CRD and update DB if changed."""
        try:
            k8s_workshop = await _k8s.get_workshop(row.k8s_name, row.namespace)
        except Exception:
            return  # k8s unreachable; leave DB state as-is

        if k8s_workshop is None:
            return

        changed = False
        new_phase = k8s_workshop.status.phase.value if k8s_workshop.status else row.phase
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
