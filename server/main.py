#!/usr/bin/env python3
"""
Orchestra API - FastAPI-based REST API for managing RStudio workshops.

This API provides a user-friendly interface for creating, monitoring, and managing
workshops through the Orchestra Operator's Workshop CRDs.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from api.core.config import get_settings
from api.core.database import get_engine
from api.core.kubernetes import get_k8s_client
from api.routes import auth, health, workshops
from api.routes import instances

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Orchestra API...")

    # Initialize Kubernetes client
    try:
        get_k8s_client()
        logger.info("Kubernetes client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Kubernetes client: {e}")
        raise

    # Verify database connectivity
    try:
        engine = get_engine()
        async with engine.connect():
            pass
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    yield

    await get_engine().dispose()

    logger.info("Shutting down Orchestra API...")


# Create FastAPI app
app = FastAPI(
    title="Orchestra API",
    description="REST API for managing RStudio workshops via Orchestra Operator",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

settings = get_settings()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(workshops.router, prefix="/workshops", tags=["workshops"])
app.include_router(instances.router, prefix="/instances", tags=["instances"])


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Orchestra API",
        "version": "0.1.0",
        "description": "REST API for managing RStudio workshops",
        "docs_url": "/docs",
        "health_url": "/health",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/elements")
@app.get("/docs", include_in_schema=False)
async def api_documentation(request: Request):
    return HTMLResponse("""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Elements in HTML</title>

    <script src="https://unpkg.com/@stoplight/elements/web-components.min.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/@stoplight/elements/styles.min.css">
  </head>
  <body>

    <elements-api
      apiDescriptionUrl="openapi.json"
      router="hash"
    />

  </body>
</html>""")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
