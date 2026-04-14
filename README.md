# Orchestra Platform

Orchestra is a cloud-native platform for managing self-service RStudio workshops on Kubernetes.

## Project Structure

This monorepo contains all the components of the Orchestra platform:

-   **`docs/`**: Documentation website powered by Starlight/Astro.
-   **`frontend/`**: React (TypeScript) dashboard for managing workshops.
-   **`operator/`**: Kubernetes operator (Python/Kopf) that manages workshop lifecycles.
-   **`server/`**: FastAPI backend that provides the API for the frontend and interacts with Kubernetes.

## Local Development

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Kubernetes enabled
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm](https://helm.sh/docs/intro/install/) (`brew install helm`)
- [just](https://github.com/casey/just) (`brew install just`)
- [uv](https://docs.astral.sh/uv/) (`brew install uv`)
- Node.js 20+ (`brew install node`)

### First-time cluster setup

Run once per machine to install Traefik and the Orchestra CRDs into your local cluster:

```bash
just dev-setup
```

This will:
1. Switch `kubectl` context to `docker-desktop`
2. Install Traefik as the ingress controller (exposed on port 30080)
3. Apply the `Workshop` CRD

### Installing dependencies

```bash
just setup
```

### Starting the dev stack

```bash
just dev
```

This starts the server, frontend, and operator in parallel as local processes (with hot-reload):

| Component | URL |
|-----------|-----|
| Frontend  | http://localhost:3000 |
| API       | http://localhost:8080 |
| API docs  | http://localhost:8080/docs |
| Docs site | run `just dev-docs` separately |

> **Note:** Ports 8000 and 8001 are occupied by Docker Desktop on Mac; 8080 is used instead.

Workshops created via the UI will be reachable at `http://<name>.orchestra.localhost:30080`. The `dev-setup` step configures dnsmasq to resolve `*.orchestra.localhost` → `127.0.0.1` automatically.

### Development without the operator

If you're working on the API or frontend only and don't need workshops to actually reconcile:

```bash
just dev-stack   # server + frontend only
```

### Config files

`just dev-setup` copies these automatically on first run:

```bash
server/.env.example    → server/.env           # API settings (gitignored)
frontend/.env.local.example → frontend/.env.local  # VITE_API_URL etc (gitignored)
```

Edit them as needed after copying.

## Docker Compose

Two compose files are provided:

| File | Use case |
|------|----------|
| `docker-compose.yml` | Full image builds, closer to production |
| `docker-compose.dev.yml` | Volume-mounted source with hot-reload |

```bash
just docker-dev-up    # dev mode (hot-reload)
just docker-up        # production-like
```

Access the components at:
-   **Frontend**: http://localhost:3002
-   **API Server**: http://localhost:8001
-   **Docs**: http://localhost:3003

## Getting Started

Refer to the `README.md` in each subdirectory for component-specific instructions.
