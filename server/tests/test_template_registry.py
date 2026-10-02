"""Tests for the in-memory template registry and the reader dependency."""

import uuid
from datetime import UTC, date, datetime

import pytest
import yaml

from api.routes.templates import get_template_reader
from api.services.template_registry import (
    TemplateRegistry,
    stable_template_id,
)

_RSTUDIO = {
    "name": "RStudio",
    "slug": "rstudio",
    "image": "rocker/rstudio:4.4",
    "defaultDuration": "4h",
    "port": 8787,
    "tier": "small",
    "resources": {"cpu": "2", "memory": "4Gi"},
    "tags": ["rstudio"],
    "enabled": True,
    "createdAt": date(2026, 10, 2),
}
_RETIRED = {
    "name": "Old Jupyter",
    "slug": "jupyter-old",
    "image": "quay.io/jupyter/base-notebook:latest",
    "port": 8888,
    "enabled": False,
    "createdAt": date(2026, 10, 2),
}


def _write(dirpath, name, data):
    (dirpath / name).write_text(yaml.safe_dump(data))


@pytest.fixture
def templates_dir(tmp_path):
    _write(tmp_path, "rstudio.yaml", _RSTUDIO)
    _write(tmp_path, "jupyter-old.yaml", _RETIRED)
    return tmp_path


class TestRegistryLoading:
    @pytest.mark.asyncio
    async def test_loads_and_lists_active_only_by_default(self, templates_dir):
        reg = TemplateRegistry.from_dir(templates_dir)
        items, total = await reg.list_templates()
        assert total == 1
        assert [t.slug for t in items] == ["rstudio"]

    @pytest.mark.asyncio
    async def test_include_inactive_returns_all(self, templates_dir):
        reg = TemplateRegistry.from_dir(templates_dir)
        items, total = await reg.list_templates(include_inactive=True)
        assert total == 2
        assert {t.slug for t in items} == {"rstudio", "jupyter-old"}

    @pytest.mark.asyncio
    async def test_enabled_maps_to_is_active(self, templates_dir):
        reg = TemplateRegistry.from_dir(templates_dir)
        retired = await reg.get_template_by_slug(slug="jupyter-old")
        assert retired is not None
        assert retired.is_active is False

    @pytest.mark.asyncio
    async def test_get_by_stable_id(self, templates_dir):
        reg = TemplateRegistry.from_dir(templates_dir)
        tid = stable_template_id("rstudio")
        fetched = await reg.get_template(template_id=tid)
        assert fetched is not None
        assert fetched.slug == "rstudio"
        assert fetched.tier == "small"

    @pytest.mark.asyncio
    async def test_templates_may_share_created_at(self, templates_dir):
        # Both fixtures carry the same createdAt day (#147).
        reg = TemplateRegistry.from_dir(templates_dir)
        items, total = await reg.list_templates(include_inactive=True)
        assert total == 2
        assert {t.created_at for t in items} == {datetime(2026, 10, 2, tzinfo=UTC)}

    def test_stable_id_is_deterministic(self):
        assert stable_template_id("rstudio") == stable_template_id("rstudio")
        assert stable_template_id("rstudio") != stable_template_id("jupyter")
        assert isinstance(stable_template_id("rstudio"), uuid.UUID)

    def test_missing_dir_yields_empty_registry(self, tmp_path):
        reg = TemplateRegistry.from_dir(tmp_path / "does-not-exist")
        assert reg._by_slug == {}


class TestReaderDependency:
    def test_reader_returns_the_registry(self, templates_dir):
        from api.services import template_registry

        # Seed the process-wide registry so get_registry() returns ours.
        reg = TemplateRegistry.from_dir(templates_dir)
        template_registry._registry = reg
        try:
            assert get_template_reader() is reg
        finally:
            template_registry.reset_registry()
