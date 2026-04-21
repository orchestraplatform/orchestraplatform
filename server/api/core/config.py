"""Configuration settings for the Orchestra API."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_prefix="ORCHESTRA_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API settings
    app_name: str = "Orchestra API"
    version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # Kubernetes settings
    kubeconfig_path: str | None = None
    kube_context: str | None = None
    in_cluster: bool = False
    default_namespace: str = "default"

    # Workshop defaults
    default_workshop_image: str = "rocker/rstudio:latest"
    default_workshop_duration: str = "4h"
    default_cpu_limit: str = "1"
    default_memory_limit: str = "2Gi"
    default_cpu_request: str = "500m"
    default_memory_request: str = "1Gi"
    default_storage_size: str = "10Gi"

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "https://app.orchestraplatform.org",
    ]

    # Authentication
    # When True (default / production), all /workshops routes require a valid
    # X-Auth-Request-Email header forwarded by the oauth2-proxy ingress.
    require_authentication: bool = True

    # Name of the header that oauth2-proxy sets after a successful login.
    # Change only if you've configured a non-default header in your proxy.
    trusted_auth_header: str = "X-Auth-Request-Email"

    # Comma-separated list of email addresses that have admin privileges.
    # Admins can list/get/delete any workshop regardless of owner.
    admin_emails: list[str] = []

    # Dev identity: if set AND require_authentication=False, the API behaves as
    # if this email was forwarded by the proxy. Lets `just dev` work without
    # any proxy. Never set this in production.
    dev_identity: str | None = None

    # Database
    # Port 5433 is used locally to avoid conflict with a system Postgres on 5432.
    # Inside docker-compose the server connects to the postgres service directly on 5432.
    database_url: str = (
        "postgresql+asyncpg://orchestra:orchestra@localhost:5433/orchestra"
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


if __name__ == "__main__":
    settings = get_settings()
    print(f"Orchestra API Settings: {settings.model_dump()}")
