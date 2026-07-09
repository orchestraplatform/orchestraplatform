---
title: "Contributing"
description: How to make changes to Orchestra — repo layout, branch and commit conventions, and the pull request workflow.
---

Orchestra is a monorepo, consolidated in 2026-04 from the legacy separate
repos. This page covers how changes land: where code lives, how to name
branches and commits, and the review workflow.

Before you start, get the stack running locally — see
[Local Development](/docs/development/local-development/).

## Repository layout

| Path | What it is |
| --- | --- |
| `operator/` | Kubernetes operator — manages Workshop CRDs and lifecycle |
| `server/` | Orchestra API (FastAPI) — REST endpoints for workshop ops |
| `frontend/` | Web dashboard (React) |
| `sidecar/` | Per-pod auth/proxy sidecar (Go) |
| `deploy/` | Helm charts and Kubernetes manifests |
| `docs/` | This documentation site (Astro / Starlight) |

The repo is driven by a `justfile` at the root — `just setup`, `just dev`,
`just test`, `just quality`. See [Local Development](/docs/development/local-development/)
for the full dev loop.

## Branch naming

Work happens on feature branches, never directly on `main`. Name branches
`type/short-description`, using the same type vocabulary as commits:

```
feat/workshop-env-args
fix/workshop-phase-enums
docs/gke-standard-plan
refactor/...
chore/add-claude-md
```

## Commit messages

Orchestra uses [Conventional Commits](https://www.conventionalcommits.org/):
`type(scope): summary`. The types and scopes already in use across the
history:

| Type | Used for |
| --- | --- |
| `feat` | New functionality |
| `fix` | Bug fixes |
| `docs` | Documentation changes |
| `chore` | Tooling, deps, housekeeping |
| `refactor` | Code restructuring with no behavior change |
| `test` | Test additions or changes |

Common scopes seen in the log: `api`, `operator`, `frontend`, `deploy`,
`docs`, `landing`, `user-guide`, `adr`, `cloudflare`. Pick the scope that
matches the area you touched; combined scopes (e.g. `test+docs:`) are fine
when a change genuinely spans two.

Examples from the history:

```
feat(operator): apply template env/args to the workshop pod
fix(api): add Starting/Terminated to WorkshopPhase enum (status-sync crash)
docs(adr): ADR-0005 GKE Standard with config-driven tenant pools
chore(frontend): clear pre-existing eslint warnings
```

## Pull request workflow

1. **Branch** off `main` using the `type/short-description` convention.
2. **Commit** in small, well-described chunks — prefer several focused
   commits over one large unreviewable one.
3. **Open a PR** against `main` on GitHub.
4. **Review** — at least one reviewer. Active collaborators are Vince Carey
   and Alex Mahmoud.
5. **Merge** via a GitHub merge commit. **Do not rebase** — history is
   preserved with merge commits (the log shows
   `Merge pull request #N from ...`), which keeps the true sequence of
   events and stays reversible.

Bring upstream changes into your branch with `git merge origin/main`, not
`git pull --rebase`.

## Review checklist

Before requesting review (and before merging), confirm:

- **Tests pass.** Run `just test` for the full monorepo suite. See the
  [Testing](/docs/development/testing/) guide for the three test tiers and
  where to add coverage.
- **Quality passes.** Run `just quality` (ruff for Python, eslint/prettier
  for JS/TS, go fmt for the sidecar).
- **Docs updated.** If the change affects behavior, configuration, or the
  public API, update the relevant page under `docs/`.
- **Types regenerated.** If you changed API models, run `just sync-types`
  so the frontend's generated types stay in sync.
- **ADR added for architectural decisions.** Record significant or
  hard-to-reverse decisions as an Architecture Decision Record under
  `docs/adr/`, following the numbered format of the existing records (e.g.
  [ADR-0005](/docs/adr/0005-gke-standard-tenant-pools/)).

## See also

- [Local Development](/docs/development/local-development/) — prerequisite setup and the dev loop.
- [Testing](/docs/development/testing/) — test strategy and where to add coverage.
- The **Decision Records** section in the sidebar — the full ADR log (e.g. [ADR-0001](/docs/adr/0001-oauth2-proxy-at-ingress/)).
