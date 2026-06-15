---
title: "ADR-0005: GKE Standard with config-driven tenant node pools"
description: Decision record — moving off Autopilot to GKE Standard and how workshop pods target tenant tiers portably.
---

**Status:** Accepted
**Date:** 2026-06-15

## Context

Orchestra's production cluster ran on **GKE Autopilot**. Autopilot is
operationally simple but bills at roughly 2× the per-vCPU/GB rate of
self-managed Standard nodes. For light usage this is fine; under heavier
workshop load — many concurrent, stateful RStudio/Jupyter pods spun up per
attendee — the premium becomes the dominant cost.

The workload has an unusual shape: pod scheduling is driven natively by the
Orchestra operator via the Workshop CRD, so we do **not** want pod-level
Horizontal Pod Autoscaling. What we want instead is responsive
*infrastructure*-level autoscaling that provisions raw VMs on demand and
dense-packs them, then scales back to zero when idle.

Two design questions fell out of this:

1. **Cluster shape** — what does the GKE Standard cluster look like?
2. **How do workshop pods land on the right nodes** — and does whatever
   mechanism we pick lock Orchestra to GKE?

The second question matters because Orchestra is a Bioconductor community
project run at multiple venues (BioC conferences, CSHL, etc.). It must remain
installable on EKS, AKS, bare-metal, and single-node clusters (kind/minikube)
for local development and demos. The operator is cloud-neutral today
(`storageClass` is parameterised in `pvc.py`; ingress is controller/annotation
driven), and that property must not regress.

Options considered for tenant targeting:

1. **No targeting** — let the default scheduler place workshop pods anywhere.
   Simple, but cannot separate small/large tenants onto right-sized pools or
   drive scale-to-zero per tier.
2. **Hardcoded GKE taints/labels in the operator** — bake the tenant-pool taint
   keys and node labels directly into `deployment.py`. Works on GKE, but couples
   the operator to one cluster topology and breaks single-node/other-cloud
   installs.
3. **Config-driven tier → scheduling map** — the operator reads a
   tier-to-(`nodeSelector`, `tolerations`) mapping from configuration; the CRD
   selects a tier *by name*. Mirrors how `storageClass` and ingress are already
   handled.

## Decision

**Move the production cluster to GKE Standard, and express tenant targeting as a
config-driven tier map (Option 3).**

**Cluster design** (implementation spec lives in `deploy/tofu/README.md`;
production OpenTofu in `monode/infrastructure/`):

- GKE Standard (not Autopilot), `optimize-utilization` autoscaling profile for
  aggressive bin-packing and fast scale-down.
- Two tenant node pools that scale to zero when idle, each with a taint and
  label the operator can target:
  - `small-tenant-pool` — e2-medium, min 0 / max 50, taint
    `tenant-size=small:NoSchedule`, label `tenant-tier=small`.
  - `large-tenant-pool` — e2-standard-4, min 0 / max 20, taint
    `tenant-size=large:NoSchedule`, label `tenant-tier=large`.
- GKE Image Streaming and `pd-balanced` 30GB nodes on both pools.
- A `cluster-warmer` balloon Deployment at a negative `PriorityClass` to hold
  warm capacity so the first tenant of a tier doesn't wait on a cold node.

**Tenant targeting design** (the operator-side decision):

- The operator emits `nodeSelector` + `tolerations` on workshop pods from a
  **configurable tier map**, e.g.:

  ```yaml
  tiers:
    small:
      nodeSelector: { tenant-tier: small }
      tolerations: [{ key: tenant-size, value: small, effect: NoSchedule }]
    large:
      nodeSelector: { tenant-tier: large }
      tolerations: [{ key: tenant-size, value: large, effect: NoSchedule }]
    default: {}        # empty → schedule anywhere
  ```

- The Workshop CRD/template references a tier **by name**; the operator looks up
  the mapping. The CRD schema contains no cloud-specific nouns.
- The taint keys, label values, and pool names are **arbitrary strings supplied
  by configuration**, not constants in Python. The GKE values above are just the
  production instance of that config.
- An empty / `default` tier emits no `nodeSelector` or `tolerations`, so
  single-node clusters (kind, minikube, Docker Desktop) and generic clusters
  schedule workshop pods normally with no setup.

## Consequences

**Positive:**

- Substantially lower compute cost under load versus Autopilot, while keeping
  scale-to-zero so idle tenants cost nothing.
- Right-sized pools: small and large workshops no longer share one machine
  shape.
- Portability is preserved. Taints/tolerations/labels are vanilla Kubernetes;
  EKS managed node groups, AKS node pools, and manually labelled bare-metal
  nodes reach the same outcome with their own values. Cloud-specific autoscaling
  (Cluster Autoscaler, Karpenter) lives in the infra layer, invisible to the
  operator.
- The tier map follows the established `storageClass`/ingress pattern, so it is
  consistent with how the chart already handles cloud variation.

**Negative / trade-offs:**

- GKE Standard shifts node upgrades, security patching, and system node-pool
  sizing onto us — operational work Autopilot absorbed.
- Balloon pods trade a small standing cost for warm-start latency; the replica
  count needs tuning against real workshop arrival patterns.
- The cluster-shape pieces (scale-to-zero, `optimize-utilization`, Image
  Streaming, balloons) are GKE-specific by nature. They are deliberately
  confined to the infra layer; other environments would need their own
  equivalents, but the operator and CRD are unaffected.

**Follow-up work (not yet implemented):**

- The operator currently sets **no** `nodeSelector`/`tolerations` on workshop
  pods (`operator/src/resources/deployment.py`), so the tainted pools would stay
  empty. The config-driven tier map above must be implemented, plus a way for
  Workshop templates to select a tier, before the GKE Standard pools carry
  traffic.
- Open infra questions tracked in `deploy/tofu/README.md`: system node-pool
  sizing, cutover sequencing from the current cluster, and balloon replica
  tuning.

**Not chosen:**

- **No targeting** was rejected because it defeats per-tier sizing and
  scale-to-zero, the cost levers that motivated the migration.
- **Hardcoded GKE taints/labels** was rejected because it couples the operator
  to one cluster topology and breaks single-node and non-GKE installs — a
  regression of Orchestra's current cloud-neutrality.
