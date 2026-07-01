---
title: "5. DNS cutover"
description: Point app, api, and the wildcard at the static IP — DNS-only, not proxied — then cut over from any old cluster and keep rollback trivial.
---

Step 5 of the [deployment sequence](/docs/deployment/overview/). With
[ingress, TLS & auth](/docs/deployment/ingress-tls-auth/) in place and serving on
the reserved static IP, this is the final networking step: point DNS at it.

## Records to set

All three [host types](/docs/deployment/overview/#the-three-host-types) resolve to
the **one static IP** you reserved for Traefik. Set three `A` records in your zone
(`<STATIC_IP>` is the reserved regional address):

| Type | Name | Value | Purpose |
| --- | --- | --- | --- |
| `A` | `app` | `<STATIC_IP>` | Dashboard (`app.<domain>`) |
| `A` | `api` | `<STATIC_IP>` | API (`api.<domain>`) |
| `A` | `*` | `<STATIC_IP>` | Per-session workshops (`*.<domain>`) |

Add the apex too if you use it.

:::caution[DNS-only, not proxied]
On Cloudflare, set each record to **DNS only (grey cloud)**, *not* proxied (orange
cloud). TLS must terminate at **Traefik** so the wildcard cert and per-session
routing work; a proxying CDN in front intercepts TLS and breaks both the DNS-01
challenge and Traefik's direct termination.
:::

Example (Cloudflare):

```
Type  Name  Content        Proxy
A     app   <STATIC_IP>    DNS only
A     api   <STATIC_IP>    DNS only
A     *     <STATIC_IP>    DNS only
```

## Parallel stand-up, then cut over

Because the static IP and cluster were stood up **alongside** any existing
(Autopilot) cluster, cutover is just moving these DNS records:

1. Validate the new cluster end-to-end while DNS still points at the old one (test
   via the raw IP / a temporary hostname).
2. Flip the `app`, `api`, and `*` records to `<STATIC_IP>`.
3. New sessions land on the new cluster; let existing time-limited sessions on the
   old cluster drain.
4. Keep the old cluster running until you're confident (a day of real workshops),
   then decommission it. If the old cluster was an out-of-band **Autopilot**
   cluster (created via `gcloud`/console, not Terraform), delete it the same way —
   there is no `tofu destroy` for it. Record final old-vs-new cost to confirm the
   savings.

## Rollback

Trivial: **repoint the DNS records back** to the old cluster's IP. Nothing about
standing up the new cluster disturbed the old one.

Next: [CI/CD](/docs/deployment/github-cicd/) to automate future deploys, and
[Troubleshooting](/docs/deployment/troubleshooting/) for the known failure modes.
