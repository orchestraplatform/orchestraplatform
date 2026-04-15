"""Authentication routes for Orchestra API."""

from typing import Any

from fastapi import APIRouter, Depends

from api.core.auth import CurrentUser, get_current_user

router = APIRouter()


@router.get("/me", response_model=dict[str, Any])
async def get_current_user_info(current_user: CurrentUser = Depends(get_current_user)):
    """Return the identity of the currently authenticated user."""
    return {
        "email": current_user.email,
        "is_admin": current_user.is_admin,
    }


@router.get("/auth-config", response_model=dict[str, Any])
async def get_auth_config():
    """Return auth endpoint URLs for the frontend.

    The frontend uses these to redirect unauthenticated users to the oauth2-proxy
    login page and to provide a logout link.
    """
    return {
        "login_url": "/oauth2/start",
        "logout_url": "/oauth2/sign_out",
    }
