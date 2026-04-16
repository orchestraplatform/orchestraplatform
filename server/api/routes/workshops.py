"""Workshop template routes (admin CRUD + user launch)."""

import logging
import random
import string
import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.auth import CurrentUser, get_current_user, require_admin
from api.core.database import get_db
from api.models.schemas.workshop_template import (
    WorkshopLaunchRequest,
    WorkshopTemplateCreate,
    WorkshopTemplateList,
    WorkshopTemplateResponse,
    WorkshopTemplateUpdate,
)
from api.models.schemas.workshop_instance import WorkshopInstanceResponse
from api.services.workshop_template_service import WorkshopTemplateService
from api.services.workshop_instance_service import WorkshopInstanceService

logger = logging.getLogger(__name__)
router = APIRouter()
template_service = WorkshopTemplateService()
instance_service = WorkshopInstanceService()


def _random_suffix(length: int = 6) -> str:
    """Return a random lowercase alphanumeric string of the given length."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


# ---------------------------------------------------------------------------
# Template endpoints (GET open to all; mutating endpoints require admin)
# ---------------------------------------------------------------------------

@router.get("/", response_model=WorkshopTemplateList)
async def list_templates(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
    include_inactive: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List workshop templates. Inactive templates are hidden unless admin requests them."""
    show_inactive = include_inactive and current_user.is_admin
    items, total = await template_service.list_templates(
        db, include_inactive=show_inactive, page=page, size=size
    )
    return WorkshopTemplateList(items=items, total=total, page=page, size=size)


@router.post(
    "/",
    response_model=WorkshopTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_template(
    data: WorkshopTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new workshop template (admin only)."""
    existing = await template_service.get_template_by_slug(db, data.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A template with slug '{data.slug}' already exists",
        )
    return await template_service.create_template(db, data, created_by=current_user.email)


@router.get("/{template_id}", response_model=WorkshopTemplateResponse)
async def get_template(
    template_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a workshop template by ID."""
    template = await template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


@router.put(
    "/{template_id}",
    response_model=WorkshopTemplateResponse,
    dependencies=[Depends(require_admin)],
)
async def update_template(
    data: WorkshopTemplateUpdate,
    template_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
):
    """Update a workshop template (admin only)."""
    template = await template_service.update_template(db, template_id, data)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def archive_template(
    template_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
):
    """Archive a workshop template (admin only). Sets is_active=False; does not hard-delete."""
    found = await template_service.archive_template(db, template_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return None


# ---------------------------------------------------------------------------
# Launch endpoint — creates a WorkshopInstance from a template
# ---------------------------------------------------------------------------

@router.post(
    "/{template_id}/launch",
    response_model=WorkshopInstanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def launch_workshop(
    body: WorkshopLaunchRequest,
    template_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Launch a new workshop instance from a template.

    The instance name is auto-generated as ``{slug}-{6-char suffix}``.
    Duration defaults to the template's default if not supplied.
    """
    template = await template_service.get_template(db, template_id)
    if not template or not template.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or inactive",
        )

    k8s_name = f"{template.slug}-{_random_suffix()}"
    duration = body.duration or template.default_duration

    try:
        instance = await instance_service.launch(
            db,
            template=template,
            k8s_name=k8s_name,
            namespace=body.namespace,
            owner_email=current_user.email,
            duration=duration,
        )
    except Exception as e:
        logger.error("Failed to launch workshop instance: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to launch workshop: {e}",
        )

    return instance
