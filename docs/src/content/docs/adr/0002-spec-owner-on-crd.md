---
title: "ADR-0002: spec.owner on the Workshop CRD"
description: Decision record — how workshop ownership is modelled.
---

**Status:** Accepted  
**Date:** 2026-04-15

## Context

Workshop resources needed an ownership model so that users can only see and
manage their own workshops, and so the future per-pod oauth2-proxy sidecar
knows which email is allowed access to each workshop.

Options considered:

1. **`spec.owner` field on the CRD** — a required, immutable email field in
   the Workshop spec.
2. **Label/annotation only** — store `orchestra.io/owner=<encoded-email>` as
   a label; no CRD schema change.
3. **External database** — a Postgres/SQLite table relating users to workshops.

## Decision

**Option 1: `spec.owner` on the CRD**, supplemented by an `orchestra.io/owner-hash`
label for efficient server-side label selector filtering (label values can't
contain `@`).

## Consequences

**Positive:**
- `kubectl get workshops` shows owners; ownership is self-documenting.
- `spec.owner` is validated by the API server (email pattern) and marked
  immutable via a CEL rule (`self.owner == oldSelf.owner`). Ownership cannot
  drift after creation.
- The operator already needs to know the owner email to provision the per-pod
  oauth2-proxy sidecar (future work). Putting it on the CR is the natural home.
- No new persistence layer required; the Kubernetes API is the single source
  of truth.

**Negative/trade-offs:**
- Changing the CRD schema is a coordinated operation (upgrade `orchestra-crds`
  chart before `orchestra` chart).
- The label value is a SHA-256 prefix (not the email itself) which requires
  documentation. The original email is always in `spec.owner`.
- If requirements grow to include sharing (multiple owners) or group
  memberships, a DB will be needed. That migration path is left for a future
  ADR.

## Implementation notes

- API stamps `spec.owner` from `X-Auth-Request-Email` at create time;
  callers cannot set it via the request body.
- List filtering: `list_workshops(owner_email=email)` builds a label selector
  `orchestra.io/owner-hash=<hash>` and passes it to the k8s client.
- Get/delete: fetch the CR, compare `workshop.owner == current_user.email`;
  mismatches return `404` (no existence leak).
- Admins (configured via `ORCHESTRA_ADMIN_EMAILS`) bypass the filter entirely.
