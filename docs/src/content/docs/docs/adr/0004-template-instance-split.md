---
title: "ADR-0004: Split Workshop into Template and Instance"
description: Decision record — separating the reusable workshop definition from the running session lifecycle.
---

**Status:** Accepted  
**Date:** 2026-04-16

## Context

The original data model had a single "Workshop" concept that conflated two distinct
concerns:

1. **Configuration** — which image to run, what resources to allocate, how long to run for.
2. **Instance lifecycle** — which user launched it, what its URL is, when it expires.

This created practical problems:

- No reuse. Every launch required re-entering the same image, resource, and duration fields.
- No launch history. Once a session was deleted from Kubernetes, all record of it was gone.
- No utilization data. There was no way to answer "how many CPU-hours did users consume
  last month?" without scraping Prometheus or pod logs.
- No admin governance. Any user could launch any image with any resource spec.

## Decision

Split "Workshop" into two distinct entities:

**Workshop (template)** — a reusable configuration object owned and managed by admins.
Stored in Postgres as the `workshops` table. Contains image, resource defaults, default
duration, and a k8s-safe slug used to generate instance names. Not directly visible in
Kubernetes.

**WorkshopInstance** — a single running session launched from a template by a specific
user. Stored in Postgres as the `workshop_instances` table. The corresponding Kubernetes
resource is the existing `Workshop` CRD (kind stays `Workshop` to avoid disrupting
running clusters — it is an operator implementation detail). One `instance_events` row
is appended each time the instance phase changes, enabling utilization tracking.

The API surface reflects this split:

- `GET/POST/PUT/DELETE /templates/` — template CRUD (admin write, all-user read)
- `POST /templates/{id}/launch` — create an instance from a template
- `GET/DELETE /instances/` — instance lifecycle (owner or admin only)
- `GET /instances/{name}/utilization` — time-in-phase breakdown
- `GET /templates/{id}/stats` — aggregate stats across all launches (admin)

## Consequences

**Benefits**

- Users browse a curated catalogue of templates; they cannot specify arbitrary images
  or resource requests at launch time.
- Every session is recorded in Postgres regardless of whether the k8s CRD still exists.
- Utilization is derivable from `instance_events` without external metrics infrastructure.
- Admin audit trail: `created_by`, `launched_at`, `terminated_at`, `owner_email` are all
  first-class DB columns.

**Trade-offs**

- Postgres is now a required dependency for the API server (previously the API was
  stateless, delegating entirely to k8s).
- A brief window exists where the k8s CRD and DB record can be out of sync (eventual
  consistency via on-read sync). The sync daemon alternative was rejected as it adds
  operational complexity for marginal gain at current scale.
- The k8s CRD kind stays `Workshop` even though the API calls it `WorkshopInstance`.
  This naming gap is intentional to avoid a cluster migration; it will be resolved if
  the CRD is ever versioned.

## Alternatives Considered

**Keep the monolithic model, add annotations to the CRD.** Rejected: k8s annotations are
not queryable or aggregatable; utilization reporting would remain difficult.

**Use a dedicated metrics store (Prometheus + recording rules).** Rejected: adds two
services (Prometheus + Grafana or similar) to a deployment that is otherwise a single
Helm chart. Time-in-phase from an event log is sufficient for the current reporting
requirements.

**Allow ad-hoc launches (user specifies image/resources at launch time) alongside
template launches.** Rejected for this iteration; can be revisited once the template
catalogue is established and admins have confidence in the resource defaults.
