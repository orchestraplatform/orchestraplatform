"""Tests for workshop Deployment creation: env merging, args, and port wiring."""

import pytest

from resources.deployment import create_rstudio_deployment


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the lru_cache on get_settings between tests."""
    from config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _app_container(deployment):
    """Return the app (non-sidecar) container from a Deployment."""
    containers = deployment.spec.template.spec.containers
    return next(c for c in containers if c.name == "rstudio")


def _env_dict(container):
    return {e.name: e.value for e in (container.env or [])}


def _make(**kwargs):
    return create_rstudio_deployment(
        "test-ws",
        "default",
        "rocker/rstudio:latest",
        "user@example.com",
        resources={},
        storage={},
        **kwargs,
    )


class TestAppEnv:
    def test_defaults_applied_when_no_env(self):
        env = _env_dict(_app_container(_make()))
        assert env["DISABLE_AUTH"] == "true"
        assert env["ROOT"] == "true"

    def test_template_env_adds_new_var(self):
        env = _env_dict(_app_container(_make(env={"MY_VAR": "x"})))
        assert env["MY_VAR"] == "x"
        # defaults still present
        assert env["DISABLE_AUTH"] == "true"

    def test_template_env_overrides_default(self):
        env = _env_dict(_app_container(_make(env={"DISABLE_AUTH": "false"})))
        assert env["DISABLE_AUTH"] == "false"


class TestArgs:
    def test_args_default_to_none(self):
        assert _app_container(_make()).args is None

    def test_args_passed_through(self):
        args = ["start-notebook.py", "--ServerApp.token=''"]
        assert _app_container(_make(args=args)).args == args


class TestPortWiring:
    def test_app_and_sidecar_use_port(self):
        deployment = _make(port=8888)
        app = _app_container(deployment)
        assert app.ports[0].container_port == 8888
        sidecar = next(
            c
            for c in deployment.spec.template.spec.containers
            if c.name == "orchestra-sidecar"
        )
        target = {e.name: e.value for e in sidecar.env}["ORCHESTRA_TARGET_URL"]
        assert target == "http://localhost:8888"
