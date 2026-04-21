"""Workshop template routes (admin CRUD + user launch)."""

import logging
import random
import string
import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.auth import CurrentUser, get_current_user, require_admin
from api.core.config import get_settings
from api.core.database import get_db
from api.models.schemas.workshop_instance import TemplateStats, WorkshopInstanceResponse
from api.models.schemas.workshop_template import (
    WorkshopLaunchRequest,
    WorkshopTemplateCreate,
    WorkshopTemplateList,
    WorkshopTemplateResponse,
    WorkshopTemplateUpdate,
)
from api.services.workshop_instance_service import (
    WorkshopInstanceService,
    get_instance_service,
)
from api.services.workshop_template_service import (
    WorkshopTemplateService,
    get_template_service,
)

logger = logging.getLogger(__name__)
router = APIRouter()


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
    svc: WorkshopTemplateService = Depends(get_template_service),
):
    """List workshop templates. Inactive templates are hidden unless admin requests them."""
    show_inactive = include_inactive and current_user.is_admin
    items, total = await svc.list_templates(
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
    svc: WorkshopTemplateService = Depends(get_template_service),
):
    """Create a new workshop template (admin only)."""
    existing = await svc.get_template_by_slug(db, data.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A template with slug '{data.slug}' already exists",
        )
    return await svc.create_template(db, data, created_by=current_user.email)


@router.get("/stats", response_model=list[TemplateStats])
async def list_template_stats(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    svc: WorkshopInstanceService = Depends(get_instance_service),
):
    """Launch counts for all templates (available to all authenticated users)."""
    return await svc.get_bulk_launch_counts(db)


@router.get("/{template_id}", response_model=WorkshopTemplateResponse)
async def get_template(
    template_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    svc: WorkshopTemplateService = Depends(get_template_service),
):
    """Get a workshop template by ID."""
    template = await svc.get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
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
    svc: WorkshopTemplateService = Depends(get_template_service),
):
    """Update a workshop template (admin only)."""
    template = await svc.update_template(db, template_id, data)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return template


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_template(
    template_id: uuid.UUID = Path(...),
    hard: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    svc: WorkshopTemplateService = Depends(get_template_service),
):
    """Archive a workshop template (admin only).

    Defaults to soft-delete (isActive=False). Use ?hard=true for permanent removal.
    """
    found = await svc.archive_template(db, template_id, hard_delete=hard)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )


@router.patch(
    "/{template_id}/toggle-active",
    response_model=WorkshopTemplateResponse,
    dependencies=[Depends(require_admin)],
)
async def toggle_template_active(
    template_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    svc: WorkshopTemplateService = Depends(get_template_service),
):
    """Toggle a template's isActive status (admin only)."""
    template = await svc.get_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    updated = await svc.update_template(
        db, template_id, WorkshopTemplateUpdate(isActive=not template.is_active)
    )
    return updated


# ---------------------------------------------------------------------------
# Template stats endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{template_id}/stats",
    response_model=TemplateStats,
    dependencies=[Depends(require_admin)],
)
async def get_template_stats(
    template_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    svc: WorkshopInstanceService = Depends(get_instance_service),
):
    """Aggregate launch and utilization statistics for a template (admin only)."""
    stats = await svc.get_template_stats(db, template_id)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return stats


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
    settings=Depends(get_settings),
    template_svc: WorkshopTemplateService = Depends(get_template_service),
    instance_svc: WorkshopInstanceService = Depends(get_instance_service),
):
    """Launch a new workshop instance from a template.

    The instance name is auto-generated as ``{slug}-{6-char suffix}``.
    Duration defaults to the template's default if not supplied.
    """
    template = await template_svc.get_template(db, template_id)
    if not template or not template.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or inactive",
        )

    k8s_name = f"{template.slug}-{_random_suffix()}"
    duration = body.duration or template.default_duration
    namespace = body.namespace or settings.default_namespace

    try:
        instance = await instance_svc.launch(
            db,
            template=template,
            k8s_name=k8s_name,
            namespace=namespace,
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
