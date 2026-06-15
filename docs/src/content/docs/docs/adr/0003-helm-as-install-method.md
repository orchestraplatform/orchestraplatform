---
title: "ADR-0003: Helm as the primary install method"
description: Decision record — why Orchestra uses Helm charts.
---

**Status:** Accepted  
**Date:** 2026-04-15

## Context

Orchestra needed a deployment story for production Kubernetes clusters. The
platform has real configuration variation: OAuth credentials, allowed email
domains, image tags, ingress hostnames, TLS issuers, and the conditional
oauth2-proxy subchart. Raw manifests or environment-specific overlays would
require users to manage this variation manually.

Options considered:

1. **Helm charts** — templated YAML rendered from `values.yaml`.
2. **Kustomize** — overlays on top of base manifests.
3. **Operator-managed install** — the Orchestra operator installs all platform
   components from a config CRD.

## Decision

**Helm**, with a two-chart layout (`orchestra-crds` + `orchestra`).

## Consequences

**Positive:**
- Standard k8s admin workflow: `helm install`, `helm upgrade`, `helm rollback`.
- `values.yaml` provides a discoverable, self-documenting interface for all
  configurable parameters.
- oauth2-proxy is added as a conditional dependency (`condition: oauth2Proxy.enabled`)
  using its official chart from `https://oauth2-proxy.github.io/manifests`.
  No re-implementation needed.
- `helm show values` lets admins see all options without reading source code.
- Artifact Hub / `helm search` make the chart discoverable.

**Negative/trade-offs:**
- CRD upgrades require care: Helm does not upgrade CRDs in a chart's `crds/`
  directory. Orchestra places the CRD in `templates/` specifically to allow
  `helm upgrade` to apply schema changes. Admins must upgrade `orchestra-crds`
  before `orchestra` on each release.
- Kustomize users can still use `helm template | kubectl apply` to generate
  raw manifests.

**Not chosen:**
- **Kustomize** was rejected because parameterising the oauth2-proxy credential
  values requires strategic merge patches that are harder to document than
  `values.yaml`.
- **Operator-managed install** was rejected as premature complexity; it adds
  a bootstrapping problem (how do you install the operator that installs the
  operator?).
