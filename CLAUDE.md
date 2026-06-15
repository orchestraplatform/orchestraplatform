# CLAUDE.md

## What this is

Orchestra Platform — cloud-native, Kubernetes-based workshop environment for bioinformatics/data science education. Provisions isolated, time-limited workshop sessions (RStudio, Jupyter, etc.) on demand via a Kubernetes operator.

Active collaborators: Vince Carey, Alex Mahmoud. Monorepo consolidated 2026-04 from legacy separate repos.

## Repo layout

```
orchestraplatform/
├── operator/     # Kubernetes operator — manages Workshop CRDs and lifecycle
├── server/       # Orchestra API — REST endpoints for workshop ops
├── frontend/     # Web dashboard (React)
├── sidecar/      # Per-pod sidecar
├── deploy/       # Kubernetes manifests / Helm charts
├── scripts/      # Dev/ops utilities
└── docs/         # Architecture docs
```

## Key open work

- [GH-1](https://github.com/orchestraplatform/orchestraplatform/issues/1) — Alex Mahmoud needs orientation on the monorepo structure and Galaxy migration path. Follow-up on this.

## Context

- Bioconductor community project — used for workshops at BioC conferences, CSHL, etc.
- Sean is responsible for the platform; Alex Mahmoud is leading active development
- Part of the broader Bioconductor infrastructure portfolio (see also `omicidx-mcp`, `uccc-genomics-db`)
- CSHL course planning (early June deadline) may involve Orchestra for workshop delivery
