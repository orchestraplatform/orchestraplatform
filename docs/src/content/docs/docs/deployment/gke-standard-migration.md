---
title: "GKE Standard migration & deploy runbook"
description: End-to-end runbook for standing up the GKE Standard cluster (NAP + system pool + balloons), deploying Orchestra onto it, cutting over from Autopilot, and decommissioning.
---

This runbook takes Orchestra from the current **GKE Autopilot** cluster to a
cost-optimized **GKE Standard** cluster per [ADR-0005](/docs/adr/0005-gke-standard-tenant-pools/).
It is a **parallel stand-up then cutover**: the new cluster is built alongside
the running Autopilot one, validated, and only then does traffic move — so a
mistake never takes production down.

:::caution[Not yet executed]
As of writing, the cluster has **not** been applied. The OpenTofu is written and
validated; the steps below are the intended procedure. Resolve the
[decisions](#0-decisions-to-make-before-you-apply) first.
:::

## Architecture at a glance

| Piece | What / why |
| --- | --- |
| **GKE Standard, zonal** (`us-central1-a`) | Bills for raw VMs, not per-pod requests (~1.7–2× cheaper under load). Zonal control plane qualifies for the free-tier credit. |
| **Node Auto-Provisioning (NAP)** | Sizes tenant nodes to each workshop pod's requests (Autopilot-like flexibility at Standard price). `optimize-utilization` bin-packs and scales to zero when idle. |
| **`tenant-compute` ComputeClass** | Workshop pods select it; NAP provisions `e2`→`n2` nodes to fit. |
| **System node pool** (always-on, `e2-standard-2`, min 1) | Holds the platform's own pods (operator, API, frontend, Traefik, oauth2-proxy). Tainted `dedicated=system:NoSchedule` so workshop pods never land here. |
| **Balloon pods** (`cluster-warmer`) | Negative-priority `pause` pods that hold a warm node; a real session preempts one and schedules instantly while a replacement node boots. |

The **operator** side of ADR-0005 (config-driven tier map, `safe-to-evict`,
grace period) is implemented — see [step 3](#3-configure--deploy-orchestra).

## Prerequisites

- `gcloud` authenticated with rights to create GKE clusters in the target
  project; **Application Default Credentials** available
  (`gcloud auth application-default login`).
- `tofu` (OpenTofu ≥ 1.11), `kubectl`, `helm`.
- The infra repo checked out: **`monode/infrastructure/terraform/`** (this is
  where the production OpenTofu lives — *not* the platform repo). The cluster
  module is on branch **`feat/gke-standard-cluster`** (`modules/gke-standard/` +
  `gke_standard.tf`).
- `deploy/gcp-values.yaml` and the gitignored `deploy/gcp-values-secrets.yaml`
  present in the platform repo (same files `just deploy-gcp` uses).

## 0. Decisions to make before you apply

The module ships safe-ish defaults but five knobs need a deliberate choice
(they're also listed in the module README):

1. **`master_authorized_networks`** — **empty by default, which leaves the public
   control-plane endpoint unrestricted.** Set this to your operator/CI egress
   CIDRs before any real use. *This is the one item that must not go to
   production open.*
2. **`network` / `subnetwork`** — default `default`. For a clean cutover, most
   likely **reuse the Autopilot cluster's VPC/subnet** (supply the names, plus
   named secondary ranges if it's a shared-VPC subnet).
3. **NAP bounds** — `nap_max_cpu=400` / `nap_max_memory_gb=1600`. Validate
   against *(realistic per-session request) × (target concurrency ≈ 300)*.
4. **Balloon shape** — `4` vCPU / `16Gi`, `balloon_replicas=1`. Must be **≥ the
   largest workshop tier** or the warm node can't host an incoming large session.
   Add `extra_balloon_tiers` if you run distinct common sizes.
5. **System pool** — `e2-standard-2`, min 1 / max 3. Confirm it fits the
   aggregate requests of the platform pods.

Put your answers in a `*.tfvars` (or the module's variable inputs) — do **not**
edit defaults in place.

## 1. Stand up the cluster (OpenTofu)

From `monode/infrastructure/terraform/` on `feat/gke-standard-cluster`:

```bash
tofu init
tofu plan   # review carefully — this touches shared remote state
```

The `tenant-compute` ComputeClass is a `kubernetes_manifest`, which reads the
cluster API **at plan time** — so on first bring-up the cluster must exist before
that resource can plan. Apply in two steps:

```bash
# 1) Create the cluster + system pool + NAP first
tofu apply -target=module.gke_standard.google_container_cluster.this \
           -target=module.gke_standard.google_container_node_pool.system

# 2) Then the full apply (ComputeClass, PriorityClass, balloon Deployment)
tofu apply
```

Get credentials and sanity-check:

```bash
gcloud container clusters get-credentials <cluster-name> --zone us-central1-a --project <project>
kubectl get nodes                    # system pool node(s) Ready
kubectl get computeclass tenant-compute
kubectl get deploy cluster-warmer    # balloon(s) Running once a node is warm
```

:::note[deletion_protection]
The cluster sets `deletion_protection = true`. To ever tear it down you must
flip that to `false` and re-apply before `tofu destroy`.
:::

## 2. Place platform pods on the system pool

The system pool is **tainted** `dedicated=system:NoSchedule`. The platform
Deployments must tolerate it (and select `pool=system`) or they'll land on
scale-to-zero NAP nodes — wasting the always-on pool and risking eviction during
consolidation.

The chart supports this via a **`systemPool` values block** (default off, so
kind/minikube/Autopilot installs are unaffected). Enable it in your GCP values so
the operator, API, and frontend get the `pool=system` `nodeSelector` and the
`dedicated=system:NoSchedule` toleration:

```yaml
systemPool:
  enabled: true
  nodeSelectorKey: pool
  nodeSelectorValue: system
  taintKey: dedicated
  taintValue: system
  taintEffect: NoSchedule
```

:::note[Traefik & oauth2-proxy]
Traefik and oauth2-proxy are installed **outside** this chart, so pin them to the
system pool in their own installs (add the same `nodeSelector`/`toleration`).
:::

## 3. Configure & deploy Orchestra

**Operator tier map (ADR-0005, implemented).** Workshop pods get their
scheduling from a config-driven tier map, and always carry
`cluster-autoscaler.kubernetes.io/safe-to-evict: "false"` +
`terminationGracePeriodSeconds` (default 120). For GKE, point the tiers at the
ComputeClass in your GCP values:

```yaml
operator:
  tierMap:
    small: { computeClass: tenant-compute }
    large: { computeClass: tenant-compute }
  computeClassLabelKey: cloud.google.com/compute-class
  terminationGracePeriodSeconds: 120
```

An empty `tierMap` (the default) emits no scheduling constraints, so single-node
clusters keep working. Templates select a tier via their existing `tier:` field
(`small`/`large`).

**Deploy** (same shape as `just deploy-gcp`, run the DB migration hook first):

```bash
SHA=$(git rev-parse --short HEAD)
just build-push                       # or let CD build; images tagged with $SHA

helm upgrade --install orchestra ./deploy/charts/orchestra \
  -n orchestra-system --create-namespace \
  -f deploy/charts/orchestra/values.yaml \
  -f deploy/gcp-values.yaml \
  -f deploy/gcp-values-secrets.yaml \
  --set operator.image.tag="$SHA" \
  --set api.image.tag="$SHA" \
  --set frontend.image.tag="$SHA" \
  --wait
```

Verify:

```bash
kubectl -n orchestra-system get pods -o wide   # platform pods on the system node
kubectl -n orchestra-system rollout status deploy/orchestra-api
```

Once CD is configured (see [GitHub CI/CD](/docs/deployment/github-cicd/)), a
merge to `main` runs this `helm upgrade` for you; the `checksum/templates`
annotation rolls the API pod so template edits go live without a manual step.

## 4. Validate end-to-end

1. Launch a **jupyter** and an **rstudio** workshop through the API/dashboard.
2. Confirm each session pod schedules on a **NAP-provisioned tenant node**, not
   the system pool:
   ```bash
   kubectl get pods -A -o wide | grep -E 'jupyter|rstudio'
   kubectl get nodes -l cloud.google.com/compute-class=tenant-compute
   ```
3. Confirm the pod carries `safe-to-evict=false` and a 120s grace period
   (`kubectl get pod <p> -o yaml | grep -A2 -e safe-to-evict -e terminationGrace`).
4. Confirm balloon behavior: after a session preempts a balloon, a replacement
   node boots and `cluster-warmer` returns to Running.
5. Full path: catalog → launch → ready → connect works over the ingress.

## 5. Cutover

With the new cluster validated and serving:

1. Point DNS / the load balancer at the new cluster's ingress.
2. Watch new sessions land on the Standard cluster; let existing Autopilot
   sessions drain (they're time-limited).
3. Keep Autopilot running until you're confident (a day of real workshops).

## 6. Decommission Autopilot

Once cutover is stable and Autopilot is idle:

1. Confirm no live sessions / no traffic on Autopilot.
2. Delete the Autopilot cluster (it was created out-of-band, **not** in
   Terraform, so remove it via `gcloud`/console — there is no `tofu destroy` for
   it).
3. Record final Autopilot vs Standard cost to confirm the savings.

## Gotchas found during the first stand-up

Validated on `orchestraplatform-dev` (2026-07-01); fixes are in the tofu module
and chart:

- **Node egress.** The Autopilot cluster runs **public nodes** with no Cloud NAT
  on the `default` VPC. Private nodes on GKE Standard therefore can't pull
  external workshop images (Docker Hub `rocker/*`, `registry.k8s.io/pause`) —
  the balloon and every workshop stay `ImagePullBackOff`. Fix: `enable_private_nodes = false`
  (or add Cloud NAT). Note `enable_private_nodes` is **immutable** — changing it
  replaces the cluster, which is blocked by `deletion_protection`; flip that off
  in a separate apply first, or just delete + recreate.
- **NAP disk vs ephemeral-storage.** A 30GB NAP node yields only ~7.8GiB
  *allocatable* ephemeral-storage — under the templates' 8Gi request — so NAP
  refuses to scale up (`NotTriggerScaleUp: Insufficient ephemeral-storage`). Use
  `nap_boot_disk_size_gb = 50` (~18GiB allocatable).
- **Fresh-install chart bug.** The `orchestra-migrate` pre-install hook must not
  set `serviceAccountName: orchestra-operator` — that SA doesn't exist yet during
  pre-install, so every fresh install fails `serviceaccount ... not found`. It
  only runs `alembic`, so the default SA is correct (fixed in `migrate-job.yaml`).
- **`uv` under `readOnlyRootFilesystem`.** Set `UV_CACHE_DIR=/tmp/uv-cache` **and**
  `UV_NO_SYNC=1` / `UV_FROZEN=1` on the API — otherwise `uv run` tries to mutate
  the baked-in `/app/.venv` at startup and crash-loops (in `gcp-values.yaml`).
- **External DB + hooks ordering.** The migrate pre-install hook needs the
  namespace and the database to already exist. Pre-create both (Postgres/Cloud
  SQL reachable) before `helm install`; if you pre-create the namespace, add the
  Helm-ownership label/annotations so the chart's `namespace.yaml` can adopt it.

## Rollback

Because this is parallel stand-up, rollback is just **repoint DNS/LB back to
Autopilot**. Nothing about creating the Standard cluster disturbs Autopilot.

## Cost note

The always-on system node plus one warm balloon node (`4` vCPU / `16Gi`) is a
standing ~2-node baseline even when fully idle — the deliberate trade for fast
session starts. Scale `cluster-warmer` to 0 for long quiet periods, and up before
a cohort (`kubectl scale deploy cluster-warmer --replicas=N`), or wire pre-warm/
cooldown CronJobs.
