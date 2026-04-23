"""Workshop event handlers for the Orchestra Operator."""

import asyncio
import logging
import random
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


@kopf.on.create(GROUP, VERSION, PLURAL)
async def workshop_create_handler(
    spec: dict[str, Any],
    meta: dict[str, Any],
    patch,
    status: dict[str, Any],
    namespace: str,
    name: str,
    **kwargs: Any,
) -> None:
    """Handle Workshop creation events."""
    logger.info("Creating workshop %s in namespace %s", name, namespace)
    settings = get_settings()

    try:
        await update_workshop_status(
            namespace, name, "Creating", "Workshop creation started", reason="Provisioning"
        )

        workshop_name = spec.get("name", name)
        duration = spec.get("duration", "4h")
        image = spec.get("image", "rocker/rstudio:latest")
        resources = spec.get("resources", {})
        storage = spec.get("storage", {})
        ingress_config = spec.get("ingress", {})
        owner_email = spec.get("owner", "unknown")

        expiration_time = get_expiration_time(duration)

        k8s_apps_v1 = k8s_client.AppsV1Api()
        k8s_core_v1 = k8s_client.CoreV1Api()
        k8s_custom_objects_v1 = k8s_client.CustomObjectsApi()

        if storage:
            pvc = create_workshop_pvc(workshop_name, namespace, storage)
            _create_or_ignore(
                lambda: k8s_core_v1.create_namespaced_persistent_volume_claim(
                    namespace=namespace, body=pvc
                ),
                "PVC", workshop_name,
            )
            await update_workshop_status(
                namespace, name, "Creating", "Storage provisioned", reason="PVCReady"
            )

        # require_auth = True whenever an auth middleware is configured.
        require_auth = bool(settings.auth_middleware or settings.oauth2_proxy_auth_url)
        deployment = create_rstudio_deployment(
            workshop_name, namespace, image, owner_email, resources, storage,
            require_auth=require_auth,
        )
        _create_or_ignore(
            lambda: k8s_apps_v1.create_namespaced_deployment(
                namespace=namespace, body=deployment
            ),
            "Deployment", workshop_name,
        )
        await update_workshop_status(
            namespace, name, "Creating", "Compute resources created", reason="DeploymentReady"
        )

        service = create_workshop_service(workshop_name, namespace)
        _create_or_ignore(
            lambda: k8s_core_v1.create_namespaced_service(namespace=namespace, body=service),
            "Service", workshop_name,
        )
        await update_workshop_status(
            namespace, name, "Creating", "Network service created", reason="ServiceReady"
        )

        # Per-workshop auth middleware (only when oauth2_proxy_auth_url is set)
        local_auth_middleware: str | None = None
        if settings.oauth2_proxy_auth_url:
            middleware = create_auth_middleware(
                workshop_name, namespace, settings.oauth2_proxy_auth_url
            )
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
        _create_or_ignore(
            lambda: k8s_custom_objects_v1.create_namespaced_custom_object(
                group="traefik.io", version="v1alpha1",
                namespace=namespace, plural="ingressroutes", body=ingress,
            ),
            "IngressRoute", workshop_name,
        )
        workshop_url = _ingress_url(ingress)
        await update_workshop_status(
            namespace, name, "Creating", "Ingress route configured", reason="IngressReady"
        )

        await update_workshop_status(
            namespace, name, "Starting",
            "Waiting for workshop pod to become ready", reason="PodStarting",
        )
        timeout = 600
        elapsed = 0.0
        while elapsed < timeout:
            dep = k8s_apps_v1.read_namespaced_deployment(
                name=f"{workshop_name}-deployment", namespace=namespace
            )
            if (dep.status.ready_replicas or 0) >= 1:
                break
            interval = 5 + random.random() * 5
            await asyncio.sleep(interval)
            elapsed += interval
        else:
            raise kopf.PermanentError(
                f"Workshop pod did not become ready within {timeout}s"
            )

        logger.info("Workshop %s created and ready", workshop_name)
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

    except kopf.PermanentError:
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


@kopf.on.delete(GROUP, VERSION, PLURAL)
async def workshop_delete_handler(
    meta: dict[str, Any], namespace: str, name: str, **kwargs: Any
) -> None:
    """Handle Workshop deletion events."""
    logger.info("Deleting workshop %s in namespace %s", name, namespace)

    try:
        workshop_name = meta.get("name", name)
        k8s_apps_v1 = k8s_client.AppsV1Api()
        k8s_core_v1 = k8s_client.CoreV1Api()
        k8s_custom_objects_v1 = k8s_client.CustomObjectsApi()

        def _delete_or_warn(delete_fn, kind: str) -> None:
            try:
                delete_fn()
            except ApiException as e:
                if e.status != 404:
                    logger.warning("Failed to delete %s for %s: %s", kind, workshop_name, e)

        _delete_or_warn(
            lambda: k8s_custom_objects_v1.delete_namespaced_custom_object(
                group="traefik.io", version="v1alpha1", namespace=namespace,
                plural="ingressroutes", name=f"{workshop_name}-ingress",
            ),
            "IngressRoute",
        )
        _delete_or_warn(
            lambda: k8s_custom_objects_v1.delete_namespaced_custom_object(
                group="traefik.io", version="v1alpha1", namespace=namespace,
                plural="middlewares", name=f"{workshop_name}-auth",
            ),
            "Middleware",
        )
        _delete_or_warn(
            lambda: k8s_core_v1.delete_namespaced_service(
                name=f"{workshop_name}-service", namespace=namespace
            ),
            "Service",
        )
        _delete_or_warn(
            lambda: k8s_apps_v1.delete_namespaced_deployment(
                name=f"{workshop_name}-deployment", namespace=namespace
            ),
            "Deployment",
        )
        _delete_or_warn(
            lambda: k8s_core_v1.delete_namespaced_persistent_volume_claim(
                name=f"{workshop_name}-pvc", namespace=namespace
            ),
            "PVC",
        )

    except Exception as e:
        logger.error("Failed to delete workshop %s: %s", name, e)
        raise kopf.PermanentError(f"Workshop deletion failed: {e}")


async def update_workshop_status(
    namespace: str,
    name: str,
    phase: str,
    message: str,
    reason: str = "StatusUpdate",
    condition_type: str = "Ready",
    condition_status: str = "False",
) -> None:
    """Patch the Workshop CRD status subresource."""
    from datetime import datetime, timezone

    custom_api = k8s_client.CustomObjectsApi()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    try:
        custom_api.patch_namespaced_custom_object_status(
            group=GROUP, version=VERSION,
            namespace=namespace, plural=PLURAL, name=name,
            body={
                "status": {
                    "phase": phase,
                    "conditions": [
                        {
                            "type": condition_type,
                            "status": condition_status,
                            "reason": reason,
                            "message": message,
                            "lastTransitionTime": now,
                        }
                    ],
                }
            },
        )
        logger.info("Updated workshop %s status: %s - %s", name, phase, message)
    except ApiException as e:
        if e.status == 404:
            logger.warning("Could not update status: workshop %s not found", name)
        else:
            logger.error("Failed to patch workshop %s status: %s", name, e)
