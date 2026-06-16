# Import all ORM models here so Alembic autogenerate sees them.
# Templates are git-managed YAML, not a DB table (ADR-0006).
from api.models.db.workshop_instance import (  # noqa: F401
    InstanceEvent,
    WorkshopInstance,
)
