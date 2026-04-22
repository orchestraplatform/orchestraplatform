# Justfile for Orchestra Platform monorepo

# Default Kubernetes context for local development
dev_k8s_context := "docker-desktop"
api_port := "8080"
frontend_port := "3000"
docs_port := "3003"

# List all recipes
default:
    @just --list

# --- One-time setup ---

# Set up all project components for local contribution and testing.
setup:
    cd docs && npm install
    cd frontend && npm install
    cd operator && uv sync --group dev
    cd server && uv sync --group dev
    just sync-types

# --- Local dev cluster setup (run once per machine) ---

# Prepare the local Kubernetes cluster for Orchestra development.
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
    kubectl apply -f deploy/charts/orchestra-crds/templates/
    @echo "==> Copying example env files (skipped if already present)"
    cp -n server/.env.example server/.env 2>/dev/null && echo "  Created server/.env" || echo "  server/.env already exists"
    cp -n frontend/.env.local.example frontend/.env.local 2>/dev/null && echo "  Created frontend/.env.local" || echo "  frontend/.env.local already exists"
    @echo ""
    @echo "✓ Dev cluster ready."
    @echo "  Workshops will be reachable at http://<name>.127.0.0.1.nip.io:30080"
    @echo "  (No dnsmasq required — nip.io resolves *.127.0.0.1.nip.io to 127.0.0.1)"

# --- Development Stack ---

# Start the full local dev stack (server + frontend + operator)

[parallel]
dev: dev-server dev-frontend dev-operator


# Run the backend server
dev-server:
    cd server && ORCHESTRA_ENVIRONMENT=local \
    ORCHESTRA_KUBE_CONTEXT={{ dev_k8s_context }} \
    ORCHESTRA_REQUIRE_AUTHENTICATION=false \
    ORCHESTRA_DEV_IDENTITY=admin@example.com \
    ORCHESTRA_ADMIN_EMAILS='["admin@example.com"]' \
    uv run python -m uvicorn main:app --reload --host 0.0.0.0 --port {{ api_port }}

# Run the frontend development server
dev-frontend:
    cd frontend && npm run dev -- --port {{ frontend_port }}

# Run the operator locally
dev-operator:
    cd operator/src && \
    ORCHESTRA_BASE_DOMAIN=127.0.0.1.nip.io \
    ORCHESTRA_INGRESS_ENTRY_POINTS='["web"]' \
    ORCHESTRA_INGRESS_PORT=30080 \
    KUBE_CONTEXT={{ dev_k8s_context }} \
    uv run python main.py

# Run the docs development server
dev-docs:
    cd docs && npm run dev -- --port {{ docs_port }}

# Stop all running local development processes
stop:
    -pkill -f uvicorn
    -pkill -f "python main.py"
    -pkill -f vite

# Restart the full local dev stack
restart: stop dev


# --- Sidecar ---

# Build and push all images to Artifact Registry (cross-compiled for linux/amd64)
# Usage: just build-push
#        just build-push registry=us-central1-docker.pkg.dev/my-project/orchestra
build-push registry="us-central1-docker.pkg.dev/orchestraplatform-dev/orchestra":
    docker buildx build --platform linux/amd64 -t {{registry}}/orchestra-api:latest --push server/
    docker buildx build --platform linux/amd64 -t {{registry}}/orchestra-operator:latest --push operator/
    docker buildx build --platform linux/amd64 -t {{registry}}/orchestra-frontend:latest --push frontend/

# Build the sidecar Docker image
sidecar-build tag="seandavi/orchestra-sidecar:latest":
    cd sidecar && docker build -t {{ tag }} .

# Build and push the sidecar image to Artifact Registry
sidecar-push registry="us-central1-docker.pkg.dev/orchestraplatform-dev/orchestra":
    docker buildx build --platform linux/amd64 -t {{registry}}/orchestra-sidecar:latest --push sidecar/

# Run sidecar tests
sidecar-test:
    cd sidecar && go test ./... -v

# --- Database & Migrations ---

# Apply all pending migrations
migrate:
    cd server && uv run python -m alembic upgrade head

# Show migration history
migrate-history:
    cd server && uv run python -m alembic history

# Generate a new migration (usage: just migration "add foo table")
migration msg:
    cd server && uv run python -m alembic revision --autogenerate -m "{{ msg }}"

# --- Types & Schema ---

# Generate OpenAPI schema and update frontend types
sync-types:
    cd server && uv run python generate_schema.py openapi.json
    cd frontend && npx openapi-typescript-codegen --input ../server/openapi.json --output ./src/api/generated --client axios

# --- Quality & Testing ---

# Run all linting and formatting checks
quality:
    @echo "--- Quality: Server ---"
    cd server && uv run ruff format . && uv run ruff check . --fix
    @echo "--- Quality: Operator ---"
    cd operator && uv run ruff format . && uv run ruff check . --fix
    @echo "--- Quality: Frontend ---"
    cd frontend && npm run lint && npm run format
    @echo "--- Quality: Sidecar ---"
    cd sidecar && go fmt ./...
    @echo "--- Quality: Docs ---"
    cd docs && npm run lint

# Run all tests
test:
    @echo "--- Test: Server ---"
    cd server && uv run python -m pytest tests/ -v
    @echo "--- Test: Operator ---"
    cd operator && uv run python -m pytest tests/ -v
    @echo "--- Test: Sidecar ---"
    cd sidecar && go test ./... -v
    @echo "--- Test: Frontend ---"
    cd frontend && npm run test -- --run --passWithNoTests

# --- Kubernetes Tools ---

# Watch workshops in the cluster
watch-workshops:
    kubectl get workshops -A -w

# List all workshop pods
workshop-pods:
    kubectl get pods -A -l workshop

# Delete all workshops (use with caution!)
clear-workshops:
    kubectl delete workshops --all -A

