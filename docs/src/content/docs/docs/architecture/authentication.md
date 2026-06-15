---
title: Authentication
description: How Orchestra authenticates users via oauth2-proxy and Google/GitHub OIDC.
---

Orchestra delegates all authentication to **oauth2-proxy**, which sits at the
ingress in front of both the frontend and the API server. Users never interact
with the Orchestra API directly — they log in once via Google (or GitHub), receive
a session cookie, and the proxy forwards their identity to the API on every
subsequent request.

## Login flow

```
Browser                  oauth2-proxy             Google OIDC         Orchestra API
   │                          │                        │                     │
   │── GET /dashboard ────────►│                        │                     │
   │   (no session cookie)    │                        │                     │
   │◄─ 302 /oauth2/start ─────│                        │                     │
   │                          │                        │                     │
   │── GET /oauth2/start ─────►│                        │                     │
   │◄─ 302 accounts.google.com/o/oauth2/auth ──────────│                     │
   │                          │                        │                     │
   │── User logs in ──────────────────────────────────►│                     │
   │◄─ 302 /oauth2/callback?code=... ─────────────────│                     │
   │                          │                        │                     │
   │── GET /oauth2/callback?code=... ────────────────►│                     │
   │                          │── exchange code ──────►│                     │
   │                          │◄─ ID token (email) ───│                     │
   │◄─ 302 /dashboard (Set-Cookie: _oauth2_proxy) ────│                     │
   │                          │                        │                     │
   │── GET /dashboard (cookie) ──────────────────────►│                     │
   │                          │── X-Auth-Request-Email: alice@example.com ──►│
   │                          │◄─────────────────────────────────── 200 OK ──│
   │◄─ 200 OK ────────────────│                        │                     │
```

## Header trust contract

After a successful login, oauth2-proxy forwards every request to the upstream
API with:

| Header | Value | Set by |
|---|---|---|
| `X-Auth-Request-Email` | Authenticated user's email | oauth2-proxy |
| `X-Auth-Request-User` | Username (provider-specific) | oauth2-proxy |

The Orchestra API reads `X-Auth-Request-Email` and uses it as the canonical
user identity. The header name is configurable via
`ORCHESTRA_TRUSTED_AUTH_HEADER` (default: `X-Auth-Request-Email`).

### Trust boundary

The Traefik `orchestra-auth-headers` Middleware **strips** any inbound
`X-Auth-Request-*` headers before oauth2-proxy validates the session. This
prevents a caller from forging their identity by sending the header directly.
The headers are re-set only after the proxy has validated the session cookie.

See `deploy/charts/orchestra/templates/oauth2proxy-config.yaml` for the
`Middleware` definition.

## Dev mode (no proxy)

For local development without a running proxy, set two environment variables:

```bash
ORCHESTRA_REQUIRE_AUTHENTICATION=false
ORCHESTRA_DEV_IDENTITY=dev@orchestra.localhost
```

When `require_authentication` is `False` **and** `dev_identity` is set, the
API short-circuits and uses `dev_identity` as the caller's email. No proxy is
needed. This is the default behaviour of `just dev`.

**Caution:** Never set `ORCHESTRA_DEV_IDENTITY` in production. The bypass only
activates when `ORCHESTRA_REQUIRE_AUTHENTICATION=false` is also set, but you
should avoid both settings in production regardless.

## Adding providers

oauth2-proxy supports Google, GitHub, and any OIDC-compliant provider. To
enable GitHub as a second provider alongside Google, see the
[oauth2-proxy setup guide](../deployment/oauth2-proxy).

## Future: per-pod workshop auth

Workshop pods currently run with `DISABLE_AUTH=true` (RStudio). The intended
model is for each pod to have an oauth2-proxy sidecar that restricts access
to the workshop owner's email (from `spec.owner` on the Workshop CR). This is
tracked as a follow-up; the `spec.owner` field on the CRD is already in place
to support it.
