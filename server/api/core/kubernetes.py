"""Kubernetes client configuration."""

import logging
from typing import Optional

try:
    import kubernetes
    from kubernetes.client.rest import ApiException
except ImportError:
    kubernetes = None
    ApiException = Exception

logger = logging.getLogger(__name__)


def get_k8s_client():
    """Get Kubernetes client."""
    if not kubernetes:
        raise ImportError("kubernetes package not installed")
    
    try:
        # Try in-cluster config first
        kubernetes.config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes configuration")
    except kubernetes.config.ConfigException:
        # Fall back to local kubeconfig
        kubernetes.config.load_kube_config()
        logger.info("Loaded local Kubernetes configuration")
    
    return kubernetes.client


def get_custom_objects_api():
    """Get Kubernetes Custom Objects API client."""
    get_k8s_client()  # Ensure config is loaded
    return kubernetes.client.CustomObjectsApi()


def get_core_v1_api():
    """Get Kubernetes Core V1 API client."""
    get_k8s_client()  # Ensure config is loaded
    return kubernetes.client.CoreV1Api()
