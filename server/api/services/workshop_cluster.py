"""WorkshopCluster: the server's seam to the cluster for Workshop CRD lifecycle.

Two adapters satisfy the interface: K8sWorkshopCluster (real) and the in-memory
FakeWorkshopCluster in tests. The CRD wire format (camelCase dicts) is hidden
behind it — only typed models cross the seam.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Protocol

from orchestra_template_tools import GROUP, KIND, PLURAL, VERSION, WorkshopSpec

from api.core.kubernetes import ApiException, get_custom_objects_api
from api.models.workshop import (
    WorkshopCondition,
    WorkshopCreate,
    WorkshopPhase,
    WorkshopResponse,
    WorkshopStatus,
)

logger = logging.getLogger(__name__)


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
    """Convert a WorkshopCreate model to a Kubernetes CRD body.

    Serialization goes through the shared WorkshopSpec contract model
    (orchestra-template-tools), which owns the camelCase wire format.
    """
    spec = WorkshopSpec.model_validate(
        {**workshop.model_dump(), "owner": owner_email}
    ).model_dump(by_alias=True, exclude_none=True)
    # Omit empty env/args so the operator applies its defaults.
    for key in ("env", "args"):
        if not spec[key]:
            del spec[key]
    return {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": KIND,
        "metadata": {
            "name": workshop.name,
            "namespace": namespace,
            "labels": {"app": "orchestra-operator", "managed-by": "orchestra-api"},
        },
        "spec": spec,
    }


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

    ws_spec = WorkshopSpec.model_validate(spec)

    return WorkshopResponse(
        name=metadata.get("name"),
        namespace=metadata.get("namespace"),
        # None for legacy CRs created before ownership was added
        owner=ws_spec.owner or None,
        spec=WorkshopCreate.model_validate(ws_spec.model_dump(exclude={"owner"})),
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
