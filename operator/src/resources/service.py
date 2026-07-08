"""Service creation for workshops."""

import kubernetes.client as k8s

from resources.naming import selector_labels, service_name


def create_workshop_service(workshop_name: str, namespace: str) -> k8s.V1Service:
    """
    Create a Kubernetes Service for a workshop.

    Args:
        workshop_name: Name of the workshop
        namespace: Kubernetes namespace

    Returns:
        V1Service object ready to be created
    """
    service = k8s.V1Service(
        api_version="v1",
        kind="Service",
        metadata=k8s.V1ObjectMeta(
            name=service_name(workshop_name),
            namespace=namespace,
            labels=selector_labels(workshop_name),
        ),
        spec=k8s.V1ServiceSpec(
            selector=selector_labels(workshop_name),
            ports=[k8s.V1ServicePort(port=80, target_port=8080, protocol="TCP")],
            type="ClusterIP",
        ),
    )

    return service
