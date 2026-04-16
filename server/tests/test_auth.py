"""Tests for the oauth2-proxy header trust authentication dependency."""

import pytest
from fastapi.testclient import TestClient

from api.core.auth import CurrentUser, get_current_user
from api.core.config import Settings


@pytest.fixture
def raw_client(_mock_k8s_startup):
    """Test client with NO dependency override — exercises the real auth logic."""
    from main import app

    # Remove any override set by the shared `client` fixture
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def auth_settings_require():
    """Settings with require_authentication=True (production default)."""
    return Settings(
        require_authentication=True,
        trusted_auth_header="X-Auth-Request-Email",
        admin_emails=["admin@example.com"],
        dev_identity=None,
    )


@pytest.fixture
def auth_settings_dev():
    """Settings with require_authentication=False and dev_identity set."""
    return Settings(
        require_authentication=False,
        trusted_auth_header="X-Auth-Request-Email",
        admin_emails=["admin@example.com"],
        dev_identity="dev@orchestra.localhost",
    )


# ── get_current_user dependency unit tests ───────────────────────────────────

class TestGetCurrentUser:
    """Unit-test the get_current_user FastAPI dependency directly."""

    @pytest.mark.asyncio
    async def test_valid_header_returns_user(self, auth_settings_require):
        """Valid X-Auth-Request-Email header produces a CurrentUser."""
        from fastapi import Request
        from unittest.mock import MagicMock

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Auth-Request-Email": "alice@example.com"}

        user = await get_current_user(mock_request, auth_settings_require)

        assert user.email == "alice@example.com"
        assert user.is_admin is False

    @pytest.mark.asyncio
    async def test_admin_email_sets_is_admin(self, auth_settings_require):
        """An email in admin_emails gets is_admin=True."""
        from fastapi import Request
        from unittest.mock import MagicMock

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Auth-Request-Email": "admin@example.com"}

        user = await get_current_user(mock_request, auth_settings_require)

        assert user.is_admin is True

    @pytest.mark.asyncio
    async def test_missing_header_raises_401(self, auth_settings_require):
        """Missing header raises HTTP 401 when require_authentication=True."""
        from fastapi import HTTPException, Request
        from unittest.mock import MagicMock

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, auth_settings_require)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_dev_identity_bypasses_header(self, auth_settings_dev):
        """dev_identity is used when require_authentication=False, no header needed."""
        from fastapi import Request
        from unittest.mock import MagicMock

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}  # No auth header

        user = await get_current_user(mock_request, auth_settings_dev)

        assert user.email == "dev@orchestra.localhost"

    @pytest.mark.asyncio
    async def test_dev_identity_not_used_without_flag(self, auth_settings_require):
        """dev_identity is ignored when require_authentication=True."""
        from fastapi import HTTPException, Request
        from unittest.mock import MagicMock

        settings = Settings(
            require_authentication=True,
            dev_identity="dev@orchestra.localhost",
            trusted_auth_header="X-Auth-Request-Email",
        )
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, settings)

        assert exc_info.value.status_code == 401


# ── Integration: header-based auth through the real endpoint ─────────────────

class TestAuthEndpoints:
    def test_me_returns_identity(self, raw_client):
        """GET /auth/me returns the forwarded email."""
        response = raw_client.get(
            "/auth/me",
            headers={"X-Auth-Request-Email": "alice@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "alice@example.com"
        assert data["is_admin"] is False

    def test_me_without_header_returns_401(self, raw_client):
        """GET /auth/me without auth header returns 401."""
        response = raw_client.get("/auth/me")
        assert response.status_code == 401

    def test_auth_config_returns_oauth2_proxy_urls(self, raw_client):
        """GET /auth/auth-config returns the oauth2-proxy login/logout URLs."""
        # auth-config itself doesn't require auth
        response = raw_client.get(
            "/auth/auth-config",
            headers={"X-Auth-Request-Email": "alice@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["login_url"] == "/oauth2/start"
        assert data["logout_url"] == "/oauth2/sign_out"
        assert data["dev_mode"] is False

    def test_auth_config_reports_dev_mode(self, raw_client):
        """GET /auth/auth-config exposes whether dev identity auth bypass is active."""
        from main import app
        from api.core.config import get_settings

        app.dependency_overrides[get_settings] = lambda: Settings(
            require_authentication=False,
            trusted_auth_header="X-Auth-Request-Email",
            admin_emails=["dev@example.com"],
            dev_identity="dev@example.com",
        )
        try:
            response = raw_client.get("/auth/auth-config")
        finally:
            app.dependency_overrides.pop(get_settings, None)

        assert response.status_code == 200
        data = response.json()
        assert data["login_url"] == "/oauth2/start"
        assert data["logout_url"] == "/oauth2/sign_out"
        assert data["dev_mode"] is True
