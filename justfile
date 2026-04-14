# Justfile for Orchestra Platform monorepo

# List all recipes
default:
    @just --list

# --- Setup ---

# Set up all project components
setup: setup-docs setup-frontend setup-operator setup-server

setup-docs:
    cd docs && npm install

setup-frontend:
    cd frontend && npm install

setup-operator:
    cd operator && uv sync

setup-server:
    cd server && uv sync

# --- Development ---

# Run the frontend development server
dev-frontend:
    cd frontend && just dev

# Run the backend server
dev-server:
    cd server && just dev

# Run the operator locally
dev-operator:
    cd operator && just run-local

# Run the docs development server
dev-docs:
    cd docs && just dev

# Run both frontend and backend for full-stack development
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

# Start all services with Docker Compose
docker-up:
    docker compose up --build -d

# Stop all services
docker-down:
    docker compose down

# View logs from all services
docker-logs:
    docker compose logs -f

# --- Quality ---

# Run all linting and formatting checks
quality: quality-frontend quality-server quality-operator

quality-frontend:
    cd frontend && just quality

quality-server:
    cd server && just quality

quality-operator:
    cd operator && just quality

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
