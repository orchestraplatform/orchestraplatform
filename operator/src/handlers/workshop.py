"""Workshop event handlers for the Orchestra Operator.

Thin kopf glue: desired state comes from resources/desired.py (pure), cluster
I/O goes through the OperatorCluster adapter on kopf's memo (set at startup).
"""

import logging
from typing import Any

import kopf

from crd import GROUP, PLURAL, VERSION
from resources.desired import (
    desired_children,
    failed_status,
    ready_status,
    starting_status,
)

logger = logging.getLogger(__name__)


@kopf.on.create(GROUP, VERSION, PLURAL)
async def workshop_create_handler(
    spec: dict[str, Any],
    meta: dict[str, Any],
    patch,
    namespace: str,
    name: str,
    memo: kopf.Memo,
    **kwargs: Any,
) -> None:
    """Handle Workshop creation events.

    Resources are created idempotently so kopf can safely retry after a
    TemporaryError. OwnerReferences on every child resource mean Kubernetes
    GC cleans them up automatically when the Workshop CRD is deleted.
    """
    logger.info("Creating workshop %s in namespace %s", name, namespace)

    try:
        children = desired_children(spec, meta, namespace)
        await memo.cluster.apply(children, namespace)

        # Check readiness — requeue cleanly if the pod isn't up yet.
        if not await memo.cluster.deployment_ready(children.workshop_name, namespace):
            patch["status"] = starting_status()
            raise kopf.TemporaryError("Workshop pod not yet ready", delay=15)

        logger.info("Workshop %s is ready", children.workshop_name)
        patch["status"] = ready_status(
            children.url, meta.get("creationTimestamp", ""), children.expires_at
        )

    except (kopf.PermanentError, kopf.TemporaryError):
        raise
    except Exception as e:
        logger.error("Failed to create workshop %s: %s", name, e)
        patch["status"] = failed_status(str(e))
        raise kopf.PermanentError(str(e))
