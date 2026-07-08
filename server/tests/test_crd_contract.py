"""Contract tests: the CRD body built by _to_kubernetes_crd must satisfy the
Workshop CRD's openAPIV3Schema.  No cluster is required — the schema is read
directly from the Helm chart source.

If these tests break after a rename, add, or remove, update either the service
function or the CRD YAML (and re-run `helm upgrade` to apply the schema change).
"""

import pathlib

import yaml

from api.models.workshop import (
    WorkshopCreate,
    WorkshopIngress,
    WorkshopPhase,
    WorkshopStorage,
)
from api.services.workshop_cluster import (
    _from_kubernetes_crd,
    _to_kubernetes_crd,
)

_CRD_YAML = (
    pathlib.Path(__file__).parents[2]
    / "deploy"
    / "charts"
    / "orchestra-crds"
    / "templates"
    / "workshop-crd.yaml"
)


def _crd_spec_schema() -> dict:
    crd = yaml.safe_load(_CRD_YAML.read_text())
    return crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"]["spec"]


def _crd_status_schema() -> dict:
    crd = yaml.safe_load(_CRD_YAML.read_text())
    return crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"][
        "status"
    ]


def _minimal_workshop() -> WorkshopCreate:
    return WorkshopCreate(name="test-abc123")


def _full_workshop() -> WorkshopCreate:
    return WorkshopCreate(
        name="test-abc123",
        duration="2h",
        image="rocker/rstudio:4.3",
        env={"FOO": "bar"},
        args=["--ServerApp.token=''"],
        storage=WorkshopStorage(size="20Gi"),
        ingress=WorkshopIngress(host="test.orchestraplatform.org"),
    )


# ---------------------------------------------------------------------------
# Required-field contract
# ---------------------------------------------------------------------------


def test_required_spec_fields_present_minimal():
    """All CRD-required spec fields must be in the body for a minimal launch."""
    required = _crd_spec_schema().get("required", [])
    spec = _to_kubernetes_crd(_minimal_workshop(), "user@example.com", "default")[
        "spec"
    ]
    missing = [f for f in required if f not in spec]
    assert not missing, f"CRD body missing required spec fields: {missing}"


def test_required_spec_fields_present_full():
    """All CRD-required spec fields must be in the body for a fully-populated launch."""
    required = _crd_spec_schema().get("required", [])
    spec = _to_kubernetes_crd(_full_workshop(), "user@example.com", "default")["spec"]
    missing = [f for f in required if f not in spec]
    assert not missing, f"CRD body missing required spec fields: {missing}"


# ---------------------------------------------------------------------------
# No unknown fields (catches typos like ownerEmail vs owner)
# ---------------------------------------------------------------------------


def test_no_unknown_top_level_spec_fields():
    """Every key in spec must be declared in the CRD schema properties."""
    known = set(_crd_spec_schema().get("properties", {}).keys())
    spec = _to_kubernetes_crd(_full_workshop(), "user@example.com", "default")["spec"]
    unknown = set(spec.keys()) - known
    assert not unknown, f"CRD body contains fields not in schema: {unknown}"


# ---------------------------------------------------------------------------
# Value pass-through
# ---------------------------------------------------------------------------


def test_owner_email_is_passed_through():
    """The owner field in the CRD body must equal the email argument."""
    body = _to_kubernetes_crd(_minimal_workshop(), "alice@example.com", "default")
    assert body["spec"]["owner"] == "alice@example.com"


def test_namespace_in_metadata():
    """The namespace passed to _to_kubernetes_crd must appear in the CRD metadata."""
    body = _to_kubernetes_crd(_minimal_workshop(), "alice@example.com", "staging")
    assert body["metadata"]["namespace"] == "staging"


def test_port_default_passed_through():
    """A workshop with no explicit port defaults to 8787 in the CRD body."""
    spec = _to_kubernetes_crd(_minimal_workshop(), "alice@example.com", "default")[
        "spec"
    ]
    assert spec["port"] == 8787


