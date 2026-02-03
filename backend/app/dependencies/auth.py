"""Authentication dependencies for FastAPI routes."""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException
from firebase_admin import auth as firebase_auth

from app.services.auth import FirebaseUser, get_auth_service


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> FirebaseUser:
    """
    FastAPI dependency to extract and validate Firebase ID token.

    Expected header format: Authorization: Bearer <id_token>

    Args:
        authorization: The Authorization header value.

    Returns:
        FirebaseUser with verified user information.

    Raises:
        HTTPException 401: Missing or invalid token.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    try:
        auth_service = get_auth_service()
        user = auth_service.verify_token(token)
        return user
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired. Please refresh your token.",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="Token expired"'
            },
        )
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked. Please sign in again.",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="Token revoked"'
            },
        )
    except firebase_auth.InvalidIdTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[FirebaseUser]:
    """
    Optional auth dependency - returns None if no token provided.

    Useful for endpoints that work for both authenticated and anonymous users.

    Args:
        authorization: The Authorization header value.

    Returns:
        FirebaseUser if valid token provided, None otherwise.
    """
    if not authorization:
        return None

    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None


async def require_admin(
    user: FirebaseUser = Depends(get_current_user),
) -> FirebaseUser:
    """
    Dependency that requires the user to be an admin.

    Args:
        user: The authenticated user from get_current_user.

    Returns:
        FirebaseUser if user is admin.

    Raises:
        HTTPException 403: User is not an admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
    return user
