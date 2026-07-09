---
title: Introduction
description: Orientation for running your own Orchestra instance — what self-hosting involves and where to start.
---

You're in the **Running Orchestra** section: standing up and operating your own
Orchestra instance on Kubernetes. Most people don't need this — if you just want
to attend, contribute, or teach a workshop, use the hosted platform at
[orchestraplatform.org](https://orchestraplatform.org) and start from the
[documentation home](/docs/).

## What self-hosting gives you

A private Orchestra instance provisions isolated, time-limited workshop sessions
(RStudio, JupyterLab, or any container image) on demand, with sign-in and
automatic cleanup handled for you. You run it when you need your own cluster,
domain, catalog, or capacity controls rather than the shared hosted platform.

## What you operate

Orchestra is a monorepo with four components:

1. **Operator** — Kubernetes operator managing the Workshop CRD and session lifecycle.
2. **API server** — FastAPI backend for templates, instances, and auth helpers.
3. **Frontend** — React web dashboard.
4. **Sidecar** — per-pod auth/proxy fronting each session.

Sessions run in isolated namespaces, each reachable at its own subdomain. See the
[Platform Overview](/docs/architecture/platform-overview/) for how the pieces fit.

## Start here

- [Installation](/docs/getting-started/installation/) — quick-start an instance (local eval or Helm).
- [Deploying Orchestra](/docs/deployment/overview/) — the authoritative end-to-end operator runbook.
- [Contribute a workshop](/docs/contribute/overview/) — add a workshop to a catalog (hosted or your own).

Orchestra is open source; report issues, request features, or contribute on GitHub.
