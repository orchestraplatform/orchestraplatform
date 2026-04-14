# Orchestra Platform

Orchestra is a cloud-native platform for managing self-service RStudio workshops on Kubernetes.

## Project Structure

This monorepo contains all the components of the Orchestra platform:

-   **`docs/`**: Documentation website powered by Starlight/Astro.
-   **`frontend/`**: React (TypeScript) dashboard for managing workshops.
-   **`operator/`**: Kubernetes operator (Python/Kopf) that manages workshop lifecycles.
-   **`server/`**: FastAPI backend that provides the API for the frontend and interacts with Kubernetes.

## Development with Docker Compose

The easiest way to run the entire platform is using Docker Compose:

```bash
just docker-up
```

Access the components at:
-   **Frontend**: http://localhost:3002
-   **API Server**: http://localhost:8001
-   **Docs**: http://localhost:3003

## Getting Started

Refer to the `README.md` in each subdirectory for component-specific instructions.
