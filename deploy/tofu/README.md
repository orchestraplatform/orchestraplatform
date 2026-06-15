# GKE Standard migration plan (OpenTofu) — proposed

**Status:** Proposed / not yet implemented. This directory holds the plan; no
`.tf` yet.

**Source:** design worked out in a Gemini session (2026-06-15,
`gemini.google.com/app/912dfa39b11aa614`) and refined in follow-up discussion.
The current target prompt is in the appendix; the original is preserved there too.

## Why: cost

Orchestra runs on **GKE Autopilot** today. Autopilot bills per pod *request* at a
premium per-unit rate; Standard bills for the raw VM. For a 1 vCPU / 3.5 GB pod +
10 GB disk in `us-central1` (on-demand):

| Mode | What's billed | ~Hourly |
| --- | --- | --- |
| Standard (`e2-medium`, 2 vCPU / 4 GB) | the whole VM | ~$0.035 |
| Autopilot (exactly 1 vCPU / 3.5 GB) | pod requests | ~$0.061 |

≈ **1.7–2× per workload** on Autopilot. Spot VMs cut compute 60–70% (but spot
preemption disconnects live sessions, so it's risky for interactive workloads).

**Utilization crossover:** Autopilot tends to be cheaper *below ~70%* cluster
utilization; Standard wins *above ~85%* saturation. The workload profile below is
what makes Standard the clear choice here.

### Workload profile (the deciding factor)
- Idle the vast majority of the time — only the operator/CRD and Traefik running.
- Bursty arrivals up to **~200–300 concurrent sessions**.
- Sessions are mostly idle even when active (RStudio/Jupyter open, not computing).
- We're willing to **oversubscribe CPU/memory**.

This is the textbook case for **Standard**:
- **Scale-to-zero when idle** → pay only for a small always-on system node + the
  (free, see below) control plane.
- **Overcommit** → on Standard you set `requests` near *idle* usage and bin-pack
  by requests, paying for VMs sized to the sum of requests rather than peak. On
  Autopilot you pay for requests regardless of actual use, so overcommit yields
  no savings (plus per-pod minimums + premium rates). This is why overcommit is
  "harder" on Autopilot — it doesn't reduce the bill.
  - **CPU:** overcommit aggressively — it's compressible (idle = unused, busy =
    throttled, nobody dies).
  - **Memory:** be conservative — RAM isn't compressible; over-packing risks
    **OOMKills** that disconnect sessions and lose in-memory state. Size memory
    requests near the realistic working set. (Standard's raw per-GB is still
    cheaper than Autopilot's, so you win on the memory you *do* provision.)

### Control plane (corrected)
The $0.10/hr (~$73/mo) cluster management fee and the GKE free-tier credit
(~$74.40/mo per billing account): the credit covers **Autopilot and *zonal*
Standard** clusters, but **not regional Standard**.

**We'll run a zonal cluster** (`us-central1-a`) — no HA is required — so the
control plane is **effectively free**, same as Autopilot. (Regional Standard
would have cost ~$73/mo; the earlier note claiming "Autopilot is never waived"
was backwards.) *Verify current GKE pricing/free-tier terms before relying on
this — they change.*

## Decision: infrastructure autoscaling only (no pod HPA)
The operator already creates exactly one pod per session on demand, so we use
**only** node-level autoscaling (Layer 2). No HPA/KEDA.

## Recommended approach: NAP + ComputeClass + system pool + balloons

Workshop templates accept **arbitrary** `cpu`/`memory`, so fixed small/large
static pools don't fit well. Use **Node Auto-Provisioning (NAP)** — GKE sizes
nodes to each pod's requests (Autopilot-like flexibility at Standard pricing).

The full hybrid:

1. **Manual always-on system pool** (small, e.g. `e2-standard-2`, min 1) for the
   platform's own pods (operator, API, frontend, Traefik, oauth2-proxy). Tainted
   so workshop pods never land there; keeps the cluster responsive while "idle."
2. **NAP + a `ComputeClass`** (prefer `e2`, fall back to `n2`) for the dynamic,
   arbitrary-shaped workshop pods. Workshop pods select the compute class.
3. **Balloon pods** for the bursty starts (below).

### NAP + balloons: the shape interaction
Balloons work under NAP, but a balloon only pre-warms the **shape it's sized
to** — NAP picks node shape from pod requests, so a warm node can only host an
incoming pod that *fits* on it.

> **Size each balloon's requests to at least the largest expected workshop pod.**
> That guarantees the warm node NAP holds is big enough to host *any* incoming
> session when the balloon is preempted. If a balloon were smaller than the pod,
> the pod couldn't use the warm node and would cold-boot anyway.

Trade-off: bigger balloons = a larger (more expensive) idle buffer; a small
session landing on a large warm node under-fills it until consolidation. If you
have a couple of common tiers, run a balloon Deployment per tier instead of one
big shape. **Bonus:** a balloon holding a node also keeps that shape's NAP pool
alive, so you skip NAP's ~30–45 s pool-creation latency for warmed shapes.

### Genuine NAP downsides (so nothing surprises us)
- ~30–45 s pool-creation latency for shapes *not* kept warm (long-tail sizes).
- Less control over node types — constrain with the ComputeClass.
- Balloon coverage is shape-specific (above).

None are dealbreakers; NAP's flexibility fits arbitrary template sizing.

## Pre-warming details
- **Balloon / pause pods** (`cluster-warmer`, `registry.k8s.io/pause:3.9`,
  PriorityClass `cluster-balloon-priority` = `-10`): a real session pod
  (priority 0) preempts a balloon → schedules instantly → the evicted balloon
  triggers a background node boot for the next user.
- **GKE Image Streaming** on all nodes so heavy RStudio/Jupyter images start
  before they finish pulling.
- **Surge handling (maps to scheduled workshops):** scale `cluster-warmer` up
  before a cohort (`kubectl scale deployment cluster-warmer --replicas=N`), back
  down after — manually or via pre-warm/cooldown CronJobs.

## Interactive-app operational requirements (operator-side, must pair with this)
`optimize-utilization` consolidates nodes by **migrating** running pods — which
for RStudio/Jupyter means a **user disconnect + loss of in-memory state** (PVC
files are safe). The operator must stamp each workshop pod with:
- **`cluster-autoscaler.kubernetes.io/safe-to-evict: "false"`** — never migrate a
  live session for consolidation. *Critical.*
- **`terminationGracePeriodSeconds: 120`** — flush to the PVC on `SIGTERM`.
- the **ComputeClass selector** (`cloud.google.com/compute-class: tenant-compute`).
- *(optional)* `podAntiAffinity` if tenants must each get a dedicated node.

Plus cluster-level **maintenance windows** so node upgrades happen off-hours.

### Operator change required (prerequisite — blocks the migration)
Today `operator/src/resources/deployment.py` sets none of the above. The
migration is blocked on an operator change that emits the compute-class selector,
the `safe-to-evict` annotation, and the longer grace period per workshop pod.

## Cluster specifics
- GKE Standard, **zonal** `us-central1-a` (no HA).
- Private cluster, public endpoint enabled.
- Autoscaling profile `optimize-utilization`.

## Alternative: static two-pool method
If we'd rather constrain templates to fixed tiers, the original design used two
scale-to-zero pools instead of NAP: `small-tenant-pool` (`e2-medium`, 0–50, taint
`tenant-size=small:NoSchedule`, label `tenant-tier=small`) and
`large-tenant-pool` (`e2-standard-4`, 0–20, `tenant-size=large`). Same image
streaming / `pd-balanced` / balloon / operator requirements apply. Kept as a
fallback; **NAP is the recommendation.**

## Deliverables (when implemented)
Modular OpenTofu: `providers.tf`, `main.tf` (cluster + NAP + system pool),
`variables.tf`, `outputs.tf`, `kubernetes.tf` (ComputeClass + PriorityClass +
balloon Deployment). Variable-driven naming. Outputs for cluster name, endpoint,
CA certificate.

## Open questions / next steps
- System pool sizing and taint/toleration wiring for platform components.
- Default NAP resource bounds (sized for ~300 sessions).
- Balloon shape(s) and baseline replica count; whether to add scheduled CronJobs.
- Spot: probably no (interactive ≠ fault-tolerant), or only a clearly-labeled tier.
- Cutover: stand up the zonal Standard cluster alongside Autopilot, deploy via
  Helm + this tofu, validate, switch the LB/DNS, decommission Autopilot.
- Measure current Autopilot utilization to confirm the savings.

Sequence: (1) write the `.tf`; (2) pair the operator scheduling +
`safe-to-evict` + grace-period change; (3) parallel stand-up, validate, cut over.

---

## Appendix — agent prompt (current target)

```markdown
You are an expert platform engineer specializing in OpenTofu and Google Cloud Platform.

Write OpenTofu manifests to provision a cost-optimized GKE Standard cluster for a multi-tenant, interactive workload: a Kubernetes operator (custom CRD) spins up one stateful pod per session (RStudio / JupyterLab) on demand. The cluster is idle the vast majority of the time (only the operator and Traefik running) and sees bursty arrivals of up to ~200–300 concurrent sessions. Pod scheduling is handled entirely by our operator — do NOT add pod-level HPA. We want responsive node-level autoscaling that bin-packs aggressively and scales unused compute to zero, and we are willing to oversubscribe CPU.

Specifications:

#### 1. Core cluster (GKE Standard, NOT Autopilot)
* Zonal control plane in us-central1-a (no HA required; zonal also qualifies for the free control-plane credit).
* Private cluster with public endpoint access enabled.
* Cluster autoscaling profile: `optimize-utilization` (aggressive bin-packing + fast scale-down).
* Release channel: regular (variable).

#### 2. Node provisioning — Node Auto-Provisioning (NAP), not static pools
* Enable NAP (`cluster_autoscaling { enabled = true }`) with global resource limits as variables (default sized for ~300 sessions, e.g. up to 400 vCPU / 1600 GB memory).
* `auto_provisioning_defaults`: `pd-balanced` 30GB disk; enable GKE Image Streaming; least-privilege OAuth scopes; Shielded Nodes; auto-repair and auto-upgrade.
* Provide a Kubernetes `ComputeClass` (kubernetes provider) named `tenant-compute` that prefers cost-optimized families (`e2`, fall back to `n2`) with `nodePoolAutoCreation.enabled = true`. Workshop pods select this class; NAP sizes nodes to their requests.

#### 3. Always-on system node pool (manual)
* A small manual node pool (`system-pool`, `e2-standard-2`, autoscaling min 1 / max 3) for the platform's own pods (operator, API, frontend, Traefik, oauth2-proxy).
* Taint it `dedicated=system:NoSchedule` and label it `pool=system` so workshop pods never land there; platform components tolerate the taint / select the label.
* Image streaming + `pd-balanced` 30GB here too.

#### 4. Pre-warming (balloon pods)
* `PriorityClass` `cluster-balloon-priority`, value `-10`, `globalDefault: false`.
* `Deployment` `cluster-warmer` using `registry.k8s.io/pause:3.9`, selecting the `tenant-compute` ComputeClass so balloons sit on NAP nodes (keeping that shape's pool warm).
* IMPORTANT: size the balloon's `resources.requests` to **at least the largest expected workshop pod** (variable; default e.g. 4 vCPU / 16 GiB) so the warm node NAP holds is large enough to host ANY incoming session when the balloon is preempted. Support a configurable shape / multiple balloon deployments if there are distinct common tiers.
* Replica count as a variable (default 1) so it can be scaled up before known surges.

#### 5. Deliverables
* Modular files: `providers.tf`, `main.tf` (cluster + NAP + system pool), `variables.tf`, `outputs.tf`, `kubernetes.tf` (ComputeClass + PriorityClass + balloon Deployment).
* Variable-driven names and knobs (zone, NAP bounds, balloon shape/replicas, system pool size).
* Outputs: cluster name, endpoint, CA certificate.

Out of scope for these manifests (handled by our operator, noted for context): each workshop pod carries the `tenant-compute` ComputeClass selector, the annotation `cluster-autoscaler.kubernetes.io/safe-to-evict: "false"` (so consolidation never disconnects a live session), and `terminationGracePeriodSeconds: 120`. Configure cluster maintenance windows for off-hours node upgrades.
```

<details>
<summary>Original prompt (superseded — static two-pool, regional)</summary>

```markdown
You are an expert platform engineer specializing in OpenTofu and Google Cloud Platform.

I need you to write OpenTofu manifests to provision a production-ready GKE Standard cluster optimized for a multi-tenant, interactive architecture (e.g., spinning up stateful RStudio pods dynamically per tenant via a custom CRD).

Our workload handles pod scheduling natively through our CRD, so we do NOT require Horizontal Pod Autoscaling (HPA) at the pod level. Instead, we need a highly responsive infrastructure-level autoscaling system that provisions raw VMs on-demand and dense-packs them efficiently to minimize costs.

Please structure the OpenTofu code to meet the following specifications:

#### 1. Core GKE Cluster Settings
* Mode: GKE Standard (do not use Autopilot).
* Region: us-central1 (regional control plane).
* Network Setup: Private cluster configuration with public endpoint access enabled.
* Autoscaling Profile: Set globally to `optimize-utilization` to ensure aggressive bin-packing and faster scale-down of idle compute.

#### 2. Node Pool Strategies (Static Pools Method)
Implement two separate node pools that scale to zero when inactive, configured with specific taints and labels so our CRD can target them cleanly:

* Pool A: `small-tenant-pool` — e2-medium (2 vCPUs, 4GB RAM); min = 0, max = 50; taint tenant-size=small:NoSchedule; label tenant-tier=small.
* Pool B: `large-tenant-pool` — e2-standard-4 (4 vCPUs, 16GB RAM); min = 0, max = 20; taint tenant-size=large:NoSchedule; label tenant-tier=large.
* Common: enable GKE Image Streaming on both pools; use Balanced Persistent Disks (pd-balanced) at 30GB per node.

#### 3. Cluster Pre-Warming Setup (Kubernetes Manifests)
* PriorityClass `cluster-balloon-priority`, value -10 (globalDefault = false).
* Deployment `cluster-warmer` using a lightweight pause image (registry.k8s.io/pause:3.9).
* Match the small tenant pool requests (1 CPU, 3.5GiB RAM), use the balloon priority class, default 1 replica.
* Tolerations + node selectors so the balloon pods sit inside the small-tenant-pool.

#### 4. Deliverables
* Modular OpenTofu files (providers.tf, main.tf, variables.tf, outputs.tf, kubernetes.tf).
* Standard naming conventions or variables.
* Outputs for cluster name, endpoint, and CA certificate.
```

</details>
