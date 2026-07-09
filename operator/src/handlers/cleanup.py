"""Cleanup handlers: workshop expiry and workspace-PVC reclamation."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import kopf

from cluster import OperatorCluster
from config import get_settings
from crd import GROUP, PLURAL, VERSION
from resources.desired import workspace_pvc_ref
from resources.pvc import LAST_USED_ANNOTATION

logger = logging.getLogger(__name__)

# One sweep per hour is plenty — the TTL is measured in days.
WORKSPACE_REAP_INTERVAL_SECONDS = 3600


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

    if datetime.now(UTC) < expiration_time:
        return  # Not expired yet

    logger.info("Workshop %s has expired — deleting CRD", name)
    try:
        if await memo.cluster.delete_workshop(name, namespace):
            logger.info("Workshop %s CRD deleted", name)
        else:
            logger.info("Workshop %s already gone", name)
    except Exception as e:
        logger.error("Failed to delete expired workshop %s: %s", name, e)


@kopf.on.delete(GROUP, VERSION, PLURAL, optional=True)  # type: ignore
async def workshop_delete_stamps_workspace(
    spec: dict, namespace: str, name: str, memo: kopf.Memo, **kwargs: Any
) -> None:
    """Session end (ADR-0010 decision E): refresh last-used on the workspace PVC.

    The PVC is unowned so it survives this deletion; the stamp is what keeps
    the idle-TTL reaper from reclaiming a recently-used workspace. Best-effort
    (optional=True — no finalizer, deletion is never blocked): creation already
    stamped a floor, so a missed update only makes the reaper conservative.
    """
    try:
        pvc = workspace_pvc_ref(dict(spec))
    except Exception:
        return  # legacy/invalid spec — nothing to stamp
    if pvc is None:
        return  # ephemeral storage; its PVC is owner-referenced and GC'd

    try:
        await memo.cluster.stamp_pvc_last_used(pvc, namespace)
        logger.info("Stamped last-used on workspace PVC %s/%s", namespace, pvc)
    except Exception as e:
        logger.warning(
            "Failed to stamp last-used on workspace PVC %s/%s: %s", namespace, pvc, e
        )


async def reap_idle_workspaces(cluster: OperatorCluster) -> None:
    """One sweep: delete workspace PVCs idle past the TTL and not mounted.

    Only PVCs matching the workspace label selector are ever listed, so the
    ephemeral per-session PVC machinery is untouched. A PVC with a missing or
    unparseable last-used annotation is kept (deletion is the irreversible
    branch, so parse doubt resolves to 'keep').
    """
    cutoff = datetime.now(UTC) - timedelta(days=get_settings().workspace_idle_ttl_days)
    pvcs = await cluster.list_workspace_pvcs()
    if not pvcs:
        return
    mounted = await cluster.mounted_pvcs()

    for pvc in pvcs:
        namespace, name = pvc.metadata.namespace, pvc.metadata.name
        if (namespace, name) in mounted:
            continue
        raw = (pvc.metadata.annotations or {}).get(LAST_USED_ANNOTATION)
        try:
            last_used = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if last_used.tzinfo is None:
                last_used = last_used.replace(tzinfo=UTC)
        except (AttributeError, ValueError):
            logger.warning(
                "Workspace PVC %s/%s has no parseable %s annotation — keeping",
                namespace,
                name,
                LAST_USED_ANNOTATION,
            )
            continue
        if last_used < cutoff:
            logger.info(
                "Reaping idle workspace PVC %s/%s (last used %s, TTL %sd)",
                namespace,
                name,
                raw,
                get_settings().workspace_idle_ttl_days,
            )
            await cluster.delete_pvc(name, namespace)


async def workspace_reaper_loop(cluster: OperatorCluster) -> None:
    """Low-frequency background sweep, started once at operator startup."""
    while True:
        try:
            await reap_idle_workspaces(cluster)
        except Exception:
            logger.exception("Workspace PVC sweep failed — retrying next interval")
        await asyncio.sleep(WORKSPACE_REAP_INTERVAL_SECONDS)


@kopf.on.field(GROUP, VERSION, PLURAL, field="status.phase")  # type: ignore
async def workshop_phase_change(
    old: str, new: str, namespace: str, name: str, **kwargs: Any
) -> None:
    """Log phase transitions for visibility."""
    if old != new:
        logger.info("Workshop %s phase changed: %s -> %s", name, old, new)
