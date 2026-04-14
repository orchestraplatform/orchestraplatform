"""Health check routes."""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "orchestra-api",
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes."""
    # Add checks for Kubernetes connectivity here
    return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/live")
async def liveness_check():
    """Liveness check for Kubernetes."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}
