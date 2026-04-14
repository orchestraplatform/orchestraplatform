# Frontend Development Justfile for Orchestra Workshop Management

# Default recipe
default:
    @just --list

# Development recipes
dev:
    npm run dev

build:
    npm run build

preview:
    npm run preview

# Code quality
lint:
    npm run lint

lint-fix:
    npm run lint:fix

format:
    npm run format

format-check:
    npm run format:check

type-check:
    npm run type-check

# Testing
test:
    npm run test

test-ui:
    npm run test:ui

test-watch:
    npm run test -- --watch

test-coverage:
    npm run test:coverage

# Quality checks
quality: lint type-check test
    @echo "✅ All quality checks passed"

# Dependencies
install:
    npm install

update-deps:
    npm update

clean:
    rm -rf node_modules dist .eslintcache

# Type generation recipes
generate-types api_url="http://localhost:8000":
    @echo "🔄 Generating TypeScript types from API at {{api_url}}"
    npx openapi-typescript-codegen --input {{api_url}}/openapi.json --output ./src/api/generated --client axios
    @echo "✅ Types generated successfully"

generate-types-file file="../orchestra-api/openapi.json":
    @echo "🔄 Generating TypeScript types from file {{file}}"
    npx openapi-typescript-codegen --input {{file}} --output ./src/api/generated --client axios
    @echo "✅ Types generated from file"

# API Integration
check-api api_url="http://localhost:8000":
    @echo "🔍 Checking API health at {{api_url}}"
    curl -s "{{api_url}}/" | jq . || echo "❌ API not accessible"

update-types: check-api generate-types
    @echo "🔄 Updated types from running API"

# Export OpenAPI schema from API for offline use
export-schema api_url="http://localhost:8000" output="../orchestra-api/openapi.json":
    @echo "💾 Exporting OpenAPI schema to {{output}}"
    curl -s "{{api_url}}/openapi.json" > {{output}}
    @echo "✅ Schema exported to {{output}}"

# Full development cycle
setup: install generate-types
    @echo "🚀 Frontend setup complete"

# Development workflow
dev-full: quality dev
    @echo "🎯 Starting development with quality checks"

# Production build with type safety
build-prod: generate-types quality build
    @echo "🏗️ Production build complete with fresh types"

# Docker recipes
docker-build tag="orchestra-frontend:latest":
    docker build -t {{tag}} .

docker-run tag="orchestra-frontend:latest" port="3000":
    docker run -p {{port}}:80 {{tag}}

# API testing helpers
test-api api_url="http://localhost:8000":
    @echo "🧪 Testing API endpoints"
    @echo "Health check:"
    curl -s "{{api_url}}/" | jq .
    @echo "Workshops list:"
    curl -s "{{api_url}}/workshops/" | jq .

create-test-workshop api_url="http://localhost:8000" name="frontend-test":
    @echo "🧪 Creating test workshop: {{name}}"
    curl -X POST "{{api_url}}/workshops/" \
        -H "Content-Type: application/json" \
        -d '{"name": "{{name}}", "duration": "1h", "image": "rocker/rstudio:latest", "resources": {"cpu": "500m", "memory": "1Gi"}, "storage": {"size": "5Gi"}}' \
        | jq .

# Cleanup
clean-generated:
    rm -rf src/api/generated
    @echo "🧹 Generated types cleaned"

reset: clean install setup
    @echo "🔄 Frontend reset complete"

# Documentation
docs:
    @echo "📚 Orchestra Frontend Documentation"
    @echo ""
    @echo "Development Commands:"
    @echo "  just dev              - Start development server"
    @echo "  just update-types     - Refresh API types"
    @echo "  just quality          - Run all quality checks"
    @echo ""
    @echo "Type Generation:"
    @echo "  just generate-types               - From running API"
    @echo "  just generate-types-file FILE     - From OpenAPI file"
    @echo "  just export-schema                - Export API schema"
    @echo ""
    @echo "Testing:"
    @echo "  just test-api         - Test API connectivity"
    @echo "  just create-test-workshop - Create test workshop"
