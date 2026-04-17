---
title: Ingress Controller Guide
description: Configure Traefik or nginx-ingress for Orchestra, including auth middleware and per-session workshop routing.
---

import { Aside, Tabs, TabItem } from '@astrojs/starlight/components';

Orchestra routes three types of traffic through the ingress layer:

1. **Frontend** — `app.<domain>` → static nginx bundle
2. **API** — `api.<domain>` → FastAPI server
3. **Workshop sessions** — `<session-name>.<domain>` → per-session containers (created dynamically by the operator)

All three require auth to be applied at the ingress, not inside the application.
The chart automates auth wiring for Traefik and nginx-ingress. Choose one before
installing.

## Why GKE native ingress is not supported

GKE's built-in ingress controller (`ingressClassName: gce`) provisions a new
Google Cloud Load Balancer for every `Ingress` resource. Workshop sessions
create one Ingress per active session — at scale that means dozens of LBs,
minutes of provisioning time per launch, and significant cost.

**Use Traefik or nginx-ingress on GKE.** Both run as in-cluster pods and update
their routing tables in seconds when a new Ingress appears.

## Traefik (recommended)

Traefik is the primary supported controller. The chart creates Traefik
`Middleware` CRDs that implement ForwardAuth, which delegates every request to
oauth2-proxy before forwarding it upstream.

### Install Traefik

```bash
helm repo add traefik https://helm.traefik.io/traefik
helm repo update
helm install traefik traefik/traefik \
  --namespace traefik \
  --create-namespace \
  --set service.type=LoadBalancer
```

Wait for an external IP:

```bash
kubectl get svc -n traefik traefik -w
```

Point your DNS wildcard record at that IP:

```
*.orchestra.example.edu  A  <EXTERNAL-IP>
```

### Chart values

```yaml
ingress:
  controller: traefik
  className: traefik
  tls:
    enabled: true
    clusterIssuer: letsencrypt-prod
```

### What the chart creates

When `ingress.controller=traefik` and `oauth2Proxy.enabled=true`, the chart
creates two Traefik `Middleware` objects in the release namespace:

| Middleware | Purpose |
|---|---|
| `orchestra-auth` | ForwardAuth — sends every request to oauth2-proxy for validation. On success, injects `X-Auth-Request-Email` and `X-Auth-Request-User`. On failure, redirects to the login page. |
| `orchestra-auth-headers` | Strips any incoming `X-Auth-Request-*` headers **before** ForwardAuth runs. Prevents clients from forging identity headers. |

Both middlewares are referenced in every Ingress annotation:

```
traefik.ingress.kubernetes.io/router.middlewares: >-
  orchestra-system-orchestra-auth@kubernetescrd,
  orchestra-system-orchestra-auth-headers@kubernetescrd
```

### Per-session workshop Ingress resources

The operator creates an `Ingress` for each active workshop session. Those
Ingresses need the same middleware annotations to enforce auth on session URLs.

Configure the operator to apply the annotation automatically (future feature —
currently requires a manual annotation in the WorkshopTemplate if sessions
should be auth-protected at the ingress level; the API enforces ownership
regardless).

## nginx-ingress

nginx-ingress implements auth via subrequest: nginx calls oauth2-proxy's
`/oauth2/auth` endpoint before forwarding each request. On success, oauth2-proxy
responds with `X-Auth-Request-Email` in headers, which nginx copies onto the
upstream request.

### Install nginx-ingress

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer
```

Wait for external IP, then create the DNS wildcard record as above.

### Chart values

```yaml
ingress:
  controller: nginx
  className: nginx
  tls:
    enabled: true
    clusterIssuer: letsencrypt-prod
```

### What the chart creates

No custom CRDs are needed. The chart adds these annotations to every Ingress:

```yaml
nginx.ingress.kubernetes.io/auth-url: "http://<release>-oauth2-proxy.<ns>.svc.cluster.local:4180/oauth2/auth"
nginx.ingress.kubernetes.io/auth-signin: "https://app.<domain>/oauth2/start?rd=$escaped_request_uri"
nginx.ingress.kubernetes.io/auth-response-headers: "X-Auth-Request-Email,X-Auth-Request-User,X-Auth-Request-Access-Token"
```

nginx-ingress automatically strips the same headers from client requests before
the auth subrequest runs, so identity spoofing is not possible.

<Aside type="note">
The `auth-signin` URL uses `app.<domain>` (the frontend host) because
oauth2-proxy's callback is served from there. Ensure the oauth2-proxy redirect
URI registered with Google includes `https://app.<domain>/oauth2/callback`.
</Aside>

## Custom controller

Use `controller: custom` when you have your own ingress setup (Cloudflare
Access, Istio, corporate proxy, etc.). No auth annotations are added by the
chart. Populate `ingress.annotations` with whatever your controller needs and
set `oauth2Proxy.enabled=false`.

```yaml
ingress:
  controller: custom
  className: nginx             # or whatever your controller uses
  annotations:
    my-proxy.example.com/auth-enabled: "true"
oauth2Proxy:
  enabled: false
```

Your proxy **must** forward `X-Auth-Request-Email: <user@domain>` to the API.
This is the only identity signal Orchestra uses.

## TLS and wildcard certificates

Each workshop session is served at a unique subdomain
(`<session>.orchestra.example.edu`). A standard cert-manager Certificate
covers only the hosts it lists, so you need a wildcard cert.

### Option A — cert-manager with DNS-01 (recommended)

Create a `Certificate` resource using a DNS-01 solver. DNS-01 is required for
wildcard SAN entries (HTTP-01 cannot validate `*.domain`).

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: orchestra-wildcard
  namespace: orchestra-system
spec:
  secretName: orchestra-wildcard-tls
  dnsNames:
    - "*.orchestra.example.edu"
    - "orchestra.example.edu"      # include apex if needed
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
```

The `ClusterIssuer` solver block depends on your DNS provider — your DNS does
not need to be at the same provider as your cluster. The [GCP Autopilot
guide](./gcp#wildcard-tls) has tabbed instructions for **Cloudflare**,
**Google Cloud DNS**, and a pointer to other supported providers.

### Option B — Default TLS store (Traefik)

Configure Traefik's default TLS store to use a pre-existing wildcard secret.
Any Ingress without a `tls` block will use it automatically.

```yaml
# traefik-default-tls.yaml
apiVersion: traefik.io/v1alpha1
kind: TLSStore
metadata:
  name: default
  namespace: traefik
spec:
  defaultCertificate:
    secretName: orchestra-wildcard-tls
```

Then set `ingress.tls.enabled=false` in Orchestra's values — Traefik provides
TLS from its default store, so no per-Ingress `tls` block is needed.

## Auth flow diagram

```
Browser → Traefik/nginx
         │
         ├─ strip X-Auth-Request-* from client headers
         ├─ subrequest → oauth2-proxy /oauth2/auth
         │               ├─ valid cookie → 200 + X-Auth-Request-Email
         │               └─ missing/expired → 401 → redirect to /oauth2/start
         │
         ├─ copy X-Auth-Request-Email onto request
         └─ forward to API / frontend / workshop session
```

The Orchestra API trusts `X-Auth-Request-Email` unconditionally — it assumes
the ingress layer has already validated it. **Never expose the API directly to
the internet without the auth proxy in front.**
