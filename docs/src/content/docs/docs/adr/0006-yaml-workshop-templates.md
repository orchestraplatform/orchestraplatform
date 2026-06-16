---
title: "ADR-0006: Git-managed YAML workshop templates"
description: Decision record — onboarding workshop templates as PR-reviewed YAML, with YAML as the source of truth instead of a database table.
---

**Status:** Accepted
**Date:** 2026-06-15

## Context

Per [ADR-0004](/docs/adr/0004-template-instance-split/), a **Template** is the
reusable, admin-owned definition (image, resources, duration, port, env, args,
storage) and a **Workshop** is the launched instance. Today templates are
created imperatively: an admin `POST`s to `/templates/` or fills the admin form,
and the template exists only as a row in the Postgres `workshops` table.

That model has gaps that matter as Orchestra moves to GKE Standard
([ADR-0005](/docs/adr/0005-gke-standard-tenant-pools/)) and serves community
workshops (BioC, CSHL):

- **No reproducibility.** A fresh cluster comes up with an *empty* catalog;
  templates live only in whatever database has been clicked into. The GKE
  Standard migration makes this concrete — standing up the new cluster would
  mean re-entering every template by hand.
- **No review gate.** A template is effectively "permission to run this image in
  our cluster," yet there is no diff, no approval step, no history.
- **No contribution path.** Workshop authors are researchers who already
  contribute a Docker image plus a little config via pull request. The imperative
  API/UI doesn't fit that workflow.

Options considered for the onboarding interface:

1. **Imperative API/UI (status quo)** — fast, no extra infra, but database-only:
   no history, no reproducibility, no review.
2. **Declarative YAML, PR-reviewed, admin-curated** — review gate, version
   history, reproducible catalogs; needs a way to load files into the platform.
3. **Self-service runtime authoring** — vetted authors create templates directly
   at runtime; requires an author role and stronger runtime validation, and
   widens the trust surface.

## Decision

Adopt **declarative, git-managed YAML templates** (Option 2). Concretely, five
linked decisions:

**A. Admin-curated via PR.** Canonical templates are YAML files in the repo.
Anyone — including community authors — opens a PR to add or change one; only
admins merge. The review gate is PR approval; no runtime self-service path is
built.

**B. YAML, not TOML.** A template is a friendly projection of the Workshop CRD
`spec`, and the entire surrounding stack (CRD, Helm values, manifests) is YAML.
The data is genuinely nested, with maps (`env`) and lists (`args`), which YAML
renders more readably than TOML's arrays-of-tables. TOML's momentum is in *flat
tool/project config* (`pyproject.toml`, `Cargo.toml`) — a different shape. YAML's
type-coercion footguns (the "Norway problem", unquoted version strings) are
neutralized by **hard schema validation in CI** plus a
`# yaml-language-server: $schema=` directive for in-editor checking.

**C. YAML is the source of truth; the templates table is dropped.** There is no
database-backed mutable template entity. The API loads YAML into an in-memory
registry at startup; `GET /templates` reads memory; launch resolves by slug.
Instances key on `template_slug` and carry a denormalized `resolved_spec`
snapshot so they are self-describing and do not depend on a template row —
implemented as the additive first step in the instance-stamping change
(`d4e5f6a7b8c9`). Per-template stats group by `template_slug`. A *derived/cached*
table (kept in sync from YAML) was rejected: a read-only, reconcile-on-deploy
table is a cache pretending to be a model, and caches drift.

**D. Stored as files, mounted via ConfigMap.** Templates live in the chart at
`deploy/charts/orchestra/files/templates/*.yaml` (inside the chart so Helm can
package them). The Helm chart renders them into a ConfigMap
(`.Files.Glob`) mounted into the API pod (e.g. `/etc/orchestra/templates/`),
read at startup. A `checksum/config` annotation on the API Deployment triggers a
rolling restart when template content changes on `helm upgrade`. Templates are
**not** baked into the container image (that would couple template edits to image
releases) and **not** fetched from a URL at runtime (that adds a boot-time
network dependency, auth, and caching for little gain at this scale). Because
there is no table, there is **no seed Job** — the API reads the mounted directory
directly.

**E. Templates declare a `tier`.** The template schema gains a `tier`
(`small`/`large`) field aligning with the ADR-0005 scheduling map, so onboarding
and node-pool targeting stay coherent.

## Consequences

**Positive:**

- Reproducible catalogs: templates ship with the chart/release and are present
  the moment the API pod is ready. The GKE Standard cluster comes up populated.
- A real review gate (PR approval) on "permission to run this image," plus git
  history, diffs, and room for comments/metadata the loader ignores.
- A contribution path that matches how the Bioconductor community already works.
- Fewer moving parts: no seed Job, no dual representation to keep in sync, and
  three fewer `selectinload(workshop)` joins now that instances are
  self-describing.
- Template edits are decoupled from image builds.

**Negative / trade-offs:**

- Changing a template now requires a PR plus `helm upgrade`, slower than a UI
  click — acceptable, even desirable, for a gate of this kind.
- The admin template UI becomes a read-only viewer (authoring moves to PRs).
- ConfigMaps cap at ~1 MiB. Dozens of small template YAMLs are far under that;
  the loader stays behind an interface so the source can later become an object
  store or git-sync sidecar if the catalog ever outgrows a ConfigMap.
- Historical instances are backfilled best-effort when the stamp columns are
  added (they reflect the template's *current* definition); new launches stamp
  the exact resolved spec.
- YAML's footguns demand disciplined CI schema validation — a hard dependency,
  not a nicety.

**Not chosen:**

- **Imperative-only (status quo)** — no reproducibility, history, or review.
- **Self-service runtime authoring** — widens the trust surface and needs more
  UI; revisit only if community demand appears.
- **Derived/cached table** — reintroduces a drift surface for no gain.
- **Image-baked or URL-fetched YAML** — couples to image releases / adds a
  runtime dependency, respectively.

## Implementation phases

1. **Done** — stamp `template_slug` / `template_name` / `resolved_spec` onto
   instances so they are self-describing (migration `d4e5f6a7b8c9`).
2. Add `tier` to the template schema (with the ADR-0005 operator work).
3. Define the YAML schema (Pydantic / JSON Schema), add the template files,
   and wire CI schema validation.
4. In-memory registry loader in the API reading the ConfigMap mount; point
   `GET /templates` and launch at it.
5. ConfigMap + mount + `checksum/config` rolling-restart in the Helm chart.
6. Drop the `workshops` table and the `workshop_id` FK (→ `template_slug`),
   migrate stats to slug, and make the admin template UI read-only.
