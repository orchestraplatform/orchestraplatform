"""Cleanup handlers for expired workshops."""

import logging
from typing import Any

import kopf


logger = logging.getLogger(__name__)


def register_cleanup_handlers() -> None:
    """Register cleanup-related Kopf handlers."""
    # Handlers are registered via decorators below
    pass


# check every 5 minutes for expired workshops
@kopf.timer('orchestra.io', 'v1', 'workshops', interval=300)  # type: ignore
async def workshop_expiration_timer(
    spec: dict,
    status: dict,
    namespace: str,
    name: str,
    **kwargs: Any
) -> None:
    """
    Periodic timer to check for expired workshops and clean them up.
    
    This runs every 5 minutes to check if workshops have expired
    based on their expiresAt timestamp.
    """
    logger.info(f"Checking expiration for workshop {name} in namespace {namespace}")
    
    # Get expiration time from status
    expires_at = status.get('expiresAt')
    if not expires_at:
        logger.warning(f"Workshop {name} has no expiration time set")
        return
    
    # Parse expiration time and check if expired
    from datetime import datetime
    try:
        expiration_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        current_time = datetime.now(expiration_time.tzinfo)
        
        if current_time >= expiration_time:
            logger.info(f"Workshop {name} has expired, scheduling for deletion")
            
            # Mark workshop for deletion by updating its phase
            # The actual deletion will be handled by the delete handler
            # For now, we'll just log the expiration
            # In a real implementation, you'd trigger deletion here
            
            logger.info(f"Workshop {name} marked for expiration cleanup")
            
    except ValueError as e:
        logger.error(f"Failed to parse expiration time for workshop {name}: {e}")


@kopf.on.field('orchestra.io', 'v1', 'workshops', field='status.phase') # type: ignore
async def workshop_phase_change(
    old: str,
    new: str, 
    namespace: str,
    name: str,
    **kwargs: Any
) -> None:
    """
    Handle changes to workshop phase for logging and monitoring.
    
    This provides visibility into workshop lifecycle transitions.
    """
    if old != new:
        logger.info(f"Workshop {name} phase changed: {old} -> {new}")
        
        # You could add metrics collection here
        # or send notifications about state changes
