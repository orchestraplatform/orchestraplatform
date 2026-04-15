"""Authentication utilities for Orchestra API.

Auth model: oauth2-proxy sits at the ingress and validates Google/GitHub OIDC
tokens. After a successful login it forwards requests to the API with the
header ``X-Auth-Request-Email: user@example.com`` (configurable via
``ORCHESTRA_TRUSTED_AUTH_HEADER``). The API trusts that header and treats its
value as the authenticated identity.

For local development without a proxy, set:
    ORCHESTRA_REQUIRE_AUTHENTICATION=false
    ORCHESTRA_DEV_IDENTITY=dev@orchestra.localhost

The ``dev_identity`` is used only when ``require_authentication=False``.
Never set it in production.
"""

from dataclasses import dataclass, field

from fastapi import Depends, HTTPException, Request, status

from api.core.config import Settings, get_settings


@dataclass
class CurrentUser:
    """Authenticated user identity forwarded by oauth2-proxy."""

    email: str
    is_admin: bool = field(default=False)


async def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    """Resolve the authenticated user from the oauth2-proxy forwarded header.

    In dev mode (``require_authentication=False`` + ``dev_identity`` set) the
    dependency short-circuits and returns the configured dev identity so the
    stack works without a running proxy.
    """
    # Dev bypass — only active when both conditions hold
    if not settings.require_authentication and settings.dev_identity:
        email = settings.dev_identity
        return CurrentUser(
            email=email,
            is_admin=email in settings.admin_emails,
        )

    email = request.headers.get(settings.trusted_auth_header)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        email=email,
        is_admin=email in settings.admin_emails,
    )


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Dependency that restricts a route to admin users."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
