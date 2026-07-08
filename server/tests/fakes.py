"""In-memory test adapters."""

from datetime import datetime

from api.models.workshop import WorkshopCreate, WorkshopResponse


class FakeWorkshopCluster:
    """In-memory WorkshopCluster adapter.

    Honors the interface contract: get() returns None and delete() returns
    False for a missing Workshop CRD. Set raise_on_create/raise_on_delete to
    inject failures.
    """

    def __init__(self):
        self.workshops: dict[tuple[str, str], WorkshopResponse] = {}
        self.deleted: list[tuple[str, str]] = []
        self.expiries: list[tuple[str, str, datetime]] = []
        self.raise_on_create: Exception | None = None
        self.raise_on_delete: Exception | None = None

    async def create(
        self, workshop: WorkshopCreate, *, owner_email: str, namespace: str
    ) -> WorkshopResponse:
        if self.raise_on_create is not None:
            raise self.raise_on_create
        response = WorkshopResponse(
            name=workshop.name,
            namespace=namespace,
            owner=owner_email,
            spec=workshop,
            status=None,
            created_at=None,
            updated_at=None,
        )
        self.workshops[(namespace, workshop.name)] = response
        return response

    async def get(self, name: str, namespace: str) -> WorkshopResponse | None:
        return self.workshops.get((namespace, name))

    async def delete(self, name: str, namespace: str) -> bool:
        if self.raise_on_delete is not None:
            raise self.raise_on_delete
        self.deleted.append((namespace, name))
        return self.workshops.pop((namespace, name), None) is not None

    async def set_expiry(self, name: str, namespace: str, expires_at: datetime) -> None:
        self.expiries.append((namespace, name, expires_at))
