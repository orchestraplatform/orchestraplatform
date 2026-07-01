---
title: "ADR-0007: External workshop-templates repo, fetched via UPath"
description: Decision record — moving workshop templates out of the platform chart into a separate git repo that the API fetches over a UPath source at runtime, with a published validator package and no offline fallback.
---

**Status:** Deferred (2026-06-30) — superseded plan retained for reference
**Date:** 2026-06-29

> **Deferral note (2026-06-30).** After implementing phase 1 (the extracted
> `orchestra-template-tools` package, [#33](https://github.com/orchestraplatform/orchestraplatform/pull/33)),
> we paused the remaining phases (2–6) and **stay on [ADR-0006](/docs/adr/0006-yaml-workshop-templates/)**:
> templates remain git-managed YAML packaged in the platform chart. Rationale:
> the runtime-fetch machinery in this ADR (external repo, UPath loader, background
> refresh, atomic swap, `stale`/`degraded` status, readiness gating, two cross-repo
> version pins) exists almost entirely to serve the *weakest* of the four driving
> requirements — **edit-the-catalog-without-a-platform-redeploy**. ADR-0006 already
> delivers the three strong ones (review gate, reproducibility, contribution path)
> with far less machinery, and a `helm upgrade` already rolls the API pod via the
> `checksum/templates` annotation, so a catalog edit does propagate without shelling
> in. A database-backed store was also reconsidered and rejected again — it would
> trade away the three strong requirements to serve the weak one.
> **What we kept:** the `orchestra-template-tools` package (schema + validator + CLI)
> is useful regardless and remains the single source of truth for the template
> contract. **Escalation path if cadence pain ever materializes:** adopt a *reduced*
> version of this ADR — **fetch-on-startup only** from an external repo (drop the
> background refresh, admin reload/validate endpoints, and atomic-swap/`degraded`
> machinery); a catalog change then propagates on a `kubectl rollout restart`, not a
> full `helm upgrade`. That captures most of the benefit for a fraction of the
> complexity. Because 0007 is deferred, **ADR-0006 decisions A and D remain in
> force** (the "Supersedes" line below describes the deferred plan, not current
> state).

**Supersedes:** [ADR-0006](/docs/adr/0006-yaml-workshop-templates/) decisions **A**
(contribution via PR against the platform repo) and **D** (templates packaged in
the chart, mounted via ConfigMap, rolled out on `helm upgrade`).
**Retains:** [ADR-0006](/docs/adr/0006-yaml-workshop-templates/) decision **C**
(git/YAML is the source of truth; there is no runtime-mutable template entity)
and **E** (templates declare a `tier`).

## Context

[ADR-0006](/docs/adr/0006-yaml-workshop-templates/) made workshop templates
git-managed YAML and packaged them *inside the platform Helm chart*
(`deploy/charts/orchestra/files/templates/*.yaml`), rendered into a ConfigMap and
loaded into an in-memory registry at startup. That fixed reproducibility, added a
review gate, and gave community authors a contribution path.

In use, the chart-bundling created a coupling we didn't want: a one-line template
edit travels through the *platform's* release cycle — a PR against the platform
repo, then a `helm upgrade` with a `checksum/config` rolling restart — just to
change a catalog entry. Templates and the platform have genuinely different
change cadences and different audiences (workshop authors are researchers, not
platform maintainers), and packaging them together forces the slower cadence on
the faster-moving artifact. We also want catalog edits to propagate to a running
instance without a platform redeploy.

We considered, over the course of this decision, a database-backed projection
(synced from YAML) and a bidirectional model (online editing plus YAML
dump/sync). Both were rejected — see *Not chosen* — for reintroducing the
"cache pretending to be a model" drift surface and, for the bidirectional case,
for having no single source of truth and quietly defeating the review gate.

## Decision

Move workshop templates into their **own repository**, fetched by the API at
runtime over a configurable **UPath** source. Six linked decisions:

**A. Templates live in a separate `workshop-templates` repo.** Canonical
templates leave the platform repo and live in
`orchestraplatform/workshop-templates`. The platform repo and the catalog now
release independently. The review gate is unchanged in spirit — PR approval, now
in the templates repo, with its own `CODEOWNERS` — but **branch protection on the
fetched branch is now load-bearing**: because the running platform reads a
mutable branch, blocking direct/force pushes is what keeps "merged = reviewed"
true.

**B. The validator ships from the platform as a small pip package.** The schema
and validation routine are factored out of `server/` into a dependency-light
package in the top-level `template-tools/` directory, `orchestra-template-tools`
(pydantic + pyyaml + the JSON Schema), that
exposes a CLI (`orchestra-validate-templates <dir>`). The **schema lives inside
this package as the single source of truth** — it is not vendored into the
templates repo. Three consumers call the one CLI: the platform's
`just validate-templates`, the templates repo's CI, and the platform's *runtime*
re-validation (decision E). The templates repo installs it straight from git,
pinned to a tag:

```
pip install "git+https://github.com/orchestraplatform/orchestraplatform.git@vX.Y.Z#subdirectory=template-tools"
```

**C. `workshop-templates` doubles as the GitHub starter template.** The repo is
marked as a GitHub *template repository* ("Use this template"), so a downstream
organizer scaffolds their own catalog repo that inherits the validation workflow,
`CODEOWNERS`, the `# yaml-language-server: $schema=` wiring, and branch-protection
guidance. The canonical `jupyter` and `rstudio` templates live there as live
catalog entries that double as worked examples. To avoid the naming collision we
standardize on **"workshop templates"** (the YAML) versus the **"starter repo"**
(the GitHub template-repository feature).

**D. The platform fetches the catalog over a configurable UPath at a cadence.**
A single config value names the source — `ORCHESTRA_TEMPLATE_SOURCE`, a
[universal_pathlib](https://github.com/fsspec/universal_pathlib) URI — defaulting
to `github://orchestraplatform:workshop-templates@<ref>`. UPath resolves
`file://`, `gs://`, `s3://`, and `github://` (the last via fsspec's
`GitHubFileSystem`) through one interface, so a downstream deployment can point at
its own repo or an object store unchanged. The loader globs `*.yaml`, parses, and
builds the in-memory registry. A background task re-reads on a configurable
cadence; `POST /admin/templates/reload` forces an immediate re-read; and
`POST /admin/templates/validate` reports per-file pass/fail against the source
*without* swapping the live registry. Per-environment refresh: **prod pins a
tag** (reproducible), **dev tracks `main`** (hot). Each refresh must invalidate
the fsspec cache (it caches listings and the filesystem instance); a token from a
Secret is passed via `storage_options` for rate limits / private sources.

**E. Runtime re-validation is the safety boundary; loads are atomic.** The
platform never trusts fetched YAML on the strength of CI. Every load
re-validates with the same CLI from decision B, and the registry swap is
**all-or-nothing** per refresh: if the fetched batch fails validation, the
last-good in-memory registry is retained and the error is surfaced via the
validate/status endpoint. CI in the templates repo is fast feedback, not the
boundary — the runtime fetches a mutable branch and schema versions can skew.

**F. A working instance fetches, or it fails — no offline fallback.** Orchestra
provisions networked Kubernetes sessions and is never useful offline, so there is
**no bundled fallback catalog** (another in-chart copy would just be a second
source of truth that drifts). The failure behavior is split by moment:

- **Startup** (or first boot where the source is unreachable, empty, or wholly
  invalid): the API **fails its readiness probe** — it sits `NotReady` with a
  clear status/event and never becomes Ready serving an empty `GET /templates`.
  We prefer NotReady-with-reason over crash-loop: same "unusable" outcome, but
  observable and self-recovering when the source returns, without restart churn.
- **A later periodic refresh fails** (a transient blip): the already-validated
  in-memory registry is **retained** and flagged `stale`/`degraded`, and the
  refresh retries. This is not a fallback and not an offline mode — it is
  declining to discard validated state over a hiccup. A single newly-invalid file
  on refresh is skipped with last-good retained for that slug and the error
  reported.

## Consequences

**Positive:**

- Templates and the platform release on independent cadences; a catalog edit no
  longer requires a platform `helm upgrade`. Merge to the fetched branch (or
  `POST /admin/templates/reload`) propagates within a cadence interval.
- A contribution path that matches the Bioconductor community: a dedicated repo
  with its own `CODEOWNERS`, scaffolded for new organizers via the starter
  template.
- The default source is the *real* fetch path, so a fresh instance exercises
  fetch → validate → register end to end — no special-cased bundle that rots
  from under-testing.
- One validator implementation (schema + CLI) shared by editor, CI, and runtime,
  so the three cannot silently disagree.
- "Pause fast" is preserved without a database or any bidirectional machinery:
  set `enabled: false` in the templates repo and `reload`.

**Negative / trade-offs:**

- The template source is now a **hard runtime dependency** — its availability is
  part of Orchestra's. Pinning a tag in prod puts GitHub's contents API in the
  boot path; acceptable, since Orchestra already depends on the cluster, registry
  pulls, and ingress, all networked.
- The schema is now a **cross-repo contract** and needs semver plus a
  backward-compat policy (the platform should tolerate unknown fields and may key
  on a `schemaVersion`), where before it was an in-tree generated file.
- **Two pins point at each other**: the platform's default config pins a
  `workshop-templates` ref, and that repo's CI pins a validator version from the
  platform. Release N ships `default-source-ref = workshop-templates@T`, and
  `T`'s CI validates against the validator from ~N. Deliberate, but a bump
  fan-out: downstream template repos must bump their validator pin on a new
  schema version (Dependabot does not track arbitrary git pins cleanly, so this
  is a docs + bump-PR story at current scale).
- Each API replica fetches independently, so the catalog is eventually consistent
  across replicas (and `reload` only hits the replica that receives it). This is
  harmless: instances stamp `resolved_spec` at launch (ADR-0006 C), so brief skew
  affects only the catalog listing, not launched workshops.

**Not chosen:**

- **Status quo (ADR-0006 chart-bundled ConfigMap)** — couples catalog edits to
  the platform release cycle, the problem this ADR exists to fix.
- **In-chart fallback catalog** — a second source of truth that drifts, and
  pointless for a platform with no useful offline state (decision F).
- **Database-backed projection synced from YAML** — reintroduces the
  "cache pretending to be a model" drift surface ADR-0006 C rejected, plus a
  table, a migration, and a sync step, while still needing a cross-replica
  invalidation story.
- **Bidirectional (online edit + YAML dump/sync)** — no single source of truth,
  silent conflict/data-loss between two writers, destroys hand-authored YAML
  comments and the `$schema` directive on round-trip, and quietly reopens the
  self-service runtime authoring that ADR-0006 rejected for widening the trust
  surface.

## Implementation phases

1. Factor the schema + validation into the `orchestra-template-tools` package
   with a CLI; point `just validate-templates` and the platform's loader at it.
2. Create `orchestraplatform/workshop-templates`: move `jupyter.yaml` /
   `rstudio.yaml`, add the CI workflow (pip-install the validator from a pinned
   tag, run the CLI), `CODEOWNERS`, and the `$schema` wiring; mark it a GitHub
   template repository and enable branch protection on the fetched branch.
3. Replace the ConfigMap loader with the UPath-backed loader: cadence refresh,
   fsspec cache invalidation, `storage_options` token from a Secret, atomic
   validated swap, last-good retention.
4. Add `POST /admin/templates/reload` and `POST /admin/templates/validate`.
5. Wire readiness to "catalog loaded" and add the `stale`/`degraded` status;
   remove the chart `files/templates/` directory, the ConfigMap, and the
   `checksum/config` rolling-restart annotation.
6. Default `ORCHESTRA_TEMPLATE_SOURCE` to
   `github://orchestraplatform:workshop-templates@<release-tag>`; document the
   per-environment pin (tag in prod, `main` in dev).
