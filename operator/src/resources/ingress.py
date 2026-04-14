"""Ingress creation for workshops."""

from typing import Any, Dict


def create_workshop_ingress(
    workshop_name: str, 
    namespace: str, 
    ingress_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a Traefik IngressRoute for a workshop.
    
    Args:
        workshop_name: Name of the workshop
        namespace: Kubernetes namespace
        ingress_config: Ingress configuration from workshop spec
        
    Returns:
        IngressRoute manifest as a dictionary ready to be created
    """
    # Generate host based on workshop name + orchestraplatform.org
    host = f"{workshop_name}.orchestraplatform.org"
    
    # Override with custom host if provided in config
    if ingress_config.get('host'):
        host = ingress_config['host']
    
    # Get entry points (default to 'web' for HTTP)
    entry_points = ingress_config.get('entryPoints', ['web'])
    
    # Additional annotations if needed
    annotations = ingress_config.get('annotations', {})
    
    ingress_route = {
        'apiVersion': 'traefik.io/v1alpha1',
        'kind': 'IngressRoute',
        'metadata': {
            'name': f"{workshop_name}-ingress",
            'namespace': namespace,
            'labels': {
                'app': workshop_name,
                'component': 'rstudio',
                'workshop': workshop_name
            },
            'annotations': annotations
        },
        'spec': {
            'entryPoints': entry_points,
            'routes': [
                {
                    'match': f"Host(`{host}`)",
                    'kind': 'Rule',
                    'services': [
                        {
                            'name': f"{workshop_name}-service",
                            'port': 80
                        }
                    ]
                }
            ]
        }
    }
    
    return ingress_route
