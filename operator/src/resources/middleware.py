"""Traefik Middleware creation for workshops."""

from typing import Any


def create_auth_middleware(
    workshop_name: str,
    namespace: str,
    auth_url: str,
) -> dict[str, Any]:
    """
    Create a Traefik ForwardAuth Middleware for a workshop.
    
    This is created in the same namespace as the workshop to satisfy Traefik's
    disallowCrossNamespace restriction.
    """
    return {
        "apiVersion": "traefik.io/v1alpha1",
        "kind": "Middleware",
        "metadata": {
            "name": f"{workshop_name}-auth",
            "namespace": namespace,
            "labels": {
                "app": workshop_name,
                "component": "rstudio",
                "workshop": workshop_name,
            },
        },
        "spec": {
            "forwardAuth": {
                "address": auth_url,
                "trustForwardHeader": True,
                "authResponseHeaders": [
                    "X-Auth-Request-User",
                    "X-Auth-Request-Email",
                    "X-Auth-Request-Access-Token",
                    "Set-Cookie",
                ],
            }
        },
    }
