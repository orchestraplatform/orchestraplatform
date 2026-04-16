# Orchestra API

FastAPI backend for the Orchestra monorepo.

The API has two main responsibilities:

- manage the **template catalog** stored in Postgres
- launch and track **workshop instances** backed by Kubernetes `Workshop` CRDs

## Quick Start

1. Install dependencies:
   ```bash
   cd server
   just setup
   ```

2. Run the API directly from the `server` directory:
   ```bash
   cd server
   just dev
   ```

3. View API docs:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

4. Run tests:
   ```bash
   cd server
   just test
   ```

`just setup` installs the `dev` dependency group with `uv`, so the test recipes
work without any extra manual setup.

## Local Development Notes

- Running the API through the monorepo root `just dev` command uses port `8080`.
- Running `cd server && just dev` uses port `8000`.
- The frontend `VITE_API_URL` should match whichever mode you are using.

## API Shape

### Health

- `GET /health/`
- `GET /health/ready`
- `GET /health/live`

### Authentication

- `GET /auth/me`
- `GET /auth/auth-config`

### Templates

- `GET /templates/` - list workshop templates
- `POST /templates/` - create template (admin)
- `GET /templates/{template_id}` - get template
- `PUT /templates/{template_id}` - update template (admin)
- `DELETE /templates/{template_id}` - archive template (admin)
- `GET /templates/{template_id}/stats` - aggregate template stats (admin)
- `POST /templates/{template_id}/launch` - launch an instance from a template

### Instances

- `GET /instances/` - list running instances for the current user
- `GET /instances/{k8s_name}` - get instance details
- `GET /instances/{k8s_name}/status` - get lightweight status
- `GET /instances/{k8s_name}/utilization` - get time-in-phase utilization
- `DELETE /instances/{k8s_name}` - terminate an instance

## Example Usage

### List templates

```bash
curl -H "X-Auth-Request-Email: alice@example.com" \
  "http://localhost:8000/templates/"
```

### Launch an instance from a template

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Auth-Request-Email: alice@example.com" \
  -d '{"duration":"2h","namespace":"default"}' \
  "http://localhost:8000/templates/<template-uuid>/launch"
```

### List instances

```bash
curl -H "X-Auth-Request-Email: alice@example.com" \
  "http://localhost:8000/instances/"
```

## Architecture

```text
Frontend → API → Postgres
              ↓
           Workshop CRD → Operator → Deployment / Service / Ingress / PVC
```

The API is intentionally split between:

- **templates** in Postgres for curated reusable configuration
- **instances** in Postgres plus Kubernetes for live runtime state and history
