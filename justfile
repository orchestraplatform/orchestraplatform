# Justfile for Orchestra Platform monorepo

# Default Kubernetes context for local development
dev_k8s_context := "docker-desktop"
# Optional kube-context override for `just doctor` (empty = current context).
context := ""
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
    ORCHESTRA_TEMPLATES_DIR=../deploy/charts/orchestra/files/templates \
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

# Build and push all images to Artifact Registry (cross-compiled for linux/amd64).
# Tags each image with the current git SHA and :latest.
# Usage: just build-push
#        just build-push registry=us-central1-docker.pkg.dev/my-project/orchestra
build-push registry="us-central1-docker.pkg.dev/orchestraplatform-dev/orchestra":
    #!/usr/bin/env bash
    set -euo pipefail
    sha=$(git rev-parse --short HEAD)
    echo "==> Building images at commit ${sha}"
    docker buildx build --platform linux/amd64 \
        -t {{registry}}/orchestra-api:${sha} \
        -t {{registry}}/orchestra-api:latest \
        -f server/Dockerfile --push .
    docker buildx build --platform linux/amd64 \
        -t {{registry}}/orchestra-operator:${sha} \
        -t {{registry}}/orchestra-operator:latest \
        --push operator/
    docker buildx build --platform linux/amd64 \
        -t {{registry}}/orchestra-frontend:${sha} \
        -t {{registry}}/orchestra-frontend:latest \
        --push frontend/
    echo "==> Done. Image tag: ${sha}"

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

# Regenerate template.schema.json from the orchestra-template-tools schema
template-schema:
    cd server && uv run python generate_template_schema.py

# Fail if the committed template.schema.json has drifted from the model
# (single-source check for CI, called by .github ci.yml). Regenerates to a temp
# file and diffs; the committed file is left untouched. Exits non-zero on drift.
check-schema:
    #!/usr/bin/env bash
    set -euo pipefail
    committed="deploy/charts/orchestra/files/templates/template.schema.json"
    generated=$(mktemp)
    trap 'rm -f "$generated"' EXIT
    ( cd template-tools && uv run orchestra-validate-templates --print-schema ) > "$generated"
    if ! diff -u "$committed" "$generated"; then
        echo ""
        echo "✗ $committed is stale — regenerate with 'just template-schema' and commit."
        exit 1
    fi
    echo "✓ $committed is in sync with the orchestra-template-tools model."

# Validate the git-managed template files against the schema (same CLI the
# workshop-templates repo's CI runs — ADR-0007).
validate-templates:
    cd template-tools && uv run orchestra-validate-templates ../deploy/charts/orchestra/files/templates

# --- Local template rehearsal (ADR-0006) ---

# Throwaway Postgres for the rehearsal (port 5433, matching server/.env.example).
rehearse_db_url := "postgresql+asyncpg://orchestra:orchestra@localhost:5433/orchestra"

