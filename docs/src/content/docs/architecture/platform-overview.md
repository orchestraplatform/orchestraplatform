---
title: Orchestra Platform Architecture
description: Complete architectural overview of the Orchestra Platform domain structure and components
---

## Domain Structure

The Orchestra Platform uses a hierarchical domain structure built around **orchestraplatform.org** to provide a comprehensive bioinformatics and data science learning environment.

See [Domain Structure](../domain-structure/) for details on subdomains and workshop URLs.

### Core Platform Subdomains

| Subdomain | Purpose | Repository |
|-----------|---------|------------|
| `app.orchestraplatform.org` | Main application dashboard and frontend where users create and manage workshops | `orchestra-frontend` |
| `api.orchestraplatform.org` | REST API endpoints for the platform | `orchestra-api` |
| `docs.orchestraplatform.org` | Documentation site (user guides, API docs, tutorials) | `orchestra-docs` |

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

### 1. Orchestra Operator (`orchestra-operator`)

- **Purpose**: Kubernetes operator that manages workshop lifecycle
- **Technology**: Python, Kopf framework
- **Responsibilities**:
  - Creates/deletes workshop resources (Deployments, Services, Ingresses, PVCs)
  - Manages workshop expiration and cleanup
  - Handles Custom Resource Definitions (CRDs)

### 2. Orchestra API (`orchestra-api`)

- **Purpose**: REST API for workshop management
- **Technology**: Python, FastAPI
- **Responsibilities**:
  - Workshop CRUD operations
  - Integration with Kubernetes operator
  - Authentication and authorization
  - Workshop status monitoring

### 3. Orchestra Frontend (`orchestra-frontend`)

- **Purpose**: Web application for users to manage workshops
- **Technology**: React, TypeScript, Vite
- **Responsibilities**:
  - Workshop creation and management UI
  - User dashboard
  - Workshop status display
  - Integration with API backend

### 4. Orchestra Docs (`orchestra-docs`)

- **Purpose**: Platform documentation
- **Technology**: Astro, Starlight
- **Content**:
  - User guides and tutorials
  - API documentation
  - Architecture documentation
  - Developer guides

## Workshop Lifecycle

1. **Creation**: User requests workshop through frontend
2. **API Processing**: Frontend calls API to create workshop
3. **Operator Handling**: API creates Kubernetes Custom Resource
4. **Resource Deployment**: Operator creates all necessary Kubernetes resources
5. **URL Generation**: Unique subdomain is assigned and ingress configured
6. **Ready State**: Workshop becomes accessible via unique URL
7. **Expiration**: Workshop automatically expires after configured duration
8. **Cleanup**: Operator removes all associated resources

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
orchestra-operator/     # Kubernetes operator
orchestra-api/         # REST API backend  
orchestra-frontend/    # React frontend
orchestra-docs/        # Documentation site
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
