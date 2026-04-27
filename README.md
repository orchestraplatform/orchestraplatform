# Welcome to Orchestra Platform

Orchestra Platform is a cloud-native, Kubernetes-based learning environment designed specifically for bioinformatics and data science education. It provides instructors and students with on-demand, isolated workshop environments that can be quickly provisioned and automatically managed.

Orchestra Platform enables educational institutions, research organizations, and training companies to deliver hands-on bioinformatics and data science workshops without the complexity of manual infrastructure management. Each workshop runs in its own isolated environment with dedicated resources, ensuring a consistent and reliable learning experience.

## Key Features

### 🚀 **Instant Workshop Creation**
- Create fully configured workshop environments in minutes
- Support for popular bioinformatics tools (RStudio, Jupyter, etc.)
- Automated resource provisioning and cleanup

### 🔒 **Secure & Isolated**
- Each workshop runs in its own Kubernetes namespace
- Network isolation between workshop instances
- Secure access via unique subdomains and HTTPS

### ⏰ **Time-Limited Sessions**
- Configurable workshop duration (hours to days)
- Automatic cleanup when sessions expire
- Resource management and cost control

### 🎯 **User-Friendly Interface**
- Simple web dashboard for workshop management
- Real-time status monitoring
- Easy sharing of workshop URLs

### 📚 **Flexible Content**
- Support for custom Docker images
- Persistent storage for workshop data
- Pre-configured environments for common workflows

## Use Cases

### Educational Institutions
- Bioinformatics courses and workshops
- Computational biology training
- Data science bootcamps
- Research method courses

### Research Organizations
- Training workshops for new tools
- Collaborative analysis sessions
- Reproducible research environments
- Method development and testing

### Industry Training
- Professional development workshops
- Customer training sessions
- Product demonstrations
- Certification programs

## Architecture Overview

Orchestra Platform consists of four main components:

1. **Orchestra Operator** - Kubernetes operator managing workshop lifecycle
2. **Orchestra API** - REST API for workshop operations
3. **Orchestra Frontend** - Web application for users
4. **Orchestra Docs** - Comprehensive documentation (this site)

Each workshop gets its own unique subdomain and runs in complete isolation from other workshops.

## Getting Started

Ready to start using Orchestra Platform? Check out our [Installation Guide](/getting-started/installation/) to set up your own instance, or jump to the [User Guide](/user-guide/creating-workshops/) to learn how to create your first workshop.

## Community and Support

Orchestra Platform is open source and welcomes contributions from the community. Visit our [GitHub repository](https://github.com/orchestraplatform/orchestraplatform) to:

- Report issues or request features
- Contribute code improvements
- Join discussions about the platform
- Access the latest development updates

For questions and support, please check our documentation or open an issue on GitHub.

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

This installs frontend/docs packages and syncs Python projects with their dev
dependency groups, so commands like `just test` work without extra setup.

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

Workshops created via the UI will be reachable at `http://<name>.127.0.0.1.nip.io:30080`. No DNS configuration required — `*.127.0.0.1.nip.io` resolves to `127.0.0.1` automatically via the public nip.io service.

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

## Getting Started

Refer to the `README.md` in each subdirectory for component-specific instructions.
