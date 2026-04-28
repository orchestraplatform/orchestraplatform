"""Service layer for Workshop templates (DB-backed)."""

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db.workshop import Workshop
from api.models.schemas.workshop_template import (
    WorkshopTemplateCreate,
    WorkshopTemplateResponse,
    WorkshopTemplateUpdate,
)

logger = logging.getLogger(__name__)


def _to_response(row: Workshop) -> WorkshopTemplateResponse:
    """Convert an ORM row to the Pydantic response schema."""
    return WorkshopTemplateResponse(
        id=row.id,
        name=row.name,
        slug=row.slug,
        description=row.description,
        image=row.image,
        defaultDuration=row.default_duration,
        resources=row.resources,
        storage=row.storage,
        tags=row.tags or [],
        isActive=row.is_active,
        createdBy=row.created_by,
        createdAt=row.created_at,
        updatedAt=row.updated_at,
    )


class WorkshopTemplateService:
    """CRUD operations for Workshop templates."""

    async def list_templates(
        self,
        db: AsyncSession,
        *,
        include_inactive: bool = False,
        page: int = 1,
        size: int = 50,
    ) -> tuple[list[WorkshopTemplateResponse], int]:
        """Return a paginated list of templates and the total count."""
        query = select(Workshop)
        if not include_inactive:
            query = query.where(Workshop.is_active.is_(True))
        query = query.order_by(Workshop.name)

        total_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar_one()

        offset = (page - 1) * size
        result = await db.execute(query.offset(offset).limit(size))
        rows = result.scalars().all()
        return [_to_response(r) for r in rows], total

    async def get_template(
        self, db: AsyncSession, template_id: uuid.UUID
    ) -> WorkshopTemplateResponse | None:
        """Fetch a single template by ID."""
        result = await db.execute(select(Workshop).where(Workshop.id == template_id))
        row = result.scalar_one_or_none()
        return _to_response(row) if row else None

    async def get_template_by_slug(
        self, db: AsyncSession, slug: str
    ) -> WorkshopTemplateResponse | None:
        """Fetch a template by slug."""
        result = await db.execute(select(Workshop).where(Workshop.slug == slug))
        row = result.scalar_one_or_none()
        return _to_response(row) if row else None

    async def create_template(
        self,
        db: AsyncSession,
        data: WorkshopTemplateCreate,
        created_by: str,
    ) -> WorkshopTemplateResponse:
        """Create a new workshop template."""
        row = Workshop(
            name=data.name,
            slug=data.slug,
            description=data.description,
            image=data.image,
            default_duration=data.default_duration,
            resources=data.resources.model_dump(by_alias=False),
            storage=data.storage.model_dump(by_alias=False) if data.storage else None,
            tags=data.tags,
            is_active=True,
            created_by=created_by,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        logger.info("Created workshop template %s (slug=%s)", row.name, row.slug)
        return _to_response(row)

    async def update_template(
        self,
        db: AsyncSession,
        template_id: uuid.UUID,
        data: WorkshopTemplateUpdate,
    ) -> WorkshopTemplateResponse | None:
        """Partially update a template. Returns None if not found."""
        result = await db.execute(select(Workshop).where(Workshop.id == template_id))
        row = result.scalar_one_or_none()
        if row is None:
            return None

        if data.name is not None:
            row.name = data.name
        if data.description is not None:
            row.description = data.description
        if data.image is not None:
            row.image = data.image
        if data.default_duration is not None:
            row.default_duration = data.default_duration
        if data.resources is not None:
            row.resources = data.resources.model_dump(by_alias=False)
        if data.storage is not None:
            row.storage = data.storage.model_dump(by_alias=False)
        if data.tags is not None:
            row.tags = data.tags
        if data.is_active is not None:
            row.is_active = data.is_active

        await db.commit()
        await db.refresh(row)
        logger.info("Updated workshop template %s", template_id)
        return _to_response(row)

    async def archive_template(
        self, db: AsyncSession, template_id: uuid.UUID, hard_delete: bool = False
    ) -> bool:
        """Archive (soft-delete) or permanently delete a template."""
        from api.models.db.workshop_instance import WorkshopInstance

        result = await db.execute(select(Workshop).where(Workshop.id == template_id))
        row = result.scalar_one_or_none()
        if row is None:
            return False

        if hard_delete:
            # Check if instances exist
            inst_result = await db.execute(
                select(WorkshopInstance)
                .where(WorkshopInstance.workshop_id == template_id)
                .limit(1)
            )
            if inst_result.scalar_one_or_none():
                logger.warning(
                    "Refusing to hard-delete template %s: instances exist", template_id
                )
                # Fallback to soft-delete
                row.is_active = False
            else:
                await db.delete(row)
                logger.info("Hard-deleted workshop template %s", template_id)
        else:
            row.is_active = False
            logger.info("Archived (soft-deleted) workshop template %s", template_id)

        await db.commit()
        return True


def get_template_service() -> WorkshopTemplateService:
    """FastAPI dependency — returns a WorkshopTemplateService instance."""
    return WorkshopTemplateService()
