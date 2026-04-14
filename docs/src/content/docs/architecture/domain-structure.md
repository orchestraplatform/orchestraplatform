---
title: Domain Structure
description: Detailed breakdown of the Orchestra Platform domain architecture and subdomain organization
---

# Domain Structure

The Orchestra Platform is organized around a clear, hierarchical domain structure that separates different platform functions and provides unique access points for individual workshops.

## Primary Domain

**orchestraplatform.org** serves as the root domain for the entire platform ecosystem.

## Subdomain Architecture

### Core Platform Services

#### Application Layer
- **app.orchestraplatform.org**
  - Main user interface
  - Workshop dashboard
  - User management
  - Workshop creation wizard

#### API Layer  
- **api.orchestraplatform.org**
  - REST API endpoints
  - Authentication services
  - Workshop management operations
  - Status and monitoring endpoints

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
`{course-type}-{identifier}-{random-suffix}`

**Examples:**
- `rnaseq-intro-march2025-a1b2c3.orchestraplatform.org`
- `genomics-advanced-cohort12-x9y8z7.orchestraplatform.org`
- `proteomics-basics-workshop1-m5n6o7.orchestraplatform.org`

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

#### Platform Administration
- **admin.orchestraplatform.org**
  - Operator dashboard
  - System configuration
  - User management
  - Resource monitoring

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
- Automatic certificate provisioning via cert-manager
- Let's Encrypt integration for trusted certificates
- Wildcard certificate support for all subdomains

## Traffic Routing

### Ingress Controller Configuration
The Kubernetes ingress controller uses host-based routing to direct traffic:

```yaml
# Example ingress configuration
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: workshop-ingress
spec:
  rules:
  - host: genomics-101-abc123.orchestraplatform.org
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: genomics-101-abc123-service
            port:
              number: 8787
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
- Per-subdomain access policies
- Workshop-specific authentication
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
