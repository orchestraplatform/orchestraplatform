"""WorkshopInstance routes (list, get, delete, status)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.auth import CurrentUser, get_current_user
from api.core.database import get_db
from api.models.schemas.workshop_instance import (
    WorkshopInstanceList,
    WorkshopInstanceResponse,
    WorkshopInstanceStatus,
)
from api.services.workshop_instance_service import WorkshopInstanceService

logger = logging.getLogger(__name__)
router = APIRouter()
instance_service = WorkshopInstanceService()


def _can_access(user: CurrentUser, owner_email: str) -> bool:
    return user.is_admin or user.email == owner_email


@router.get("/", response_model=WorkshopInstanceList)
async def list_instances(
    namespace: str = Query(default="default"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List running workshop instances.

    Regular users see only their own. Admins see all.
    """
    owner_filter = None if current_user.is_admin else current_user.email
    items, total = await instance_service.list_instances(
        db, owner_email=owner_filter, page=page, size=size
    )
    return WorkshopInstanceList(items=items, total=total, page=page, size=size)


@router.get("/{k8s_name}", response_model=WorkshopInstanceResponse)
async def get_instance(
    k8s_name: str = Path(..., description="Workshop instance k8s name"),
    namespace: str = Query(default="default"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a workshop instance, syncing live status from k8s."""
    instance = await instance_service.get_instance(db, k8s_name, namespace)
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
):
    """Terminate a workshop instance (deletes k8s CRD + marks DB record terminated)."""
    # Check ownership before terminating
    instance = await instance_service.get_instance(db, k8s_name, namespace)
    if not instance or not _can_access(current_user, instance.owner_email):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {k8s_name} not found",
        )
    await instance_service.terminate(db, k8s_name, namespace)
    return None


@router.get("/{k8s_name}/status", response_model=WorkshopInstanceStatus)
async def get_instance_status(
    k8s_name: str = Path(..., description="Workshop instance k8s name"),
    namespace: str = Query(default="default"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Lightweight status and URL for a workshop instance."""
    instance_status = await instance_service.get_status(db, k8s_name, namespace)
    if not instance_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {k8s_name} not found",
        )
    # Verify ownership via full record
    instance = await instance_service.get_instance(db, k8s_name, namespace)
    if not instance or not _can_access(current_user, instance.owner_email):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {k8s_name} not found",
        )
    return instance_status
