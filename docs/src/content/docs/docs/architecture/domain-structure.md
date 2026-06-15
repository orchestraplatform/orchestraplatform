---
title: Domain Structure
description: Detailed breakdown of the Orchestra Platform domain architecture and subdomain organization
---

# Domain Structure

The Orchestra Platform is organized around a clear, hierarchical domain structure that separates different platform functions and provides unique access points for individual workshops.

## Primary Domain

The base domain is **configurable**: set `global.domain` in the Helm chart and every
hostname below derives from it — `app.<domain>`, `api.<domain>`, and `*.<domain>` for
workshop sessions. The examples on this page use **orchestraplatform.org** (the
reference deployment); substitute your own domain.

> The `app.` and `api.` prefixes are fixed — you configure the base domain, not the
> individual subdomain names. The oauth2-proxy `redirect-url` / `cookie-domain` values
> and the Google OAuth console redirect URI must be set to match your domain.

## Subdomain Architecture

### Core Platform Services

#### Application Layer
- **app.orchestraplatform.org**
  - Main user interface
  - Instance dashboard
  - Template browser
  - Session launch flow

#### API Layer  
- **api.orchestraplatform.org**
  - REST API endpoints
  - Authentication helpers
  - Template catalog operations
  - Instance lifecycle and status endpoints

#### Documentation
- **docs.orchestraplatform.org**
  - User guides and tutorials
  - API documentation
  - Developer resources
  - Platform architecture

### Dynamic Workshop Subdomains

Each workshop instance receives a unique subdomain following a consistent naming pattern:

```
{workshop-id}.orchestraplatform.org
```

#### Workshop ID Format
The host has two parts: the workshop instance name, then the base domain —
`{template-slug}-{6 random chars}.{base_domain}`. The instance name is
generated at launch as the template's slug plus a 6-character lowercase
alphanumeric suffix.

**Examples:**
- `rnaseq-intro-a1b2c3.orchestraplatform.org`
- `genomics-advanced-x9y8z7.orchestraplatform.org`
- `proteomics-basics-m5n6o7.orchestraplatform.org`

#### Benefits of This Structure
- **Memorability**: Clear, descriptive workshop names
- **Uniqueness**: Random suffix prevents collisions
- **Organization**: Course type enables easy categorization
- **Scalability**: Supports unlimited workshop instances

### Administrative Subdomains

#### System Monitoring
- **status.orchestraplatform.org**
  - Platform health dashboard
  - Service uptime monitoring
  - Performance metrics
  - Incident reporting

#### Development Environment
- **staging.orchestraplatform.org**
  - Pre-production testing
  - Feature validation
  - Integration testing
  - Performance testing

## DNS Configuration

### Wildcard DNS Record
```
*.orchestraplatform.org → Kubernetes Ingress Controller
```

This configuration allows dynamic creation of workshop subdomains without manual DNS updates.

### SSL/TLS Certificate Management
TLS is brought to the IngressRoute in one of two ways — the chart does not
provision a wildcard certificate by itself:

- **Per-host certs via cert-manager** — set a cluster-issuer annotation so
  cert-manager issues a Let's Encrypt certificate for each workshop host on
  demand.
- **Bring-your-own wildcard secret** — supply an existing wildcard TLS secret
  via `ingress.tls.existingSecret` and reference it from the IngressRoute.

## Traffic Routing

### Ingress Controller Configuration
The operator creates a Traefik **`IngressRoute`** (not a vanilla
`networking.k8s.io/v1` Ingress) for each workshop, routing on `Host(...)` to
the workshop's Service on port `80`. The Service maps port `80` →
`targetPort 8080` (the `orchestra-sidecar`), which then proxies to the app
container's port (default `8787`):

```yaml
# Example workshop IngressRoute (created by the operator)
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: genomics-101-abc123-ingress
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`genomics-101-abc123.orchestraplatform.org`)
      kind: Rule
      services:
        - name: genomics-101-abc123-service
          port: 80   # Service maps 80 -> 8080 (sidecar) -> app :8787
```

### Load Balancing
- Geographic load balancing for global availability
- Session affinity for workshop continuity
- Health check integration for automatic failover

## Security Considerations

### Domain Validation
- Strict hostname validation in ingress controllers
- Prevention of subdomain hijacking
- Regular certificate rotation

### Access Control
- oauth2-proxy in front of the main app and API
- Workshop ownership tracked on the CRD and in Postgres
- Network isolation between workshops

## Monitoring and Analytics

### Domain-Level Metrics
- Traffic patterns by subdomain
- Workshop usage analytics
- Performance monitoring per domain
- Error rate tracking

### DNS Health Monitoring
- DNS propagation verification
- Certificate expiration alerts
- Subdomain availability checks
