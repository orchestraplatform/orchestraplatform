# Orchestra API Development Tasks

# Default API configuration
api_host := "0.0.0.0"
api_port := "8000"
api_url := "http://localhost:" + api_port

# List available commands
default:
    @just --list

# === Development Setup ===

# Install dependencies
install-deps:
    uv sync

# Install development dependencies
install-dev:
    uv sync --group dev

# Sync lock file
sync:
    uv sync --frozen

# === Running the API ===

# Run API server locally
run host=api_host port=api_port:
    uvicorn main:app --reload --host {{host}} --port {{port}}

# Run API server in background
run-bg host=api_host port=api_port:
    uvicorn main:app --host {{host}} --port {{port}} &

# Run API in development mode with hot reload
dev:
    uvicorn main:app --reload --host {{api_host}} --port {{api_port}}

# Run API in production mode
prod:
    uvicorn main:app --host {{api_host}} --port {{api_port}} --workers 4

# === Testing ===

# Run all tests
test:
    pytest tests/ -v

# Run tests with coverage
test-cov:
    pytest tests/ --cov=api --cov-report=html --cov-report=term

# Run specific test file
test-file file:
    pytest {{file}} -v

# Run tests in watch mode
test-watch:
    pytest-watch

# === Code Quality ===

# Format code with black
format:
    black .

# Sort imports with isort
sort-imports:
    isort .

# Lint code with ruff
lint:
    ruff check .

# Fix linting issues
lint-fix:
    ruff check . --fix

# Run all code quality checks
quality: format sort-imports lint

# === API Testing ===

# Check API health
health url=api_url:
    curl "{{url}}/health/" | jq

# Check API readiness
ready url=api_url:
    curl "{{url}}/health/ready" | jq

# List all workshops
list-workshops url=api_url:
    curl "{{url}}/api/v1/workshops/" | jq

# Get specific workshop
get-workshop name url=api_url:
    curl "{{url}}/api/v1/workshops/{{name}}" | jq

# Get workshop status
workshop-status name url=api_url:
    curl "{{url}}/api/v1/workshops/{{name}}/status" | jq

# Create workshop from example file
create-example url=api_url:
    curl -X POST "{{url}}/api/v1/workshops/" \
      -H "Content-Type: application/json" \
      -d @examples/workshop-api-example.json | jq

# Create a simple test workshop
create-test-workshop name="test-workshop" url=api_url:
    curl -X POST "{{url}}/api/v1/workshops/" \
      -H "Content-Type: application/json" \
      -d '{"name":"{{name}}","duration":"2h","image":"rocker/rstudio:latest","resources":{"cpu":"1","memory":"2Gi"}}' | jq

# Delete a workshop
delete-workshop name url=api_url:
    curl -X DELETE "{{url}}/api/v1/workshops/{{name}}"

# === Documentation ===

# Open API documentation in browser
docs url=api_url:
    open "{{url}}/docs"

# Open ReDoc documentation
redoc url=api_url:
    open "{{url}}/redoc"

# Generate OpenAPI spec file from running API
openapi-spec url=api_url:
    curl "{{url}}/openapi.json" | jq > openapi.json

# Generate OpenAPI schema directly from FastAPI app (no server required)
generate-schema output="openapi.json":
    @echo "📋 Generating OpenAPI schema to {{output}}"
    uv run python generate_schema.py {{output}}
    @echo "✅ Schema generated at {{output}}"

# Serve OpenAPI schema file on localhost:8001 for frontend development
serve-schema port="8001":
    @echo "🌐 Serving OpenAPI schema at http://localhost:{{port}}/openapi.json"
    uv run python serve_schema.py {{port}}

# Update frontend types from generated schema
update-frontend-types frontend_path="../orchestra-frontend":
    @echo "🔄 Updating frontend types from API schema"
    just generate-schema
    cd {{frontend_path}} && just generate-types-file ../orchestra-api/openapi.json
    @echo "✅ Frontend types updated from static schema"

# Update frontend types from running API
update-frontend-types-live frontend_path="../orchestra-frontend" url=api_url:
    @echo "🔄 Updating frontend types from running API at {{url}}"
    cd {{frontend_path}} && just generate-types {{url}}
    @echo "✅ Frontend types updated from running API"

# === Kubernetes Integration ===

# Port-forward to operator for local development
port-forward-operator:
    kubectl port-forward -n orchestra-system svc/orchestra-operator-metrics 8080:8080

# Check operator logs
operator-logs:
    kubectl logs -n orchestra-system -l app=orchestra-operator --tail=50

# Watch workshops in Kubernetes
watch-workshops:
    kubectl get workshops -w

# List workshop pods
workshop-pods:
    kubectl get pods -l workshop

# === Environment Management ===

# Clean virtual environment
clean-venv:
    rm -rf .venv
    uv sync

# Update dependencies
update-deps:
    uv sync --upgrade

# Show dependency tree
deps-tree:
    uv tree

# === Docker ===

# Build API Docker image
build-image tag="orchestra-api:latest":
    docker build -t {{tag}} .

# Run API in Docker container
run-docker tag="orchestra-api:latest" port=api_port:
    docker run -p {{port}}:8000 {{tag}}

# === Load Testing ===

# Run basic load test (requires apache bench)
load-test url=api_url requests="100" concurrency="10":
    ab -n {{requests}} -c {{concurrency}} "{{url}}/health/"

# === Database/State ===

# Clear all workshops (use with caution!)
clear-workshops:
    kubectl delete workshops --all

# === Development Workflow ===

# Complete development setup with schema generation
setup: install-deps generate-schema
    echo "Orchestra API development environment ready!"
    echo "Run 'just dev' to start the API server"
    echo "Run 'just docs' to open API documentation"
    echo "Run 'just update-frontend-types' to sync types with frontend"

# Full test suite and quality checks
ci: quality test
    echo "All checks passed!"

# Quick development cycle: format, lint, test
check: format lint test

# Reset everything for clean start
reset: clean-venv clear-workshops setup

# === Monitoring ===

# Show API metrics (if available)
metrics url=api_url:
    curl "{{url}}/metrics" || echo "Metrics endpoint not available"

# Tail API logs (assumes you're running with systemd or similar)
logs:
    journalctl -f -u orchestra-api || echo "Not running as a service"

# === Frontend Integration ===

# Start API in background for frontend development
dev-for-frontend:
    @echo "🚀 Starting API in background for frontend development"
    just run-bg
    sleep 2
    just health
    @echo "✅ API ready for frontend at {{api_url}}"

# Full development setup for frontend work
frontend-dev-setup frontend_path="../orchestra-frontend":
    @echo "🔧 Setting up full-stack development environment"
    just dev-for-frontend
    just update-frontend-types-live {{frontend_path}}
    @echo "✅ Both API and frontend types are ready"

# Development cycle: update API, regenerate schema, update frontend types
dev-cycle frontend_path="../orchestra-frontend":
    @echo "🔄 Running development cycle"
    just quality
    just generate-schema
    cd {{frontend_path}} && just generate-types-file ../orchestra-api/openapi.json
    @echo "✅ Development cycle complete - API validated, schema updated, frontend types synced"
