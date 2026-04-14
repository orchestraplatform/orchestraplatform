# Justfile for Orchestra Platform monorepo

# Default Kubernetes context for local development
dev_k8s_context := "docker-desktop"

# List all recipes
default:
    @just --list

# --- One-time setup ---

# Set up all project components (install dependencies)
setup: setup-docs setup-frontend setup-operator setup-server

setup-docs:
    cd docs && npm install

setup-frontend:
    cd frontend && npm install

setup-operator:
    cd operator && uv sync

setup-server:
    cd server && uv sync

# --- Local dev cluster setup (run once per machine) ---

# Prepare the local Kubernetes cluster for Orchestra development.
# Switches to docker-desktop context, installs Traefik, applies CRDs,
# and copies .env example files if no local copies exist yet.
dev-setup:
    @echo "==> Switching to {{ dev_k8s_context }} context"
    kubectl config use-context {{ dev_k8s_context }}
    @echo "==> Verifying cluster is reachable"
    kubectl cluster-info
    @echo "==> Installing Traefik (skipped if already present)"
    helm repo add traefik https://traefik.github.io/charts 2>/dev/null || true
    helm repo update
    helm upgrade --install traefik traefik/traefik \
        --namespace traefik --create-namespace \
        --set ports.web.nodePort=30080 \
        --set service.type=NodePort \
        --wait
    @echo "==> Applying Orchestra CRDs"
    kubectl apply -f operator/config/crd/
    @echo "==> Copying example env files (skipped if already present)"
    cp -n server/.env.example server/.env 2>/dev/null && echo "  Created server/.env" || echo "  server/.env already exists"
    cp -n frontend/.env.local.example frontend/.env.local 2>/dev/null && echo "  Created frontend/.env.local" || echo "  frontend/.env.local already exists"
    @echo ""
    @echo "✓ Dev cluster ready."
    @echo "  Workshops will be reachable at http://<name>.127.0.0.1.nip.io:30080"
    @echo "  Run 'just dev' to start the local development stack."

# --- Development ---

# Start the full local dev stack (server + frontend + operator)
# Run 'just dev-setup' first if this is a new machine.
dev:
    @just -j 3 dev-server dev-frontend dev-operator

# Run the frontend development server
dev-frontend:
    cd frontend && just dev

# Run the backend server
# Uses port 8080 — ports 8000 and 8001 are occupied by Docker Desktop on Mac.
dev-server:
    cd server && ORCHESTRA_ENVIRONMENT=local \
    ORCHESTRA_KUBE_CONTEXT={{ dev_k8s_context }} \
    ORCHESTRA_REQUIRE_AUTHENTICATION=false \
    ORCHESTRA_PORT=8080 \
    just dev port=8080

# Run the operator locally
dev-operator:
    ORCHESTRA_ENVIRONMENT=local \
    KUBE_CONTEXT={{ dev_k8s_context }} \
    cd operator && just run-local

# Run the docs development server
dev-docs:
    cd docs && just dev

# Run only server + frontend (no operator — workshops created but not reconciled)
dev-stack:
    @just -j 2 dev-frontend dev-server

# --- API Coordination ---

# Generate OpenAPI schema from server
generate-schema:
    cd server && just generate-schema

# Update frontend types from the server's OpenAPI schema
sync-types: generate-schema
    cd frontend && just generate-types-file ../server/openapi.json

# --- Docker Compose ---

# Start all services with Docker Compose (production-like, full image builds)
docker-up:
    docker compose up --build -d

# Start all services with Docker Compose in dev mode (hot-reload)
docker-dev-up:
    docker compose -f docker-compose.dev.yml up --build

# Stop all services (production compose)
docker-down:
    docker compose down

# Stop all services (dev compose)
docker-dev-down:
    docker compose -f docker-compose.dev.yml down

# View logs from all services
docker-logs:
    docker compose logs -f

# View logs from dev services
docker-dev-logs:
    docker compose -f docker-compose.dev.yml logs -f

# --- Quality ---

# Run all linting and formatting checks
quality: quality-frontend quality-server quality-operator quality-docs

quality-frontend:
    cd frontend && just quality

quality-server:
    cd server && just quality

quality-operator:
    cd operator && just quality

quality-docs:
    cd docs && just quality

# --- Testing ---

# Run all tests
test: test-frontend test-server

test-frontend:
    cd frontend && npm test

test-server:
    cd server && uv run pytest

# --- Build ---

# Build all components
build: build-frontend build-docs

build-frontend:
    cd frontend && npm run build

build-docs:
    cd docs && npm run build
