"""OperatorCluster: the operator's seam to the cluster for Workshop children.

Two adapters satisfy the interface: K8sOperatorCluster (real) and the
in-memory FakeOperatorCluster in tests. Handlers receive the adapter via
kopf's memo (set in main.py's startup handler).
"""

import asyncio
import logging
from typing import Protocol

import kubernetes.client as k8s_client
from kubernetes.client.rest import ApiException

from crd import GROUP, PLURAL, VERSION
from resources.desired import WorkshopChildren
from resources.naming import deployment_name

logger = logging.getLogger(__name__)


class OperatorCluster(Protocol):
    """Interface contract: apply() is idempotent (already-existing children
    are skipped); delete_workshop() returns False on a missing Workshop CRD;
    all other API errors propagate."""

    async def apply(self, children: WorkshopChildren, namespace: str) -> None: ...

    async def deployment_ready(self, workshop_name: str, namespace: str) -> bool: ...

    async def delete_workshop(self, name: str, namespace: str) -> bool: ...


class K8sOperatorCluster:
    """OperatorCluster adapter backed by the Kubernetes API.

    The sync kubernetes client is wrapped in asyncio.to_thread so calls don't
    block the kopf event loop that runs every other handler and timer.
    """

    async def apply(self, children: WorkshopChildren, namespace: str) -> None:
        """Create every child resource, skipping ones that already exist so
        kopf can safely retry after a TemporaryError."""
        apps = k8s_client.AppsV1Api()
        core = k8s_client.CoreV1Api()
        custom = k8s_client.CustomObjectsApi()
        name = children.workshop_name

        if children.pvc is not None:
            await self._create_or_ignore(
                core.create_namespaced_persistent_volume_claim,
                "PVC",
                name,
                namespace=namespace,
                body=children.pvc,
            )

        await self._create_or_ignore(
            apps.create_namespaced_deployment,
            "Deployment",
            name,
            namespace=namespace,
            body=children.deployment,
        )

        await self._create_or_ignore(
            core.create_namespaced_service,
            "Service",
            name,
            namespace=namespace,
            body=children.service,
        )

        if children.middleware is not None:
            await self._create_or_ignore(
                custom.create_namespaced_custom_object,
                "Middleware",
                name,
                group="traefik.io",
                version="v1alpha1",
                namespace=namespace,
                plural="middlewares",
                body=children.middleware,
            )

        await self._create_or_ignore(
            custom.create_namespaced_custom_object,
            "IngressRoute",
            name,
            group="traefik.io",
            version="v1alpha1",
            namespace=namespace,
            plural="ingressroutes",
            body=children.ingress,
        )

    async def deployment_ready(self, workshop_name: str, namespace: str) -> bool:
        dep = await asyncio.to_thread(
            k8s_client.AppsV1Api().read_namespaced_deployment,
            name=deployment_name(workshop_name),
            namespace=namespace,
        )
        return (dep.status.ready_replicas or 0) >= 1

    async def delete_workshop(self, name: str, namespace: str) -> bool:
        try:
            await asyncio.to_thread(
                k8s_client.CustomObjectsApi().delete_namespaced_custom_object,
                group=GROUP,
                version=VERSION,
                namespace=namespace,
                plural=PLURAL,
                name=name,
            )
        except ApiException as e:
            if e.status == 404:
                return False
            raise
        return True

    @staticmethod
    async def _create_or_ignore(api_call, kind: str, name: str, **kwargs) -> None:
        try:
            await asyncio.to_thread(api_call, **kwargs)
        except ApiException as e:
            if e.status == 409:
                logger.info("%s %s already exists", kind, name)
            else:
                raise
