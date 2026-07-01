---
title: "ADR-0008: Cluster provisioning boundary"
description: Decision record — the platform depends on a cluster contract, not a specific cluster; cluster provisioning + state live in the infra layer, separate from the app repo, with a deferred trigger for extracting a reusable module.
---

**Status:** Accepted
**Date:** 2026-07-02

## Context

Orchestra now runs on a GKE Standard cluster ([ADR-0005](/docs/adr/0005-gke-standard-tenant-pools/)).
Standing it up raised a repo-ownership question that ADR-0005 did not settle:
**where does cluster *provisioning* live relative to the platform?** Two framings
were floated — leave the cluster's OpenTofu in the infra repo and assume a cluster
exists when installing Orchestra, or move cluster setup into the platform repo.

The question is muddier than a two-way split because **three distinct things** get
conflated into two repos:

1. **Orchestra the platform** — the operator, API, and Helm chart. Cloud-neutral by
   design: [ADR-0005](/docs/adr/0005-gke-standard-tenant-pools/) made tenant
   targeting a config-driven tier map, not GKE constants, and storage/ingress are
   already parameterised. Lives in the platform repo (`orchestraplatform`).
2. **A generic, reusable cluster module** — parameterised OpenTofu for "build a
   cluster that satisfies Orchestra's requirements on GKE," with no project-,
   backend-, or account-specific values.
3. **A specific production instance** — the actual cluster, wired to a GCP project,
   a Terraform state backend, Secret Manager, DNS, and neighbouring infrastructure.

The current production instance lives in a **private infra monorepo** (`monode`)
alongside the rest of the operators' infrastructure (shared Terraform state bucket,
Secret Manager, Cloudflare, Postgres, etc.), where items 2 and 3 are currently
merged — the module carries the production project and state backend inline.

Two forces pull in opposite directions:

- **Separation of state and lifecycle.** A cluster's Terraform state can *destroy the
  cluster*; it must not share a repo (or a review surface) with high-churn
  application changes. Infra changes rarely and deliberately; the platform ships
  often. The Orchestra cluster is also genuinely entangled with the infra
  monorepo's ecosystem (shared state bucket, secrets, DNS, sibling infra).
- **Deployable by others.** Orchestra is a Bioconductor community platform meant to
  be stood up by *other* organisers at other venues (BioC, CSHL). Cluster
  provisioning that is only expressible inside a private infra monorepo is not
  reproducible by them.

## Decision

**The platform depends on a cluster *contract*, not a specific cluster; cluster
provisioning and its state live in the infra layer, separate from the app repo.**

1. **Contract, not cluster.** The operator and chart target a conformant cluster —
   an ingress controller, a storage class, node targeting via the config-driven
   tier map / a `tenant-compute`-style ComputeClass, and egress for image pulls —
   without owning how that cluster is built. This extends ADR-0005's
   cloud-neutrality from "the operator emits portable primitives" to "the platform
   never provisions infrastructure."

2. **Provisioning + state live in the infra layer, not the app repo.** The specific
   production instance stays in the infra monorepo (`monode`), which owns its
   Terraform state, backend, and secrets. The platform repo assumes a cluster
   exists. This keeps the destructive state surface, the slow/deliberate cadence,
   and the entanglement with neighbouring infra out of the fast-moving app repo.

3. **`just doctor` is the contract validator.** Rather than documenting cluster
   requirements only in prose, the platform ships an executable preflight
   (`scripts/doctor.sh`) that checks whether a given cluster satisfies Orchestra's
   needs (node egress, ephemeral-storage headroom vs. template requests,
   ingress/cert-manager/oauth2-proxy presence, requests ≤ limits, secrets). The
   deployment docs carry the generic requirements plus a GKE reference.

## Deferred (with an explicit trigger)

**Extracting the generic module (item 2) into the platform repo — e.g.
`orchestraplatform/deploy/tofu/gke-standard` — that the infra monorepo *consumes*
via a versioned `source` reference, is deliberately deferred, not rejected.**

- **Trigger to do it:** when reproduction by an external operator becomes a real
  near-term goal rather than a possibility.
- **Why it's safe to defer:** the module as written is already ~90% variables
  (project, network, node privacy, disk size, NAP bounds, balloon shape are all
  inputs), so genericising it and repointing the infra monorepo at it is a small,
  bounded change — deferring does not paint us into a corner.
- **Why extract *there* when we do:** the cluster contract (the ComputeClass name,
  node-targeting labels, egress needs) is coupled to what the operator emits, so
  the reference module should be versioned *with* the platform and change in
  lockstep — while the infra monorepo remains the layer that supplies the
  production project, backend, and secrets.

Recording this as deferred-with-a-trigger is the point of this ADR: leaving the
module in the infra monorepo today is a **deliberate, revisitable** choice, not an
oversight, and there is a named condition under which we revisit it.

## Consequences

**Positive:**

- Clean separation of blast radius, cadence, and state ownership between the
  platform and its infrastructure.
- The platform stays honestly cloud-neutral: "assumes a cluster, validates it with
  `just doctor`" is a healthy, portable posture that works for GKE, EKS, AKS, or a
  single-node dev cluster.
- The reproducibility gap for external operators is **acknowledged and owned**, with
  a concrete, cheap path to close it when needed — not accidental.

**Negative / trade-offs:**

- Until the trigger fires, the reusable module lives in a private repo, so an
  external operator reproduces the cluster from the docs + a reference rather than
  by consuming a published module. This is the deliberately-accepted cost.
- Two repos must stay coherent: a change to what the operator expects of the cluster
  (the contract) may require a matching infra change. `just doctor` is the guard
  that surfaces drift.

## Not chosen

- **Cluster IaC in the platform (app) repo** — rejected: couples a destructive
  Terraform state surface and a slow infra cadence to a high-churn app repo, and
  drags the app repo into the infra monorepo's state/secret/DNS entanglement.
- **A third dedicated infra repo for the module** — rejected as over-fragmentation
  for an artifact this small; when extraction happens it belongs in-repo under
  `deploy/tofu/`, consumed by the infra monorepo.
