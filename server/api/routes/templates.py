"""Workshop template routes — read + launch.

Templates are git-managed YAML served from an in-memory registry (ADR-0006).
There are no imperative create/update/delete endpoints: the catalog is changed
by editing files under deploy/charts/orchestra/files/templates/ via a PR.
"""

import logging
import random
import string
import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.auth import CurrentUser, get_current_user, require_admin
from api.core.config import get_settings
from api.core.database import get_db
from api.models.schemas.workshop_instance import (
    LaunchConflict,
    TemplateStats,
    WorkshopInstanceResponse,
)
from api.models.schemas.workshop_template import (
    WorkshopLaunchRequest,
    WorkshopTemplateList,
    WorkshopTemplateResponse,
)
from api.services.template_registry import TemplateRegistry, get_registry
from api.services.workshop_instance_service import (
    ActiveSessionConflictError,
    WorkshopInstanceService,
    get_instance_service,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _random_suffix(length: int = 6) -> str:
    """Return a random lowercase alphanumeric string of the given length."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def get_template_reader() -> TemplateRegistry:
    """Source for template reads + launch (the git-managed file registry)."""
    return get_registry()


# ---------------------------------------------------------------------------
# Template endpoints — read-only; the catalog is managed in git
# ---------------------------------------------------------------------------


@router.get("/", response_model=WorkshopTemplateList)
async def list_templates(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
    include_inactive: bool = Query(default=False),
    current_user: CurrentUser = Depends(get_current_user),
    reader: TemplateRegistry = Depends(get_template_reader),
):
    """List workshop templates. Disabled templates are hidden unless admin asks."""
    show_inactive = include_inactive and current_user.is_admin
    items, total = await reader.list_templates(
        include_inactive=show_inactive, page=page, size=size
    )
    return WorkshopTemplateList(items=items, total=total, page=page, size=size)


@router.get("/stats", response_model=list[TemplateStats])
async def list_template_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    svc: WorkshopInstanceService = Depends(get_instance_service),
):
    """Launch counts for all templates (available to all authenticated users)."""
    return await svc.get_bulk_launch_counts(db)


@router.get("/{template_id}", response_model=WorkshopTemplateResponse)
async def get_template(
    template_id: uuid.UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    reader: TemplateRegistry = Depends(get_template_reader),
):
    """Get a workshop template by ID."""
    template = await reader.get_template(template_id=template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return template


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
    responses={
        status.HTTP_409_CONFLICT: {
            "model": LaunchConflict,
            "description": "The caller already has an active session of this "
            "persistence-enabled workshop (ADR-0010 decision F). Continue with "
            "the returned instance, or relaunch with replaceExisting=true to "
            "terminate it and start fresh.",
        }
    },
)
async def launch_workshop(
    body: WorkshopLaunchRequest,
    template_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    settings=Depends(get_settings),
    reader: TemplateRegistry = Depends(get_template_reader),
    instance_svc: WorkshopInstanceService = Depends(get_instance_service),
):
    """Launch a new workshop instance from a template.

    The instance name is auto-generated as ``{slug}-{6-char suffix}``.
    Duration defaults to the template's default if not supplied.
    """
    template = await reader.get_template(template_id=template_id)
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
            replace_existing=body.replace_existing,
        )
    except ActiveSessionConflictError as e:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=LaunchConflict(instance=e.existing).model_dump(
                mode="json", by_alias=True
            ),
        )
    except Exception as e:
        logger.error("Failed to launch workshop instance: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to launch workshop: {e}",
        )

    return instance
