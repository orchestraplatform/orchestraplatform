"""Child-resource names and labels for a workshop — the single source.

The builders, the desired-state module, and the cluster adapter all derive
names from here; nothing else may concatenate ``f"{workshop_name}-..."``.
"""

import hashlib


def deployment_name(workshop_name: str) -> str:
    return f"{workshop_name}-deployment"


def service_name(workshop_name: str) -> str:
    return f"{workshop_name}-service"


def pvc_name(workshop_name: str) -> str:
    return f"{workshop_name}-pvc"


def owner_hash(owner_email: str) -> str:
    """Short, stable, name/label-safe hash of the owner email (ADR-0010)."""
    return hashlib.sha256(owner_email.encode()).hexdigest()[:12]


def workspace_pvc_name(template_slug: str, owner_email: str) -> str:
    """The durable per-(user, workshop) workspace PVC (ADR-0010).

    Keyed by (template slug, owner hash) — NOT the instance name — so a
    relaunch of the same workshop by the same user reattaches the same volume.
    Fits the 63-char name limit: 3 + slug (<=40) + 1 + 12 = 56.
    """
    return f"ws-{template_slug}-{owner_hash(owner_email)}"


def ingress_name(workshop_name: str) -> str:
    return f"{workshop_name}-ingress"


def auth_middleware_name(workshop_name: str) -> str:
    return f"{workshop_name}-auth"


def workshop_labels(workshop_name: str) -> dict[str, str]:
    """Label set for the deployment/pod template and Traefik objects.

    Not universal: the Service carries only selector_labels(), and the PVC
    uses component=storage (see resources/pvc.py)."""
    return {"app": workshop_name, "component": "rstudio", "workshop": workshop_name}


def selector_labels(workshop_name: str) -> dict[str, str]:
    """Immutable selector subset — a Deployment selector can never change, so
    this must stay a stable subset of workshop_labels()."""
    return {"app": workshop_name, "component": "rstudio"}
