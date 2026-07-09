"""Front-door size-preset expansion (ADR-0009)."""

import pytest
import yaml

from orchestra_template_tools import SIZE_NAMES, render_submission

BASE = {"name": "X", "slug": "x"}

# (size, expected tier, expected memory limit == request)
EXPECTED = [
    ("small", "small", "2Gi"),
    ("standard", "small", "4Gi"),
    ("large", "large", "8Gi"),
    ("xlarge", "large", "16Gi"),
]


def _resources(size: str) -> dict:
    result = render_submission({**BASE, "size": size})
    assert result.ok, result.errors
    doc = yaml.safe_load(result.yaml_text)
    return doc


def test_size_names_are_the_four_presets():
    assert SIZE_NAMES == ("small", "standard", "large", "xlarge")


@pytest.mark.parametrize("size,tier,memory", EXPECTED)
def test_size_expands_to_tier_and_resources(size, tier, memory):
    doc = _resources(size)
    assert doc["tier"] == tier
    res = doc["resources"]
    assert res["cpu"] == "2"
    assert res["cpuRequest"] == "500m"
    assert res["memory"] == memory
    assert res["memoryRequest"] == memory
    assert res["ephemeralStorage"] == "8Gi"
    assert res["ephemeralStorageRequest"] == "8Gi"


def test_size_takes_precedence_over_supplied_tier_and_resources():
    doc = _resources_with_overrides()
    assert doc["tier"] == "large"
    assert doc["resources"]["memory"] == "8Gi"


def _resources_with_overrides() -> dict:
    result = render_submission(
        {**BASE, "size": "large", "tier": "small", "resources": {"cpu": "99"}}
    )
    assert result.ok, result.errors
    return yaml.safe_load(result.yaml_text)


def test_unknown_size_is_field_error():
    result = render_submission({**BASE, "size": "gigantic"})
    assert not result.ok
    assert result.yaml_text is None
    assert len(result.errors) == 1
    assert result.errors[0].startswith("size:")
    assert "gigantic" in result.errors[0]


def test_size_omitted_uses_model_defaults():
    doc = yaml.safe_load(render_submission(BASE).yaml_text)
    assert doc["tier"] == "small"
    assert doc["resources"]["memory"] == "2Gi"  # WorkshopResources default
    assert "size" not in doc  # never a stored field