def test_port_override_passed_through():
    """An explicit port (e.g. JupyterLab on 8888) is passed through to the CRD body."""
    workshop = WorkshopCreate(name="test-abc123", port=8888)
    spec = _to_kubernetes_crd(workshop, "alice@example.com", "default")["spec"]
    assert spec["port"] == 8888


def test_tier_default_passed_through():
    """A workshop with no explicit tier defaults to 'small' in the CRD body."""
    spec = _to_kubernetes_crd(_minimal_workshop(), "alice@example.com", "default")[
        "spec"
    ]
    assert spec["tier"] == "small"


def test_tier_override_passed_through():
    """An explicit tier is passed through to the CRD body."""
    workshop = WorkshopCreate(name="test-abc123", tier="large")
    spec = _to_kubernetes_crd(workshop, "alice@example.com", "default")["spec"]
    assert spec["tier"] == "large"


def test_env_and_args_omitted_when_empty():
    """Empty env/args must not appear in the CRD body (operator applies defaults)."""
    spec = _to_kubernetes_crd(_minimal_workshop(), "alice@example.com", "default")[
        "spec"
    ]
    assert "env" not in spec
    assert "args" not in spec


def test_env_and_args_passed_through():
    """Non-empty env/args are passed through to the CRD body verbatim."""
    workshop = WorkshopCreate(
        name="test-abc123",
        env={"DISABLE_AUTH": "false", "FOO": "bar"},
        args=["start-notebook.py", "--ServerApp.token=''"],
    )
    spec = _to_kubernetes_crd(workshop, "alice@example.com", "default")["spec"]
    assert spec["env"] == {"DISABLE_AUTH": "false", "FOO": "bar"}
    assert spec["args"] == ["start-notebook.py", "--ServerApp.token=''"]


# ---------------------------------------------------------------------------
# Phase enum consistency
# ---------------------------------------------------------------------------


def test_status_phase_enum_contains_starting():
    """The CRD status.phase enum should include 'Starting' (operator sets this phase
    while waiting for the pod to become ready).  If this fails, add Starting to the
    CRD's enum list in workshop-crd.yaml."""
    phases = _crd_status_schema()["properties"]["phase"]["enum"]
    assert "Starting" in phases, (
        f"CRD status.phase enum is missing 'Starting': {phases}\n"
        "Add it to deploy/charts/orchestra-crds/templates/workshop-crd.yaml"
    )


def _crd_with_phase(phase: str) -> dict:
    return {
        "metadata": {"name": "test-abc123", "namespace": "workshops"},
        "spec": {"name": "test-abc123"},
        "status": {"phase": phase},
    }


def test_from_crd_parses_starting_phase():
    """A CRD whose status.phase is 'Starting' must parse without raising.

    The operator emits this phase while waiting for the pod to become ready;
    if WorkshopPhase lacks the member the read path raises ValueError.
    """
    resp = _from_kubernetes_crd(_crd_with_phase("Starting"))
    assert resp.status is not None
    assert resp.status.phase is WorkshopPhase.STARTING


def test_terminated_is_a_valid_phase():
    """'Terminated' is the API's marker for a vanished CRD and must be a
    valid WorkshopPhase member."""
    assert WorkshopPhase("Terminated") is WorkshopPhase.TERMINATED


def test_from_crd_tolerates_unknown_phase():
    """An unknown phase (e.g. one a future operator adds) must not crash the
    read path; it falls back to Pending."""
    resp = _from_kubernetes_crd(_crd_with_phase("Hibernating"))
    assert resp.status is not None
    assert resp.status.phase is WorkshopPhase.PENDING


def test_phase_vocabulary_matches_crd():
    """The server's WorkshopPhase enum must equal the CRD's status.phase enum,
    plus the server-only synthetic Terminated (stamped by the API when the
    backing Workshop CRD has vanished — never written to a CRD)."""
    crd_phases = set(_crd_status_schema()["properties"]["phase"]["enum"])
    server_phases = {p.value for p in WorkshopPhase}
    assert crd_phases == server_phases - {WorkshopPhase.TERMINATED.value}
