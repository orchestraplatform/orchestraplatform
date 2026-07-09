"""Operator configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TierScheduling(BaseModel):
    """Scheduling constraints for one tenant tier (ADR-0005).

    All fields are optional and default to "no constraint", so an empty entry
    (``{}``) schedules pods anywhere. Every value is an operator-config-supplied
    string — there are no cloud-specific constants here, which preserves
    cloud-neutrality (GKE / EKS / AKS / kind each supply their own values; the
    GKE production instance is just one instance of this config).

    - ``node_selector``: plain ``nodeSelector`` labels (e.g. ``{tenant-tier: small}``).
    - ``tolerations``: taints the tier's pool carries, as ``key`` / ``value`` /
      ``effect`` dicts (``operator`` defaults to ``Equal``).
    - ``compute_class``: convenience for a single scheduling label such as GKE's
      ``cloud.google.com/compute-class: tenant-compute`` (NAP ComputeClass). It
      is merged into ``node_selector`` under ``compute_class_label_key``; kept
      separate only so a tier can name its compute class without repeating the
      label key. Both the key and the value come from config, so this stays
      generic.
    """

    model_config = ConfigDict(populate_by_name=True)

    node_selector: dict[str, str] = Field(default_factory=dict, alias="nodeSelector")
    tolerations: list[dict[str, str]] = Field(default_factory=list)
    compute_class: str = Field(default="", alias="computeClass")


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

    # ── Tenant tier scheduling (ADR-0005) ─────────────────────────────────────
    # Config-driven tier map: tier name -> scheduling constraints. A template
    # (or Workshop CRD) selects a tier *by name*; the operator looks the name up
    # here and stamps the pod's nodeSelector / tolerations / compute-class label.
    #
    # Default is EMPTY, which is correct for GKE Autopilot and single-node dev
    # (kind, minikube): every tier resolves to "no constraints", so pods schedule
    # anywhere with zero config. The GKE Standard production instance sets this
    # via the Helm chart (see values.yaml `operator.tierMap`).
    #
    # Supplied as JSON in ORCHESTRA_TIER_MAP, e.g.:
    #   {"small": {"computeClass": "tenant-compute"},
    #    "large": {"nodeSelector": {"tenant-tier": "large"},
    #              "tolerations": [{"key": "tenant-size", "value": "large",
    #                               "effect": "NoSchedule"}]}}
    tier_map: dict[str, TierScheduling] = Field(default_factory=dict)

    # Label key used to emit a tier's ``compute_class`` value. Configurable so the
    # compute-class concept isn't GKE-specific; the GKE value is the default
    # because it's the documented ComputeClass selector.
    compute_class_label_key: str = "cloud.google.com/compute-class"

    # ── Interactive-session safety (ADR-0005 / tofu README) ───────────────────
    # Workshop pods are always interactive, so these are stamped on EVERY pod
    # regardless of tier:
    #   * annotation cluster-autoscaler.kubernetes.io/safe-to-evict=false — never
    #     migrate a live session for bin-packing consolidation (loses in-memory
    #     state / disconnects the user). CRITICAL; not configurable.
    #   * terminationGracePeriodSeconds — time to flush to the PVC on SIGTERM.
    #     Configurable, default 120s per the tofu README.
    termination_grace_period_seconds: int = 120

    # ── Persistent workspace reclamation (ADR-0010 decision E) ────────────────
    # A persistent workspace PVC is deliberately unowned so it survives Workshop
    # CR deletion; the operator's low-frequency sweep deletes it once its
    # last-used annotation is older than this many days (and it isn't mounted).
    # Set via ORCHESTRA_WORKSPACE_IDLE_TTL_DAYS / chart workspaceIdleTtlDays.
    workspace_idle_ttl_days: int = 30

    # ── Sidecar ───────────────────────────────────────────────────────────────
    sidecar_image: str = "seandavi/orchestra-sidecar:latest"
    sidecar_pull_policy: str = "Always"


@lru_cache
def get_settings() -> OperatorSettings:
    """Return the cached operator settings."""
    return OperatorSettings()
