"""RStudio Deployment creation for workshops."""

from typing import Any

import kubernetes.client as k8s

from config import get_settings

# Default environment for the app container. These are rocker/rstudio flags
# (auto-login + sudo); they are harmless no-ops on non-RStudio images. A
# template's ``env`` overrides any of these by name.
_DEFAULT_APP_ENV = {"DISABLE_AUTH": "true", "ROOT": "true"}


def _tier_scheduling(
    tier: str | None,
) -> tuple[dict[str, str] | None, list[k8s.V1Toleration] | None]:
    """Return (nodeSelector, tolerations) for a tenant tier, or (None, None).

    Only emits scheduling constraints when tenant pools are enabled
    (``ORCHESTRA_TENANT_POOLS_ENABLED``). On GKE Autopilot / single-node dev the
    feature is off, so pods carry no nodeSelector/tolerations and schedule
    anywhere — emitting them there would leave pods Pending (ADR-0005/0006).
    """
    settings = get_settings()
    if not settings.tenant_pools_enabled or not tier:
        return None, None
    node_selector = {settings.tenant_tier_label_key: tier}
    tolerations = [
        k8s.V1Toleration(
            key=settings.tenant_tier_taint_key,
            operator="Equal",
            value=tier,
            effect="NoSchedule",
        )
    ]
    return node_selector, tolerations


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
) -> k8s.V1Deployment:
    """Create a Kubernetes Deployment for a workshop app with an auth sidecar.

    ``port`` is the port the application container listens on (e.g. 8787 for
    RStudio, 8888 for JupyterLab); the sidecar proxies to it on localhost.

    ``env`` is merged on top of the default app environment (template values
    win). ``args``, when given, replaces the image's default CMD.

    ``tier`` selects a tenant node pool; it only affects scheduling when tenant
    pools are enabled in operator config (see :func:`_tier_scheduling`).
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

    sidecar_container = k8s.V1Container(
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

    volumes = []
    if storage:
        volumes.append(
            k8s.V1Volume(
                name="workshop-data",
                persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
                    claim_name=f"{workshop_name}-pvc"
                ),
            )
        )

    return k8s.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=k8s.V1ObjectMeta(
            name=f"{workshop_name}-deployment",
            namespace=namespace,
            labels={
                "app": workshop_name,
                "component": "rstudio",
                "workshop": workshop_name,
            },
        ),
        spec=k8s.V1DeploymentSpec(
            replicas=1,
            selector=k8s.V1LabelSelector(
                match_labels={"app": workshop_name, "component": "rstudio"}
            ),
            template=k8s.V1PodTemplateSpec(
                metadata=k8s.V1ObjectMeta(
                    labels={
                        "app": workshop_name,
                        "component": "rstudio",
                        "workshop": workshop_name,
                    }
                ),
                spec=k8s.V1PodSpec(
                    containers=[app_container, sidecar_container],
                    volumes=volumes if volumes else None,
                    node_selector=node_selector,
                    tolerations=tolerations,
                ),
            ),
        ),
    )
