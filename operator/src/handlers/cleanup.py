"""Cleanup handlers for expired workshops."""

import logging
from datetime import datetime, timezone
from typing import Any

import kopf

from crd import GROUP, PLURAL, VERSION

logger = logging.getLogger(__name__)


@kopf.timer(GROUP, VERSION, PLURAL, interval=30, idle=10)  # type: ignore
async def workshop_expiration_timer(
    spec: dict, status: dict, namespace: str, name: str, memo: kopf.Memo, **kwargs: Any
) -> None:
    """Periodic timer to delete workshops that have passed their expiresAt time.

    Runs every 30 seconds. Deleting the CRD triggers workshop_delete_handler
    which cleans up the deployment, service, ingress, and PVC.
    """
    expires_at_str = status.get("expiresAt")
    if not expires_at_str:
        return  # No expiry set — not an error, just skip

    try:
        expiration_time = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
    except ValueError as e:
        logger.error("Failed to parse expiresAt for workshop %s: %s", name, e)
        return

    if datetime.now(timezone.utc) < expiration_time:
        return  # Not expired yet

    logger.info("Workshop %s has expired — deleting CRD", name)
    try:
        if await memo.cluster.delete_workshop(name, namespace):
            logger.info("Workshop %s CRD deleted", name)
        else:
            logger.info("Workshop %s already gone", name)
    except Exception as e:
        logger.error("Failed to delete expired workshop %s: %s", name, e)


@kopf.on.field(GROUP, VERSION, PLURAL, field="status.phase")  # type: ignore
async def workshop_phase_change(
    old: str, new: str, namespace: str, name: str, **kwargs: Any
) -> None:
    """Log phase transitions for visibility."""
    if old != new:
        logger.info("Workshop %s phase changed: %s -> %s", name, old, new)
