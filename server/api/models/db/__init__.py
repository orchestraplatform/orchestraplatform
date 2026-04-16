# Import all ORM models here so Alembic autogenerate sees them.
from api.models.db.workshop import Workshop  # noqa: F401
from api.models.db.workshop_instance import (  # noqa: F401
    InstanceEvent,
    WorkshopInstance,
)
