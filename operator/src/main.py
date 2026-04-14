#!/usr/bin/env python3
"""
Orchestra Operator - Kubernetes operator for managing RStudio workshop instances.

This operator manages the complete lifecycle of RStudio workshops:
- Creating Pods, Services, and Ingress resources
- Managing workshop expiration and cleanup
- Health monitoring and status reporting
"""

import asyncio
import logging
import sys
from typing import Any, Dict

import kopf
import kubernetes

from handlers.workshop import register_workshop_handlers
from handlers.cleanup import register_cleanup_handlers


def setup_logging() -> None:
    """Configure logging for the operator."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    
    # Set kubernetes client logging to WARNING to reduce noise
    logging.getLogger("kubernetes").setLevel(logging.WARNING)


def setup_kubernetes() -> None:
    """Initialize Kubernetes client configuration."""
    try:
        # Try in-cluster config first (when running in pod)
        kubernetes.config.load_incluster_config()
        logging.info("Loaded in-cluster Kubernetes configuration")
    except kubernetes.config.ConfigException:
        # Fall back to local kubeconfig (for development)
        kubernetes.config.load_kube_config()
        logging.info("Loaded local Kubernetes configuration")


@kopf.on.startup()
async def startup_handler(settings: kopf.OperatorSettings, **kwargs: Any) -> None:
    """Initialize the operator on startup."""
    logging.info("Orchestra Operator starting up...")
    
    # Configure Kopf settings
    settings.posting.level = logging.INFO
    settings.watching.reconnect_backoff = 1.0
    settings.batching.worker_limit = 20
    
    # Setup Kubernetes client
    setup_kubernetes()
    
    logging.info("Orchestra Operator startup complete")


@kopf.on.cleanup()
async def cleanup_handler(**kwargs: Any) -> None:
    """Clean up resources on operator shutdown."""
    logging.info("Orchestra Operator shutting down...")


def main() -> None:
    """Main entry point for the operator."""
    setup_logging()
    
    # Register all handlers
    register_workshop_handlers()
    register_cleanup_handlers()
    
    logging.info("Starting Orchestra Operator...")
    
    # Run the operator
    kopf.run(
        clusterwide=False,  # Namespace-scoped for security
        namespace=None,     # Watch all namespaces the operator has access to
    )


if __name__ == "__main__":
    main()
