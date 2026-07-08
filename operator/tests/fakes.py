"""In-memory test adapters."""

from resources.desired import WorkshopChildren


class FakeOperatorCluster:
    """In-memory OperatorCluster adapter.

    apply() records the children; deployment_ready() returns the `ready`
    toggle; delete_workshop() honors the contract (False when nothing was
    deleted). Set raise_on_apply/raise_on_delete to inject failures.
    """

    def __init__(self, ready: bool = True):
        self.ready = ready
        self.applied: list[tuple[WorkshopChildren, str]] = []
        self.workshops: set[tuple[str, str]] = set()
        self.deleted: list[tuple[str, str]] = []
        self.raise_on_apply: Exception | None = None
        self.raise_on_delete: Exception | None = None

    async def apply(self, children: WorkshopChildren, namespace: str) -> None:
        if self.raise_on_apply is not None:
            raise self.raise_on_apply
        self.applied.append((children, namespace))
        self.workshops.add((namespace, children.workshop_name))

    async def deployment_ready(self, workshop_name: str, namespace: str) -> bool:
        return self.ready

    async def delete_workshop(self, name: str, namespace: str) -> bool:
        if self.raise_on_delete is not None:
            raise self.raise_on_delete
        self.deleted.append((namespace, name))
        try:
            self.workshops.remove((namespace, name))
            return True
        except KeyError:
            return False
