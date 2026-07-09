# Orchestra Platform

Provisions isolated, time-limited workshop sessions (RStudio, Jupyter, …) on
Kubernetes for bioinformatics/data-science education. Single context; the
load-bearing decisions live in `docs/src/content/docs/docs/adr/`.

## Language

**Workshop template**:
A reusable, admin-curated workshop configuration, git-managed as YAML in the
platform chart (ADR-0006). Identified by slug.
_Avoid_: workshop (alone), template row

**WorkshopInstance**:
A single running, time-limited session launched from a Workshop template by a
specific user. Recorded in the database with a denormalized resolved spec.
_Avoid_: session, workshop, deployment

**Workshop CRD**:
The Kubernetes custom resource representing a WorkshopInstance inside the
cluster. Its kind stays `Workshop` for compatibility (ADR-0004); it is an
operator implementation detail, never shown to users.
_Avoid_: workshop resource, CR (unqualified)

**Launch**:
The act of creating a WorkshopInstance from a Workshop template: one Workshop
CRD in the cluster plus one instance record in the database.
_Avoid_: start, spawn, provision

**WorkshopCluster**:
The server's seam to the cluster for Workshop CRD lifecycle (create, get,
delete, set expiry). Two adapters: the real Kubernetes one and an in-memory
fake for tests. The CRD wire format is hidden behind it.
_Avoid_: k8s helpers, cluster client, kube service

**OperatorCluster**:
The operator's seam to the cluster for a Workshop's child resources (apply
children, read readiness, delete the Workshop CRD). Mirrors WorkshopCluster:
a real Kubernetes adapter and an in-memory fake for tests.
_Avoid_: k8s helpers, api clients

**Phase**:
The lifecycle state of a WorkshopInstance (Pending, Creating, Starting, Ready,
Running, Terminating, Failed; plus Terminated, a server-only synthetic phase
for instances whose Workshop CRD has vanished — contract-tested, never written
to a CRD).
_Avoid_: status (for the state value), state

**Template front door**:
The structured GitHub issue form through which instructors submit or update
Workshop templates. An Action auto-validates the submission and comments; a
maintainer applies the `approve` label and a GitHub App opens the pull
request with generated YAML (ADR-0009). Git remains the source of truth.
_Avoid_: template API, self-service portal, template upload

**Workshop size**:
A front-door input preset (Small / Standard / Large / X-Large) that bundles a
tenant tier and a curated cpu/memory/ephemeral profile aligned to what the node
pools can schedule. Chosen on the form and expanded to explicit resources in
the generated template YAML — it is not a stored template field.
_Avoid_: t-shirt size, resource class, flavor

**Tier map**:
Operator configuration mapping a template's tier name to node-targeting
constraints, keeping the operator cloud-neutral (ADR-0005).
_Avoid_: node pool config, scheduling map
