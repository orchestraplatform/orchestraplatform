"""Workshop event handlers for the Orchestra Operator."""

import logging
import os
from typing import Any

import kopf
import kubernetes.client as k8s_client
from kubernetes.client.rest import ApiException

from resources.deployment import create_rstudio_deployment
from resources.ingress import (
    _LOCAL_ENV,
    _LOCAL_INGRESS_PORT,
    create_workshop_ingress,
)
from resources.pvc import create_workshop_pvc
from resources.service import create_workshop_service
from utils.time_utils import get_expiration_time

logger = logging.getLogger(__name__)

# When ORCHESTRA_REQUIRE_AUTHENTICATION=false, the sidecar will not enforce 
# the X-Auth-Request-Email header. Defaults to false in local dev.
_REQUIRE_AUTH = os.environ.get("ORCHESTRA_REQUIRE_AUTHENTICATION", "").lower() != "false"
if _LOCAL_ENV and "ORCHESTRA_REQUIRE_AUTHENTICATION" not in os.environ:
    _REQUIRE_AUTH = False


def _ingress_url(ingress: dict[str, Any]) -> str:
    """Derive the public URL from an IngressRoute manifest.

    Uses the entry points to decide the scheme (websecure → https, web → http).
    The host is stored in a dedicated label on the IngressRoute so we never need
    to parse the Traefik match expression.
    """
    entry_points = ingress["spec"].get("entryPoints", ["web"])
    scheme = "https" if "websecure" in entry_points else "http"
    host = ingress["metadata"]["annotations"].get("orchestra.io/host", "")
    port_suffix = f":{_LOCAL_INGRESS_PORT}" if _LOCAL_ENV and _LOCAL_INGRESS_PORT else ""
    return f"{scheme}://{host}{port_suffix}"


def register_workshop_handlers() -> None:
    """Register all workshop-related Kopf handlers."""
    # Handlers are registered via decorators below
    pass


@kopf.on.create("orchestra.io", "v1", "workshops")
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
    logger.info(f"Creating workshop {name} in namespace {namespace}")

    try:
        # Update status to Creating immediately
        await update_workshop_status(
            namespace, name, "Creating", "Workshop creation started", reason="Provisioning"
        )

        # Extract workshop configuration
        workshop_name = spec.get("name", name)
        duration = spec.get("duration", "4h")
        image = spec.get("image", "rocker/rstudio:latest")
        resources = spec.get("resources", {})
        storage = spec.get("storage", {})
        ingress_config = spec.get("ingress", {})

        # Calculate expiration time
        expiration_time = get_expiration_time(duration)

        # Create Kubernetes client
        k8s_apps_v1 = k8s_client.AppsV1Api()
        k8s_core_v1 = k8s_client.CoreV1Api()
        k8s_custom_objects_v1 = k8s_client.CustomObjectsApi()

        # Create PersistentVolumeClaim for workshop data
        if storage:
            try:
                pvc = create_workshop_pvc(workshop_name, namespace, storage)
                k8s_core_v1.create_namespaced_persistent_volume_claim(
                    namespace=namespace, body=pvc
                )
                logger.info(f"Created PVC for workshop {workshop_name}")
                await update_workshop_status(
                    namespace, name, "Creating", "Storage provisioned", reason="PVCReady"
                )
            except ApiException as e:
                if e.status == 409:  # Already exists
                    logger.info(f"PVC for workshop {workshop_name} already exists")
                else:
                    raise

        # Create Deployment for RStudio
        try:
            owner_email = spec.get("owner", "unknown")
            deployment = create_rstudio_deployment(
                workshop_name, 
                namespace, 
                image, 
                owner_email, 
                resources, 
                storage,
                require_auth=_REQUIRE_AUTH
            )
            k8s_apps_v1.create_namespaced_deployment(
                namespace=namespace, body=deployment
            )
            logger.info(f"Created deployment for workshop {workshop_name}")
            await update_workshop_status(
                namespace, name, "Creating", "Compute resources created", reason="DeploymentReady"
            )
        except ApiException as e:
            if e.status == 409:  # Already exists
                logger.info(f"Deployment for workshop {workshop_name} already exists")
            else:
                raise

        # Create Service
        try:
            service = create_workshop_service(workshop_name, namespace)
            k8s_core_v1.create_namespaced_service(namespace=namespace, body=service)
            logger.info(f"Created service for workshop {workshop_name}")
            await update_workshop_status(
                namespace, name, "Creating", "Network service created", reason="ServiceReady"
            )
        except ApiException as e:
            if e.status == 409:  # Already exists
                logger.info(f"Service for workshop {workshop_name} already exists")
            else:
                raise

        # Create Ingress
        workshop_url = None
        try:
            ingress = create_workshop_ingress(workshop_name, namespace, ingress_config)
            k8s_custom_objects_v1.create_namespaced_custom_object(
                group="traefik.io",
                version="v1alpha1",
                namespace=namespace,
                plural="ingressroutes",
                body=ingress,
            )
            workshop_url = _ingress_url(ingress)
            logger.info(
                f"Created ingress route for workshop {workshop_name} at {workshop_url}"
            )
            await update_workshop_status(
                namespace, name, "Creating", "Ingress route configured", reason="IngressReady"
            )
        except ApiException as e:
            if e.status == 409:  # Already exists
                # Reconstruct the URL from the ingress we would have created
                ingress = create_workshop_ingress(workshop_name, namespace, ingress_config)
                workshop_url = _ingress_url(ingress)
                logger.info(
                    f"Ingress route for workshop {workshop_name} already exists at {workshop_url}"
                )
            else:
                raise

        logger.info(f"Workshop {workshop_name} created successfully")
        
        # Finally, the Ready status will be returned by the handler via patch
        status_return = {
            "phase": "Ready",
            "url": workshop_url,
            "createdAt": meta.get("creationTimestamp", ""),
            "expiresAt": expiration_time.isoformat(),
            "conditions": [
                {
                    "type": "Ready",
                    "status": "True",
                    "reason": "WorkshopCreated",
                    "message": "Workshop resources created successfully",
                }
            ],
        }
        logger.info(f"Workshop {workshop_name} status updated: {status_return}")
        patch["status"] = status_return

    except Exception as e:
        logger.error(f"Failed to create workshop {name}: {e}")
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


