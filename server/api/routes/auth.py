"""Authentication routes for Orchestra API."""

from datetime import timedelta
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from api.core.auth import (
    create_access_token, 
    create_refresh_token,
    verify_token,
    OAuthProvider,
    get_current_user,
    TokenData
)
from api.core.config import get_settings

router = APIRouter()
settings = get_settings()


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request model."""
    code: str
    state: str = None


@router.post("/oauth/callback", response_model=TokenResponse)
async def oauth_callback(request: OAuthCallbackRequest):
    """Handle OAuth callback and exchange code for tokens."""
    try:
        # Exchange authorization code for access token
        token_data = await OAuthProvider.exchange_code_for_token(request.code)
        
        if "access_token" not in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token from OAuth provider"
            )
        
        # Get user information from OAuth provider
        user_info = await OAuthProvider.get_user_info(token_data["access_token"])
        
        # Create internal JWT tokens
        token_payload = {
            "sub": user_info.get("login") or user_info.get("email"),
            "user_id": str(user_info.get("id")),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "avatar_url": user_info.get("avatar_url"),
            "scopes": ["user"]  # Default scopes, can be customized
        }
        
        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token({"sub": token_payload["sub"]})
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
            user={
                "id": token_payload["user_id"],
                "username": token_payload["sub"],
                "email": token_payload.get("email"),
                "name": token_payload.get("name"),
                "avatar_url": token_payload.get("avatar_url")
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )


@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token."""
    try:
        payload = verify_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Create new access token
        new_token_data = {"sub": payload["sub"]}
        access_token = create_access_token(new_token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """Get current user information."""
    return {
        "username": current_user.username,
        "user_id": current_user.user_id,
        "scopes": current_user.scopes
    }


@router.get("/auth-config")
async def get_auth_config():
    """Get authentication configuration for frontend."""
    if not settings.oauth_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth not configured"
        )
    
    auth_urls = {
        "github": f"https://github.com/login/oauth/authorize?client_id={settings.oauth_client_id}&redirect_uri={settings.oauth_redirect_uri}&scope=user:email",
        "google": f"https://accounts.google.com/o/oauth2/auth?client_id={settings.oauth_client_id}&redirect_uri={settings.oauth_redirect_uri}&scope=openid email profile&response_type=code"
    }
    
    return {
        "provider": settings.oauth_provider,
        "auth_url": auth_urls.get(settings.oauth_provider),
        "redirect_uri": settings.oauth_redirect_uri,
        "require_authentication": settings.require_authentication
    }
