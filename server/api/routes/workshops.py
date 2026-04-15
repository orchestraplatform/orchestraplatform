"""Workshop API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from api.core.auth import CurrentUser, get_current_user
from api.models.workshop import (
    WorkshopCreate,
    WorkshopList,
    WorkshopResponse,
)
from api.services.workshop_service import WorkshopService

logger = logging.getLogger(__name__)
router = APIRouter()
workshop_service = WorkshopService()


@router.post("/", response_model=WorkshopResponse, status_code=status.HTTP_201_CREATED)
async def create_workshop(
    workshop: WorkshopCreate,
    namespace: str = Query(default="default", description="Kubernetes namespace"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new workshop owned by the authenticated user."""
    try:
        logger.info(
            f"Creating workshop {workshop.name} in namespace {namespace} "
            f"for {current_user.email}"
        )
        result = await workshop_service.create_workshop(
            workshop, owner_email=current_user.email, namespace=namespace
        )
        return result
    except Exception as e:
        logger.error(f"Failed to create workshop: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workshop: {str(e)}",
        )


@router.get("/", response_model=WorkshopList)
async def list_workshops(
    namespace: str = Query(default="default", description="Kubernetes namespace"),
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=50, ge=1, le=100, description="Page size"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List workshops.

    Regular users see only their own workshops. Admins see all workshops.
    """
    try:
        # Admins can see all workshops; regular users are filtered to their own.
        owner_filter = None if current_user.is_admin else current_user.email
        workshops = await workshop_service.list_workshops(
            namespace=namespace, owner_email=owner_filter
        )

        start = (page - 1) * size
        end = start + size
        paginated = workshops[start:end]

        return WorkshopList(
            items=paginated, total=len(workshops), page=page, size=size
        )
    except Exception as e:
        logger.error(f"Failed to list workshops: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workshops: {str(e)}",
        )


@router.get("/{workshop_name}", response_model=WorkshopResponse)
async def get_workshop(
    workshop_name: str = Path(..., description="Workshop name"),
    namespace: str = Query(default="default", description="Kubernetes namespace"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a workshop by name.

    Returns 404 if the workshop does not exist or belongs to another user
    (avoids leaking existence information).
    """
    try:
        workshop = await workshop_service.get_workshop(workshop_name, namespace)
        if not workshop or not _can_access(current_user, workshop):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workshop {workshop_name} not found",
            )
        return workshop
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workshop {workshop_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workshop: {str(e)}",
        )


@router.delete("/{workshop_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workshop(
    workshop_name: str = Path(..., description="Workshop name"),
    namespace: str = Query(default="default", description="Kubernetes namespace"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Delete a workshop.

    Returns 404 if the workshop does not exist or belongs to another user.
    """
    try:
        workshop = await workshop_service.get_workshop(workshop_name, namespace)
        if not workshop or not _can_access(current_user, workshop):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workshop {workshop_name} not found",
            )
        await workshop_service.delete_workshop(workshop_name, namespace)
        logger.info(
            f"Deleted workshop {workshop_name} by {current_user.email}"
        )
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workshop {workshop_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workshop: {str(e)}",
        )


@router.get("/{workshop_name}/status", response_model=dict)
async def get_workshop_status(
    workshop_name: str = Path(..., description="Workshop name"),
    namespace: str = Query(default="default", description="Kubernetes namespace"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get workshop status information."""
    try:
        workshop = await workshop_service.get_workshop(workshop_name, namespace)
        if not workshop or not _can_access(current_user, workshop):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workshop {workshop_name} not found",
            )

        return {
            "name": workshop.name,
            "namespace": workshop.namespace,
            "owner": workshop.owner,
            "status": workshop.status.model_dump() if workshop.status else None,
            "url": workshop.status.url if workshop.status else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workshop status {workshop_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workshop status: {str(e)}",
        )


def _can_access(user: CurrentUser, workshop: WorkshopResponse) -> bool:
    """Return True if the user may read or modify this workshop.

    Legacy CRs without an owner (created before ownership was added) are
    visible only to admins.
    """
    if workshop.owner is None:
        return user.is_admin
    return user.is_admin or workshop.owner == user.email
