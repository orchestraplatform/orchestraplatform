"""Tests for the in-memory template registry and source/guard dependencies."""

import uuid

import pytest
import yaml
from fastapi import HTTPException

from api.routes.templates import forbid_when_git_managed, get_template_reader
from api.services.template_registry import (
    TemplateRegistry,
    stable_template_id,
)
from api.services.workshop_template_service import WorkshopTemplateService

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
}
_RETIRED = {
    "name": "Old Jupyter",
    "slug": "jupyter-old",
    "image": "quay.io/jupyter/base-notebook:latest",
    "port": 8888,
    "enabled": False,
}


def _write(dirpath, name, data):
    (dirpath / name).write_text(yaml.safe_dump(data))


@pytest.fixture
def templates_dir(tmp_path):
    _write(tmp_path, "rstudio.yaml", _RSTUDIO)
    _write(tmp_path, "jupyter-old.yaml", _RETIRED)
    return tmp_path


class FakeSettings:
    def __init__(self, use_file_templates: bool):
        self.use_file_templates = use_file_templates


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

    def test_stable_id_is_deterministic(self):
        assert stable_template_id("rstudio") == stable_template_id("rstudio")
        assert stable_template_id("rstudio") != stable_template_id("jupyter")
        assert isinstance(stable_template_id("rstudio"), uuid.UUID)

    def test_missing_dir_yields_empty_registry(self, tmp_path):
        reg = TemplateRegistry.from_dir(tmp_path / "does-not-exist")
        assert reg._by_slug == {}


class TestSourceAndGuardDependencies:
    def test_reader_is_registry_in_file_mode(self, templates_dir):
        from api.services import template_registry

        # Seed the process-wide registry so get_registry() returns ours.
        reg = TemplateRegistry.from_dir(templates_dir)
        template_registry._registry = reg
        try:
            reader = get_template_reader(
                settings=FakeSettings(use_file_templates=True),
                svc=WorkshopTemplateService(),
            )
            assert reader is reg
        finally:
            template_registry.reset_registry()

    def test_reader_is_db_service_in_db_mode(self):
        svc = WorkshopTemplateService()
        reader = get_template_reader(
            settings=FakeSettings(use_file_templates=False), svc=svc
        )
        assert reader is svc

    def test_guard_blocks_in_file_mode(self):
        with pytest.raises(HTTPException) as exc:
            forbid_when_git_managed(settings=FakeSettings(use_file_templates=True))
        assert exc.value.status_code == 409

    def test_guard_allows_in_db_mode(self):
        assert (
            forbid_when_git_managed(settings=FakeSettings(use_file_templates=False))
            is None
        )
