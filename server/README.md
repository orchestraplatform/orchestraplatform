# Orchestra API

REST API for managing RStudio workshops via the Orchestra Operator.

## Quick Start

1. **Install dependencies**:
   ```bash
   cd server
   just setup
   ```

2. **Run the API**:
   ```bash
   cd server
   just dev
   ```

3. **View API documentation**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

4. **Run the server test suite**:
   ```bash
   cd server
   just test
   ```

`just setup` installs the `dev` dependency group with `uv`, so `pytest` is
available via `uv run` in all of the test recipes.

## API Endpoints

### Health Checks
- `GET /health/` - Basic health check
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

### Workshops
- `POST /api/v1/workshops/` - Create a new workshop
- `GET /api/v1/workshops/` - List all workshops
- `GET /api/v1/workshops/{name}` - Get workshop details
- `DELETE /api/v1/workshops/{name}` - Delete a workshop
- `GET /api/v1/workshops/{name}/status` - Get workshop status

## Example Usage

### Create a Workshop
```bash
curl -X POST "http://localhost:8000/api/v1/workshops/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-workshop",
    "duration": "4h",
    "image": "rocker/rstudio:latest",
    "resources": {
      "cpu": "1",
      "memory": "2Gi",
      "cpuRequest": "500m",
      "memoryRequest": "1Gi"
    },
    "storage": {
      "size": "10Gi"
    },
    "ingress": {
      "host": "workshop.example.com"
    }
  }'
```

### List Workshops
```bash
curl "http://localhost:8000/api/v1/workshops/"
```

### Get Workshop Status
```bash
curl "http://localhost:8000/api/v1/workshops/my-workshop/status"
```

## Development

The API interacts with the Orchestra Operator through Kubernetes Custom Resource Definitions (CRDs). It creates, monitors, and manages Workshop resources that the operator then reconciles into actual RStudio instances.

## Architecture

```
Client → API → Workshop CRD → Orchestra Operator → RStudio Pod
```

The API layer provides:
- User-friendly REST interface
- Input validation
- Error handling
- Status monitoring
- Multi-workshop management
