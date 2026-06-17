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


def _make(resources=None, **kwargs):
    return create_rstudio_deployment(
        "test-ws",
        "default",
        "rocker/rstudio:latest",
        "user@example.com",
        resources=resources or {},
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


class TestResources:
    """The app container must carry ephemeral-storage requests/limits.

    GKE Autopilot defaults ephemeral-storage to 1Gi when unset, which Bioconductor
    sessions exceed and get evicted (incident 2026-06-16). The operator sets it
    explicitly, defaulting when the Workshop spec omits it.
    """

    def test_ephemeral_storage_defaults_applied(self):
        app = _app_container(_make(resources={}))
        assert app.resources.limits["ephemeral-storage"] == "8Gi"
        assert app.resources.requests["ephemeral-storage"] == "8Gi"

    def test_ephemeral_storage_from_spec(self):
        app = _app_container(
            _make(
                resources={
                    "ephemeralStorage": "16Gi",
                    "ephemeralStorageRequest": "8Gi",
                }
            )
        )
        assert app.resources.limits["ephemeral-storage"] == "16Gi"
        assert app.resources.requests["ephemeral-storage"] == "8Gi"

    def test_cpu_memory_still_wired(self):
        app = _app_container(
            _make(resources={"cpu": "4", "memory": "8Gi", "memoryRequest": "4Gi"})
        )
        assert app.resources.limits["cpu"] == "4"
        assert app.resources.limits["memory"] == "8Gi"
        assert app.resources.requests["memory"] == "4Gi"


class TestTierScheduling:
    """Tier maps to nodeSelector/tolerations ONLY when tenant pools are enabled.

    On GKE Autopilot / single-node dev the feature is off (the default), so pods
    must carry no scheduling constraints — otherwise they'd stay Pending.
    """

    def _pod_spec(self, deployment):
        return deployment.spec.template.spec

    def test_no_scheduling_by_default(self):
        """Tenant pools disabled (default): tier is ignored, no constraints."""
        pod = self._pod_spec(_make(tier="small"))
        assert pod.node_selector is None
        assert pod.tolerations is None

    def test_scheduling_emitted_when_enabled(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRA_TENANT_POOLS_ENABLED", "true")
        from config import get_settings

        get_settings.cache_clear()
        pod = self._pod_spec(_make(tier="large"))
        assert pod.node_selector == {"tenant-tier": "large"}
        assert len(pod.tolerations) == 1
        tol = pod.tolerations[0]
        assert tol.key == "tenant-size"
        assert tol.value == "large"
        assert tol.effect == "NoSchedule"

    def test_no_scheduling_when_enabled_but_no_tier(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRA_TENANT_POOLS_ENABLED", "true")
        from config import get_settings

        get_settings.cache_clear()
        pod = self._pod_spec(_make(tier=None))
        assert pod.node_selector is None
        assert pod.tolerations is None

    def test_label_and_taint_keys_are_configurable(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRA_TENANT_POOLS_ENABLED", "true")
        monkeypatch.setenv("ORCHESTRA_TENANT_TIER_LABEL_KEY", "pool")
        monkeypatch.setenv("ORCHESTRA_TENANT_TIER_TAINT_KEY", "dedicated")
        from config import get_settings

        get_settings.cache_clear()
        pod = self._pod_spec(_make(tier="small"))
        assert pod.node_selector == {"pool": "small"}
        assert pod.tolerations[0].key == "dedicated"
