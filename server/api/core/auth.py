"""Authentication utilities for Orchestra API."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt  
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx

from api.core.config import get_settings

settings = get_settings()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData:
    """Token data structure."""
    def __init__(self, username: str = None, user_id: str = None, scopes: list = None):
        self.username = username
        self.user_id = user_id
        self.scopes = scopes or []


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(data: dict):
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token)
    
    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return TokenData(
        username=username,
        user_id=payload.get("user_id"),
        scopes=payload.get("scopes", [])
    )


async def get_current_active_user(current_user: TokenData = Depends(get_current_user)):
    """Get current active user (can add additional checks here)."""
    return current_user


class OAuthProvider:
    """OAuth provider interface."""
    
    @staticmethod
    async def exchange_code_for_token(code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        if settings.oauth_provider == "github":
            return await GitHubOAuth.exchange_code_for_token(code)
        elif settings.oauth_provider == "google":
            return await GoogleOAuth.exchange_code_for_token(code)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {settings.oauth_provider}"
            )
    
    @staticmethod
    async def get_user_info(access_token: str) -> Dict[str, Any]:
        """Get user information from OAuth provider."""
        if settings.oauth_provider == "github":
            return await GitHubOAuth.get_user_info(access_token)
        elif settings.oauth_provider == "google":
            return await GoogleOAuth.get_user_info(access_token)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {settings.oauth_provider}"
            )


class GitHubOAuth:
    """GitHub OAuth implementation."""
    
    @staticmethod
    async def exchange_code_for_token(code: str) -> Dict[str, Any]:
        """Exchange GitHub authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": settings.oauth_client_id,
                    "client_secret": settings.oauth_client_secret,
                    "code": code,
                    "redirect_uri": settings.oauth_redirect_uri,
                },
                headers={"Accept": "application/json"}
            )
            return response.json()
    
    @staticmethod
    async def get_user_info(access_token: str) -> Dict[str, Any]:
        """Get GitHub user information."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            return response.json()


class GoogleOAuth:
    """Google OAuth implementation."""
    
    @staticmethod
    async def exchange_code_for_token(code: str) -> Dict[str, Any]:
        """Exchange Google authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.oauth_client_id,
                    "client_secret": settings.oauth_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.oauth_redirect_uri,
                }
            )
            return response.json()
    
    @staticmethod
    async def get_user_info(access_token: str) -> Dict[str, Any]:
        """Get Google user information."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            return response.json()


# Optional: Workshop access control
def require_workshop_access(workshop_id: str):
    """Dependency to check if user has access to specific workshop."""
    def _check_access(current_user: TokenData = Depends(get_current_active_user)):
        # Implement your workshop access logic here
        # For example: check if user is owner, collaborator, or has specific permissions
        return current_user
    return _check_access


def require_admin():
    """Dependency to check if user has admin privileges."""
    def _check_admin(current_user: TokenData = Depends(get_current_active_user)):
        if "admin" not in current_user.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        return current_user
    return _check_admin
