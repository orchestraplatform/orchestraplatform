"""Tests for ingress resource creation and URL derivation."""

import os

import pytest

from resources.ingress import _default_entry_points, _default_host, create_workshop_ingress
from handlers.workshop import _ingress_url


class TestDefaultHost:
    def test_local_env_uses_local_domain(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRA_ENVIRONMENT", "local")
        monkeypatch.setenv("ORCHESTRA_LOCAL_DOMAIN", "orchestra.localhost")
        # Re-import to pick up env changes (module-level constants are set at import time)
        import importlib
        import resources.ingress as ingress_mod
        importlib.reload(ingress_mod)
        assert ingress_mod._default_host("my-workshop") == "my-workshop.orchestra.localhost"

    def test_prod_env_uses_prod_domain(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRA_ENVIRONMENT", "production")
        monkeypatch.setenv("ORCHESTRA_BASE_DOMAIN", "orchestraplatform.org")
        import importlib
        import resources.ingress as ingress_mod
        importlib.reload(ingress_mod)
        assert ingress_mod._default_host("my-workshop") == "my-workshop.orchestraplatform.org"


class TestDefaultEntryPoints:
    def test_local_env_returns_web(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRA_ENVIRONMENT", "local")
        import importlib
        import resources.ingress as ingress_mod
        importlib.reload(ingress_mod)
        assert ingress_mod._default_entry_points() == ["web"]

    def test_prod_env_returns_websecure(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRA_ENVIRONMENT", "production")
        import importlib
        import resources.ingress as ingress_mod
        importlib.reload(ingress_mod)
        assert ingress_mod._default_entry_points() == ["websecure"]


class TestCreateWorkshopIngress:
    def test_host_annotation_is_set(self):
        ingress = create_workshop_ingress("test-ws", "default", {})
        assert "orchestra.io/host" in ingress["metadata"]["annotations"]

    def test_explicit_host_wins_over_default(self):
        ingress = create_workshop_ingress(
            "test-ws", "default", {"host": "custom.example.com"}
        )
        assert ingress["metadata"]["annotations"]["orchestra.io/host"] == "custom.example.com"
        assert ingress["spec"]["routes"][0]["match"] == "Host(`custom.example.com`)"

    def test_explicit_entry_points_wins_over_default(self):
        ingress = create_workshop_ingress(
            "test-ws", "default", {"entryPoints": ["websecure"]}
        )
        assert ingress["spec"]["entryPoints"] == ["websecure"]

    def test_user_annotations_are_preserved(self):
        ingress = create_workshop_ingress(
            "test-ws", "default", {"annotations": {"traefik.io/foo": "bar"}}
        )
        assert ingress["metadata"]["annotations"]["traefik.io/foo"] == "bar"
        # orchestra.io/host must also be present
        assert "orchestra.io/host" in ingress["metadata"]["annotations"]

    def test_service_name_matches_workshop(self):
        ingress = create_workshop_ingress("my-ws", "default", {})
        assert ingress["spec"]["routes"][0]["services"][0]["name"] == "my-ws-service"

    def test_ingress_name_includes_workshop_name(self):
        ingress = create_workshop_ingress("my-ws", "ns1", {})
        assert ingress["metadata"]["name"] == "my-ws-ingress"
        assert ingress["metadata"]["namespace"] == "ns1"


class TestIngressUrl:
    def test_websecure_produces_https(self):
        ingress = {
            "spec": {"entryPoints": ["websecure"]},
            "metadata": {"annotations": {"orchestra.io/host": "ws.example.com"}},
        }
        assert _ingress_url(ingress) == "https://ws.example.com"

    def test_web_produces_http(self):
        ingress = {
            "spec": {"entryPoints": ["web"]},
            "metadata": {"annotations": {"orchestra.io/host": "ws.orchestra.localhost"}},
        }
        assert _ingress_url(ingress) == "http://ws.orchestra.localhost"

    def test_missing_entry_points_defaults_to_http(self):
        ingress = {
            "spec": {},
            "metadata": {"annotations": {"orchestra.io/host": "ws.example.com"}},
        }
        assert _ingress_url(ingress) == "http://ws.example.com"

    def test_round_trip_with_create_ingress(self, monkeypatch):
        """URL derived from a created ingress should match the host annotation."""
        monkeypatch.setenv("ORCHESTRA_ENVIRONMENT", "local")
        monkeypatch.setenv("ORCHESTRA_LOCAL_DOMAIN", "orchestra.localhost")
        import importlib
        import resources.ingress as ingress_mod
        importlib.reload(ingress_mod)

        ingress = ingress_mod.create_workshop_ingress("roundtrip", "default", {})
        url = _ingress_url(ingress)
        assert url == "http://roundtrip.orchestra.localhost"
