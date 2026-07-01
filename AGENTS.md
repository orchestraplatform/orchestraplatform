# AGENTS.md — bringing Orchestra up

For an operator (or coding agent) standing up an **Orchestra** instance in a new
environment. This is a **thin entry point**: it points at the docs, it does not
duplicate them. For repo-working guidance (layout, dev workflow, open work) see
[`CLAUDE.md`](./CLAUDE.md).

Orchestra is a cloud-native, Kubernetes-based workshop platform: a Helm-installed
API + operator + frontend that provisions isolated, time-limited workshop sessions
(RStudio, Jupyter, …) on demand via a Workshop CRD, one subdomain per session.

## The path

1. **Run `just doctor`** — no-cluster preflight (toolchain, auth, required inputs).
2. **Follow the numbered [Deploying Orchestra](docs/src/content/docs/docs/deployment/overview.mdx)
   runbook** — the authoritative operator path:
   overview → cluster setup (GKE Standard) → Helm install → ingress/TLS/auth →
   DNS cutover → CI/CD → troubleshooting.

Rendered docs: `/docs/deployment/overview/` (the `docs/` Astro Starlight site).

## Inputs you must supply

Full table with details is in the
[deployment overview](docs/src/content/docs/docs/deployment/overview.mdx#inputs-you-must-supply).
In short:

- **GCP project(s)** — cluster + Artifact Registry images in one project; TF state
  and secrets may live in another (multi-project is the real layout).
- **Base domain** (`global.domain`) — derives `app.`, `api.`, `*.<domain>`.
- **DNS provider + API token** — Cloudflare in the reference deploy; token has
  `Zone → DNS → Edit`, stored as a Secret for cert-manager's DNS-01 solver.
- **Image registry** — Artifact Registry (`orchestra-{api,operator,frontend,sidecar}`).
- **Database** — Cloud SQL (managed) *or* in-cluster Postgres. Reachable **before**
  install (migrate pre-install hook).
- **OAuth client** — Google client id/secret (+ generated cookie-secret).
- **Static regional IP** — reserved for the Traefik LoadBalancer; all hosts point here.

## External dependencies (chart does NOT install these)

- **Traefik** — ingress controller (per-session routing; GKE native ingress is
  one-LB-per-session, not viable). Traefik v3, pinned to the static IP, on the
  system pool.
- **cert-manager** — wildcard TLS via a Let's Encrypt **DNS-01** ClusterIssuer
  (HTTP-01 can't do `*.<domain>`).
- **oauth2-proxy** — bundled subchart by default; or bring your own (IAP,
  Cloudflare Access, corporate proxy).

## Key decisions & rationale (see the ADRs)

- **Helm as the install method** — [ADR-0003](docs/src/content/docs/docs/adr/0003-helm-as-install-method.md).
- **GKE Standard over Autopilot** — ~1.7–2× cheaper under load, keeps
  scale-to-zero; portable config-driven tenant tier map keeps the operator
  cloud-neutral — [ADR-0005](docs/src/content/docs/docs/adr/0005-gke-standard-tenant-pools.md).
- **Public nodes** — the reference VPC has no Cloud NAT (matches the old Autopilot
  cluster); private nodes would need a NAT gateway first.
- **DB choice** — Cloud SQL + Auth Proxy sidecar + Workload Identity (no password
  in a Secret) is the reference; in-cluster Postgres is the simpler dev/test option
  ([#27](https://github.com/orchestraplatform/orchestraplatform/issues/27)).
- **Wildcard via DNS-01** — required for per-session subdomains; served to
  per-session routes through Traefik's default `TLSStore`.
- **oauth2-proxy at the ingress** (not in the app) —
  [ADR-0001](docs/src/content/docs/docs/adr/0001-oauth2-proxy-at-ingress.md).
- **Git-managed YAML workshop templates** shipped in the chart —
  [ADR-0006](docs/src/content/docs/docs/adr/0006-yaml-workshop-templates.md) /
  [ADR-0007](docs/src/content/docs/docs/adr/0007-external-template-repo.md).

## Where things live

- **Chart** — `deploy/charts/orchestra` (+ `deploy/charts/orchestra-crds`).
- **Values** — `deploy/charts/orchestra/values.yaml` (defaults) →
  `deploy/gcp-values.yaml` (GCP reference) → `deploy/gcp-values-standard.yaml`
  (systemPool + tierMap) → `deploy/gcp-values-secrets.yaml` (**gitignored**,
  OAuth creds).
- **OpenTofu cluster module** — **separate infra repo**
  `monode/infrastructure/terraform/`, module `modules/gke-standard/`. Design spec
  in this repo at `deploy/tofu/README.md`.
- **Secrets** — Google Secret Manager (`gcp-values-secrets.yaml` contents; OAuth,
  DB, Cloudflare token as k8s Secrets).
- **Deploy recipes** — `justfile`: `just doctor`, `just deploy-gcp`, `just ship-gcp`.
