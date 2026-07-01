---
title: "7. Troubleshooting & gotchas"
description: The real GKE Standard deployment failure modes, each as symptom → cause → fix.
---

Step 7 of the [deployment sequence](/docs/deployment/overview/). These are the
failure modes that actually bit us bringing Orchestra up on GKE Standard. Each is
symptom → cause → fix.

## migrate-job ServiceAccount on fresh install

**Symptom.** On a first install the `orchestra-migrate-*` pre-install Job fails;
the Cloud SQL Auth Proxy sidecar logs an IAM/permission-denied error and the whole
`helm upgrade --install` never completes.

**Cause.** The migrate Job runs *before* the release's ServiceAccount has the
Workload Identity annotation (`iam.gke.io/gcp-service-account=...`), so the proxy
can't authenticate to Cloud SQL. On upgrades the annotation already exists, so it
only bites the very first install.

**Fix.** Pre-create the namespace and ServiceAccount, annotate it for Workload
Identity, and ensure the GCP SA has `roles/cloudsql.client` **before** the first
install — see
[Install: fresh-install ordering](/docs/deployment/install/#fresh-install-ordering-this-matters).
Then run `helm upgrade --install`.

## `uv` under readOnlyRootFilesystem

**Symptom.** The API (or migrate Job) crashes at startup with `uv` failing to
write — e.g. cannot create/write its cache, or a "read-only file system" error.

**Cause.** The API container runs with `readOnlyRootFilesystem: true`
(hardening), but `uv` wants to write a cache and sync state under `$HOME`/the
project dir.

**Fix.** Point `uv` at a writable `emptyDir` and disable its sync. The reference
`gcp-values.yaml` mounts an `emptyDir` at `/tmp` and sets `UV_CACHE_DIR=/tmp/uv-cache`;
add `UV_NO_SYNC=1` as well if a command triggers a sync:

```yaml
api:
  extraEnv:
    - name: UV_CACHE_DIR
      value: /tmp/uv-cache
    - name: UV_NO_SYNC
      value: "1"
  extraVolumes:
    - name: tmp
      emptyDir: {}
  extraVolumeMounts:
    - name: tmp
      mountPath: /tmp
```

## NAP disk too small for ephemeral request

**Symptom.** Workshop pods stay `Pending`; the NAP-provisioned tenant node reports
insufficient `ephemeral-storage`, or the pod is evicted under disk pressure.

**Cause.** The workshop templates request **8Gi ephemeral storage**, but the NAP
`auto_provisioning_defaults` boot disk defaults to **30 GB** — after the OS/image
and system reserve there isn't 8Gi of allocatable ephemeral storage, so the pod
can't fit.

**Fix.** Set `nap_boot_disk_size_gb = 50` (≥ the largest template's ephemeral
request plus headroom) in the cluster module. See
[Cluster setup: decisions](/docs/deployment/cluster-setup/#0-decisions-to-make-before-you-apply).

## requests exceed limits on GKE Standard

**Symptom.** oauth2-proxy (or the frontend) pod won't schedule / is rejected;
the API server complains that a container's resource **requests are greater than
its limits**.

**Cause.** Some chart defaults set `requests` higher than `limits`. **Autopilot
silently auto-fixes** this (it rewrites requests down to the minimum); **GKE
Standard rejects it** outright.

**Fix.** Set explicit `resources.requests ≤ resources.limits` for the affected
components in your values. A chart fix that normalizes this is landing separately.

```yaml
"oauth2-proxy":
  resources:
    requests: { cpu: 250m, memory: 512Mi }
    limits:   { cpu: 500m, memory: 512Mi }
```

## Private nodes need Cloud NAT

**Symptom.** With private nodes, image pulls fail and pods can't reach the
internet / ACME / Cloud SQL public IP; the cluster looks up but nothing egresses.

**Cause.** Private GKE nodes have no external IP, so they need a **Cloud NAT** for
egress. The reference deployment's **default VPC has no Cloud NAT**, so the cluster
uses **public nodes** (matching the Autopilot cluster).

**Fix.** Either use **public nodes** (the reference choice — set the module
accordingly), or provision a Cloud Router + Cloud NAT in the VPC first and then use
private nodes. See
[Cluster setup: decisions](/docs/deployment/cluster-setup/#0-decisions-to-make-before-you-apply).

## Namespace / secret adoption by Helm

**Symptom.** `helm upgrade --install` fails with `invalid ownership metadata` /
"exists and cannot be imported into the current release" for the namespace or a
Secret you pre-created.

**Cause.** Helm refuses to adopt a resource that lacks its ownership
label/annotations.

**Fix.** Add the Helm-ownership metadata to anything you pre-create:

```bash
kubectl label   namespace orchestra-system app.kubernetes.io/managed-by=Helm
kubectl annotate namespace orchestra-system \
  meta.helm.sh/release-name=orchestra \
  meta.helm.sh/release-namespace=orchestra-system
```

(Same pattern for a pre-created Secret.) See
[Install: fresh-install ordering](/docs/deployment/install/#fresh-install-ordering-this-matters).

## Workshop session shows the wrong / no certificate

**Symptom.** `app.<domain>` and `api.<domain>` are fine over HTTPS, but a
per-session `<session>.<domain>` URL serves a default/self-signed cert or a TLS
error.

**Cause.** Per-session `IngressRoute`s carry **no explicit TLS secret** and rely on
Traefik's **default `TLSStore`**. Traefik serves the default store's cert only from
a secret in its **own** namespace, so the wildcard must exist in `traefik`.

**Fix.** Issue a copy of the wildcard into the `traefik` namespace and point
`TLSStore/default` at it — see
[Ingress, TLS & auth: default TLSStore](/docs/deployment/ingress-tls-auth/#4-wire-traefiks-default-tlsstore-for-per-session-routes).

## See also

- [oauth2-proxy troubleshooting](/docs/deployment/oauth2-proxy/#troubleshooting) —
  403-after-login, redirect loops, API 401s.
- [GCP Autopilot notes](/docs/deployment/gcp/#autopilot-specific-notes) — the
  Autopilot-specific minimums (legacy path).
