"""Authentication and session security for Admin Dashboard."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
import jwt
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse

from memetek.config import settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
COOKIE_NAME = "memetek_session"


def create_access_token(username: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create signed JWT for admin session."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=12))
    payload = {
        "sub": username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "memetek-bot",
    }
    return jwt.encode(payload, settings.DASHBOARD_SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[str]:
    """Verify and decode JWT token. Returns username if valid, None otherwise."""
    try:
        payload = jwt.decode(token, settings.DASHBOARD_SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except (jwt.PyJWTError, Exception):
        return None


def get_current_admin_or_none(request: Request) -> Optional[str]:
    """Extract authenticated admin username from cookie or authorization header."""
    # Check Cookie
    token = request.cookies.get(COOKIE_NAME)
    if token:
        username = verify_token(token)
        if username:
            return username

    # Check Authorization header (Bearer token)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        username = verify_token(token)
        if username:
            return username

    return None


async def require_admin_page(request: Request) -> str:
    """Dependency for HTML pages: redirects to login if unauthenticated."""
    username = get_current_admin_or_none(request)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )
    return username


async def require_admin_api(request: Request) -> str:
    """Dependency for REST API endpoints: returns 401 if unauthenticated."""
    username = get_current_admin_or_none(request)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for administrative actions.",
        )
    return username
