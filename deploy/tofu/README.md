# GKE Standard migration plan (OpenTofu) — proposed

**Status:** Proposed / not yet implemented. This directory currently holds only
the plan; the `.tf` manifests have not been written.

**Source:** design worked out in a Gemini session (2026-06-15,
`gemini.google.com/app/912dfa39b11aa614`). The original copy-paste agent prompt
is preserved verbatim in the appendix; the body below distills the decisions and
the operational details that came out of that conversation.

## Why: cost

Orchestra runs on **GKE Autopilot** today
(`gke_orchestraplatform-dev_us-central1_orchestra-dev`). Autopilot bills per pod
*request* at a premium per-unit rate; Standard bills for the raw VM. For a
1 vCPU / 3.5 GB pod + 10 GB disk in `us-central1` (on-demand):

| Mode | What's billed | ~Hourly |
| --- | --- | --- |
| Standard (`e2-medium`, 2 vCPU / 4 GB) | the whole VM | ~$0.035 |
| Autopilot (exactly 1 vCPU / 3.5 GB) | pod requests | ~$0.061 |

≈ **1.7–2× per workload** on Autopilot. Caveats that matter for us:

- **Cluster management fee** ($0.10/hr) is *waived for one zonal Standard
  cluster* but **always** charged on Autopilot.
- **Spot** VMs/pods cut compute **60–70%** (but see the interactive-app caveat
  below — spot preemption disconnects live sessions).
- **Utilization crossover:** Autopilot tends to be *cheaper below ~70% cluster
  utilization* (you pay for zero slack); Standard wins *above ~85% saturation*.
  Orchestra's workshop load is **bursty**, so the savings depend on keeping
  Standard nodes well-packed — which is exactly what `optimize-utilization` +
  scale-to-zero pools + balloon pods (below) are for. **Measure current
  Autopilot utilization before committing** so the move is actually a win.

## Decision: infrastructure autoscaling only (no pod HPA)

The operator/CRD already creates exactly one pod per workshop on demand, so we do
**not** need Layer-1 pod autoscaling (HPA/KEDA). We use **only Layer 2**: the GKE
Cluster Autoscaler provisions and consolidates *nodes* as the CRD's pods go
`Pending`. This reproduces today's Autopilot behavior on Standard's cheaper raw
VMs.

## Node provisioning: two options (decide before implementing)

**Method 1 — Static pools** (what the spec below encodes): pre-defined
small/large pools at `min=0`, with taints + labels the operator targets. Scales
up slightly faster (the pool framework already exists). Best when tenant shapes
fall into a few fixed buckets.

**Method 2 — Node Auto-Provisioning (NAP) + ComputeClass:** GKE builds
right-sized node pools on the fly from each pod's `requests` (Autopilot-like, at
Standard pricing). Adds ~30–45 s pool-creation latency on a cold shape. Best when
pods request **arbitrary** sizes.

