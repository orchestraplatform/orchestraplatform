---
title: Helm Install Guide
description: Install Orchestra on Kubernetes using Helm.
---

Orchestra ships as two Helm charts:

| Chart | Purpose |
|---|---|
| `orchestra-crds` | The Workshop `CustomResourceDefinition` — install once, upgrade separately |
| `orchestra` | Operator, API, frontend, oauth2-proxy, ingress, and Traefik middleware |

## Prerequisites

- Kubernetes 1.25+ (CEL validation on CRDs requires 1.25+)
- Helm 3.12+
- Traefik ingress controller
- cert-manager (for TLS; can be disabled for dev)
- Google OAuth credentials (see [oauth2-proxy setup](./oauth2-proxy))

## Install

```bash
# 1. Install CRDs first (separate lifecycle from the app)
helm install orchestra-crds deploy/charts/orchestra-crds \
  --namespace orchestra-system \
  --create-namespace

# 2. Install the platform
helm install orchestra deploy/charts/orchestra \
  --namespace orchestra-system \
  --set global.domain=orchestra.example.edu \
  --set oauth2Proxy.config.clientID=<your-google-client-id> \
  --set oauth2Proxy.config.clientSecret=<your-google-client-secret> \
  --set oauth2Proxy.config.cookieSecret=$(python3 -c "import secrets; print(secrets.token_hex(16))") \
  --set "oauth2Proxy.config.allowedDomains={example.edu}" \
  --set "api.adminEmails={admin@example.edu}"
```

## Values reference

| Key | Default | Description |
|---|---|---|
| `global.domain` | `orchestra.localhost` | Base domain; produces `app.<domain>` and `api.<domain>` |
| `operator.image.tag` | `latest` | Operator container image tag |
| `api.image.tag` | `latest` | API server container image tag |
| `frontend.image.tag` | `latest` | Frontend container image tag |
| `api.adminEmails` | `[]` | List of admin email addresses |
| `api.requireAuthentication` | `true` | Set to `false` with `devIdentity` for dev mode |
| `api.devIdentity` | `null` | Dev-mode identity bypass email |
| `ingress.className` | `traefik` | Ingress class |
| `ingress.tls.enabled` | `true` | Enable TLS via cert-manager |
| `ingress.tls.clusterIssuer` | `letsencrypt-prod` | cert-manager ClusterIssuer name |
| `oauth2Proxy.enabled` | `true` | Deploy bundled oauth2-proxy |
| `oauth2Proxy.config.clientID` | `""` | Google OAuth client ID |
| `oauth2Proxy.config.clientSecret` | `""` | Google OAuth client secret |
| `oauth2Proxy.config.cookieSecret` | `""` | 16-byte random hex string |
| `oauth2Proxy.config.allowedDomains` | `["*"]` | Email domains allowed to log in |
| `oauth2Proxy.config.allowedEmails` | `[]` | Specific email addresses allowed to log in |

## Upgrading

```bash
# Upgrade CRDs (run this before upgrading the main chart)
helm upgrade orchestra-crds deploy/charts/orchestra-crds \
  --namespace orchestra-system

# Upgrade the platform
helm upgrade orchestra deploy/charts/orchestra \
  --namespace orchestra-system \
  -f values-prod.yaml
```

:::note
Helm does not upgrade CRDs in a chart's `crds/` directory. Orchestra places
the CRD in `templates/` specifically so `helm upgrade` applies schema changes.
Always upgrade `orchestra-crds` before `orchestra` when the CRD schema has
changed.
:::

## Local dev (kind)

Use the provided `values-dev.yaml` to install without TLS or a real Google
credential:

```bash
kind create cluster
helm install orchestra-crds deploy/charts/orchestra-crds
helm install orchestra deploy/charts/orchestra \
  --namespace orchestra-system \
  --create-namespace \
  -f deploy/values-dev.yaml
```

All API calls will be attributed to `dev@orchestra.localhost`. Admin access
is also granted to that email.

## Disabling the bundled oauth2-proxy

If your cluster already has a proxy (corporate oauth2-proxy fleet, Istio
RequestAuthentication, etc.) you can disable the subchart:

```yaml
oauth2Proxy:
  enabled: false
api:
  requireAuthentication: true
```

Your proxy must forward `X-Auth-Request-Email: <user-email>` to the API.
The Orchestra `orchestra-auth-headers` Traefik Middleware will still strip any
inbound versions of that header before your proxy re-sets it.
