---
title: "2. Cluster setup (GKE Standard)"
description: Stand up the GKE Standard cluster — the OpenTofu module, NAP + ComputeClass + system pool + balloons, and the two-step apply — before installing Orchestra.
---

This is step 2 of the [deployment sequence](/docs/deployment/overview/). It builds
the **GKE Standard** cluster that Orchestra runs on, per
[ADR-0005](/docs/adr/0005-gke-standard-tenant-pools/). Standard bills for raw VMs
rather than per-pod requests (~1.7–2× cheaper under load) while keeping
scale-to-zero for idle tenants.

:::tip[Run `just doctor` first]
If you haven't already, run the `just doctor` preflight — it verifies `gcloud`
auth, `tofu`/`kubectl`/`helm`, and the inputs from the
[overview](/docs/deployment/overview/#inputs-you-must-supply).
:::

If you are migrating off an existing **Autopilot** cluster, this is a **parallel
stand-up then cutover**: build the new cluster alongside the running one, validate
it, and only then move DNS ([step 5](/docs/deployment/dns-cutover/)). A mistake
never takes production down; rollback is just repointing DNS back.

## Architecture at a glance

| Piece | What / why |
| --- | --- |
| **GKE Standard, zonal** (`us-central1-a`) | Bills for raw VMs, not per-pod requests. Zonal control plane qualifies for the free-tier credit (no HA required). |
| **Node Auto-Provisioning (NAP)** | Sizes tenant nodes to each workshop pod's requests. `optimize-utilization` bin-packs and scales to zero when idle. |
| **`tenant-compute` ComputeClass** | Workshop pods select it (`cloud.google.com/compute-class: tenant-compute`); NAP provisions `e2`→`n2` nodes to fit. |
| **System node pool** (always-on, `e2-standard-2`, min 1) | Holds the platform's own pods (operator, API, frontend, Traefik, oauth2-proxy). Labelled `pool=system` and tainted `dedicated=system:NoSchedule` so workshop pods never land here. |
| **Balloon pods** (`cluster-warmer`) | Negative-priority `pause` pods that hold a warm node; a real session preempts one and schedules instantly while a replacement node boots. |

## Prerequisites

- `gcloud` authenticated with rights to create GKE clusters in the target
  project; **Application Default Credentials** available
  (`gcloud auth application-default login`).
- `tofu` (OpenTofu ≥ 1.11), `kubectl`, `helm`.
- The infra repo checked out: **`monode/infrastructure/terraform/`** — this is
  where the production OpenTofu lives, **not** the platform repo. The cluster
  module is **`modules/gke-standard/`** (plus a `gke_standard.tf` that
  instantiates it). The design spec is in this repo at `deploy/tofu/README.md`.

## 0. Decisions to make before you apply

The module ships safe-ish defaults, but these knobs need a deliberate choice
(also listed in the module README). Put your answers in a `*.tfvars` (or the
module's variable inputs) — do **not** edit defaults in place.

1. **`master_authorized_networks`** — **empty by default, which leaves the public
   control-plane endpoint unrestricted.** Set this to your operator/CI egress
   CIDRs before any real use. *This is the one item that must not go to production
   open.*
2. **`network` / `subnetwork`** — the reference cluster uses **public nodes**
   because the default VPC has **no Cloud NAT** (this matches the Autopilot
   cluster). Private nodes would need a NAT gateway first — see the
   [gotcha](/docs/deployment/troubleshooting/#private-nodes-need-nat). For a clean
   cutover, most likely reuse the Autopilot cluster's VPC/subnet.
3. **`nap_boot_disk_size_gb`** — **must be ≥ the templates' ephemeral-storage
   request.** The default **30 GB is too small** for the 8Gi ephemeral request the
   workshop templates carry (system reserve eats into it) — **use 50 GB.** See the
   [gotcha](/docs/deployment/troubleshooting/#nap-disk-too-small-for-ephemeral-request).
4. **NAP bounds** — `nap_max_cpu` / `nap_max_memory_gb`. Validate against
   *(realistic per-session request) × (target concurrency ≈ 300)*.
5. **Balloon shape** — must be **≥ the largest workshop tier** or the warm node
   can't host an incoming large session. Add extra balloon tiers if you run
   distinct common sizes.
6. **System pool** — `e2-standard-2`, min 1 / max 3. Confirm it fits the aggregate
   requests of the platform pods (operator, API, frontend, Traefik, oauth2-proxy).

## 1. Stand up the cluster (OpenTofu)

From `monode/infrastructure/terraform/`:

```bash
tofu init
tofu plan   # review carefully — this touches shared remote state
```

The `tenant-compute` ComputeClass is a `kubernetes_manifest`, which reads the
cluster API **at plan time** — so on first bring-up the cluster must exist before
that resource can plan. **Apply in two steps:**

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
The cluster sets `deletion_protection = true`. To ever tear it down you must flip
that to `false` and re-apply before `tofu destroy`.
:::

## 2. Confirm the system pool is ready for platform pods

The system pool is labelled `pool=system` and **tainted**
`dedicated=system:NoSchedule`. Orchestra's platform Deployments must select the
label and tolerate the taint, or they'll land on scale-to-zero NAP nodes — wasting
the always-on pool and risking eviction during consolidation.

The chart handles this via the **`systemPool` values block** (configured in
[step 3](/docs/deployment/install/#pin-platform-pods-to-the-system-pool)).
Traefik and oauth2-proxy are installed **outside** the chart, so you pin those in
their own installs — covered in
[Ingress, TLS & auth](/docs/deployment/ingress-tls-auth/).

## Generic Kubernetes / non-GKE

The operator and chart are **cloud-neutral** (see
[ADR-0005](/docs/adr/0005-gke-standard-tenant-pools/)). On kind, EKS, AKS, or
bare metal you don't need NAP or ComputeClasses — you supply your own equivalents:

- **Ingress** — install Traefik (or nginx-ingress) and point the chart at it.
- **Storage** — set `persistence.storageClass` to a `ReadWriteOnce` class your
  cluster provides.
- **Tenant tier map** — the operator's `tierMap` maps tier names to arbitrary
  `nodeSelector`/`tolerations`. On EKS use managed node groups + labels/taints; on
  AKS use node pools; on a single node leave `tierMap` empty (the default) and
  workshop pods schedule normally with no setup.

Everything else (Helm install, ingress/TLS/auth, DNS) is the same. The
cloud-specific pieces here (NAP, ComputeClass, balloons) live in the infra layer
and never touch the CRD or operator code.

Next: [Install Orchestra (Helm)](/docs/deployment/install/).
