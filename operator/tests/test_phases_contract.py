"""Contract test: the operator's WorkshopPhase enum must equal the Workshop
CRD's status.phase enum. The CRD YAML in the chart is the shared artifact;
the server pins itself to the same file (server/tests/test_crd_contract.py),
so the two enums stay equal transitively."""

import pathlib

import yaml

from utils.phases import WorkshopPhase

_CRD_YAML = (
    pathlib.Path(__file__).parents[2]
    / "deploy"
    / "charts"
    / "orchestra-crds"
    / "templates"
    / "workshop-crd.yaml"
)


def test_operator_phase_vocabulary_matches_crd():
    crd = yaml.safe_load(_CRD_YAML.read_text())
    schema = crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]
    crd_phases = set(schema["properties"]["status"]["properties"]["phase"]["enum"])
    assert crd_phases == {p.value for p in WorkshopPhase}
