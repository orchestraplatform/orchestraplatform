"""Contract tests: the CRD body built by _to_kubernetes_crd must satisfy the
Workshop CRD's openAPIV3Schema.  No cluster is required — the schema is read
directly from the Helm chart source.

If these tests break after a rename, add, or remove, update either the service
function or the CRD YAML (and re-run `helm upgrade` to apply the schema change).
"""

import pathlib

import pytest
import yaml

from api.models.workshop import WorkshopCreate, WorkshopIngress, WorkshopStorage
from api.services.workshop_instance_service import _to_kubernetes_crd

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
    return crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"]["status"]


def _minimal_workshop() -> WorkshopCreate:
    return WorkshopCreate(name="test-abc123")


def _full_workshop() -> WorkshopCreate:
    return WorkshopCreate(
        name="test-abc123",
        duration="2h",
        image="rocker/rstudio:4.3",
        storage=WorkshopStorage(size="20Gi"),
        ingress=WorkshopIngress(host="test.orchestraplatform.org"),
    )


# ---------------------------------------------------------------------------
# Required-field contract
# ---------------------------------------------------------------------------

def test_required_spec_fields_present_minimal():
    """All CRD-required spec fields must be in the body for a minimal launch."""
    required = _crd_spec_schema().get("required", [])
    spec = _to_kubernetes_crd(_minimal_workshop(), "user@example.com", "default")["spec"]
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
