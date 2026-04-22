"""Kubernetes client configuration."""

import logging
import os

import kubernetes
from kubernetes.client.rest import ApiException

from api.core.config import get_settings

logger = logging.getLogger(__name__)


def get_k8s_client():
    """Configure the kubernetes client, returning the client module.

    Auto-detects in-cluster via KUBERNETES_SERVICE_HOST (set by k8s itself).
    Falls back to local kubeconfig using ORCHESTRA_KUBE_CONTEXT if set.
    """
    settings = get_settings()

    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        kubernetes.config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes configuration")
    else:
        try:
            kubernetes.config.load_kube_config(
                config_file=settings.kubeconfig_path,
                context=settings.kube_context,
            )
            logger.info(
                "Loaded local Kubernetes configuration (context: %s)",
                settings.kube_context or "default",
            )
        except Exception as e:
            logger.error("Failed to load local Kubernetes configuration: %s", e)
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
