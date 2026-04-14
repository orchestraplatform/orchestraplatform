"""Workshop API routes."""

import logging
from typing import List, Optional

try:
    from fastapi import APIRouter, HTTPException, Query, Path, status
    from fastapi.responses import JSONResponse
except ImportError:
    # Fallback when FastAPI is not installed
    class APIRouter:
        def __init__(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): pass
        def post(self, *args, **kwargs): pass
        def delete(self, *args, **kwargs): pass
    HTTPException = Exception
    Query = Path = lambda *args, **kwargs: None
    JSONResponse = dict

from api.models.workshop import (
    WorkshopCreate,
    WorkshopResponse, 
    WorkshopList,
    ErrorResponse
)
from api.services.workshop_service import WorkshopService

logger = logging.getLogger(__name__)
router = APIRouter()
workshop_service = WorkshopService()


@router.post("/", response_model=WorkshopResponse, status_code=status.HTTP_201_CREATED)
async def create_workshop(
    workshop: WorkshopCreate,
    namespace: str = Query(default="default", description="Kubernetes namespace")
):
    """Create a new workshop."""
    try:
        logger.info(f"Creating workshop {workshop.name} in namespace {namespace}")
        result = await workshop_service.create_workshop(workshop, namespace)
        return result
    except Exception as e:
        logger.error(f"Failed to create workshop: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workshop: {str(e)}"
        )


@router.get("/", response_model=WorkshopList)
async def list_workshops(
    namespace: str = Query(default="default", description="Kubernetes namespace"),
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=50, ge=1, le=100, description="Page size")
):
    """List workshops in a namespace."""
    try:
        workshops = await workshop_service.list_workshops(namespace)
        
        # Simple pagination
        start = (page - 1) * size
        end = start + size
        paginated_workshops = workshops[start:end]
        
        return WorkshopList(
            items=paginated_workshops,
            total=len(workshops),
            page=page,
            size=size
        )
    except Exception as e:
        logger.error(f"Failed to list workshops: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workshops: {str(e)}"
        )


@router.get("/{workshop_name}", response_model=WorkshopResponse)
async def get_workshop(
    workshop_name: str = Path(..., description="Workshop name"),
    namespace: str = Query(default="default", description="Kubernetes namespace")
):
    """Get a workshop by name."""
    try:
        workshop = await workshop_service.get_workshop(workshop_name, namespace)
        if not workshop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workshop {workshop_name} not found"
            )
        return workshop
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workshop {workshop_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workshop: {str(e)}"
        )


@router.delete("/{workshop_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workshop(
    workshop_name: str = Path(..., description="Workshop name"),
    namespace: str = Query(default="default", description="Kubernetes namespace")
):
    """Delete a workshop."""
    try:
        deleted = await workshop_service.delete_workshop(workshop_name, namespace)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workshop {workshop_name} not found"
            )
        logger.info(f"Deleted workshop {workshop_name}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workshop {workshop_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workshop: {str(e)}"
        )


@router.get("/{workshop_name}/status", response_model=dict)
async def get_workshop_status(
    workshop_name: str = Path(..., description="Workshop name"),
    namespace: str = Query(default="default", description="Kubernetes namespace")
):
    """Get workshop status information."""
    try:
        workshop = await workshop_service.get_workshop(workshop_name, namespace)
        if not workshop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workshop {workshop_name} not found"
            )
        
        return {
            "name": workshop.name,
            "namespace": workshop.namespace,
            "status": workshop.status.dict() if workshop.status else None,
            "url": workshop.status.url if workshop.status else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workshop status {workshop_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workshop status: {str(e)}"
        )
