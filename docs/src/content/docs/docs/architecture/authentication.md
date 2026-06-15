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

## Per-pod workshop auth

Each workshop pod enforces owner-only access via the Orchestra **`orchestra-sidecar`**
(a small Go reverse proxy in `sidecar/src/main.go`) — **not** a per-pod
oauth2-proxy. The operator injects the sidecar as a second container in every
workshop Deployment alongside the app container.

How it fits together:

- The workshop **Service** exposes port `80` and maps it to `targetPort: 8080`
  — the sidecar's listen port. The sidecar then proxies to the app container on
  `localhost:<port>` (default `8787` for RStudio, `8888` for JupyterLab).
- On every request the sidecar compares the inbound `X-Auth-Request-Email`
  (set by the global ingress oauth2-proxy) against `ORCHESTRA_OWNER_EMAIL`
  (stamped from `spec.owner` on the Workshop CR). On a mismatch it returns
  **403 Forbidden**; only the owner reaches the app.
- The app container still runs with `DISABLE_AUTH=true` (an RStudio flag, a
  harmless no-op on other images). Auth is **not** absent — it is enforced one
  hop earlier by the sidecar, so the app itself does not need its own login.
- In dev mode (`ORCHESTRA_REQUIRE_AUTHENTICATION=false`) the sidecar logs but
  does not block, so the stack works without a proxy.