@kopf.on.update("orchestra.io", "v1", "workshops")
async def workshop_update_handler(
    spec: dict[str, Any],
    meta: dict[str, Any],
    status: dict[str, Any],
    namespace: str,
    name: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Handle Workshop update events."""
    logger.info(f"Updating workshop {name} in namespace {namespace}")

    # For now, we'll just log updates
    # In the future, we might support scaling or configuration changes
    return {"phase": status.get("phase", "Ready")}


@kopf.on.delete("orchestra.io", "v1", "workshops")
async def workshop_delete_handler(
    meta: dict[str, Any], namespace: str, name: str, **kwargs: Any
) -> None:
    """Handle Workshop deletion events."""
    logger.info(f"Deleting workshop {name} in namespace {namespace}")

    try:
        workshop_name = meta.get("name", name)

        # Create Kubernetes clients
        k8s_apps_v1 = k8s_client.AppsV1Api()
        k8s_core_v1 = k8s_client.CoreV1Api()
        k8s_custom_objects_v1 = k8s_client.CustomObjectsApi()

        # Delete in reverse order: IngressRoute -> Service -> Deployment -> PVC

        # Delete IngressRoute
        try:
            k8s_custom_objects_v1.delete_namespaced_custom_object(
                group="traefik.io",
                version="v1alpha1",
                namespace=namespace,
                plural="ingressroutes",
                name=f"{workshop_name}-ingress",
            )
            logger.info(f"Deleted ingress route for workshop {workshop_name}")
        except ApiException as e:
            if e.status != 404:  # Ignore not found errors
                logger.warning(f"Failed to delete ingress route: {e}")

        # Delete Service
        try:
            k8s_core_v1.delete_namespaced_service(
                name=f"{workshop_name}-service", namespace=namespace
            )
            logger.info(f"Deleted service for workshop {workshop_name}")
        except ApiException as e:
            if e.status != 404:
                logger.warning(f"Failed to delete service: {e}")

        # Delete Deployment
        try:
            k8s_apps_v1.delete_namespaced_deployment(
                name=f"{workshop_name}-deployment", namespace=namespace
            )
            logger.info(f"Deleted deployment for workshop {workshop_name}")
        except ApiException as e:
            if e.status != 404:
                logger.warning(f"Failed to delete deployment: {e}")

        # Delete PVC (optionally preserve data by commenting this out)
        try:
            k8s_core_v1.delete_namespaced_persistent_volume_claim(
                name=f"{workshop_name}-pvc", namespace=namespace
            )
            logger.info(f"Deleted PVC for workshop {workshop_name}")
        except ApiException as e:
            if e.status != 404:
                logger.warning(f"Failed to delete PVC: {e}")

    except Exception as e:
        logger.error(f"Failed to delete workshop {name}: {e}")
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
    """Update the status of a Workshop resource immediately via API."""
    custom_api = k8s_client.CustomObjectsApi()
    
    # Fetch current status to preserve other fields (like url, expiresAt)
    try:
        current = custom_api.get_namespaced_custom_object(
            group="orchestra.io",
            version="v1",
            namespace=namespace,
            plural="workshops",
            name=name,
        )
        status = current.get("status", {})
    except ApiException as e:
        logger.error(f"Failed to fetch workshop {name} for status update: {e}")
        status = {}

    status.update({
        "phase": phase,
    })
    
    # Update or add the condition
    conditions = status.get("conditions", [])
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    new_condition = {
        "type": condition_type,
        "status": condition_status,
        "reason": reason,
        "message": message,
        "lastTransitionTime": now
    }
    
    # Replace existing condition of same type or append
    updated = False
    for i, c in enumerate(conditions):
        if c.get("type") == condition_type:
            conditions[i] = new_condition
            updated = True
            break
    if not updated:
        conditions.append(new_condition)
    
    status["conditions"] = conditions

    try:
        custom_api.patch_namespaced_custom_object_status(
            group="orchestra.io",
            version="v1",
            namespace=namespace,
            plural="workshops",
            name=name,
            body={"status": status},
        )
        logger.info(f"Updated workshop {name} status: {phase} - {message}")
    except ApiException as e:
        logger.error(f"Failed to patch workshop {name} status: {e}")
