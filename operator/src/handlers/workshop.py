"""Workshop event handlers for the Orchestra Operator."""

import logging
from typing import Any

import kopf
import kubernetes.client as k8s_client
from kubernetes.client.rest import ApiException

from config import get_settings
from crd import GROUP, PLURAL, VERSION
from resources.deployment import create_rstudio_deployment
from resources.ingress import create_workshop_ingress
from resources.middleware import create_auth_middleware
from resources.pvc import create_workshop_pvc
from resources.service import create_workshop_service
from utils.time_utils import get_expiration_time

logger = logging.getLogger(__name__)


def _ingress_url(ingress: dict[str, Any]) -> str:
    """Derive the public URL from an IngressRoute manifest."""
    settings = get_settings()
    entry_points = ingress["spec"].get("entryPoints", ["web"])
    scheme = "https" if "websecure" in entry_points else "http"
    host = ingress["metadata"]["annotations"].get("orchestra.io/host", "")
    port_suffix = f":{settings.ingress_port}" if settings.ingress_port else ""
    return f"{scheme}://{host}{port_suffix}"


def _create_or_ignore(api_call, kind: str, name: str) -> None:
    """Run a k8s create call; silently skip if the resource already exists (409)."""
    try:
        api_call()
    except ApiException as e:
        if e.status == 409:
            logger.info("%s %s already exists", kind, name)
        else:
            raise


def _owner_ref(meta: dict[str, Any]) -> k8s_client.V1OwnerReference:
    """Build an OwnerReference pointing at the Workshop CRD being handled."""
    return k8s_client.V1OwnerReference(
        api_version=f"{GROUP}/{VERSION}",
        kind="Workshop",
        name=meta["name"],
        uid=meta["uid"],
        block_owner_deletion=True,
        controller=True,
    )


def _owner_ref_dict(meta: dict[str, Any]) -> dict[str, Any]:
    """Build an ownerReference dict for raw Traefik custom objects."""
    return {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": "Workshop",
        "name": meta["name"],
        "uid": meta["uid"],
        "blockOwnerDeletion": True,
        "controller": True,
    }


@kopf.on.create(GROUP, VERSION, PLURAL)
async def workshop_create_handler(
    spec: dict[str, Any],
    meta: dict[str, Any],
    patch,
    namespace: str,
    name: str,
    **kwargs: Any,
) -> None:
    """Handle Workshop creation events.

    Resources are created idempotently so kopf can safely retry after a
    TemporaryError. OwnerReferences on every child resource mean Kubernetes
    GC cleans them up automatically when the Workshop CRD is deleted.
    """
    logger.info("Creating workshop %s in namespace %s", name, namespace)
    settings = get_settings()

    try:
        workshop_name = spec.get("name", name)
        duration = spec.get("duration", "4h")
        image = spec.get("image", settings.default_workshop_image)
        resources = spec.get("resources", {})
        storage = spec.get("storage", {})
        ingress_config = spec.get("ingress", {})
        owner_email = spec.get("owner", "unknown")

        expiration_time = get_expiration_time(duration)
        owner_ref = _owner_ref(meta)
        owner_ref_dict = _owner_ref_dict(meta)

        k8s_apps_v1 = k8s_client.AppsV1Api()
        k8s_core_v1 = k8s_client.CoreV1Api()
        k8s_custom_objects_v1 = k8s_client.CustomObjectsApi()

        if storage:
            pvc = create_workshop_pvc(workshop_name, namespace, storage)
            pvc.metadata.owner_references = [owner_ref]
            _create_or_ignore(
                lambda: k8s_core_v1.create_namespaced_persistent_volume_claim(
                    namespace=namespace, body=pvc
                ),
                "PVC", workshop_name,
            )

        require_auth = bool(settings.auth_middleware or settings.oauth2_proxy_auth_url)
        deployment = create_rstudio_deployment(
            workshop_name, namespace, image, owner_email, resources, storage,
            require_auth=require_auth,
        )
        deployment.metadata.owner_references = [owner_ref]
        _create_or_ignore(
            lambda: k8s_apps_v1.create_namespaced_deployment(
                namespace=namespace, body=deployment
            ),
            "Deployment", workshop_name,
        )

        service = create_workshop_service(workshop_name, namespace)
        service.metadata.owner_references = [owner_ref]
        _create_or_ignore(
            lambda: k8s_core_v1.create_namespaced_service(namespace=namespace, body=service),
            "Service", workshop_name,
        )

        local_auth_middleware: str | None = None
        if settings.oauth2_proxy_auth_url:
            middleware = create_auth_middleware(
                workshop_name, namespace, settings.oauth2_proxy_auth_url
            )
            middleware["metadata"]["ownerReferences"] = [owner_ref_dict]
            _create_or_ignore(
                lambda: k8s_custom_objects_v1.create_namespaced_custom_object(
                    group="traefik.io", version="v1alpha1",
                    namespace=namespace, plural="middlewares", body=middleware,
                ),
                "Middleware", workshop_name,
            )
            local_auth_middleware = f"{workshop_name}-auth"

        ingress = create_workshop_ingress(
            workshop_name, namespace, ingress_config,
            auth_middleware_override=local_auth_middleware,
        )
        ingress["metadata"]["ownerReferences"] = [owner_ref_dict]
        _create_or_ignore(
            lambda: k8s_custom_objects_v1.create_namespaced_custom_object(
                group="traefik.io", version="v1alpha1",
                namespace=namespace, plural="ingressroutes", body=ingress,
            ),
            "IngressRoute", workshop_name,
        )
        workshop_url = _ingress_url(ingress)

        # Check readiness — requeue cleanly if the pod isn't up yet.
        dep = k8s_apps_v1.read_namespaced_deployment(
            name=f"{workshop_name}-deployment", namespace=namespace
        )
        if (dep.status.ready_replicas or 0) < 1:
            patch["status"] = {"phase": "Starting"}
            raise kopf.TemporaryError("Workshop pod not yet ready", delay=15)

        logger.info("Workshop %s is ready", workshop_name)
        patch["status"] = {
            "phase": "Ready",
            "url": workshop_url,
            "createdAt": meta.get("creationTimestamp", ""),
            "expiresAt": expiration_time.isoformat(),
            "conditions": [
                {
                    "type": "Ready",
                    "status": "True",
                    "reason": "WorkshopReady",
                    "message": "Workshop pod is running and ready",
                }
            ],
        }

    except (kopf.PermanentError, kopf.TemporaryError):
        raise
    except Exception as e:
        logger.error("Failed to create workshop %s: %s", name, e)
        patch["status"] = {
            "phase": "Failed",
            "conditions": [
                {
                    "type": "Ready",
                    "status": "False",
                    "reason": "CreationFailed",
                    "message": str(e),
                }
            ],
        }
        raise kopf.PermanentError(str(e))


@kopf.on.update(GROUP, VERSION, PLURAL)
async def workshop_update_handler(
    spec: dict[str, Any],
    status: dict[str, Any],
    namespace: str,
    name: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Handle Workshop update events."""
    logger.info("Workshop %s updated (no-op for now)", name)
    return {"phase": status.get("phase", "Ready")}
