"""In-memory registry of git-managed workshop templates (ADR-0006 phase 4).

Loads ``deploy/templates/*.yaml`` (mounted via a ConfigMap in production) into
memory and serves the read + launch paths. It mirrors the read-side interface of
``WorkshopTemplateService`` (async methods that accept a ``db`` they ignore), so
routes can depend on either source uniformly while the migration is in flight.

The registry is the source of truth in file mode; the database template table is
retired in a later phase.
"""

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml

from api.core.config import get_settings
from api.models.schemas.workshop_template import (
    WorkshopTemplateFile,
    WorkshopTemplateResponse,
)

logger = logging.getLogger(__name__)

# Fixed namespace so a slug always maps to the same template id across restarts
# and replicas. Lets the existing id-based API surface keep working for files.
_TEMPLATE_ID_NAMESPACE = uuid.UUID("6f3a5f7e-9b2c-4d1a-8e6f-0a1b2c3d4e5f")


def stable_template_id(slug: str) -> uuid.UUID:
    """Deterministic template id derived from the slug."""
    return uuid.uuid5(_TEMPLATE_ID_NAMESPACE, slug)


def _to_response(
    tmpl: WorkshopTemplateFile, loaded_at: datetime
) -> WorkshopTemplateResponse:
    return WorkshopTemplateResponse(
        id=stable_template_id(tmpl.slug),
        name=tmpl.name,
        slug=tmpl.slug,
        description=tmpl.description,
        image=tmpl.image,
        defaultDuration=tmpl.default_duration,
        port=tmpl.port,
        tier=tmpl.tier,
        env=tmpl.env,
        args=tmpl.args,
        resources=tmpl.resources,
        storage=tmpl.storage,
        tags=tmpl.tags,
        isActive=tmpl.enabled,
        createdBy="git",
        createdAt=loaded_at,
        updatedAt=loaded_at,
    )


class TemplateRegistry:
    """Read-only view over the templates loaded from a directory."""

    def __init__(self, templates: list[WorkshopTemplateResponse]):
        self._by_id = {t.id: t for t in templates}
        self._by_slug = {t.slug: t for t in templates}

    @classmethod
    def from_dir(cls, path: Path | str) -> "TemplateRegistry":
        """Load and validate every ``*.yaml`` in ``path``.

        A malformed file raises during load (fail fast at startup) — the CI gate
        in ``test_template_files.py`` should catch this before deploy.
        """
        directory = Path(path)
        loaded_at = datetime.now(UTC)
        templates: list[WorkshopTemplateResponse] = []
        if not directory.is_dir():
            logger.warning(
                "Templates dir %s does not exist; registry is empty", directory
            )
            return cls(templates)
        for file in sorted(directory.glob("*.yaml")):
            data = yaml.safe_load(file.read_text())
            tmpl = WorkshopTemplateFile.model_validate(data)
            templates.append(_to_response(tmpl, loaded_at))
        logger.info("Loaded %d template(s) from %s", len(templates), directory)
        return cls(templates)

    # ── Read interface (mirrors WorkshopTemplateService; db is ignored) ────────

    async def list_templates(
        self,
        db=None,
        *,
        include_inactive: bool = False,
        page: int = 1,
        size: int = 50,
    ) -> tuple[list[WorkshopTemplateResponse], int]:
        items = [t for t in self._by_id.values() if include_inactive or t.is_active]
        items.sort(key=lambda t: t.name)
        total = len(items)
        start = (page - 1) * size
        return items[start : start + size], total

    async def get_template(
        self, db=None, template_id: uuid.UUID | None = None
    ) -> WorkshopTemplateResponse | None:
        return self._by_id.get(template_id)

    async def get_template_by_slug(
        self, db=None, slug: str = ""
    ) -> WorkshopTemplateResponse | None:
        return self._by_slug.get(slug)


_registry: TemplateRegistry | None = None


def get_registry() -> TemplateRegistry:
    """Return the process-wide registry, loading it on first use."""
    global _registry  # noqa: PLW0603 — module-level singleton cache
    if _registry is None:
        _registry = TemplateRegistry.from_dir(get_settings().templates_dir)
    return _registry


def reset_registry() -> None:
    """Drop the cached registry (used by tests and for reload)."""
    global _registry  # noqa: PLW0603 — module-level singleton cache
    _registry = None
