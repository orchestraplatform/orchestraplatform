---
title: Orchestra Platform Architecture
description: Complete architectural overview of the Orchestra Platform domain structure and components
---

## Domain Structure

The Orchestra Platform uses a hierarchical domain structure built around **orchestraplatform.org** to provide a comprehensive bioinformatics and data science learning environment.

See [Domain Structure](../domain-structure/) for details on subdomains and workshop URLs.

### Core Platform Subdomains

| Subdomain | Purpose | Monorepo Path |
|-----------|---------|---------------|
| `app.orchestraplatform.org` | Main application dashboard and frontend where users launch and manage workshop instances | `frontend/` |
| `api.orchestraplatform.org` | REST API endpoints for templates, instances, and auth helpers | `server/` |
| `docs.orchestraplatform.org` | Documentation site (user guides, API docs, tutorials) | `docs/` |

### Workshop Subdomains

Each workshop instance gets a unique hostname following the pattern:

```
{workshop-id}.orchestraplatform.org
```

**Examples:**
- `genomics-101-abc123.orchestraplatform.org`
- `rnaseq-analysis-2025jan-a1b2c3.orchestraplatform.org`
- `proteomics-intro-cohort5-x9y8z7.orchestraplatform.org`

### Additional Service Subdomains

| Subdomain | Purpose |
|-----------|---------|
| `status.orchestraplatform.org` | System status page and uptime monitoring |
| `admin.orchestraplatform.org` | Administrative interface for platform operators |
| `staging.orchestraplatform.org` | Staging environment for testing |

## Workshop ID Strategy

Workshop IDs follow the pattern: `{course-name}-{session-id}-{random}`

- **course-name**: Descriptive identifier for the workshop type
- **session-id**: Time-based or cohort identifier
- **random**: Short random string for uniqueness

This provides readable URLs while maintaining uniqueness and reasonable length.

## DNS Configuration

### Wildcard DNS Setup

A wildcard DNS record `*.orchestraplatform.org` points to the Kubernetes ingress controller, which handles routing individual workshop subdomains to the correct pods.

### SSL/TLS

All subdomains use HTTPS with automatic certificate management through cert-manager and Let's Encrypt.

## Platform Components

### 1. Orchestra Operator (`operator/`)

- **Purpose**: Kubernetes operator that manages workshop lifecycle
- **Technology**: Python, Kopf framework
- **Responsibilities**:
  - Creates/deletes workshop resources (Deployments, Services, Ingresses, PVCs)
  - Manages workshop expiration and cleanup
  - Handles Custom Resource Definitions (CRDs)

### 2. Orchestra API (`server/`)

- **Purpose**: REST API for workshop management
- **Technology**: Python, FastAPI
- **Responsibilities**:
  - Template CRUD and launch operations
  - Instance history and status sync
  - Authentication and authorization
  - Integration with Kubernetes operator

### 3. Orchestra Frontend (`frontend/`)

- **Purpose**: Web application for users to manage workshops
- **Technology**: React, TypeScript, Vite
- **Responsibilities**:
  - Template browsing and launch UI
  - User dashboard for running instances
  - Instance status display
  - Integration with API backend

### 4. Orchestra Docs (`docs/`)

- **Purpose**: Platform documentation
- **Technology**: Astro, Starlight
- **Content**:
  - User guides and tutorials
  - API documentation
  - Architecture documentation
  - Developer guides

## Workshop Lifecycle

1. **Template selection**: User browses a curated workshop template in the frontend
2. **Launch request**: Frontend calls the API to launch an instance from that template
3. **API persistence**: API records the instance in Postgres and creates a `Workshop` CRD
4. **Operator handling**: Operator reconciles the CRD into Kubernetes resources
5. **URL generation**: Unique subdomain is assigned and ingress configured
6. **Ready state**: Workshop becomes accessible via unique URL
7. **Expiration**: Operator deletes expired workshop CRDs
8. **Cleanup and sync**: API syncs terminated state and history back into Postgres

## Security Architecture

### Network Security
- All traffic encrypted with TLS 1.2+
- Workshop pods isolated in separate namespaces
- Network policies restrict inter-workshop communication

### Access Control
- OAuth/OIDC integration for user authentication
- Role-based access control (RBAC) for Kubernetes resources
- Workshop-level access controls

### Data Protection
- Persistent volumes for workshop data
- Configurable data retention policies
- Secure secret management

## Scalability Design

### Horizontal Scaling
- Multiple operator instances with leader election
- API server horizontal pod autoscaling
- Frontend served via CDN

### Resource Management
- Configurable resource limits per workshop
- Automatic resource cleanup on expiration
- Monitoring and alerting for resource usage

## Development Workflow

### Repository Structure
```
operator/    # Kubernetes operator
server/      # FastAPI backend
frontend/    # React frontend
docs/        # Documentation site
```

### Deployment Pipeline
1. Code changes trigger CI/CD pipeline
2. Automated testing and building
3. Container image creation and registry push
4. Kubernetes deployment updates
5. Health checks and monitoring

## Future Considerations

### Multi-Cloud Support
- Abstract cloud-specific resources
- Support for AWS EKS, Google GKE, Azure AKS

### Advanced Features
- Workshop templates and marketplace
- Collaborative workshop sessions
- Integration with learning management systems
- Advanced analytics and usage reporting
