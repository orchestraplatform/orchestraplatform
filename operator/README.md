# Orchestra Operator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-1.28+-blue.svg)](https://kubernetes.io/)

A Kubernetes operator for managing RStudio workshop instances with automated lifecycle management, resource provisioning, and cleanup.

## 🎯 Overview

Orchestra Operator automates the creation, management, and cleanup of RStudio workshop environments on Kubernetes. It provides a declarative API for workshop provisioning with features like time-based expiration, resource management, and persistent storage.

### Key Features

- 🚀 **Automated Workshop Provisioning** - One-click RStudio environment creation
- ⏰ **Time-based Expiration** - Automatic cleanup after configurable duration
- 💾 **Persistent Storage** - Workshop data retention with PVCs
- 🌐 **Ingress Integration** - Traefik support for external access
- 📊 **Resource Management** - CPU/memory limits and requests
- 🔄 **Lifecycle Monitoring** - Real-time status and health tracking

## 🏗️ Architecture

The operator manages the complete workshop lifecycle:

```
User Request → Workshop CRD → Operator → Pod/Service/Ingress → Ready for Use
```

### Components

- **Workshop CRD**: Custom resource definition for workshop specifications
- **Main Operator**: Kopf-based controller with event handlers
- **Resource Managers**: Kubernetes resource creation and management
- **Cleanup Controller**: Expiration monitoring and automated cleanup

## 🚀 Quick Start

### Prerequisites

