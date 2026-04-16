"""API routes — all routers wired with prefixes and tags."""

from fastapi import APIRouter

from api.routes import auth, health, instances, workshops

router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(workshops.router, prefix="/workshops", tags=["workshops"])
router.include_router(instances.router, prefix="/instances", tags=["instances"])
