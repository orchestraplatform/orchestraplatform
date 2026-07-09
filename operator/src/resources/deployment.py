"""RStudio Deployment creation for workshops."""

import logging
from typing import Any

import kubernetes.client as k8s

from config import get_settings
from resources.naming import (
    deployment_name,
    pvc_name,
    selector_labels,
    workshop_labels,
)

logger = logging.getLogger(__name__)

# Default environment for the app container. These are rocker/rstudio flags
# (auto-login + sudo); they are harmless no-ops on non-RStudio images. A
# template's ``env`` overrides any of these by name.
_DEFAULT_APP_ENV = {"DISABLE_AUTH": "true", "ROOT": "true"}

# Cluster-autoscaler hint stamped on EVERY workshop pod. Interactive sessions
# must never be migrated for bin-packing consolidation — that disconnects the
# user and loses in-memory state (PVC files survive). Always-on, not per-tier
# (ADR-0005 / deploy/tofu README). This is a plain Kubernetes annotation, so it
# is a harmless no-op on clusters without the GKE cluster-autoscaler.
_SAFE_TO_EVICT_ANNOTATION = {"cluster-autoscaler.kubernetes.io/safe-to-evict": "false"}


def _tier_scheduling(
    tier: str | None,
) -> tuple[dict[str, str] | None, list[k8s.V1Toleration] | None]:
    """Resolve a tenant tier name to (nodeSelector, tolerations), or (None, None).

    The tier map lives in operator config (``ORCHESTRA_TIER_MAP``); a template
    selects a tier *by name* and the operator looks it up here. Every value is a
    config-supplied string, so this stays cloud-neutral — GKE's taint keys /
    compute-class label are just one instance of the config.

    Behaviour:
    - No tier, or an empty tier map (the default — GKE Autopilot / single-node
      dev): emit nothing, so pods schedule anywhere with zero config.
    - A tier whose entry is empty (``{}``, e.g. a ``default`` tier): emit nothing.
    - An **unknown** tier name (not present in the map): fall back to "no
      constraints" and log a warning. This is the safer failure mode — a mistyped
      tier still schedules and the session runs, rather than the pod staying
      Pending forever on a bad nodeSelector. The warning surfaces the misconfig.
    """
    settings = get_settings()
    if not tier or not settings.tier_map:
        return None, None

    tier_cfg = settings.tier_map.get(tier)
    if tier_cfg is None:
        logger.warning(
            "Workshop tier %r is not in the operator tier map %s; scheduling "
            "the pod with no nodeSelector/tolerations (falls back to default).",
            tier,
            sorted(settings.tier_map),
        )
        return None, None

    node_selector = dict(tier_cfg.node_selector)
    if tier_cfg.compute_class:
        node_selector[settings.compute_class_label_key] = tier_cfg.compute_class

    tolerations = [
        k8s.V1Toleration(
            key=t["key"],
            operator=t.get("operator", "Equal"),
            value=t.get("value"),
            effect=t.get("effect", "NoSchedule"),
        )
        for t in tier_cfg.tolerations
    ]

    return (node_selector or None), (tolerations or None)


def _sidecar_container(
    port: int, owner_email: str, require_auth: bool
) -> k8s.V1Container:
    """The auth/proxy sidecar that fronts the app container on :8080."""
    settings = get_settings()
    return k8s.V1Container(
        name="orchestra-sidecar",
        image=settings.sidecar_image,
        image_pull_policy=settings.sidecar_pull_policy,
        ports=[k8s.V1ContainerPort(container_port=8080, name="http-proxy")],
        env=[
            k8s.V1EnvVar(name="ORCHESTRA_TARGET_URL", value=f"http://localhost:{port}"),
            k8s.V1EnvVar(name="ORCHESTRA_OWNER_EMAIL", value=owner_email),
            k8s.V1EnvVar(name="ORCHESTRA_LISTEN_ADDR", value=":8080"),
            k8s.V1EnvVar(
                name="ORCHESTRA_REQUIRE_AUTHENTICATION",
                value="true" if require_auth else "false",
            ),
        ],
        resources=k8s.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "64Mi"},
            limits={"cpu": "200m", "memory": "128Mi"},
        ),
        liveness_probe=k8s.V1Probe(
            http_get=k8s.V1HTTPGetAction(path="/orchestra/health", port=8080),
            initial_delay_seconds=5,
            period_seconds=10,
        ),
        readiness_probe=k8s.V1Probe(
            http_get=k8s.V1HTTPGetAction(path="/orchestra/health", port=8080),
            initial_delay_seconds=2,
            period_seconds=5,
        ),
    )


