"""WorkshopCluster: the server's seam to the cluster for Workshop CRD lifecycle.

Two adapters satisfy the interface: K8sWorkshopCluster (real) and the in-memory
FakeWorkshopCluster in tests. The CRD wire format (camelCase dicts) is hidden
behind it — only typed models cross the seam.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Protocol

from api.core.kubernetes import ApiException, get_custom_objects_api
from api.models.workshop import (
    WorkshopCondition,
    WorkshopCreate,
    WorkshopIngress,
    WorkshopPhase,
    WorkshopResources,
    WorkshopResponse,
    WorkshopStatus,
    WorkshopStorage,
)

logger = logging.getLogger(__name__)

GROUP = "orchestra.io"
VERSION = "v1"
PLURAL = "workshops"


class WorkshopCluster(Protocol):
    """Interface contract: get() returns None on a missing Workshop CRD,
    delete() returns False on a missing Workshop CRD; all other API errors
    propagate."""

    async def create(
        self, workshop: WorkshopCreate, *, owner_email: str, namespace: str
    ) -> WorkshopResponse: ...

    async def get(self, name: str, namespace: str) -> WorkshopResponse | None: ...

    async def delete(self, name: str, namespace: str) -> bool: ...

    async def set_expiry(
        self, name: str, namespace: str, expires_at: datetime
    ) -> None: ...


# ---------------------------------------------------------------------------
# CRD wire-format mapping (implementation detail of the real adapter)
# ---------------------------------------------------------------------------


def _parse_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None


def _to_kubernetes_crd(
    workshop: WorkshopCreate, owner_email: str, namespace: str
) -> dict[str, Any]:
    """Convert a WorkshopCreate model to a Kubernetes CRD body."""
    crd: dict[str, Any] = {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": "Workshop",
        "metadata": {
            "name": workshop.name,
            "namespace": namespace,
            "labels": {"app": "orchestra-operator", "managed-by": "orchestra-api"},
        },
        "spec": {
            "name": workshop.name,
            "owner": owner_email,
            "duration": workshop.duration,
            "image": workshop.image,
            "port": workshop.port,
            "tier": workshop.tier,
            "resources": {
                "cpu": workshop.resources.cpu,
                "memory": workshop.resources.memory,
                "cpuRequest": workshop.resources.cpu_request,
                "memoryRequest": workshop.resources.memory_request,
                "ephemeralStorage": workshop.resources.ephemeral_storage,
                "ephemeralStorageRequest": workshop.resources.ephemeral_storage_request,
            },
        },
    }
    if workshop.env:
        crd["spec"]["env"] = dict(workshop.env)
    if workshop.args:
        crd["spec"]["args"] = list(workshop.args)
    if workshop.storage:
        crd["spec"]["storage"] = {"size": workshop.storage.size}
        if workshop.storage.storage_class:
            crd["spec"]["storage"]["storageClass"] = workshop.storage.storage_class
    if workshop.ingress:
        crd["spec"]["ingress"] = {}
        if workshop.ingress.host:
            crd["spec"]["ingress"]["host"] = workshop.ingress.host
        if workshop.ingress.annotations:
            crd["spec"]["ingress"]["annotations"] = workshop.ingress.annotations
    return crd


def _from_kubernetes_crd(crd: dict[str, Any]) -> WorkshopResponse:
    """Convert a Kubernetes CRD dict to a WorkshopResponse."""
    metadata = crd.get("metadata", {})
    spec = crd.get("spec", {})
    status = crd.get("status", {})

    workshop_status = None
    if status:
        conditions = [
            WorkshopCondition(
                type=c.get("type"),
                status=c.get("status"),
                reason=c.get("reason"),
                message=c.get("message"),
                last_transition_time=c.get("lastTransitionTime"),
            )
            for c in status.get("conditions", [])
        ]
        raw_phase = status.get("phase", "Pending")
        try:
            phase = WorkshopPhase(raw_phase)
        except ValueError:
            logger.warning(
                "Unknown workshop phase %r from CRD; falling back to Pending",
                raw_phase,
            )
            phase = WorkshopPhase.PENDING
        workshop_status = WorkshopStatus(
            phase=phase,
            url=status.get("url"),
            created_at=_parse_datetime(status.get("createdAt")),
            expires_at=_parse_datetime(status.get("expiresAt")),
            conditions=conditions,
        )

    res = spec.get("resources", {})
    storage_spec = spec.get("storage")
    ingress_spec = spec.get("ingress")

    return WorkshopResponse(
        name=metadata.get("name"),
        namespace=metadata.get("namespace"),
        # Support both old "owner" and new "ownerEmail" CRD field names
        owner=spec.get("ownerEmail") or spec.get("owner") or None,
        spec=WorkshopCreate(
            name=spec.get("name"),
            duration=spec.get("duration", "4h"),
            image=spec.get("image", "rocker/rstudio:latest"),
            port=spec.get("port", 8787),
            tier=spec.get("tier", "small"),
            env=spec.get("env") or {},
            args=spec.get("args") or [],
            resources=WorkshopResources(
                cpu=res.get("cpu", "1"),
                memory=res.get("memory", "2Gi"),
                cpuRequest=res.get("cpuRequest", "500m"),
                memoryRequest=res.get("memoryRequest", "1Gi"),
                ephemeralStorage=res.get("ephemeralStorage", "8Gi"),
                ephemeralStorageRequest=res.get("ephemeralStorageRequest", "8Gi"),
            ),
            storage=WorkshopStorage(
                size=storage_spec.get("size", "10Gi"),
                storageClass=storage_spec.get("storageClass"),
            )
            if storage_spec
            else None,
            ingress=WorkshopIngress(
                host=ingress_spec.get("host"),
                annotations=ingress_spec.get("annotations", {}),
            )
            if ingress_spec
            else None,
        ),
        status=workshop_status,
        created_at=_parse_datetime(metadata.get("creationTimestamp")),
        updated_at=None,
    )


# ---------------------------------------------------------------------------
# Real adapter
# ---------------------------------------------------------------------------


class K8sWorkshopCluster:
    """WorkshopCluster adapter backed by the Kubernetes API.

    The sync kubernetes client is wrapped in asyncio.to_thread so calls don't
    block the event loop (SSE streams poll on the same loop).
    """

    async def create(
        self, workshop: WorkshopCreate, *, owner_email: str, namespace: str
    ) -> WorkshopResponse:
        api = get_custom_objects_api()
        result = await asyncio.to_thread(
            api.create_namespaced_custom_object,
            group=GROUP,
            version=VERSION,
            namespace=namespace,
            plural=PLURAL,
            body=_to_kubernetes_crd(workshop, owner_email, namespace),
        )
        logger.info("Created k8s Workshop CRD %s in %s", workshop.name, namespace)
        return _from_kubernetes_crd(result)

    async def get(self, name: str, namespace: str) -> WorkshopResponse | None:
        api = get_custom_objects_api()
        try:
            result = await asyncio.to_thread(
                api.get_namespaced_custom_object,
                group=GROUP,
                version=VERSION,
                namespace=namespace,
                plural=PLURAL,
                name=name,
            )
        except ApiException as e:
            if e.status == 404:
                return None
            raise
        return _from_kubernetes_crd(result)

    async def delete(self, name: str, namespace: str) -> bool:
        api = get_custom_objects_api()
        try:
            await asyncio.to_thread(
                api.delete_namespaced_custom_object,
                group=GROUP,
                version=VERSION,
                namespace=namespace,
                plural=PLURAL,
                name=name,
            )
        except ApiException as e:
            if e.status == 404:
                return False
            raise
        logger.info("Deleted k8s Workshop CRD %s in %s", name, namespace)
        return True

    async def set_expiry(self, name: str, namespace: str, expires_at: datetime) -> None:
        """Push a new expiry into the Workshop CRD status subresource so the
        operator picks it up."""
        api = get_custom_objects_api()
        await asyncio.to_thread(
            api.patch_namespaced_custom_object_status,
            group=GROUP,
            version=VERSION,
            namespace=namespace,
            plural=PLURAL,
            name=name,
            body={"status": {"expiresAt": expires_at.isoformat()}},
        )
