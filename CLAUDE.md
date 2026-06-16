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

- ADR-0006 (git-managed YAML workshop templates) — all six phases merged to
  `main`. JupyterLab (`jupyter`) and Bioconductor RStudio (`rstudio`) templates
  ship in `deploy/charts/orchestra/files/templates/`.
- Local template rehearsal: `just rehearse-check` (no-cluster smoke checks) +
  the printed runbook validate catalog → launch → ready → connect via `just dev`.
- [#27](https://github.com/orchestraplatform/orchestraplatform/issues/27) —
  optional bundled Postgres subchart for dev/test installs.
- [#28](https://github.com/orchestraplatform/orchestraplatform/issues/28) —
  Helm chart hardcodes the operator ingress entrypoint to `websecure` and omits
  `ORCHESTRA_INGRESS_PORT`, so a pure-Helm install can't route sessions on a
  local NodePort — the rehearsal uses `just dev` instead.
- Next: run the rehearsal, then the GKE Standard migration (ADR-0005).

## Context

- Bioconductor community project — used for workshops at BioC conferences, CSHL, etc.
- Sean is responsible for the platform; Alex Mahmoud is leading active development
- Part of the broader Bioconductor infrastructure portfolio (see also `omicidx-mcp`, `uccc-genomics-db`)
- CSHL course planning (early June deadline) may involve Orchestra for workshop delivery
