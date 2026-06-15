# GKE Standard migration plan (OpenTofu) — proposed

**Status:** Proposed / not yet implemented. This directory currently holds only
the plan; the `.tf` manifests have not been written.

## Why

Orchestra currently runs on a **GKE Autopilot** cluster
(`gke_orchestraplatform-dev_us-central1_orchestra-dev`). Autopilot bills per
pod request and works out to roughly **~2× the cost per vCPU / GB** compared to
running the same workloads on **GKE Standard** nodes. That's fine for light
usage, but for heavier / sustained workshop load it becomes a real cost problem.

The plan is to move to a **GKE Standard** cluster tuned for our workload: a
multi-tenant, interactive architecture that spins up stateful RStudio/JupyterLab
pods on demand via the Workshop CRD. Because the operator already handles pod
scheduling through the CRD, we do **not** want pod-level HPA — we want
responsive *infrastructure-level* autoscaling that provisions raw VMs on demand
and dense-packs them to minimize cost.

> Drafted from a design session with Gemini; the original prompt is preserved
> verbatim in the appendix below.

## Proposed design

### 1. Core GKE cluster
- **Mode:** GKE Standard (not Autopilot).
- **Region:** `us-central1` (regional control plane).
- **Network:** private cluster, public endpoint access enabled.
- **Autoscaling profile:** `optimize-utilization` globally — aggressive
  bin-packing and faster scale-down of idle nodes.

### 2. Node pools (static pools, scale-to-zero)
Two pools that scale to zero when idle, with taints + labels so the operator can
target them cleanly:

| Pool | Machine type | min/max | Taint | Label |
| --- | --- | --- | --- | --- |
| `small-tenant-pool` | `e2-medium` (2 vCPU / 4 GB) | 0 / 50 | `tenant-size=small:NoSchedule` | `tenant-tier=small` |
| `large-tenant-pool` | `e2-standard-4` (4 vCPU / 16 GB) | 0 / 20 | `tenant-size=large:NoSchedule` | `tenant-tier=large` |

Common to both pools: **GKE Image Streaming** enabled (faster container start),
and **balanced PD** (`pd-balanced`, 30 GB) for node root disk.

### 3. Pre-warming ("balloon" / hot-standby) — `kubernetes.tf`
So users don't wait for a ~90s node cold-boot:
- `PriorityClass` **`cluster-balloon-priority`**, value `-10`, `globalDefault: false`.
- `Deployment` **`cluster-warmer`** using a lightweight pause image
  (`registry.k8s.io/pause:3.9`), requests matching a small tenant (1 CPU /
  3.5 GiB), the balloon priority class, 1 replica by default.
- Tolerations + nodeSelector so the balloon pods land in `small-tenant-pool`.

The balloon pods hold a warm node; when a real (higher-priority) workshop pod
needs to schedule, the balloon is preempted and the cluster autoscaler has
already provisioned the node.

### 4. Deliverables (when implemented)
Modular OpenTofu: `providers.tf`, `main.tf`, `variables.tf`, `outputs.tf`,
`kubernetes.tf`. Variable-driven resource naming. Outputs for cluster name,
endpoint, and CA certificate.

## Dependency: operator must pin pods to the pools

⚠️ The tainted pools above only receive workshop pods if the pods carry matching
**tolerations** and a **nodeSelector**. As of this writing the operator does
**not** set any node scheduling on workshop pods
(`operator/src/resources/deployment.py` builds a `V1PodSpec` with no
`node_selector`, `tolerations`, or `affinity`). So this migration must be paired
with an operator change that emits, per workshop:

- `tolerations: [{ key: "tenant-size", value: <small|large>, effect: NoSchedule }]`
- `nodeSelector: { tenant-tier: <small|large> }`

and a way for a template to choose its tier (a new template field, or derived
from the requested resources). Until that ships, the pools would scale up but
stay empty (pods would land on a default pool instead).

