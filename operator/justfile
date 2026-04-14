# Kubernetes development tasks

# Default Kubernetes version and cluster name
k8s_version := "v1.28.0"
cluster_name := "orchestra-test"
docker_name := "orchestra-operator"
docker_tag := "latest"
docker_user := "seandavi"
docker_image := docker_user + "/" + docker_name + ":" + docker_tag

# List available commands
default:
    @just --list

# Create kind cluster for development
cluster-up version=k8s_version name=cluster_name:
    #!/usr/bin/env bash
    echo "Creating kind cluster '{{name}}' with Kubernetes {{version}}"
    kind create cluster --name {{name}} --image kindest/node:{{version}}
    kubectl cluster-info --context kind-{{name}}

# Delete kind cluster
cluster-down name=cluster_name:
    kind delete cluster --name {{name}}

# Reset cluster (delete and recreate)
cluster-reset version=k8s_version name=cluster_name: (cluster-down name) (cluster-up version name)

# Load operator image into cluster
load-image name=cluster_name image=docker_image:
    kind load docker-image {{image}} --name {{name}}

push-image image=docker_image:
    docker push {{image}}

# Install CRDs and deploy operator
deploy: build-image load-image
    kubectl apply -f config/crd/
    kubectl apply -f config/deploy/

# Build operator Docker image
build-image image=docker_image:
    docker build -t {{image}} .

# Install Python dependencies
install-deps:
    uv sync

# Run operator locally (for development)
run-local:
    cd src && uv run python main.py

# Run operator locally with debug logging
run-debug:
    cd src && KOPF_VERBOSE=1 uv run python main.py

# === Code Quality ===

# Format code with ruff
format:
    uv run ruff format .

# Lint code with ruff
lint:
    uv run ruff check .

# Fix linting issues
lint-fix:
    uv run ruff check . --fix

# Type checking with mypy
type-check:
    uv run mypy src/

# Run all code quality checks
quality: format lint type-check

# === Testing ===

# Apply CRDs to cluster
apply-crd:
    kubectl apply -f config/crd/

# Run tests against cluster
test:
    uv run pytest tests/ -v

# Run tests with coverage
test-coverage:
    uv run pytest tests/ --cov=src --cov-report=html --cov-report=term

# === Development Workflows ===

# Setup development environment
dev-setup: cluster-up apply-crd deploy
    echo "Development environment ready!"
    echo "To start the API, go to orchestra-api folder and run 'just dev'"
    echo "Run 'just run-local' to start operator locally"

# Full development cycle with quality checks
dev-cycle: quality test
    just build-image
    just load-image
    kubectl rollout restart deployment/orchestra-operator -n orchestra-system || echo "Operator not deployed yet"

# === Monitoring and Debugging ===

# Watch workshop resources
watch-workshops:
    kubectl get workshops -w

# Get workshop details
describe-workshop name:
    kubectl describe workshop {{name}}

# Check operator logs
operator-logs:
    kubectl logs -n orchestra-system -l app=orchestra-operator --tail=50 -f

# Check operator deployment status
operator-status:
    kubectl get deployment -n orchestra-system
    kubectl get pods -n orchestra-system

# === Workshop Management ===

# Create example workshop
create-example:
    kubectl apply -f examples/workshop-example.yaml

# Delete all workshops
delete-workshops:
    kubectl delete workshops --all

# List all workshop pods
workshop-pods:
    kubectl get pods -l workshop

# === Integration Testing ===

# Full integration test: operator + API + example workshop
integration-test api_path="../orchestra-api":
    @echo "🧪 Running full integration test"
    just dev-setup
    cd {{api_path}} && just run-bg
    sleep 5
    just create-example
    sleep 10
    kubectl get workshops
    kubectl get pods -l workshop
    @echo "✅ Integration test complete"

# CI/CD setup (lightweight)
ci-setup version=k8s_version:
    just cluster-up {{version}} ci-cluster
    just load-image ci-cluster

# === Multi-Repository Workflows ===

# Start all services for full-stack development
start-all-services api_path="../orchestra-api" frontend_path="../orchestra-frontend":
    @echo "🚀 Starting full Orchestra stack"
    just dev-setup
    cd {{api_path}} && just dev-for-frontend
    cd {{frontend_path}} && just update-types
    @echo "✅ Full stack ready:"
    @echo "  - Operator: Running in cluster"
    @echo "  - API: http://localhost:8000"
    @echo "  - Frontend: Run 'just dev' in orchestra-frontend"

# Clean up everything
cleanup: cluster-down
    docker system prune -f
    @echo "🧹 Cleanup complete"

# === Documentation ===

# Show architecture overview
docs:
    @echo "📚 Orchestra Architecture Overview"
    @echo ""
    @echo "Components:"
    @echo "  1. Orchestra Operator (Kubernetes Kopf-based)"
    @echo "     - Manages workshop lifecycle"
    @echo "     - Creates deployments, services, ingress"
    @echo "     - Handles cleanup and monitoring"
    @echo ""
    @echo "  2. Orchestra API (FastAPI)"
    @echo "     - REST API for workshop management"
    @echo "     - Integrates with Kubernetes operator"
    @echo "     - Provides status monitoring"
    @echo ""
    @echo "  3. Orchestra Frontend (React + TypeScript)"
    @echo "     - Web UI for workshop management"
    @echo "     - Type-safe API integration"
    @echo "     - Real-time status updates"
    @echo ""
    @echo "Development Commands:"
    @echo "  just start-all-services  - Start complete stack"
    @echo "  just integration-test    - Run full integration test"
    @echo "  just cleanup            - Clean up all resources"