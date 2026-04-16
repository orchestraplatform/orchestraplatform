"""WorkshopInstance routes (list, get, delete, status, utilization)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.auth import CurrentUser, get_current_user
from api.core.database import get_db
from api.models.schemas.workshop_instance import (
    InstanceUtilization,
    WorkshopInstanceList,
    WorkshopInstanceResponse,
    WorkshopInstanceStatus,
)
from api.services.workshop_instance_service import (
    WorkshopInstanceService,
    get_instance_service,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _can_access(user: CurrentUser, owner_email: str) -> bool:
    return user.is_admin or user.email == owner_email


@router.get("/", response_model=WorkshopInstanceList)
async def list_instances(
    namespace: str = Query(default="default"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    svc: WorkshopInstanceService = Depends(get_instance_service),
):
    """List running workshop instances.

    Regular users see only their own. Admins see all.
    """
    owner_filter = None if current_user.is_admin else current_user.email
    items, total = await svc.list_instances(db, owner_email=owner_filter, page=page, size=size)
    return WorkshopInstanceList(items=items, total=total, page=page, size=size)


@router.get("/{k8s_name}", response_model=WorkshopInstanceResponse)
async def get_instance(
    k8s_name: str = Path(..., description="Workshop instance k8s name"),
    namespace: str = Query(default="default"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    svc: WorkshopInstanceService = Depends(get_instance_service),
):
    """Get a workshop instance, syncing live status from k8s."""
    instance = await svc.get_instance(db, k8s_name, namespace)
    if not instance or not _can_access(current_user, instance.owner_email):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {k8s_name} not found",
        )
    return instance


@router.delete("/{k8s_name}", status_code=status.HTTP_204_NO_CONTENT)
async def terminate_instance(
    k8s_name: str = Path(..., description="Workshop instance k8s name"),
    namespace: str = Query(default="default"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    svc: WorkshopInstanceService = Depends(get_instance_service),
):
    """Terminate a workshop instance (deletes k8s CRD + marks DB record terminated)."""
    instance = await svc.get_instance(db, k8s_name, namespace)
    if not instance or not _can_access(current_user, instance.owner_email):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {k8s_name} not found",
        )
    await svc.terminate(db, k8s_name, namespace)
    return None


@router.get("/{k8s_name}/utilization", response_model=InstanceUtilization)
async def get_instance_utilization(
    k8s_name: str = Path(..., description="Workshop instance k8s name"),
    namespace: str = Query(default="default"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    svc: WorkshopInstanceService = Depends(get_instance_service),
):
    """Time-in-phase utilization breakdown for a workshop instance."""
    instance = await svc.get_instance(db, k8s_name, namespace)
    if not instance or not _can_access(current_user, instance.owner_email):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {k8s_name} not found",
        )
    utilization = await svc.get_utilization(db, k8s_name, namespace)
    if not utilization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {k8s_name} not found",
        )
    return utilization


@router.get("/{k8s_name}/status", response_model=WorkshopInstanceStatus)
async def get_instance_status(
    k8s_name: str = Path(..., description="Workshop instance k8s name"),
    namespace: str = Query(default="default"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    svc: WorkshopInstanceService = Depends(get_instance_service),
):
    """Lightweight status and URL for a workshop instance."""
    instance = await svc.get_instance(db, k8s_name, namespace)
    if not instance or not _can_access(current_user, instance.owner_email):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {k8s_name} not found",
        )
    instance_status = await svc.get_status(db, k8s_name, namespace)
    if not instance_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {k8s_name} not found",
        )
    return instance_status
