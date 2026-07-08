"""Pure desired-state for a Workshop: spec -> child manifests + status dicts.

No I/O happens here. The kopf handler calls desired_children() and hands the
result to the OperatorCluster adapter (cluster.py); tests exercise the full
manifest/naming/owner-reference logic without a cluster.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import kubernetes.client as k8s_client

from config import get_settings
from crd import GROUP, VERSION
from resources.deployment import create_rstudio_deployment
from resources.ingress import create_workshop_ingress
from resources.middleware import create_auth_middleware
from resources.naming import auth_middleware_name
from resources.pvc import create_workshop_pvc
from resources.service import create_workshop_service
from utils.phases import WorkshopPhase
from utils.time_utils import get_expiration_time


@dataclass
class WorkshopChildren:
    """Everything a Workshop CRD wants to exist in the cluster, plus the
    derived facts (URL, expiry) the status will need."""

    workshop_name: str
    deployment: k8s_client.V1Deployment
    service: k8s_client.V1Service
    ingress: dict[str, Any]
    url: str
    expires_at: datetime
    pvc: k8s_client.V1PersistentVolumeClaim | None = None
    middleware: dict[str, Any] | None = None


def _owner_reference_dict(meta: dict[str, Any]) -> dict[str, Any]:
    """ownerReference for raw custom-object manifests (Traefik dicts)."""
    return {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": "Workshop",
        "name": meta["name"],
        "uid": meta["uid"],
        "blockOwnerDeletion": True,
        "controller": True,
    }


def _owner_reference(meta: dict[str, Any]) -> k8s_client.V1OwnerReference:
    """The same reference as a typed object, derived from the dict form."""
    d = _owner_reference_dict(meta)
    return k8s_client.V1OwnerReference(
        api_version=d["apiVersion"],
        kind=d["kind"],
        name=d["name"],
        uid=d["uid"],
        block_owner_deletion=d["blockOwnerDeletion"],
        controller=d["controller"],
    )


def _ingress_url(ingress: dict[str, Any]) -> str:
    """Derive the public URL from an IngressRoute manifest."""
    settings = get_settings()
    entry_points = ingress["spec"].get("entryPoints", ["web"])
    scheme = "https" if "websecure" in entry_points else "http"
    host = ingress["metadata"]["annotations"].get("orchestra.io/host", "")
    port_suffix = f":{settings.ingress_port}" if settings.ingress_port else ""
    return f"{scheme}://{host}{port_suffix}"


def desired_children(
    spec: dict[str, Any], meta: dict[str, Any], namespace: str
) -> WorkshopChildren:
    """Build every child manifest for a Workshop CRD, owner-referenced so
    Kubernetes GC removes them when the Workshop is deleted."""
    settings = get_settings()

    workshop_name = spec.get("name", meta["name"])
    duration = spec.get("duration", "4h")
    image = spec.get("image", settings.default_workshop_image)
    port = spec.get("port", 8787)
    tier = spec.get("tier")
    env = spec.get("env") or {}
    args = spec.get("args") or None
    resources = spec.get("resources", {})
    storage = spec.get("storage", {})
    ingress_config = spec.get("ingress", {})
    # Support both new 'ownerEmail' and legacy 'owner' CRD field names
    owner_email = spec.get("ownerEmail") or spec.get("owner", "unknown")

    owner_ref = _owner_reference(meta)
    owner_ref_dict = _owner_reference_dict(meta)

    pvc = None
    if storage:
        pvc = create_workshop_pvc(workshop_name, namespace, storage)
        pvc.metadata.owner_references = [owner_ref]

    require_auth = bool(settings.auth_middleware or settings.oauth2_proxy_auth_url)
    deployment = create_rstudio_deployment(
        workshop_name,
        namespace,
        image,
        owner_email,
        resources,
        storage,
        require_auth=require_auth,
        port=port,
        env=env,
        args=args,
        tier=tier,
    )
    deployment.metadata.owner_references = [owner_ref]

    service = create_workshop_service(workshop_name, namespace)
    service.metadata.owner_references = [owner_ref]

    middleware = None
    local_auth_middleware: str | None = None
    if settings.oauth2_proxy_auth_url:
        middleware = create_auth_middleware(
            workshop_name, namespace, settings.oauth2_proxy_auth_url
        )
        middleware["metadata"]["ownerReferences"] = [owner_ref_dict]
        local_auth_middleware = auth_middleware_name(workshop_name)

    ingress = create_workshop_ingress(
        workshop_name,
        namespace,
        ingress_config,
        auth_middleware_override=local_auth_middleware,
    )
    ingress["metadata"]["ownerReferences"] = [owner_ref_dict]

    return WorkshopChildren(
        workshop_name=workshop_name,
        deployment=deployment,
        service=service,
        ingress=ingress,
        url=_ingress_url(ingress),
        expires_at=get_expiration_time(duration),
        pvc=pvc,
        middleware=middleware,
    )


# ---------------------------------------------------------------------------
# Status builders (pure)
# ---------------------------------------------------------------------------


def starting_status() -> dict[str, Any]:
    return {"phase": WorkshopPhase.STARTING}


def ready_status(url: str, created_at: str, expires_at: datetime) -> dict[str, Any]:
    return {
        "phase": WorkshopPhase.READY,
        "url": url,
        "createdAt": created_at,
        "expiresAt": expires_at.isoformat(),
        "conditions": [
            {
                "type": "Ready",
                "status": "True",
                "reason": "WorkshopReady",
                "message": "Workshop pod is running and ready",
            }
        ],
    }


def failed_status(message: str) -> dict[str, Any]:
    return {
        "phase": WorkshopPhase.FAILED,
        "conditions": [
            {
                "type": "Ready",
                "status": "False",
                "reason": "CreationFailed",
                "message": message,
            }
        ],
    }
