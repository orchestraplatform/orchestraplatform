---
title: "Custom Resource Definitions"
description: Field reference for the Workshop CRD — the Kubernetes object that represents a single running workshop session.
---

Orchestra defines one Custom Resource Definition: `Workshop`
(`workshops.orchestra.io`, API version `v1`, scope `Namespaced`,
short name `ws`). A `Workshop` object is the **live runtime representation**
of a single workshop session. The operator watches these objects and
reconciles each one into a Deployment (app container + auth sidecar), a
Service, a PersistentVolumeClaim, and a Traefik `IngressRoute`.

## Where the CRD sits in the model

Orchestra splits the old monolithic "workshop" concept into a reusable
template and a running instance (see
[ADR-0004](/docs/adr/0004-template-instance-split/)):

```
Template (Postgres `workshops` table)
   └─ launch → WorkshopInstance (Postgres `workshop_instances` table)
                  └─ Workshop CRD (this page) → Deployment / Service / PVC / IngressRoute → pod
```

- A **Template** is an admin-curated configuration stored in Postgres. It is
  never visible in Kubernetes.
- Launching a template creates a **WorkshopInstance** DB row *and* a
  **Workshop CRD** in the cluster. The CRD kind stays `Workshop` (not
  `WorkshopInstance`) to avoid disrupting running clusters — the API layer
  calls it an instance, but the in-cluster object is a `Workshop`.
