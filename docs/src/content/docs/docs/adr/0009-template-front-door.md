---
title: "ADR-0009: Template submission front door"
description: Decision record — instructors submit workshop templates through a structured GitHub issue form that a bot converts into a validated pull request; git YAML stays the source of truth, and the DB-table and GUI alternatives were rejected.
---

**Status:** Accepted
**Date:** 2026-07-08

## Context

[ADR-0006](/docs/adr/0006-yaml-workshop-templates/) made workshop templates
git-managed YAML in the platform chart: PR-reviewed, schema-validated in CI,
loaded into an in-memory registry at startup. The templates *table* was
dropped; instances stamp a denormalized `resolved_spec` at launch so nothing
depends on a template row. [ADR-0007](/docs/adr/0007-external-template-repo/)
(external repo + runtime fetch) was deferred 2026-06-30 with fetch-on-startup
recorded as the escalation path.

Living with ADR-0006 surfaced two frictions:

1. **YAML is twitchy to author.** The `$schema` editor directive and CI
   annotations help people with a checkout, but community instructors
   (BioC, CSHL) — the authors ADR-0006's decision A explicitly anticipated —
   are being asked to fork, hand-indent YAML, and open a PR.
2. **Shipping a template requires a deploy.** A merged template reaches the
   cluster via `helm upgrade`, which meant CLI access or CI wiring. (In
   practice this is nearly solved: `deploy.yml` CD is fully written and only
   awaits GitHub environment configuration — variables, WIF secrets, and the
   values-secrets blob. Once set, merge = deployed, and a templates-only
   change redeploys nothing but a ConfigMap.)

Three alternatives were considered for fixing the authoring friction:

- **A structured GitHub issue whose contents are written directly to a
  database table** (with CI checks and optional human approval on the issue).
- **A GUI in the app** for admin/instructor template CRUD backed by the
  database.
- **A structured GitHub issue that a bot converts into an ordinary pull
  request** against the existing YAML files.

## Decision

**Keep ADR-0006 intact — git YAML remains the sole source of truth — and add
an issue-form → auto-PR front door for authoring.** Five linked decisions:

**A. The front door is a GitHub issue form.** Instructors fill a typed form
(no YAML): slug, name, description, image, port, tier, resource preset, env,
args, storage. A GitHub Action parses the submission, round-trips it through
the `orchestra-template-tools` models (the existing single source of truth
for the template schema), and reports validation errors as a comment on the
issue.

**B. The bot's output is a pull request, not a database write.** On
successful validation the Action opens a PR containing the generated YAML.
The slug decides create-vs-update: an existing file is rewritten (the PR
diff shows exactly what changed), a new slug adds a file. Deletion stays an
admin-only direct PR. Humans never hand-author template YAML again, but the
artifact under review is the same boring file ADR-0006 standardized.

**C. HITL approval is PR approval.** CODEOWNERS on
`deploy/charts/orchestra/files/templates/` (the platform admins) plus branch
protection make "merged = reviewed" an enforced invariant — strictly
stronger than label-based approval on an issue. The existing
`validate-templates.yml` CI gate runs on the bot's PR like any other.

**D. Compute is preset-constrained; workshop knowledge is free-form.** The
form's tier field is a dropdown of the names the operator tier map actually
resolves (`small`/`large`), and resources are a small set of named presets
aligned with what the tenant node pools can schedule (pool machine types,
the ephemeral-storage ceiling). `image`, `port`, `env`, and `args` are
free-form — that is instructor-owned knowledge. Exceptions go through an
admin editing the generated YAML in the bot's PR before merge, so the
ceiling is soft exactly where a human is already in the loop.

**E. Delivery is CD-on-merge; ADR-0007 stays the escalation path.**
Finishing `deploy.yml`'s GitHub environment configuration is sequenced
*before* the front door — without it, a merged template still needs a manual
deploy and the front door would feel broken on day one. If merge-to-live
latency (minutes) ever proves too slow in practice, the recorded escalation
is reviving ADR-0007's fetch-on-startup — not a database table.

## Alternatives considered

**Issue → database table (rejected).** Tempting because it makes template
changes deploy-free and CLI-free, but it silently supersedes ADR-0006's
decision C: the mutable DB template entity returns, and with it everything
the YAML move deliberately bought — git history as audit, `git revert` as
rollback, branch-protection-enforced review — now has to be rebuilt as
bespoke machinery. It also creates a write path from GitHub Actions into
Cloud SQL (credentials for a private production database living in CI) and
either a second source of truth beside the chart files or a registry rework.
The issue *form* is the valuable half of this idea; the DB write is the
expensive half. Taking the form and pointing it at a PR keeps the value and
discards the cost.

**GUI in the app (rejected for now).** The "runtime self-service path"
ADR-0006 explicitly declined to build. Most implementation work of the three
(forms, validation UX, authz, audit), reopens the source-of-truth question,
and serves a same-day-self-service need no current user has demonstrated.
Revisit via a new ADR if non-technical admins ever need it.

**ADR-0007 revival (rejected as premature).** Decouples templates from
deploys while keeping git, but was deferred twelve days ago with an explicit
revisit trigger — "the in-chart flow proves too slow" — that cannot have
fired before CD-on-merge has even been configured.

## Consequences

- Instructors get a form; admins get a reviewable YAML diff; the platform
  keeps one source of truth. Nothing about ADR-0006's load-bearing
  guarantees changes.
- New pieces to build and own: the issue form template, the parse/validate/
  auto-PR Action, and a small form-to-YAML entry point in
  `orchestra-template-tools`.
- Resource presets encode node-pool capacity in one reviewable place; when
  pools change (ADR-0005 evolution), the presets are part of that change's
  blast radius.
- Sequencing (decided with this ADR): (1) CD GitHub environment config,
  (2) front door + this ADR, (3) CI-gate work (frontend job, helm lint,
  sync-types drift, preflight dedup), (4) shared typed CRD contract module.
