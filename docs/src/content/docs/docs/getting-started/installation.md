---
title: Installation
description: Get an Orchestra instance running — a local cluster for evaluation, or a production deployment via Helm.
---

import { Aside, Steps, Tabs, TabItem } from '@astrojs/starlight/components';

This page is a quick-start for **standing up an Orchestra instance**. For a local
evaluation cluster, follow the local path. For a real deployment, the Helm and
cloud guides under [Deployment](/docs/deployment/helm/) are the source of truth —
this page just orients you.

## Prerequisites

- A **Kubernetes cluster** (Docker Desktop's built-in cluster is fine for local eval; GKE/EKS/etc. for production).
- **`kubectl`** and **`helm`** on your `PATH`.
- An **ingress controller** (Orchestra is tested with Traefik) and, for real domains, **cert-manager** for TLS.
- A **Google OAuth client** for login (see [oauth2-proxy Setup](/docs/deployment/oauth2-proxy/)).

<Tabs>
<TabItem label="Local (evaluation)">

The repo's `justfile` wraps the local setup against Docker Desktop's Kubernetes.

<Steps>

1. Install toolchains and dependencies:

   ```sh
   just setup
   ```

2. Prepare the local cluster (switches to the `docker-desktop` context, installs
   Traefik, applies the Orchestra CRDs, seeds `.env` files):

   ```sh
   just dev-setup
   ```

3. Run the stack (API, frontend, operator) — see
   [Local Development](/docs/development/local-development/) for details:

   ```sh
   just dev
   ```

</Steps>

Workshop sessions are reachable at `http://<name>.127.0.0.1.nip.io:30080`
(`nip.io` resolves to localhost — no DNS setup needed).

</TabItem>
<TabItem label="Production (Helm)">

Apply the CRDs, then install the chart. The CRDs ship as a separate chart so the
Workshop CRD is registered before the operator starts.

```sh
# 1. CRDs first
kubectl apply -f deploy/charts/orchestra-crds/templates/

# 2. Install/upgrade the platform
helm upgrade --install orchestra ./deploy/charts/orchestra \
  -n orchestra-system --create-namespace \
  -f deploy/charts/orchestra/values.yaml \
  -f your-values.yaml
```

<Aside type="note">
The chart runs database migrations automatically as a Helm `pre-upgrade` hook,
so they apply in the right order on every install/upgrade.
</Aside>

See the [Helm Chart guide](/docs/deployment/helm/) for the full values reference,
[Ingress Controller](/docs/deployment/ingress/) for routing and wildcard TLS, and
[GCP Autopilot](/docs/deployment/gcp/) for an end-to-end cloud walkthrough.

</TabItem>
</Tabs>

## Next steps

- [Configuring Workshop Images](/docs/user-guide/configuring-images/) — make any container image run as a workshop.
- [Platform Overview](/docs/architecture/platform-overview/) — how the pieces fit together.
