"""Ingress creation for workshops."""

from typing import Any

from config import get_settings


def _default_host(workshop_name: str) -> str:
    """Return the default hostname for a workshop."""
    return f"{workshop_name}.{get_settings().base_domain}"


def create_workshop_ingress(
    workshop_name: str,
    namespace: str,
    ingress_config: dict[str, Any],
    auth_middleware_override: str | None = None,
) -> dict[str, Any]:
    """Create a Traefik IngressRoute for a workshop.

    Args:
        workshop_name: Name of the workshop
        namespace: Kubernetes namespace
        ingress_config: Ingress configuration from workshop spec
        auth_middleware_override: Local per-workshop middleware name (production
            only; overrides the system-wide auth_middleware from settings)
    """
    settings = get_settings()

    host = ingress_config.get("host") or _default_host(workshop_name)
    entry_points = ingress_config.get("entryPoints") or settings.ingress_entry_points
    annotations = ingress_config.get("annotations", {})

    # Store the resolved host as an annotation for easy URL reconstruction.
    meta_annotations = {**annotations, "orchestra.io/host": host}

    routes = [
        {
            "match": f"Host(`{host}`)",
            "kind": "Rule",
            "services": [{"name": f"{workshop_name}-service", "port": 80}],
        }
    ]

    middleware_name = auth_middleware_override or settings.auth_middleware
    if middleware_name:
        routes[0]["middlewares"] = [{"name": middleware_name}]

    return {
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
            "routes": routes,
        },
    }
