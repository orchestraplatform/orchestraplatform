"""Configuration settings for the Orchestra API."""

from functools import lru_cache
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for when pydantic-settings is not available
    class BaseSettings:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


class Settings(BaseSettings):
    """Application settings."""
    
    # API settings
    app_name: str = "Orchestra API"
    version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Kubernetes settings
    kubeconfig_path: Optional[str] = None
    in_cluster: bool = False
    
    # Workshop defaults
    default_workshop_image: str = "rocker/rstudio:latest"
    default_workshop_duration: str = "4h"
    default_cpu_limit: str = "1"
    default_memory_limit: str = "2Gi"
    default_cpu_request: str = "500m"
    default_memory_request: str = "1Gi"
    default_storage_size: str = "10Gi"
    
    # Security
    cors_origins: list = ["*"]
    
    # Authentication settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # OAuth settings
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    oauth_redirect_uri: str = "http://localhost:3000/auth/callback"
    oauth_provider: str = "github"  # github, google, oidc
    
    # OIDC settings (for institutional SSO)
    oidc_issuer: Optional[str] = None
    oidc_audience: Optional[str] = None
    
    # Workshop access control
    require_authentication: bool = True
    allow_anonymous_read: bool = False
    
    class Config:
        env_prefix = "ORCHESTRA_"
        case_sensitive = False
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

if __name__ == "__main__":
    settings = get_settings()
    print(f"Orchestra API Settings: {settings.model_dump()}")