- Kubernetes cluster (v1.28+)
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) for dependency management
- [just](https://github.com/casey/just) for task automation
- [kind](https://kind.sigs.k8s.io/) for local development

### Installation

1. **Open the monorepo**
   ```bash
   cd operator
   ```

2. **Set up development environment**
   ```bash
   # Install dependencies
   just install-deps
   
   # Create Kind cluster
   just cluster-up
   
   # Apply CRDs
   just apply-crd
   ```

3. **Run the operator locally**
   ```bash
   just run-local
   ```

4. **Create a workshop**
   ```bash
   kubectl apply -f examples/workshop-example.yaml
   ```

## 📖 Usage

### Creating a Workshop

Create a workshop by applying a Workshop custom resource:

```yaml
apiVersion: orchestra.io/v1
kind: Workshop
metadata:
  name: data-science-101
  namespace: default
spec:
  name: "data-science-101"
  duration: "4h"
  image: "rocker/rstudio:latest"
  resources:
    cpu: "2"
    memory: "4Gi"
    cpuRequest: "1"
    memoryRequest: "2Gi"
  storage:
    size: "20Gi"
    storageClass: "fast-ssd"
  ingress:
    host: "workshop.example.com"
    annotations:
      kubernetes.io/ingress.class: "traefik"
```

### Monitoring Workshops

```bash
# List all workshops
kubectl get workshops

# Get workshop details
kubectl describe workshop data-science-101

# Check workshop status
kubectl get workshop data-science-101 -o jsonpath='{.status.phase}'
```

### Accessing Workshops

For local development with port-forwarding:

```bash
# Port-forward to RStudio service
kubectl port-forward service/data-science-101-service 8787:80

# Access RStudio at http://localhost:8787
# (Authentication disabled in demo mode)
```

## 🛠️ Development

### Project Structure

```
operator/
├── config/
│   ├── crd/                    # Custom Resource Definitions
│   ├── rbac/                   # Role-based access control
│   └── deploy/                 # Deployment manifests
├── src/
│   ├── main.py                 # Operator entry point
│   ├── handlers/               # Event handlers
│   │   ├── workshop.py         # Workshop reconciliation and deletion
│   │   └── cleanup.py          # Expiration and cleanup
│   ├── resources/              # K8s resource creation
│   │   ├── deployment.py       # RStudio deployments
│   │   ├── service.py          # Service creation
│   │   ├── ingress.py          # Ingress management
│   │   └── pvc.py              # Storage provisioning
│   └── utils/
│       └── time_utils.py       # Duration parsing
├── examples/                   # Example workshop definitions
├── tests/                      # Test suites
├── justfile                    # Development tasks
├── pyproject.toml              # Python dependencies
└── Dockerfile                  # Container image
```

### Development Workflow

1. **Set up local environment**
   ```bash
   just install-deps
   just cluster-up
   ```

2. **Run tests**
   ```bash
   just test
   ```

3. **Run operator locally**
   ```bash
   just run-local
   ```

4. **Build and deploy**
   ```bash
   just build-image
   just deploy
   ```

### Available Commands

```bash
just --list                     # Show all available commands
just cluster-up                 # Create Kind cluster
just cluster-down               # Delete Kind cluster
just cluster-reset              # Reset cluster (delete + create)
just install-deps               # Install Python dependencies
just run-local                  # Run operator locally
just build-image                # Build Docker image
just apply-crd                  # Apply CRDs to cluster
just deploy                     # Deploy operator to cluster
just test                       # Run test suite
```

## 📋 API Reference

### Workshop Spec

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | *required* | Workshop instance name |
| `duration` | string | `"4h"` | Workshop duration (e.g., "2h30m", "1d") |
| `image` | string | `"rocker/rstudio:latest"` | RStudio Docker image |
| `resources.cpu` | string | `"1"` | CPU limit |
| `resources.memory` | string | `"2Gi"` | Memory limit |
| `resources.cpuRequest` | string | `"500m"` | CPU request |
| `resources.memoryRequest` | string | `"1Gi"` | Memory request |
| `storage.size` | string | `"10Gi"` | Storage size |
| `storage.storageClass` | string | `""` | Storage class name |
| `ingress.host` | string | `""` | Ingress hostname |
| `ingress.annotations` | object | `{}` | Ingress annotations |

### Workshop Status

| Field | Type | Description |
|-------|------|-------------|
| `phase` | string | Current phase: `Pending`, `Creating`, `Ready`, `Running`, `Terminating`, `Failed` |
| `url` | string | Workshop access URL |
| `createdAt` | string | Creation timestamp |
| `expiresAt` | string | Expiration timestamp |
| `conditions` | array | Detailed status conditions |

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHONPATH` | `/app/src` | Python module path |
| `KOPF_LOG_LEVEL` | `INFO` | Logging level |

### Operator Settings

The operator can be configured via Kopf settings in `src/main.py`:

```python
settings.posting.level = logging.INFO
settings.watching.reconnect_backoff = 1.0
settings.batching.worker_limit = 20
```

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
just test

# Run with uv directly
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

### Manual Testing

1. Create a test workshop:
   ```bash
   kubectl apply -f examples/workshop-example.yaml
   ```

2. Monitor the workshop creation:
   ```bash
   kubectl get workshops -w
   ```

3. Check created resources:
   ```bash
   kubectl get pods,services,ingress,pvc -l workshop=data-science-101
   ```

## 📦 Deployment

### Production Deployment

1. **Build and push image**
   ```bash
   docker build -t your-registry/orchestra-operator:v1.0.0 .
   docker push your-registry/orchestra-operator:v1.0.0
   ```

2. **Deploy to cluster** (use the Helm chart in `deploy/charts/orchestra`)
   ```bash
   helm upgrade --install orchestra deploy/charts/orchestra -f deploy/gcp-values.yaml
   ```

## 🤝 Contributing

We welcome contributions! Please see our [contributing guidelines](CONTRIBUTING.md) for details.

### Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Ensure tests pass: `just test`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Style

- Use [Black](https://github.com/psf/black) for code formatting
- Use [isort](https://github.com/PyCQA/isort) for import sorting
- Follow [PEP 8](https://pep8.org/) style guidelines
- Add type hints where appropriate

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Kopf](https://kopf.readthedocs.io/) - Kubernetes Operators Framework
- [RStudio](https://www.rstudio.com/) - The R IDE we're orchestrating
- [Kubernetes](https://kubernetes.io/) - Container orchestration platform

## 📞 Support

- Use the main monorepo issue tracker and docs for follow-up work.