Other open questions to resolve during implementation:
- A small **default/system node pool** (or Autopilot-style system handling) for
  the platform's own pods (api, operator, frontend, oauth2-proxy) vs. running
  them on the tenant pools.
- How the migration cuts over from the existing Autopilot cluster (new cluster +
  re-deploy via Helm, then DNS/LB switch) with minimal downtime.
- Tuning balloon replica count per pool against the cost of holding warm nodes.

## Next steps
1. Write the `.tf` manifests per the spec above.
2. Pair with the operator scheduling change (tolerations + nodeSelector + tier).
3. Stand up alongside the current Autopilot cluster, validate, then cut over.

---

## Appendix — original design prompt (verbatim)

> You are an expert platform engineer specializing in OpenTofu and Google Cloud Platform.
>
> I need you to write OpenTofu manifests to provision a production-ready GKE Standard cluster optimized for a multi-tenant, interactive architecture (e.g., spinning up stateful RStudio pods dynamically per tenant via a custom CRD).
>
> Our workload handles pod scheduling natively through our CRD, so we do NOT require Horizontal Pod Autoscaling (HPA) at the pod level. Instead, we need a highly responsive infrastructure-level autoscaling system that provisions raw VMs on-demand and dense-packs them efficiently to minimize costs.
>
> Please structure the OpenTofu code to meet the following specifications:
>
> #### 1. Core GKE Cluster Settings
> * **Mode:** GKE Standard (do not use Autopilot).
> * **Region:** us-central1 (regional control plane).
> * **Network Setup:** Private cluster configuration with public endpoint access enabled.
> * **Autoscaling Profile:** Set globally to `optimize-utilization` to ensure aggressive bin-packing and faster scale-down of idle compute.
>
> #### 2. Node Pool Strategies (Static Pools Method)
> Implement two separate node pools that scale to zero when inactive, configured with specific taints and labels so our CRD can target them cleanly:
>
> * **Pool A: `small-tenant-pool`**
>   * Machine Type: `e2-medium` (2 vCPUs, 4GB RAM)
>   * Autoscaling bounds: min = 0, max = 50 nodes.
>   * Node Taints: `tenant-size=small:NoSchedule`
>   * Node Labels: `tenant-tier=small`
>
> * **Pool B: `large-tenant-pool`**
>   * Machine Type: `e2-standard-4` (4 vCPUs, 16GB RAM)
>   * Autoscaling bounds: min = 0, max = 20 nodes.
>   * Node Taints: `tenant-size=large:NoSchedule`
>   * Node Labels: `tenant-tier=large`
>
> * **Common Node Pool Settings:** Enable **GKE Image Streaming** on both pools to optimize container startup latency, and use Balanced Persistent Disks (`pd-balanced`) at 30GB per node for root storage.
>
> #### 3. Cluster Pre-Warming Setup (Kubernetes Manifests)
> Include a separate OpenTofu file (using the `kubernetes` provider) to provision our "hot standby" balloon pod infrastructure. This ensures incoming users don't wait for a 90-second cold-boot:
> * Create a `PriorityClass` named `cluster-balloon-priority` with a value of `-10` (globalDefault = false).
> * Create a `Deployment` named `cluster-warmer` using a lightweight pause image (e.g., `registry.k8s.io/pause:3.9`).
> * The deployment should match the resource requests of our small tenant pool (1 CPU, 3.5GiB RAM), utilize the `cluster-balloon-priority` priority class, and default to 1 replica.
> * Add appropriate tolerations and node selectors to the deployment so these balloon pods sit cleanly inside the `small-tenant-pool`.
>
> #### 4. Deliverables
> * Provide clean, modular OpenTofu files (`providers.tf`, `main.tf`, `variables.tf`, `outputs.tf`, and `kubernetes.tf`).
> * Ensure all GCP resource names use standard naming conventions or variables.
> * Include outputs for the cluster name, endpoint, and CA certificate.
