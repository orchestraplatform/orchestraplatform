"""Ingress creation for workshops."""

import os
from typing import Any

# When ORCHESTRA_ENVIRONMENT=local, workshops are reachable at
# {name}.127.0.0.1.nip.io — no DNS config required on Docker Desktop.
# In any other environment the hostname follows the production convention.
_LOCAL_ENV = os.environ.get("ORCHESTRA_ENVIRONMENT", "").lower() == "local"
_PROD_BASE_DOMAIN = os.environ.get("ORCHESTRA_BASE_DOMAIN", "orchestraplatform.org")
# Local dev domain — resolved by dnsmasq (*.orchestra.localhost → 127.0.0.1).
# See docs/dev-setup for dnsmasq configuration instructions.
_LOCAL_BASE_DOMAIN = os.environ.get("ORCHESTRA_LOCAL_DOMAIN", "orchestra.localhost")


def _default_host(workshop_name: str) -> str:
    """Return the default hostname for a workshop based on the environment."""
    if _LOCAL_ENV:
        return f"{workshop_name}.{_LOCAL_BASE_DOMAIN}"
    return f"{workshop_name}.{_PROD_BASE_DOMAIN}"


def _default_entry_points() -> list[str]:
    """Return Traefik entry points appropriate for the environment."""
    # Local dev uses plain HTTP; production uses TLS.
    return ["web"] if _LOCAL_ENV else ["websecure"]


def create_workshop_ingress(
    workshop_name: str, namespace: str, ingress_config: dict[str, Any]
) -> dict[str, Any]:
    """
    Create a Traefik IngressRoute for a workshop.

    Args:
        workshop_name: Name of the workshop
        namespace: Kubernetes namespace
        ingress_config: Ingress configuration from workshop spec

    Returns:
        IngressRoute manifest as a dictionary ready to be created
    """
    # Explicit host in the spec always wins; otherwise derive from environment.
    host = ingress_config.get("host") or _default_host(workshop_name)
    entry_points = ingress_config.get("entryPoints") or _default_entry_points()
    annotations = ingress_config.get("annotations", {})

    # Store the resolved host as an annotation so callers can retrieve it
    # without re-parsing the Traefik match expression.
    meta_annotations = {**annotations, "orchestra.io/host": host}

    ingress_route = {
        "apiVersion": "traefik.io/v1alpha1",
        "kind": "IngressRoute",
        "metadata": {
            "name": f"{workshop_name}-ingress",
            "namespace": namespace,
            "labels": {
                "app": workshop_name,
                "component": "rstudio",
                "workshop": workshop_name,
            },
            "annotations": meta_annotations,
        },
        "spec": {
            "entryPoints": entry_points,
            "routes": [
                {
                    "match": f"Host(`{host}`)",
                    "kind": "Rule",
                    "services": [{"name": f"{workshop_name}-service", "port": 80}],
                }
            ],
        },
    }

    return ingress_route
