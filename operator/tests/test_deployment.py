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


def _enable_tier_map(monkeypatch, tier_map_json):
    """Set the ORCHESTRA_TIER_MAP env var and reset the settings cache."""
    monkeypatch.setenv("ORCHESTRA_TIER_MAP", tier_map_json)
    from config import get_settings

    get_settings.cache_clear()


# A representative GKE-style tier map: a `small` tier that only names a GKE
# ComputeClass, a `large` tier that uses a static tainted/labelled pool, and an
# empty `default` tier. All values are config strings — no GKE constants live in
# the operator code.
_TIER_MAP_JSON = (
    '{"small": {"computeClass": "tenant-compute"},'
    ' "large": {"nodeSelector": {"tenant-tier": "large"},'
    '           "tolerations": [{"key": "tenant-size", "value": "large",'
    '                            "effect": "NoSchedule"}]},'
    ' "default": {}}'
)


class TestTierScheduling:
    """A template selects a tier by name; the operator resolves it via the map.

    The map is config-driven (ORCHESTRA_TIER_MAP). An empty map (the default,
    correct for GKE Autopilot / single-node dev) emits no constraints so pods
    schedule anywhere. No GKE constants appear in operator code.
    """

    def _pod_spec(self, deployment):
        return deployment.spec.template.spec

    def test_no_scheduling_when_map_empty(self):
        """Empty tier map (default): the tier is ignored, no constraints."""
        pod = self._pod_spec(_make(tier="small"))
        assert pod.node_selector is None
        assert pod.tolerations is None

    def test_no_scheduling_for_none_tier(self, monkeypatch):
        _enable_tier_map(monkeypatch, _TIER_MAP_JSON)
        pod = self._pod_spec(_make(tier=None))
        assert pod.node_selector is None
        assert pod.tolerations is None

    def test_empty_named_tier_emits_nothing(self, monkeypatch):
        """A defined-but-empty tier (`default: {}`) schedules anywhere."""
        _enable_tier_map(monkeypatch, _TIER_MAP_JSON)
        pod = self._pod_spec(_make(tier="default"))
        assert pod.node_selector is None
        assert pod.tolerations is None

    def test_nodeselector_and_tolerations_tier(self, monkeypatch):
        _enable_tier_map(monkeypatch, _TIER_MAP_JSON)
        pod = self._pod_spec(_make(tier="large"))
        assert pod.node_selector == {"tenant-tier": "large"}
        assert len(pod.tolerations) == 1
        tol = pod.tolerations[0]
        assert tol.key == "tenant-size"
        assert tol.value == "large"
        assert tol.effect == "NoSchedule"
        assert tol.operator == "Equal"

    def test_compute_class_tier(self, monkeypatch):
        """A tier naming only a compute class emits the compute-class label."""
        _enable_tier_map(monkeypatch, _TIER_MAP_JSON)
        pod = self._pod_spec(_make(tier="small"))
        assert pod.node_selector == {"cloud.google.com/compute-class": "tenant-compute"}
        assert pod.tolerations is None

    def test_compute_class_label_key_is_configurable(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRA_COMPUTE_CLASS_LABEL_KEY", "compute.example/class")
        _enable_tier_map(monkeypatch, '{"small": {"computeClass": "tenant-compute"}}')
        pod = self._pod_spec(_make(tier="small"))
        assert pod.node_selector == {"compute.example/class": "tenant-compute"}

    def test_compute_class_merges_with_node_selector(self, monkeypatch):
        _enable_tier_map(
            monkeypatch,
            '{"big": {"nodeSelector": {"disk": "ssd"},'
            ' "computeClass": "tenant-compute"}}',
        )
        pod = self._pod_spec(_make(tier="big"))
        assert pod.node_selector == {
            "disk": "ssd",
            "cloud.google.com/compute-class": "tenant-compute",
        }

    def test_unknown_tier_falls_back_to_no_constraints(self, monkeypatch, caplog):
        """An unknown tier name schedules anywhere and logs a warning (safer
        than leaving the pod Pending on a bad nodeSelector)."""
        import logging

        _enable_tier_map(monkeypatch, _TIER_MAP_JSON)
        with caplog.at_level(logging.WARNING):
            pod = self._pod_spec(_make(tier="does-not-exist"))
        assert pod.node_selector is None
        assert pod.tolerations is None
        assert any("does-not-exist" in r.message for r in caplog.records)


class TestInteractiveSafety:
    """safe-to-evict + grace period are stamped on EVERY workshop pod, always."""

    def _template(self, deployment):
        return deployment.spec.template

    def test_safe_to_evict_annotation_always_present(self):
        tmpl = self._template(_make())
        assert (
            tmpl.metadata.annotations["cluster-autoscaler.kubernetes.io/safe-to-evict"]
            == "false"
        )

    def test_safe_to_evict_present_with_tier(self, monkeypatch):
        _enable_tier_map(monkeypatch, _TIER_MAP_JSON)
        tmpl = self._template(_make(tier="large"))
        assert (
            tmpl.metadata.annotations["cluster-autoscaler.kubernetes.io/safe-to-evict"]
            == "false"
        )

    def test_grace_period_defaults_to_120(self):
        tmpl = self._template(_make())
        assert tmpl.spec.termination_grace_period_seconds == 120

    def test_grace_period_is_configurable(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRA_TERMINATION_GRACE_PERIOD_SECONDS", "180")
        from config import get_settings

        get_settings.cache_clear()
        tmpl = self._template(_make())
        assert tmpl.spec.termination_grace_period_seconds == 180