def create_rstudio_deployment(
    workshop_name: str,
    namespace: str,
    image: str,
    owner_email: str,
    resources: dict[str, Any],
    storage: dict[str, Any],
    require_auth: bool = True,
    port: int = 8787,
    env: dict[str, str] | None = None,
    args: list[str] | None = None,
    tier: str | None = None,
    pvc_claim_name: str | None = None,
) -> k8s.V1Deployment:
    """Create a Kubernetes Deployment for a workshop app with an auth sidecar.

    ``port`` is the port the application container listens on (e.g. 8787 for
    RStudio, 8888 for JupyterLab); the sidecar proxies to it on localhost.

    ``env`` is merged on top of the default app environment (template values
    win). ``args``, when given, replaces the image's default CMD.

    ``tier`` selects a tenant node pool by name; the operator resolves it against
    the configured tier map to a nodeSelector / tolerations / compute-class label
    (see :func:`_tier_scheduling`). An empty tier map (the default) emits nothing,
    so pods schedule anywhere.

    Every workshop pod is also stamped with interactive-session safety settings
    regardless of tier: the ``safe-to-evict=false`` annotation (never migrate a
    live session for consolidation) and a longer ``terminationGracePeriodSeconds``
    (flush to the PVC on SIGTERM) — see ADR-0005 / deploy/tofu README.
    """
    settings = get_settings()
    node_selector, tolerations = _tier_scheduling(tier)

    cpu_limit = resources.get("cpu", "1")
    memory_limit = resources.get("memory", "2Gi")
    cpu_request = resources.get("cpuRequest", "500m")
    memory_request = resources.get("memoryRequest", "1Gi")
    # Ephemeral storage covers everything written outside the /data PVC: R/Python
    # package installs, compilation artifacts, /tmp, logs, and the container's
    # writable layer. The limit is the kubelet's eviction threshold — exceeding it
    # evicts the whole pod (not just a container restart). When unset, GKE Autopilot
    # defaults this to 1Gi, which Bioconductor sessions blow past, so set it
    # explicitly (incident 2026-06-16).
    #
    # CAP: GKE Autopilot rejects pods whose *total* ephemeral-storage request
    # across all containers exceeds 10Gi, and forces limit == request. With the
    # sidecar requesting 1Gi, the app can request at most ~9Gi here. Going beyond
    # 10Gi/pod needs Local SSD-backed ephemeral storage or GKE Standard (ADR-0005).
    ephemeral_limit = resources.get("ephemeralStorage", "8Gi")
    ephemeral_request = resources.get("ephemeralStorageRequest", "8Gi")

    app_env = {**_DEFAULT_APP_ENV, **(env or {})}

    app_container = k8s.V1Container(
        name="rstudio",
        image=image,
        ports=[k8s.V1ContainerPort(container_port=port, name="app-api")],
        env=[k8s.V1EnvVar(name=k, value=v) for k, v in app_env.items()],
        args=list(args) if args else None,
        resources=k8s.V1ResourceRequirements(
            requests={
                "cpu": cpu_request,
                "memory": memory_request,
                "ephemeral-storage": ephemeral_request,
            },
            limits={
                "cpu": cpu_limit,
                "memory": memory_limit,
                "ephemeral-storage": ephemeral_limit,
            },
        ),
        volume_mounts=[k8s.V1VolumeMount(name="workshop-data", mount_path="/data")]
        if storage
        else None,
    )

    sidecar_container = _sidecar_container(port, owner_email, require_auth)

    volumes = []
    if storage:
        volumes.append(
            k8s.V1Volume(
                name="workshop-data",
                persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
                    # The persistent workspace (ADR-0010) claims a shared
                    # per-(user, workshop) PVC instead of the per-instance one.
                    claim_name=pvc_claim_name or pvc_name(workshop_name)
                ),
            )
        )

    return k8s.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=k8s.V1ObjectMeta(
            name=deployment_name(workshop_name),
            namespace=namespace,
            labels=workshop_labels(workshop_name),
        ),
        spec=k8s.V1DeploymentSpec(
            replicas=1,
            selector=k8s.V1LabelSelector(
                match_labels=selector_labels(workshop_name)
            ),
            template=k8s.V1PodTemplateSpec(
                metadata=k8s.V1ObjectMeta(
                    labels=workshop_labels(workshop_name),
                    annotations=dict(_SAFE_TO_EVICT_ANNOTATION),
                ),
                spec=k8s.V1PodSpec(
                    containers=[app_container, sidecar_container],
                    volumes=volumes if volumes else None,
                    node_selector=node_selector,
                    tolerations=tolerations,
                    termination_grace_period_seconds=(
                        settings.termination_grace_period_seconds
                    ),
                ),
            ),
        ),
    )
