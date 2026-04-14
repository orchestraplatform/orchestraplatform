"""RStudio Deployment creation for workshops."""

from typing import Any, Dict
import kubernetes.client as k8s


def create_rstudio_deployment(
    workshop_name: str,
    namespace: str, 
    image: str,
    resources: Dict[str, Any],
    storage: Dict[str, Any]
) -> k8s.V1Deployment:
    """
    Create a Kubernetes Deployment for an RStudio workshop instance.
    
    Args:
        workshop_name: Name of the workshop
        namespace: Kubernetes namespace
        image: Docker image for RStudio
        resources: Resource limits and requests
        storage: Storage configuration
        
    Returns:
        V1Deployment object ready to be created
    """
    # Resource limits and requests
    cpu_limit = resources.get('cpu', '1')
    memory_limit = resources.get('memory', '2Gi')
    cpu_request = resources.get('cpuRequest', '500m')
    memory_request = resources.get('memoryRequest', '1Gi')
    
    # Container definition
    container = k8s.V1Container(
        name='rstudio',
        image=image,
        ports=[
            k8s.V1ContainerPort(container_port=8787, name='rstudio')
        ],
        env=[
            k8s.V1EnvVar(name='DISABLE_AUTH', value='true'),  # For demo purposes
            k8s.V1EnvVar(name='ROOT', value='true'),
        ],
        resources=k8s.V1ResourceRequirements(
            requests={
                'cpu': cpu_request,
                'memory': memory_request
            },
            limits={
                'cpu': cpu_limit,
                'memory': memory_limit
            }
        ),
        volume_mounts=[
            k8s.V1VolumeMount(
                name='workshop-data',
                mount_path='/data'
            )
        ] if storage else None
    )
    
    # Volume definition (if storage is configured)
    volumes = []
    if storage:
        volumes.append(
            k8s.V1Volume(
                name='workshop-data',
                persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
                    claim_name=f"{workshop_name}-pvc"
                )
            )
        )
    
    # Pod template
    pod_template = k8s.V1PodTemplateSpec(
        metadata=k8s.V1ObjectMeta(
            labels={
                'app': workshop_name,
                'component': 'rstudio',
                'workshop': workshop_name
            }
        ),
        spec=k8s.V1PodSpec(
            containers=[container],
            volumes=volumes if volumes else None
        )
    )
    
    # Deployment specification
    deployment_spec = k8s.V1DeploymentSpec(
        replicas=1,
        selector=k8s.V1LabelSelector(
            match_labels={
                'app': workshop_name,
                'component': 'rstudio'
            }
        ),
        template=pod_template
    )
    
    # Create the deployment
    deployment = k8s.V1Deployment(
        api_version='apps/v1',
        kind='Deployment',
        metadata=k8s.V1ObjectMeta(
            name=f"{workshop_name}-deployment",
            namespace=namespace,
            labels={
                'app': workshop_name,
                'component': 'rstudio',
                'workshop': workshop_name
            }
        ),
        spec=deployment_spec
    )
    
    return deployment
