"""Workshop service layer for Kubernetes integration."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from api.core.kubernetes import get_custom_objects_api, ApiException
from api.models.workshop import (
    WorkshopCreate, 
    WorkshopResponse, 
    WorkshopPhase,
    WorkshopStatus,
    WorkshopCondition
)

logger = logging.getLogger(__name__)

# Kubernetes API constants
GROUP = "orchestra.io"
VERSION = "v1"
PLURAL = "workshops"


class WorkshopService:
    """Service for managing workshops via Kubernetes CRDs."""
    
    def __init__(self):
        self.custom_api = get_custom_objects_api()
    
    async def create_workshop(
        self, 
        workshop: WorkshopCreate, 
        namespace: str = "default"
    ) -> WorkshopResponse:
        """Create a new workshop."""
        try:
            # Convert Pydantic model to Kubernetes CRD
            workshop_crd = self._to_kubernetes_crd(workshop, namespace)
            
            # Create the workshop in Kubernetes
            result = self.custom_api.create_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                namespace=namespace,
                plural=PLURAL,
                body=workshop_crd
            )
            
            logger.info(f"Created workshop {workshop.name} in namespace {namespace}")
            return self._from_kubernetes_crd(result)
            
        except ApiException as e:
            logger.error(f"Failed to create workshop {workshop.name}: {e}")
            raise
    
    async def get_workshop(
        self, 
        name: str, 
        namespace: str = "default"
    ) -> Optional[WorkshopResponse]:
        """Get a workshop by name."""
        try:
            result = self.custom_api.get_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                namespace=namespace,
                plural=PLURAL,
                name=name
            )
            return self._from_kubernetes_crd(result)
            
        except ApiException as e:
            if e.status == 404:
                return None
            logger.error(f"Failed to get workshop {name}: {e}")
            raise
    
    async def list_workshops(
        self, 
        namespace: str = "default",
        label_selector: Optional[str] = None
    ) -> List[WorkshopResponse]:
        """List all workshops in a namespace."""
        try:
            result = self.custom_api.list_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                namespace=namespace,
                plural=PLURAL,
                label_selector=label_selector
            )
            
            workshops = []
            for item in result.get("items", []):
                workshops.append(self._from_kubernetes_crd(item))
            
            return workshops
            
        except ApiException as e:
            logger.error(f"Failed to list workshops: {e}")
            raise
    
    async def delete_workshop(
        self, 
        name: str, 
        namespace: str = "default"
    ) -> bool:
        """Delete a workshop."""
        try:
            self.custom_api.delete_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                namespace=namespace,
                plural=PLURAL,
                name=name
            )
            logger.info(f"Deleted workshop {name} in namespace {namespace}")
            return True
            
        except ApiException as e:
            if e.status == 404:
                return False
            logger.error(f"Failed to delete workshop {name}: {e}")
            raise
    
    def _to_kubernetes_crd(self, workshop: WorkshopCreate, namespace: str) -> Dict[str, Any]:
        """Convert Pydantic model to Kubernetes CRD format."""
        crd = {
            "apiVersion": f"{GROUP}/{VERSION}",
            "kind": "Workshop",
            "metadata": {
                "name": workshop.name,
                "namespace": namespace,
                "labels": {
                    "app": "orchestra-operator",
                    "managed-by": "orchestra-api"
                }
            },
            "spec": {
                "name": workshop.name,
                "duration": workshop.duration,
                "image": workshop.image,
                "resources": {
                    "cpu": workshop.resources.cpu,
                    "memory": workshop.resources.memory,
                    "cpuRequest": workshop.resources.cpu_request,
                    "memoryRequest": workshop.resources.memory_request,
                }
            }
        }
        
        # Add optional fields
        if workshop.storage:
            crd["spec"]["storage"] = {
                "size": workshop.storage.size
            }
            if workshop.storage.storage_class:
                crd["spec"]["storage"]["storageClass"] = workshop.storage.storage_class
        
        if workshop.ingress:
            crd["spec"]["ingress"] = {}
            if workshop.ingress.host:
                crd["spec"]["ingress"]["host"] = workshop.ingress.host
            if workshop.ingress.annotations:
                crd["spec"]["ingress"]["annotations"] = workshop.ingress.annotations
        
        return crd
    
    def _from_kubernetes_crd(self, crd: Dict[str, Any]) -> WorkshopResponse:
        """Convert Kubernetes CRD to Pydantic model."""
        metadata = crd.get("metadata", {})
        spec = crd.get("spec", {})
        status = crd.get("status", {})
        
        # Parse status
        workshop_status = None
        if status:
            conditions = []
            for cond in status.get("conditions", []):
                conditions.append(WorkshopCondition(
                    type=cond.get("type"),
                    status=cond.get("status"),
                    reason=cond.get("reason"),
                    message=cond.get("message"),
                    last_transition_time=cond.get("lastTransitionTime")
                ))
            
            workshop_status = WorkshopStatus(
                phase=WorkshopPhase(status.get("phase", "Pending")),
                url=status.get("url"),
                created_at=self._parse_datetime(status.get("createdAt")),
                expires_at=self._parse_datetime(status.get("expiresAt")),
                conditions=conditions
            )
        
        # Build workshop response
        return WorkshopResponse(
            name=metadata.get("name"),
            namespace=metadata.get("namespace"),
            spec=self._parse_spec(spec),
            status=workshop_status,
            created_at=self._parse_datetime(metadata.get("creationTimestamp")),
            updated_at=self._parse_datetime(metadata.get("resourceVersion"))
        )
    
    def _parse_spec(self, spec: Dict[str, Any]) -> WorkshopCreate:
        """Parse workshop spec from Kubernetes CRD."""
        # This is a simplified version - you'd want more robust parsing
        from api.models.workshop import WorkshopResources, WorkshopStorage, WorkshopIngress
        
        resources = WorkshopResources(
            cpu=spec.get("resources", {}).get("cpu", "1"),
            memory=spec.get("resources", {}).get("memory", "2Gi"),
            cpu_request=spec.get("resources", {}).get("cpuRequest", "500m"),
            memory_request=spec.get("resources", {}).get("memoryRequest", "1Gi"),
        )
        
        storage = None
        if "storage" in spec:
            storage = WorkshopStorage(
                size=spec["storage"].get("size", "10Gi"),
                storage_class=spec["storage"].get("storageClass")
            )
        
        ingress = None
        if "ingress" in spec:
            ingress = WorkshopIngress(
                host=spec["ingress"].get("host"),
                annotations=spec["ingress"].get("annotations", {})
            )
        
        return WorkshopCreate(
            name=spec.get("name"),
            duration=spec.get("duration", "4h"),
            image=spec.get("image", "rocker/rstudio:latest"),
            resources=resources,
            storage=storage,
            ingress=ingress
        )
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string."""
        if not dt_str:
            return None
        try:
            # Handle various datetime formats
            if dt_str.endswith('Z'):
                dt_str = dt_str[:-1] + '+00:00'
            return datetime.fromisoformat(dt_str)
        except ValueError:
            return None
