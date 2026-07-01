---
title: GitHub CI/CD setup
description: Required GitHub repository settings for the CI and CD workflows — Workload Identity Federation, branch protection, and environment protection rules.
---

The repo ships three GitHub Actions workflows (ADR-0006 phases 2 & 3):

| Workflow | File | Trigger | Purpose |
| --- | --- | --- | --- |
| CI | `.github/workflows/ci.yml` | PR + push to `main` | server pytest + ruff, template-tools pytest + ruff, template-schema-in-sync |
| Validate templates | `.github/workflows/validate-templates.yml` | PR touching `deploy/charts/orchestra/files/templates/**` | per-file template validation with inline annotations |
| Deploy | `.github/workflows/deploy.yml` | push to `main` → dev, tag `v*` → prod | build/push images + `helm upgrade` |

Each workflow invokes the same `just` recipes developers run locally
(`lint-server`, `test-server`, `lint-template-tools`, `test-template-tools`,
`check-schema`) plus the helm flags from `just deploy-gcp`.

These will **not** work until the settings below are configured. None of the
values are committed — set them in repo settings.

## 1. Workload Identity Federation (no JSON key)

`deploy.yml` authenticates with `google-github-actions/auth` via OIDC. Create a
Workload Identity Pool + provider bound to this repo, and a deploy service
account with permission to push to Artifact Registry and run `helm upgrade`
against the GKE cluster (`roles/container.developer`,
`roles/artifactregistry.writer`, and access to the `orchestra-system`
namespace).

Then set these as **secrets** (repo-level, or per-environment):

- [ ] `WIF_PROVIDER` — full provider resource name, e.g.
  `projects/<number>/locations/global/workloadIdentityPools/github/providers/orchestra`
- [ ] `WIF_SERVICE_ACCOUNT` — deploy SA email, e.g.
  `orchestra-deployer@<project>.iam.gserviceaccount.com`
- [ ] `GCP_VALUES_SECRETS` — full contents of the gitignored
  `deploy/gcp-values-secrets.yaml` (OAuth client id/secret). The workflow writes
  it to disk so the 3-values-file `helm upgrade` matches `just deploy-gcp`, then
  deletes it.

And these as **environment variables** (set differently for the `dev` and `prod`
environments):

- [ ] `GCP_PROJECT`
- [ ] `GCP_REGION` (e.g. `us-central1`)
- [ ] `GKE_CLUSTER` (e.g. `orchestra-dev`)
- [ ] `GKE_LOCATION` (cluster zone/region)
- [ ] `ARTIFACT_REGISTRY` (e.g.
  `us-central1-docker.pkg.dev/orchestraplatform-dev/orchestra`)

The workflow leaves each of these as a `# TODO: set <VAR>` placeholder pointing
here.

## 2. Environments

Create two environments (**Settings → Environments**):

- [ ] `dev` — targeted by pushes to `main`. No approval needed.
- [ ] `prod` — targeted by `v*` tags. Add a **Required reviewers** protection
  rule so prod deploys wait for manual approval. Optionally restrict deployment
  branches/tags to `v*`.

Attach the WIF/`GCP_VALUES_SECRETS` secrets and the `GCP_*`/`GKE_*` variables to
each environment so dev and prod can differ.

## 3. Branch protection (required status checks)

On the `main` branch ruleset, require these status checks to pass before merge
(names come from the CI job `name:` fields):

- [ ] `server (pytest + ruff)`
- [ ] `template-tools (pytest + ruff)`
- [ ] `template schema in sync`
- [ ] `orchestra-validate-templates` (only runs when templates change; mark as
  required only if you always want template edits gated)

Also recommended:

- [ ] Require a pull request before merging.
- [ ] Require review from Code Owners (activates `.github/CODEOWNERS`).

## 4. CODEOWNERS teams

`.github/CODEOWNERS` references two org teams that must exist and have write
access, or the ownership rules silently do nothing:

- [ ] `@orchestraplatform/maintainers` — default owner.
- [ ] `@orchestraplatform/template-reviewers` — owns
  `deploy/charts/orchestra/files/templates/**` and `template-tools/**`.
