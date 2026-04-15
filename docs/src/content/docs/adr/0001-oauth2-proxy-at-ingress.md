---
title: "ADR-0001: oauth2-proxy at the ingress"
description: Decision record — why Orchestra uses oauth2-proxy for control-plane auth.
---

**Status:** Accepted  
**Date:** 2026-04-15

## Context

The Orchestra API (`/workshops/*`) had no authentication — any caller could
create or delete workshops in any namespace. The API contained scaffolding for
self-issued JWTs (GitHub/Google OAuth exchange, `passlib`, `pyjwt`) but the
dependency was never applied to the workshop routes.

Options considered:

1. **Self-issued JWT** — API exchanges OAuth codes, mints its own JWTs, frontend
   stores and refreshes tokens.
2. **oauth2-proxy at the ingress** — A reverse proxy validates OIDC tokens and
   forwards `X-Auth-Request-Email` to the API.
3. **In-process OIDC verification** — API verifies Google ID tokens directly
   (no proxy, no self-issued JWT).

## Decision

**Option 2: oauth2-proxy at the ingress.**

## Consequences

**Positive:**
- The API validates one header (`X-Auth-Request-Email`), not a JWT. The
  security-critical token validation is handled by a battle-tested component.
- The existing JWT scaffolding (`passlib`, `pyjwt`, OAuth callback/refresh
  routes, `HTTPBearer`) can be removed, reducing custom security code by ~60%.
- No login UI in the frontend; the browser redirect flow is handled entirely
  by the proxy.
- Same component will protect workshop pods (per-pod sidecar model, future
  work), so the platform has a unified auth story.
- oauth2-proxy natively supports Google, GitHub, and any OIDC provider —
  switching or adding providers is a ConfigMap change.

**Negative/trade-offs:**
- An ingress and oauth2-proxy Deployment must be deployed for auth to work.
  Local dev requires either running the proxy or setting
  `ORCHESTRA_DEV_IDENTITY` + `ORCHESTRA_REQUIRE_AUTHENTICATION=false`.
- Non-browser clients (CLIs, scripts) must obtain a session cookie or go
  through the OAuth flow. This is acceptable for Orchestra's primary audience
  (interactive users), but would require further design for a headless CLI.

## Header trust boundary

To prevent callers from forging their identity by sending `X-Auth-Request-Email`
directly to the API, a Traefik `Middleware` strips those headers on ingress
before the proxy re-sets them on the forwarded request. See
`deploy/charts/orchestra/templates/oauth2proxy-config.yaml`.
