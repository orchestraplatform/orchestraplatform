"""Kubernetes client configuration."""

import logging

import kubernetes
from kubernetes.client.rest import ApiException

from api.core.config import get_settings

logger = logging.getLogger(__name__)


def get_k8s_client():
    """Get Kubernetes client."""
    settings = get_settings()

    try:
        # Try in-cluster config first
        if settings.in_cluster:
            kubernetes.config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes configuration")
        else:
            raise kubernetes.config.ConfigException("Not in-cluster")
    except kubernetes.config.ConfigException:
        # Fall back to local kubeconfig
        try:
            kubernetes.config.load_kube_config(
                config_file=settings.kubeconfig_path, context=settings.kube_context
            )
            logger.info(
                f"Loaded local Kubernetes configuration (context: {settings.kube_context or 'default'})"
            )
        except Exception as e:
            logger.error(f"Failed to load local Kubernetes configuration: {e}")
            raise

    return kubernetes.client


def get_custom_objects_api():
    """Get Kubernetes Custom Objects API client."""
    get_k8s_client()  # Ensure config is loaded
    return kubernetes.client.CustomObjectsApi()


def get_core_v1_api():
    """Get Kubernetes Core V1 API client."""
    get_k8s_client()  # Ensure config is loaded
    return kubernetes.client.CoreV1Api()
