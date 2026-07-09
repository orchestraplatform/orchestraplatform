"""PersistentVolumeClaim creation for workshops."""

from datetime import UTC, datetime
from typing import Any

import kubernetes.client as k8s

from resources.naming import owner_hash, pvc_name, workspace_pvc_name

# The idle-TTL reaper's clock (ADR-0010 decision E): stamped at creation as a
# floor, refreshed by the session-end handler, read by the sweep.
LAST_USED_ANNOTATION = "orchestra.io/last-used"

# Label selector scoping the reaper's sweep to persistent workspace PVCs only.
# Requiring the orchestra.io/owner-hash label (not just component=workspace)
# keeps foreign PVCs that happen to use the generic label out of scope.
WORKSPACE_PVC_SELECTOR = "component=workspace,orchestra.io/owner-hash"


def create_workshop_pvc(
    workshop_name: str, namespace: str, storage_config: dict[str, Any]
) -> k8s.V1PersistentVolumeClaim:
    """
    Create a PersistentVolumeClaim for workshop data.

    Args:
        workshop_name: Name of the workshop
        namespace: Kubernetes namespace
        storage_config: Storage configuration from workshop spec

    Returns:
        V1PersistentVolumeClaim object ready to be created
    """
    size = storage_config.get("size", "10Gi")
    storage_class = storage_config.get("storageClass")

    pvc = k8s.V1PersistentVolumeClaim(
        api_version="v1",
        kind="PersistentVolumeClaim",
        metadata=k8s.V1ObjectMeta(
            name=pvc_name(workshop_name),
            namespace=namespace,
            labels={"app": workshop_name, "component": "storage"},
        ),
        spec=k8s.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            resources=k8s.V1ResourceRequirements(requests={"storage": size}),
            storage_class_name=storage_class,
        ),
    )

    return pvc


def create_workspace_pvc(
    template_slug: str,
    owner_email: str,
    namespace: str,
    storage_config: dict[str, Any],
) -> k8s.V1PersistentVolumeClaim:
    """The durable per-(user, workshop) workspace PVC (ADR-0010).

    Deliberately carries NO owner-reference: the volume must survive Workshop
    CR deletion so /data persists across sessions. The idle-TTL reaper
    (handlers/cleanup.py) owns reclamation — the labels key its sweep and the
    ``last-used`` annotation is its clock (stamped here at creation as a
    floor, refreshed at session end).
    RWO like the ephemeral PVC; the storage class comes from the spec (cluster
    default when unset).
    """
    size = storage_config.get("size", "10Gi")
    storage_class = storage_config.get("storageClass")

    return k8s.V1PersistentVolumeClaim(
        api_version="v1",
        kind="PersistentVolumeClaim",
        metadata=k8s.V1ObjectMeta(
            name=workspace_pvc_name(template_slug, owner_email),
            namespace=namespace,
            labels={
                "component": "workspace",
                "orchestra.io/template-slug": template_slug,
                "orchestra.io/owner-hash": owner_hash(owner_email),
            },
            annotations={
                LAST_USED_ANNOTATION: datetime.now(UTC).isoformat(),
            },
        ),
        spec=k8s.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            resources=k8s.V1ResourceRequirements(requests={"storage": size}),
            storage_class_name=storage_class,
        ),
    )