# Smoke-test the git-managed templates without a cluster, then print the
# interactive launch->ready->connect runbook. Proves the ADR-0006 wiring:
# schema validity, ConfigMap projection, and the per-template port contract
# (RStudio 8787 / JupyterLab 8888). Run this first; it changes nothing.
rehearse-check:
    #!/usr/bin/env bash
    set -euo pipefail
    schema="deploy/charts/orchestra/files/templates/template.schema.json"
    echo "==> [1/4] Template files validate against the schema"
    just validate-templates
    echo "==> [2/4] template.schema.json is in sync with the model"
    before=$(mktemp); cp "$schema" "$before"
    just template-schema >/dev/null
    if ! diff -q "$before" "$schema" >/dev/null; then
        rm -f "$before"
        echo "  ! $schema is stale — regenerated by 'just template-schema'; commit it"; exit 1
    fi
    rm -f "$before"
    echo "==> [3/4] Both templates project into the Helm ConfigMap"
    rendered=$(helm template orchestra deploy/charts/orchestra \
        --set api.database.url="{{ rehearse_db_url }}" \
        --show-only templates/templates-configmap.yaml)
    for slug in jupyter rstudio; do
        echo "$rendered" | grep -q "${slug}.yaml:" || { echo "  ! ${slug}.yaml missing from ConfigMap"; exit 1; }
    done
    echo "==> [4/4] Templates declare distinct app ports (per-template routing)"
    grep -q "^port: 8787" deploy/charts/orchestra/files/templates/rstudio.yaml || { echo "  ! rstudio port != 8787"; exit 1; }
    grep -q "^port: 8888" deploy/charts/orchestra/files/templates/jupyter.yaml || { echo "  ! jupyter port != 8888"; exit 1; }
    echo ""
    echo "✓ No-cluster checks passed."
    echo ""
    echo "── Interactive cluster rehearsal (RStudio + JupyterLab, lightweight images) ──"
    echo "  Uses the proven 'just dev' path. The Helm chart hardcodes the operator"
    echo "  ingress entrypoint to 'websecure', so a pure-Helm install does NOT route"
    echo "  on docker-desktop's web/NodePort 30080 — see the chart-gap issue."
    echo ""
    echo "  For a fast local run, point the two templates at light images (YAML-only,"
    echo "  uncommitted): rstudio -> rocker/rstudio:latest, jupyter -> quay.io/jupyter/"
    echo "  base-notebook:latest. Restore with 'git restore' before promoting to GKE."
    echo ""
    echo "  1. just dev-setup                 # docker-desktop, Traefik web@30080, CRDs"
    echo "  2. just rehearse-db-up            # throwaway Postgres on :5433"
    echo "  3. just migrate                   # (uses ORCHESTRA_DATABASE_URL from .env)"
    echo "  4. just dev                       # server + frontend + operator"
    echo "  5. GET /templates -> jupyter + rstudio appear (registry loaded from files)"
    echo "  6. Launch each; watch 'just watch-workshops' + the pod:"
    echo "       - link/READY must NOT activate until the app pod is truly Ready (GH-1)"
    echo "       - sidecar proxies localhost:8787 (RStudio) / :8888 (JupyterLab)"
    echo "       - JupyterLab comes up token-less via template args (no code edits)"
    echo "  7. Open http://<name>.127.0.0.1.nip.io:30080 for each; confirm it loads"
    echo "  8. just rehearse-db-down          # stop Postgres when done"

# Start a throwaway Postgres for the rehearsal (docker; data is not persisted).
rehearse-db-up:
    docker run -d --rm --name orchestra-rehearse-db \
        -e POSTGRES_USER=orchestra -e POSTGRES_PASSWORD=orchestra -e POSTGRES_DB=orchestra \
        -p 5433:5432 postgres:16-alpine
    @echo "✓ Postgres up on localhost:5433 (orchestra/orchestra). Ensure server/.env ORCHESTRA_DATABASE_URL points at it."

# Stop and remove the throwaway rehearsal Postgres.
rehearse-db-down:
    -docker stop orchestra-rehearse-db

# --- Deployment preflight ---

# Read-only preflight for an Orchestra deploy. Checks the environment
# interdependencies that make an install fail at runtime — tooling + cluster
# reachability, node egress for external image pulls, ephemeral-storage headroom
# vs the workshop templates, rendered request<=limit (Autopilot hides this,
# Standard rejects it), external deps (IngressClass / cert-manager / oauth2-proxy),
# required DB + oauth secrets, chart lint + template-schema sync, and migrate-hook
# prerequisites. Prints PASS/WARN/FAIL with a concrete fix per item and exits
# non-zero if anything FAILs. Changes NOTHING. Static checks (lint, schema,
# resource-limit render, ephemeral-vs-template) still run with no cluster.
#   just doctor                    # current kubectl context
#   context=my-ctx just doctor     # override the kube context
#   KUBECONFIG=/path just doctor   # or target a specific kubeconfig
doctor:
    @context="{{ context }}" bash scripts/doctor.sh

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

# Non-mutating lint check for the Python server (CI gate; unlike `quality`,
# does not rewrite files). Used by .github ci.yml.
lint-server:
    cd server && uv run ruff check . && uv run ruff format --check .

# Non-mutating lint check for the template-tools package (CI gate).
lint-template-tools:
    cd template-tools && uv run ruff check . && uv run ruff format --check .

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

# Server Python test suite only (CI gate).
test-server:
    cd server && uv run python -m pytest tests/ -v

# template-tools package test suite only (CI gate).
test-template-tools:
    cd template-tools && uv run python -m pytest tests/ -v

