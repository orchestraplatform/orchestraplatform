"""In-memory test adapters."""

import kubernetes.client as k8s

from resources.desired import WorkshopChildren


class FakeOperatorCluster:
    """In-memory OperatorCluster adapter.

    apply() records the children; deployment_ready() returns the `ready`
    toggle; delete_workshop() honors the contract (False when nothing was
    deleted). Set raise_on_apply/raise_on_delete to inject failures.
    Workspace-PVC methods operate on `pvcs` (keyed (namespace, name)) and the
    `mounted` set; stamps and deletions are recorded.
    """

    def __init__(self, ready: bool = True):
        self.ready = ready
        self.applied: list[tuple[WorkshopChildren, str]] = []
        self.workshops: set[tuple[str, str]] = set()
        self.deleted: list[tuple[str, str]] = []
        self.raise_on_apply: Exception | None = None
        self.raise_on_delete: Exception | None = None
        self.pvcs: dict[tuple[str, str], k8s.V1PersistentVolumeClaim] = {}
        self.mounted: set[tuple[str, str]] = set()
        self.stamped: list[tuple[str, str]] = []
        self.deleted_pvcs: list[tuple[str, str]] = []

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

    async def stamp_pvc_last_used(self, name: str, namespace: str) -> None:
        # Like the real adapter, a missing PVC is a no-op — still recorded so
        # tests can assert the stamp was attempted.
        self.stamped.append((namespace, name))

    async def list_workspace_pvcs(self) -> list[k8s.V1PersistentVolumeClaim]:
        return list(self.pvcs.values())

    async def mounted_pvcs(self) -> set[tuple[str, str]]:
        return set(self.mounted)

    async def delete_pvc(self, name: str, namespace: str) -> None:
        self.pvcs.pop((namespace, name), None)
        self.deleted_pvcs.append((namespace, name))
