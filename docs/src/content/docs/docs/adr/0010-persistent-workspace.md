---
title: "ADR-0010: Per-(user, workshop) persistent workspace"
description: Decision record — a durable /data volume scoped per user-and-workshop, backed by a ReadWriteOnce persistent disk the operator creates unowned and a reaper reclaims; gcsfuse is used only for read-only reference data.
---

**Status:** Accepted
**Date:** 2026-07-09

## Context

Workshop sessions are time-limited. Today the operator creates a `/data` PVC and
owner-references it to the `Workshop` CR, so Kubernetes GC deletes it when the
session expires — everything a participant saved is gone (the "save your work
before it expires" gotcha in the participant guide). We want **durable storage**
so a learner's work survives between sessions (day-to-day of a multi-day course,
revisiting next week), without persisting container config in ways that break
across heterogeneous images.

Two axes were open: **what the durable volume is keyed to**, and **what backs
it**. A gcsfuse spike (throwaway `orchestraplatform-dev` VM) measured the object
-store trade-off directly:

| Operation | Local pd-balanced | gcsfuse | penalty |
|---|---|---|---|
| seq write 512MB | 4.5s | 4.7s | ~same |
| seq read 512MB | 4.3s | 2.5s | *faster* |
| write 1000×8KB | 1.5s | 230s | **155×** |
| read 1000×8KB | 0.6s | 71s | **119×** |
| delete 1000 files | 0.03s | 50s | **1870×** |

gcsfuse is excellent for large sequential IO and pathological for many small
files (each op is a GCS object round-trip).

## Decision

A **per-(user, workshop) persistent workspace at `/data`**, seven linked
decisions:

**A. Scope: per (user, workshop).** The durable volume is keyed by
`(owner-hash, template-slug)`. Different workshops run concurrently (each has its
own disk); the same workshop relaunched by the same user reattaches the same
volume. Chosen over one cross-workshop volume per user because that would either
bleed one workshop's `/home` config into another or force a single global active
session; per-workshop keying makes concurrency and reattach trivial.

**B. Mount at `/data`; `/home` stays ephemeral.** Only `/data` persists.
Container config, package installs, and history in `/home` reset each session —
so a broken `/home` state can never lock a user out of a workshop, and the rule
for users is simply "keep what matters in `/data`."

**C. Backend: a ReadWriteOnce `pd-balanced` PVC — not gcsfuse.** A working
directory is inherently many small files (project files, package installs,
notebooks, SQLite); the 155–1870× small-file penalty makes gcsfuse unusable as a
writable workspace. The PVC also needs no Workload Identity, avoiding the
Cloud SQL-proxy blast radius (the proxy authenticates via node SA today).

**D. Lifecycle in the operator reconcile, PVC unowned.** `desired_children`
declares the PVC (`ws-<slug>-<hash>`, **no owner-reference**, so it survives the
CR); `OperatorCluster.apply()` creates it if absent and reattaches it if present.
This is the existing reconcile (the pure-desired / imperative-apply split, PR
#45) minus the owner-ref — no new CRD, and the server stays out of raw-PVC
management.

**E. Reclaim with an idle-TTL reaper.** Session end stamps the PVC with a
`last-used` annotation; a low-frequency operator sweep deletes PVCs idle past a
configurable TTL (~30 days) that aren't currently mounted. Bounds cost without a
per-user quota; the TTL is config like the tier map / grace period.

**F. Same-workshop-twice is a user choice.** Because the volume is RWO, a second
concurrent session of the *same* workshop can't attach it. Rather than block or
silently replace, the launch surfaces a choice: **Continue** (reconnect the live
session) or **Start fresh** (terminate it and relaunch — `/data` reattaches, so
saved work carries over; only ephemeral session state resets). The server
supports both paths; the frontend shows the dialog. Ephemeral templates are
unaffected (no shared volume).

**G. Opt-in at authoring time, per template.** The author declares
`storage.workspace.persist: per-user`; every launch of that workshop then
persists. Ephemeral is the default. The author knows whether a workshop benefits
better than an attendee does, and it avoids a "do you want persistence?" prompt a
learner could forget (losing work — the exact gotcha this solves).

**Behind a StorageBackend seam.** Templates declare storage *intent*
(`workspace: {size, persist}`, and later `reference: {source, mountPath}`); the
operator resolves it to volumes via swappable backends (`PersistentDisk`,
`GcsFuse`). Which backend a `persist: per-user` maps to is cluster config, like
the tier map — keeping the template cloud-neutral (ADR-0005).

## Consequences

- Durable `/data` survives session expiry; relaunching a workshop reattaches it.
- One component (the operator) owns the durable lifecycle via an unowned PVC plus
  a reaper — a lifecycle deliberately decoupled from the instance lifecycle.
- The launch path (server) and dashboard (frontend) gain the Continue / Start
  fresh choice — persistence reaches beyond the operator.
- Cost is bounded by the idle-TTL reaper; concurrency is limited only to
  same-workshop-twice (rare), not globally.
- gcsfuse is **not** used for writable per-user storage. It remains the backend
  for **read-only, author-supplied reference data** ([#81](https://github.com/orchestraplatform/orchestraplatform/issues/81)) —
  large sequential reads are its strong path — as a separate step that requires
  enabling Workload Identity on the cluster.

## Alternatives considered

- **gcsfuse for the writable workspace** — rejected by the benchmark (small-file
  penalty) and the WI enablement cost.
- **One cross-workshop volume per user** — rejected: `/home` config bleed across
  images, and a global single-active-session limit.
- **A dedicated `UserWorkspace` CRD + controller** — cleaner separation but heavy
  new machinery; revisit if retention/quota state grows complex.
- **Server-side PVC provisioning** — splits volume-building across server and
  operator; the operator is the natural k8s-object builder.
- **Never GC / manual cleanup** — unbounded cost; "temporary manual cleanup"
  tends to persist.