# operator test suite only (CI gate). Tests only — the operator carries
# pre-existing ruff/format debt that is out of scope for the template work.
test-operator:
    cd operator && uv run python -m pytest tests/ -v

# --- GCP / Production Deployment ---

# GCP deployment config lives in:
#   deploy/gcp-values.yaml        — environment overrides (committed)
#   deploy/gcp-values-secrets.yaml — OAuth credentials (gitignored, local only)
#
# To create the secrets file on a new machine, see docs/deployment/gcp.mdx.

gcp_context := "gke_orchestraplatform-dev_us-central1_orchestra-dev"
gcp_namespace := "orchestra-system"

# Deploy (or upgrade) Orchestra to GCP. Requires deploy/gcp-values-secrets.yaml.
# Pins images to the current git SHA so each Helm revision is traceable.
deploy-gcp:
    #!/usr/bin/env bash
    set -euo pipefail
    sha=$(git rev-parse --short HEAD)
    kubectl config use-context {{ gcp_context }}
    kubectl apply -f ./deploy/charts/orchestra-crds/templates/
    helm upgrade --install orchestra ./deploy/charts/orchestra \
        -n {{ gcp_namespace }} --create-namespace \
        -f deploy/charts/orchestra/values.yaml \
        -f deploy/gcp-values.yaml \
        -f deploy/gcp-values-secrets.yaml \
        --set operator.image.tag="${sha}" \
        --set api.image.tag="${sha}" \
        --set frontend.image.tag="${sha}" \
        --wait

# Build, push, and deploy to GCP in one atomic step — prevents SHA mismatch between images and Helm.
ship-gcp registry="us-central1-docker.pkg.dev/orchestraplatform-dev/orchestra":
    #!/usr/bin/env bash
    set -euo pipefail
    sha=$(git rev-parse --short HEAD)
    echo "==> Building images at commit ${sha}"
    docker buildx build --platform linux/amd64 \
        -t {{registry}}/orchestra-api:${sha} \
        -t {{registry}}/orchestra-api:latest \
        -f server/Dockerfile --push .
    docker buildx build --platform linux/amd64 \
        -t {{registry}}/orchestra-operator:${sha} \
        -t {{registry}}/orchestra-operator:latest \
        --push operator/
    docker buildx build --platform linux/amd64 \
        -t {{registry}}/orchestra-frontend:${sha} \
        -t {{registry}}/orchestra-frontend:latest \
        --push frontend/
    echo "==> Deploying sha=${sha}"
    kubectl config use-context {{ gcp_context }}
    kubectl apply -f ./deploy/charts/orchestra-crds/templates/
    helm upgrade --install orchestra ./deploy/charts/orchestra \
        -n {{ gcp_namespace }} --create-namespace \
        -f deploy/charts/orchestra/values.yaml \
        -f deploy/gcp-values.yaml \
        -f deploy/gcp-values-secrets.yaml \
        --set operator.image.tag="${sha}" \
        --set api.image.tag="${sha}" \
        --set frontend.image.tag="${sha}" \
        --wait
    echo "==> Done. Deployed sha=${sha}"

# Dry-run the GCP deployment (renders templates, validates against cluster, no changes).
deploy-gcp-dry-run:
    #!/usr/bin/env bash
    set -euo pipefail
    sha=$(git rev-parse --short HEAD)
    kubectl config use-context {{ gcp_context }}
    helm upgrade --install orchestra ./deploy/charts/orchestra \
        -n {{ gcp_namespace }} --create-namespace \
        -f deploy/charts/orchestra/values.yaml \
        -f deploy/gcp-values.yaml \
        -f deploy/gcp-values-secrets.yaml \
        --set operator.image.tag="${sha}" \
        --set api.image.tag="${sha}" \
        --set frontend.image.tag="${sha}" \
        --dry-run --debug 2>&1 | head -200

# Show the values currently deployed to GCP (redacts nothing — contains secrets).
deploy-gcp-values:
    kubectl config use-context {{ gcp_context }}
    helm get values orchestra -n {{ gcp_namespace }}

# Show the Helm release history for GCP.
deploy-gcp-history:
    kubectl config use-context {{ gcp_context }}
    helm history orchestra -n {{ gcp_namespace }}

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

