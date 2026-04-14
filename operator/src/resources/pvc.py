"""PersistentVolumeClaim creation for workshops."""

from typing import Any, Dict
import kubernetes.client as k8s


def create_workshop_pvc(
    workshop_name: str,
    namespace: str,
    storage_config: Dict[str, Any]
) -> k8s.V1PersistentVolumeClaim:
    """
    Create a PersistentVolumeClaim for workshop data.
    
    Args:
        workshop_name: Name of the workshop
        namespace: Kubernetes namespace
        storage_config: Storage configuration from workshop spec
        
    Returns:
        V1PersistentVolumeClaim object ready to be created
    """
    size = storage_config.get('size', '10Gi')
    storage_class = storage_config.get('storageClass')
    
    pvc = k8s.V1PersistentVolumeClaim(
        api_version='v1',
        kind='PersistentVolumeClaim',
        metadata=k8s.V1ObjectMeta(
            name=f"{workshop_name}-pvc",
            namespace=namespace,
            labels={
                'app': workshop_name,
                'component': 'storage'
            }
        ),
        spec=k8s.V1PersistentVolumeClaimSpec(
            access_modes=['ReadWriteOnce'],
            resources=k8s.V1ResourceRequirements(
                requests={'storage': size}
            ),
            storage_class_name=storage_class
        )
    )
    
    return pvc
