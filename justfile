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
    cd frontend && npm run dev

# Run the backend server
dev-server:
    cd server && uv run main.py

# Run the docs development server
dev-docs:
    cd docs && npm run dev

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