> ⚠️ **Decision point for Orchestra:** workshop templates already accept
> **arbitrary** `cpu`/`memory` (the `resources` field), not just two tiers — so
> **NAP (Method 2) may fit better than two static pools.** The static-pool spec
> below assumes we bucket workshops into small/large. Choose based on how much we
> want to constrain template sizing. (Static pools + a tier field is simpler to
> reason about; NAP is more flexible and closer to today's Autopilot behavior.)

## Proposed cluster + pools (static-pool spec)

### Core GKE cluster
- **Mode:** GKE Standard (not Autopilot).
- **Region:** `us-central1` (regional control plane).
- **Network:** private cluster, public endpoint enabled.
- **Autoscaling profile:** `optimize-utilization` — aggressive bin-packing +
  faster scale-down of idle nodes. (Changeable live via
  `gcloud container clusters update --autoscaling-profile`.)

### Node pools (scale-to-zero)
| Pool | Machine type | min/max | Taint | Label |
| --- | --- | --- | --- | --- |
| `small-tenant-pool` | `e2-medium` (2 vCPU / 4 GB) | 0 / 50 | `tenant-size=small:NoSchedule` | `tenant-tier=small` |
| `large-tenant-pool` | `e2-standard-4` (4 vCPU / 16 GB) | 0 / 20 | `tenant-size=large:NoSchedule` | `tenant-tier=large` |

Common: **GKE Image Streaming** enabled (heavy RStudio/Jupyter images start
before they finish pulling) and **`pd-balanced`** 30 GB node root disk.

## Pre-warming (avoid the ~60–90 s node cold-boot)

A request → live pod has two latencies: **decision** (autoscaler noticing the
pending pod — fast, profile-tunable) and **provisioning** (VM boot + image pull —
60–90 s, the real bottleneck). Bypass the provisioning latency with warm capacity:

- **Balloon / pause pods** — `cluster-warmer` Deployment of
  `registry.k8s.io/pause:3.9` at a low `PriorityClass` (`cluster-balloon-priority`,
  value `-10`). They hold a warm node; a real workshop pod (priority 0) preempts a
  balloon → schedules **instantly** → the evicted balloon goes `Pending` and
  triggers a background node boot for the *next* user.
- **Image Streaming** on the pools (above).
- **Surge handling — maps directly to scheduled workshops.** Scale the buffer up
  before a cohort arrives (`kubectl scale deployment cluster-warmer --replicas=N`)
  and back down after. Automate with **pre-warm / cooldown CronJobs** (e.g. scale
  to 15 at 08:45, back to 1 at 09:30 on class days). The balloon's `requests`
  match the small-tenant shape (1 CPU / 3.5 GiB); change the shape with
  `kubectl apply` if workload sizes change.

## Interactive-app operational requirements (must pair with the migration)

`optimize-utilization` continuously consolidates nodes — on Standard that means
GKE will **migrate (destroy + recreate) running pods** to pack them tighter.
Kubernetes has no live migration, so for an RStudio/Jupyter session a migration =
**user disconnect + loss of in-memory state** (files on the PVC are safe; active
R/Python memory is wiped). To protect active sessions, the operator must stamp
each workshop pod with:

- **`cluster-autoscaler.kubernetes.io/safe-to-evict: "false"`** (annotation) —
  the autoscaler will never migrate the pod for consolidation. **Critical**:
  without it, `optimize-utilization` will disconnect live users. The node stays up
  until the CRD deletes the pod at session end.
- **`terminationGracePeriodSeconds: 120`** — let RStudio flush to its PVC on
  `SIGTERM` instead of being `SIGKILL`ed at 30 s.
- **Node scheduling** for the chosen pool: `nodeSelector` + matching
  `tolerations` (Method 1) or a compute-class selector (Method 2).
- *(Optional)* **`podAntiAffinity`** (`topologyKey: kubernetes.io/hostname`) if
  tenants must each get their own node for isolation — better isolation, but it
  defeats bin-packing and raises cost.

Cluster-level: configure **maintenance windows** so node upgrades/repairs (the
*other* forced-migration trigger) happen off-hours.

## Operator changes required (prerequisite — blocks the migration)

Today `operator/src/resources/deployment.py` builds a `V1PodSpec` with **none** of
the above (no `node_selector`, `tolerations`, `affinity`, no
`safe-to-evict`/grace-period). Before the tainted pools (or NAP) are usable the
operator must emit, per workshop pod: the scheduling fields for the chosen
method, the `safe-to-evict: "false"` annotation, and a longer grace period — plus
a way for a template to select its tier (Method 1) or compute class (Method 2).
Until then, pools would scale up but stay empty (pods land on a default pool).

## Deliverables (when implemented)
Modular OpenTofu: `providers.tf`, `main.tf`, `variables.tf`, `outputs.tf`,
`kubernetes.tf`. Variable-driven naming. Outputs for cluster name, endpoint, CA
certificate.

## Open questions / next steps
- **Method 1 (static pools) vs Method 2 (NAP)** given arbitrary template sizing.
- **System node pool** for the platform's own pods (api/operator/frontend/
  oauth2-proxy) vs running them on tenant pools — likely a small always-on pool.
- **Spot VMs?** Interactive sessions are *not* fault-tolerant — spot preemption
  disconnects users — so spot is risky for live workshops (maybe only a cheap,
  clearly-labeled tier).
- **Cutover:** stand up the Standard cluster alongside Autopilot, deploy via Helm
  + this tofu, validate, then switch the GKE LB / DNS; decommission Autopilot.

Sequence: (1) pick Method 1 vs 2; (2) write the `.tf`; (3) pair the operator
scheduling + `safe-to-evict` + grace-period change; (4) parallel stand-up,
validate, cut over; (5) confirm real-world cost vs Autopilot.

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
