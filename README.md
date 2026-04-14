# Orchestra Platform

Orchestra is a cloud-native platform for managing self-service RStudio workshops on Kubernetes.

## Project Structure

This monorepo contains all the components of the Orchestra platform:

-   **`docs/`**: Documentation website powered by Starlight/Astro.
-   **`frontend/`**: React (TypeScript) dashboard for managing workshops.
-   **`operator/`**: Kubernetes operator (Python/Kopf) that manages workshop lifecycles.
-   **`server/`**: FastAPI backend that provides the API for the frontend and interacts with Kubernetes.

## Getting Started

Refer to the `README.md` in each subdirectory for component-specific instructions.
