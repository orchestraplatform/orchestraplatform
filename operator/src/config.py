"""Operator configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class OperatorSettings(BaseSettings):
    """All operator configuration, read from ORCHESTRA_* env vars.

    Production values come from the Helm chart (deploy/charts/orchestra).
    Local dev values come from the justfile (just dev-operator).
    """

    model_config = SettingsConfigDict(
        env_prefix="ORCHESTRA_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Ingress ───────────────────────────────────────────────────────────────
    # Base domain for workshop hostnames. Chart sets this to the cluster domain;
    # local dev overrides it to orchestra.localhost.
    base_domain: str = "orchestraplatform.org"

    # Traefik entry points for IngressRoute resources.
    # "websecure" (HTTPS, default) for production; "web" (HTTP) for local dev.
    ingress_entry_points: list[str] = ["websecure"]

    # Optional port suffix appended to workshop URLs (e.g. ":30080" for the
    # Traefik NodePort in local dev). Empty string means no suffix.
    ingress_port: str = ""

    # ── Authentication ────────────────────────────────────────────────────────
    # System-wide Traefik Middleware for ForwardAuth (format: "ns-name@kubernetescrd").
    # Set by the chart; empty in local dev (no auth proxy running).
    auth_middleware: str = ""

    # oauth2-proxy /oauth2/auth URL used when per-workshop Middleware CRDs are
    # created alongside each IngressRoute. Set by the chart in production.
    oauth2_proxy_auth_url: str = ""

    # ── Workshop defaults ─────────────────────────────────────────────────────
    default_workshop_image: str = "rocker/rstudio:latest"

    # ── Tenant node pools (ADR-0005) ──────────────────────────────────────────
    # When False (the default, and correct for GKE Autopilot / single-node dev),
    # the operator emits NO nodeSelector/tolerations and workshop pods schedule
    # anywhere. Flip to True only on a cluster that actually has the labelled,
    # tainted tenant pools (GKE Standard) — otherwise pods would stay Pending.
    tenant_pools_enabled: bool = False
    # Node label key the operator targets per tier; the tier value (small/large)
    # is the label value. Configurable so the scheme isn't GKE-specific.
    tenant_tier_label_key: str = "tenant-tier"
    # Taint key the tenant pools carry; the tier value is the taint value,
    # tolerated with effect NoSchedule.
    tenant_tier_taint_key: str = "tenant-size"

    # ── Sidecar ───────────────────────────────────────────────────────────────
    sidecar_image: str = "seandavi/orchestra-sidecar:latest"
    sidecar_pull_policy: str = "Always"


@lru_cache
def get_settings() -> OperatorSettings:
    """Return the cached operator settings."""
    return OperatorSettings()
