---
title: "REST API"
description: Reference for the Orchestra REST API — live OpenAPI docs, the header-based auth model, and the main template and instance endpoints.
---

The Orchestra API is a FastAPI service that manages workshop **templates** and
running workshop **instances**. The frontend dashboard is just a client of this
API, and you can call it directly for scripting or automation.

## Live OpenAPI / Swagger docs

The API serves its own interactive, always-up-to-date spec. On the API host:

- **Swagger UI:** `https://app.<your-domain>/docs`
- **ReDoc:** `https://app.<your-domain>/redoc`
- **OpenAPI JSON:** `https://app.<your-domain>/openapi.json`

These are generated from the live code, so they are the **source of truth** for
exact request/response schemas, query parameters, and status codes. The table
below is a quick map; reach for `/docs` for the full detail.

## Authentication

Orchestra does not implement its own login. All authentication is handled by
**oauth2-proxy** at the ingress (see
[Authentication](../architecture/authentication) and
[ADR-0001](../adr/0001-authentication-architecture)). After a user logs in via
Google or GitHub, the proxy forwards every upstream request with a trusted
header:

```
X-Auth-Request-Email: alice@example.com
```

The API reads this header (configurable via `ORCHESTRA_TRUSTED_AUTH_HEADER`,
default `X-Auth-Request-Email`) and treats its value as the caller's identity. A
request that reaches the API without it gets **401 Unauthorized**.

Because the proxy terminates auth, you don't send a bearer token to the API —
you authenticate to oauth2-proxy (carrying its session cookie) and it injects
the header. The Traefik middleware **strips** any inbound `X-Auth-Request-*`
headers before re-setting them, so callers cannot forge an identity.

**Admin vs. regular users.** A caller is treated as an admin when their email is
in the server's `admin_emails` list. Admin-only routes return **403 Forbidden**
otherwise. Regular users see and act on only their own instances; admins see
all.

**Local development.** With `ORCHESTRA_REQUIRE_AUTHENTICATION=false` and
`ORCHESTRA_DEV_IDENTITY` set, the API short-circuits to that identity so you can
call it without a proxy. Never use this in production.

## Endpoints

All paths are relative to the API root. `{id}` is a template UUID; `{name}` is a
workshop instance's Kubernetes name.

### Identity

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/auth/me` | Identity of the current user (`email`, `is_admin`). |
| `GET` | `/auth/auth-config` | Login/logout URLs and dev-mode flag for the frontend. |

### Workshop templates

Templates are **git-managed YAML** served read-only (see [ADR-0006](/docs/adr/0006-yaml-workshop-templates/)).
There are no create/update/delete endpoints — edit the files under
`deploy/charts/orchestra/files/templates/` via a pull request. Template ids are
deterministic (derived from the slug).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/templates/` | List templates (paginated). `include_inactive` is admin-only. |
| `GET` | `/templates/{id}` | Get a template by ID. |
| `GET` | `/templates/stats` | Launch counts for all templates. |
| `GET` | `/templates/{id}/stats` | Launch/utilization stats for one template. **Admin.** |

### Launch & instance lifecycle

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/templates/{id}/launch` | Launch a new workshop instance from a template. Name is auto-generated as `{slug}-{suffix}`. |
| `GET` | `/instances/` | List running instances. Users see their own; admins see all. |
| `GET` | `/instances/{name}` | Get one instance, syncing live status from Kubernetes. |
| `GET` | `/instances/{name}/status` | Lightweight status and URL for an instance. |
| `GET` | `/instances/{name}/utilization` | Time-in-phase utilization breakdown. |
| `POST` | `/instances/{name}/extend` | Extend an instance's expiry (`extra_hours`, default +1h). |
| `DELETE` | `/instances/{name}` | Terminate an instance (deletes the CRD, marks the record terminated). |
| `GET` | `/instances/events` | Server-sent event stream of instance updates for the caller. |
| `GET` | `/instances/summary` | Aggregate launch counts (all-time and last 7 days). **Admin.** |

### Health

These are unauthenticated and intended for probes and uptime checks.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health/` | Basic health check. |
| `GET` | `/health/ready` | Readiness probe. |
| `GET` | `/health/live` | Liveness probe. |

## Source of truth

This page is a curated map of the main routes. The live spec at **`/docs`** (and
`/openapi.json`) is generated from the running code and always reflects the
current schemas, parameters, and response codes — defer to it when the two
disagree.
