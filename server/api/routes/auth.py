"""Authentication routes for Orchestra API."""

from typing import Any

from fastapi import APIRouter, Depends

from api.core.auth import CurrentUser, get_current_user
from api.core.config import Settings, get_settings

router = APIRouter()


@router.get("/me", response_model=dict[str, Any])
async def get_current_user_info(current_user: CurrentUser = Depends(get_current_user)):
    """Return the identity of the currently authenticated user."""
    return {
        "email": current_user.email,
        "is_admin": current_user.is_admin,
    }


@router.get("/auth-config", response_model=dict[str, Any])
async def get_auth_config(settings: Settings = Depends(get_settings)):
    """Return auth endpoint URLs and mode flags for the frontend."""
    dev_mode = not settings.require_authentication and bool(settings.dev_identity)
    return {
        "login_url": "/oauth2/start",
        "logout_url": "/oauth2/sign_out",
        "dev_mode": dev_mode,
    }