- The CRD is therefore the focus of this page: it is the object the operator
  acts on. The template's fields map almost one-to-one onto the CRD `spec`
  (`image`, `port`, `env`, `args`, `resources`, `storage`, `ingress`, and the
  template's `default_duration` → `spec.duration`); the template `slug` is
  used to generate the CRD `name`, and the launching user becomes
  `spec.owner`. See [Data Model](/docs/architecture/data-model/) for the
  database side.

## `spec` reference

Source of truth: `deploy/charts/orchestra-crds/templates/workshop-crd.yaml`.

| Field | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `name` | string | **yes** | — | Workshop instance name. Used as the base name for all child resources (`{name}-deployment`, `{name}-service`, `{name}-pvc`, `{name}-ingress`) and labels. |
| `owner` | string | **yes** | — | Email of the workshop owner, set by the API from the authenticated user. Validated against an email regex and **immutable once set** (enforced by a CEL validation rule). Passed to the auth sidecar as `ORCHESTRA_OWNER_EMAIL` so only the owner can reach the session. |
| `duration` | string | no | `"4h"` | Session lifetime (e.g. `4h`, `2h30m`, `90m`, `1d`). Parsed to compute `status.expiresAt`; the cleanup handler tears the workshop down when it expires. |
| `image` | string | no | `"rocker/rstudio:latest"` | Container image for the app. Any web app image works (RStudio, JupyterLab, …); the operator naming is RStudio-flavoured for historical reasons. |
| `port` | integer | no | `8787` | Port the app listens on **inside** the container (1–65535). The sidecar proxies to `localhost:{port}`. E.g. `8787` for RStudio, `8888` for JupyterLab. |
| `env` | map[string]string | no | — | Extra environment variables for the app container. **Merged over** the operator's default app env (`DISABLE_AUTH=true`, `ROOT=true`); template values win on name collision. |
| `args` | []string | no | — | Container args. When set, **replaces** the image's default CMD (e.g. JupyterLab launch flags). Leave unset to use the image default. |
| `resources` | object | no | see below | CPU/memory requests and limits for the app container. |
| `resources.cpu` | string | no | `"1"` | CPU **limit**. |
| `resources.memory` | string | no | `"2Gi"` | Memory **limit**. |
| `resources.cpuRequest` | string | no | `"500m"` | CPU **request**. |
| `resources.memoryRequest` | string | no | `"1Gi"` | Memory **request**. |
| `resources.ephemeralStorage` | string | no | `"8Gi"` | Ephemeral storage **limit** — the kubelet's eviction threshold for everything written outside the `/data` PVC (package installs, `/tmp`, container writable layer). GKE Autopilot defaults this to 1Gi when unset, which Bioconductor sessions exceed. |
| `resources.ephemeralStorageRequest` | string | no | `"8Gi"` | Ephemeral storage **request**. |
| `storage` | object | no | — | Persistent storage for the session. When present, a PVC is created and mounted at `/data`; omit the whole block for an ephemeral session. |
| `storage.size` | string | no | `"10Gi"` | Requested volume size (PVC access mode is `ReadWriteOnce`). |
| `storage.storageClass` | string | no | — | StorageClass name; unset uses the cluster default. |
| `ingress` | object | no | — | Ingress (Traefik `IngressRoute`) overrides. |
| `ingress.host` | string | no | `{name}.{base_domain}` | Hostname for the route. Defaults to the operator's configured base domain when unset. |
| `ingress.annotations` | map[string]string | no | — | Extra annotations placed on the generated `IngressRoute`. |

:::note
The CRD schema requires `owner`. The operator handler also accepts a legacy
`ownerEmail` key for backward compatibility (`spec.ownerEmail or spec.owner`),
but `owner` is the authoritative field defined in the schema and the one the
API writes.
:::

## `status`

`status` is written by the operator; do not set it by hand. Phase transitions
on the CRD drive the `instance_events` log on the API side.

| Field | Type | Meaning |
|---|---|---|
| `phase` | string (enum) | Lifecycle phase. One of `Pending`, `Creating`, `Starting`, `Ready`, `Running`, `Terminating`, `Failed`. The create handler sets `Starting` while the pod comes up and `Ready` once a replica is available; `Failed` on an unrecoverable error. |
| `url` | string | Public URL of the session, derived from the resolved ingress host and scheme. |
| `createdAt` | string (date-time) | Creation timestamp, taken from the object's `metadata.creationTimestamp`. |
| `expiresAt` | string (date-time) | When the session expires, computed from `spec.duration`. The cleanup handler uses this to tear the workshop down. |
| `conditions` | array | Standard-style condition entries, each with `type`, `status`, `reason`, `message`, and `lastTransitionTime`. The create handler emits a `Ready` condition (`True` on success, `False` with the failure reason otherwise). |

## Example manifest

A minimal Workshop only needs `name` and `owner`; everything else falls back
to the schema defaults shown above:

```yaml
apiVersion: orchestra.io/v1
kind: Workshop
metadata:
  name: bioc-intro-a1b2c3
  namespace: orchestra-workshops
spec:
  name: bioc-intro-a1b2c3
  owner: attendee@example.org
```

A fuller example overriding image, port, env, args, resources, storage, and
ingress — e.g. a JupyterLab session:

```yaml
apiVersion: orchestra.io/v1
kind: Workshop
metadata:
  name: jupyter-rnaseq-9f8e7d
  namespace: orchestra-workshops
spec:
  name: jupyter-rnaseq-9f8e7d
  owner: attendee@example.org
  duration: 2h30m
  image: jupyter/datascience-notebook:latest
  port: 8888
  env:
    JUPYTER_ENABLE_LAB: "yes"
  args:
    - start-notebook.sh
    - --NotebookApp.token=
  resources:
    cpu: "2"
    memory: 4Gi
    cpuRequest: "1"
    memoryRequest: 2Gi
    ephemeralStorage: 8Gi
    ephemeralStorageRequest: 8Gi
  storage:
    size: 20Gi
    storageClass: standard-rwo
  ingress:
    host: jupyter-rnaseq.workshops.example.org
    annotations:
      orchestra.io/course: rnaseq-2026
```

The operator reconciles this into a Deployment (app container on `port` plus
the Orchestra auth sidecar on `8080`), a Service, a PVC mounted at `/data`,
and a Traefik `IngressRoute` for `ingress.host`, then writes `status.url` and
`status.expiresAt` back to the object.
