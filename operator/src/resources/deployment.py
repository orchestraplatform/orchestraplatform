"""RStudio Deployment creation for workshops."""

import os
from typing import Any

import kubernetes.client as k8s


def create_rstudio_deployment(
    workshop_name: str,
    namespace: str,
    image: str,
    owner_email: str,
    resources: dict[str, Any],
    storage: dict[str, Any],
    sidecar_image: str = "seandavi/orchestra-sidecar:latest",
    require_auth: bool = True,
) -> k8s.V1Deployment:
    """
    Create a Kubernetes Deployment for an RStudio workshop instance with an auth sidecar.

    Args:
        workshop_name: Name of the workshop
        namespace: Kubernetes namespace
        image: Docker image for RStudio
        owner_email: Email of the workshop owner
        resources: Resource limits and requests
        storage: Storage configuration
        sidecar_image: Image for the orchestra sidecar proxy

    Returns:
        V1Deployment object ready to be created
    """
    # Resource limits and requests
    cpu_limit = resources.get("cpu", "1")
    memory_limit = resources.get("memory", "2Gi")
    cpu_request = resources.get("cpuRequest", "500m")
    memory_request = resources.get("memoryRequest", "1Gi")

    # 1. RStudio Application Container
    app_container = k8s.V1Container(
        name="rstudio",
        image=image,
        ports=[k8s.V1ContainerPort(container_port=8787, name="rstudio-api")],
        env=[
            k8s.V1EnvVar(name="DISABLE_AUTH", value="true"),
            k8s.V1EnvVar(name="ROOT", value="true"),
        ],
        resources=k8s.V1ResourceRequirements(
            requests={"cpu": cpu_request, "memory": memory_request},
            limits={"cpu": cpu_limit, "memory": memory_limit},
        ),
        volume_mounts=[k8s.V1VolumeMount(name="workshop-data", mount_path="/data")]
        if storage
        else None,
    )

    # 2. Orchestra Sidecar Proxy
    sidecar_pull_policy = os.environ.get("ORCHESTRA_SIDECAR_PULL_POLICY", "Always")
    
    sidecar_container = k8s.V1Container(
        name="orchestra-sidecar",
        image=os.environ.get("ORCHESTRA_SIDECAR_IMAGE", sidecar_image),
        image_pull_policy=sidecar_pull_policy,
        ports=[k8s.V1ContainerPort(container_port=8080, name="http-proxy")],
        env=[
            k8s.V1EnvVar(name="ORCHESTRA_TARGET_URL", value="http://localhost:8787"),
            k8s.V1EnvVar(name="ORCHESTRA_OWNER_EMAIL", value=owner_email),
            k8s.V1EnvVar(name="ORCHESTRA_LISTEN_ADDR", value=":8080"),
            k8s.V1EnvVar(name="ORCHESTRA_REQUIRE_AUTHENTICATION", value="true" if require_auth else "false"),
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

    # Volume definition (if storage is configured)
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

    # Pod template
    pod_template = k8s.V1PodTemplateSpec(
        metadata=k8s.V1ObjectMeta(
            labels={
                "app": workshop_name,
                "component": "rstudio",
                "workshop": workshop_name,
            }
        ),
        spec=k8s.V1PodSpec(
            containers=[app_container, sidecar_container], 
            volumes=volumes if volumes else None
        ),
    )

    # Deployment specification
    deployment_spec = k8s.V1DeploymentSpec(
        replicas=1,
        selector=k8s.V1LabelSelector(
            match_labels={"app": workshop_name, "component": "rstudio"}
        ),
        template=pod_template,
    )

    # Create the deployment
    deployment = k8s.V1Deployment(
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
        spec=deployment_spec,
    )

    return deployment
