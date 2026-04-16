"""Orchestra API — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.core.config import get_settings
from api.core.database import get_engine
from api.core.kubernetes import get_k8s_client
from api.routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise external connections on startup; clean up on shutdown."""
    logger.info("Starting Orchestra API...")

    try:
        get_k8s_client()
        logger.info("Kubernetes client initialised")
    except Exception as e:
        logger.error("Failed to initialise Kubernetes client: %s", e)
        raise

    try:
        engine = get_engine()
        async with engine.connect():
            pass
        logger.info("Database connection verified")
    except Exception as e:
        logger.error("Failed to connect to database: %s", e)
        raise

    yield

    await get_engine().dispose()
    logger.info("Orchestra API shut down")


settings = get_settings()

app = FastAPI(
    title="Orchestra API",
    description="REST API for managing RStudio workshops via Orchestra Operator",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", response_model=dict)
async def root():
    """Root endpoint — API metadata."""
    return {
        "name": "Orchestra API",
        "version": "0.1.0",
        "docs_url": "/docs",
        "health_url": "/health",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
