# Orchestra Operator Specification

## Overview
The Orchestra Operator manages the lifecycle of RStudio workshop instances on Kubernetes. It automates the creation, management, and cleanup of workshop environments for data science education and training.

## Architecture

### Custom Resource Definitions (CRDs)

#### Workshop CRD
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: workshops.orchestra.io
spec:
  group: orchestra.io
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              name:
                type: string
                description: "Workshop instance name"
              duration:
                type: string
                default: "4h"
                description: "Workshop duration (e.g., 4h, 2h30m)"
              image:
                type: string
                default: "rocker/rstudio:latest"
                description: "RStudio Docker image to use"
              resources:
                type: object
                properties:
                  cpu:
                    type: string
                    default: "1"
                  memory:
                    type: string
                    default: "2Gi"
              storage:
                type: object
                properties:
                  size:
                    type: string
                    default: "10Gi"
                  storageClass:
                    type: string
              ingress:
                type: object
                properties:
                  host:
                    type: string
                  annotations:
                    type: object
          status:
            type: object
            properties:
              phase:
                type: string
                enum: ["Pending", "Creating", "Ready", "Running", "Terminating", "Failed"]
              url:
                type: string
              createdAt:
                type: string
              expiresAt:
                type: string
              conditions:
                type: array
                items:
                  type: object
  scope: Namespaced
  names:
    plural: workshops
    singular: workshop
    kind: Workshop
```

## Controller Logic

### Workshop Controller Reconciliation Loop

1. **Creation Phase** (`Pending` → `Creating` → `Ready`)
   - Create PersistentVolumeClaim for user data
   - Create Deployment with RStudio container
   - Create Service to expose RStudio
   - Create Ingress for external access
   - Wait for all resources to be ready
   
2. **Running Phase** (`Ready` → `Running`)
   - Monitor workshop health
   - Track usage and expiration
   - Handle participant connections
   
3. **Cleanup Phase** (`Running` → `Terminating`)
   - Delete Ingress (stop external access)
   - Delete Service 
   - Delete Deployment
   - Optionally preserve PVC for data retention

### State Transitions

```
Pending → Creating → Ready → Running → Terminating → (Deleted)
    ↓         ↓        ↓        ↓
   Failed   Failed   Failed   Failed
```

## Key Features

### Automatic Workshop Lifecycle
- **Time-based expiration**: Workshops auto-terminate after specified duration
- **Resource management**: CPU, memory, and storage limits
- **Health monitoring**: Restart failed workshops
- **Graceful shutdown**: Save work before termination

### Integration Points
- **Traefik**: Ingress controller for routing
- **Persistent Storage**: Workshop data persistence
- **RBAC**: Secure access controls
- **Monitoring**: Metrics and logging

### Operator Components

1. **Workshop Controller**: Main reconciliation logic
2. **Cleanup Controller**: Handles expired workshops  
3. **Health Monitor**: Monitors workshop pod health
4. **Metrics Exporter**: Prometheus metrics

## Implementation Plan

### Phase 1: Core CRD and Operator Setup
- [ ] Define Workshop CRD YAML
- [ ] Set up Python project with Kopf
- [ ] Implement basic operator with create/update/delete handlers
- [ ] Pod/Service/Ingress creation logic
- [ ] Basic status reporting

### Phase 2: Lifecycle Management  
- [ ] Workshop expiration handling with background tasks
- [ ] Automatic cleanup using Kopf timers
- [ ] Health monitoring
- [ ] Error handling and retries

### Phase 3: Advanced Features
- [ ] Multi-participant workshops
- [ ] Data persistence options
- [ ] Resource quotas and limits
- [ ] Monitoring and metrics

### Phase 4: Production Readiness
- [ ] RBAC implementation
- [ ] Security hardening
- [ ] Performance optimization
- [ ] Documentation and examples

## File Structure (Python/Kopf)
```
orchestra-operator/
├── config/
│   ├── crd/
│   │   └── workshop-crd.yaml
│   ├── rbac/
│   │   ├── role.yaml
│   │   ├── role-binding.yaml
│   │   └── service-account.yaml
│   └── deploy/
│       └── deployment.yaml
├── src/
│   ├── operator.py              # Main Kopf operator
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── workshop.py          # Workshop CRUD handlers
│   │   └── cleanup.py           # Cleanup and expiration
│   ├── resources/
│   │   ├── __init__.py
│   │   ├── deployment.py        # RStudio Deployment creation
│   │   ├── service.py           # Service creation
│   │   ├── ingress.py           # Ingress creation
│   │   └── pvc.py               # PersistentVolumeClaim creation
│   └── utils/
│       ├── __init__.py
│       ├── k8s_client.py        # Kubernetes client utilities
│       └── time_utils.py        # Duration parsing, expiration
├── tests/
│   ├── unit/
│   └── e2e/
├── pyproject.toml               # Python dependencies
├── Dockerfile
├── justfile                     # Development tasks
└── requirements.txt
```

## Kopf Operator Architecture

### Main Components

1. **Workshop Handler**: Responds to Workshop CRD events
2. **Resource Managers**: Create/update Kubernetes resources
3. **Background Tasks**: Handle expiration and cleanup
4. **Health Monitoring**: Monitor workshop pod status

### Key Kopf Features We'll Use

- **Event Handlers**: `@kopf.on.create`, `@kopf.on.update`, `@kopf.on.delete`
- **Background Tasks**: `@kopf.timer` for periodic cleanup
- **Status Management**: Built-in status field handling
- **Error Handling**: Automatic retries and backoff
- **Finalizers**: Ensure proper cleanup on deletion