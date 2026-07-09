"""Contract tests: the shared WorkshopSpec model (orchestra-template-tools)
must match the Workshop CRD's openAPIV3Schema in the chart. Mirrors
server/tests/test_crd_contract.py — no cluster required, the schema is read
directly from the Helm chart source.

If these tests break after a CRD field rename/add/remove, update the shared
model in template-tools (and re-run `helm upgrade` to apply the schema change).
"""

import pathlib

import yaml
from orchestra_template_tools import (
    GROUP,
    KIND,
    PLURAL,
    VERSION,
    WorkshopIngress,
    WorkshopResources,
    WorkshopSpec,
    WorkshopStorage,
    WorkspaceStorage,
)

_CRD_YAML = (
    pathlib.Path(__file__).parents[2]
    / "deploy"
    / "charts"
    / "orchestra-crds"
    / "templates"
    / "workshop-crd.yaml"
)


def _crd() -> dict:
    return yaml.safe_load(_CRD_YAML.read_text())


def _spec_properties() -> dict:
    version = _crd()["spec"]["versions"][0]
    return version["schema"]["openAPIV3Schema"]["properties"]["spec"]["properties"]


# A spec exercising every field the CRD schema declares (asserted below).
FULL_SPEC = {
    "name": "rstudio-abc123",
    "templateSlug": "rstudio",
    "owner": "alice@example.com",
    "duration": "2h",
    "image": "rocker/rstudio:4.4",
    "port": 8888,
    "tier": "large",
    "env": {"FOO": "bar"},
    "args": ["--flag"],
    "resources": {
        "cpu": "2",
        "memory": "4Gi",
        "cpuRequest": "1",
        "memoryRequest": "2Gi",
        "ephemeralStorage": "9Gi",
        "ephemeralStorageRequest": "9Gi",
    },
    "storage": {
        "size": "20Gi",
        "storageClass": "fast",
        "workspace": {"persist": "per-user"},
    },
    "ingress": {"host": "abc.example.org", "annotations": {"a": "b"}},
}


def test_crd_identity_matches_chart():
    crd = _crd()
    assert crd["spec"]["group"] == GROUP
    assert crd["spec"]["names"]["plural"] == PLURAL
    assert crd["spec"]["names"]["kind"] == KIND
    assert crd["spec"]["versions"][0]["name"] == VERSION


def test_model_accepts_spec_with_every_schema_field():
    assert set(FULL_SPEC) == set(_spec_properties()), (
        "FULL_SPEC must exercise every schema field"
    )
    ws = WorkshopSpec.model_validate(FULL_SPEC)
    assert ws.owner == "alice@example.com"
    assert ws.template_slug == "rstudio"
    assert ws.resources.ephemeral_storage == "9Gi"
    assert ws.storage.storage_class == "fast"
    assert ws.storage.workspace.persist == "per-user"
    assert ws.ingress.host == "abc.example.org"


def _model_keys(model_cls) -> set[str]:
    """The wire-format (camelCase) field names of a pydantic model."""
    return {f.alias or name for name, f in model_cls.model_fields.items()}


def test_model_field_names_match_schema_properties():
    props = _spec_properties()
    assert _model_keys(WorkshopSpec) == set(props)
    assert _model_keys(WorkshopResources) == set(props["resources"]["properties"])
    assert _model_keys(WorkshopStorage) == set(props["storage"]["properties"])
    assert _model_keys(WorkspaceStorage) == set(
        props["storage"]["properties"]["workspace"]["properties"]
    )
    assert _model_keys(WorkshopIngress) == set(props["ingress"]["properties"])
