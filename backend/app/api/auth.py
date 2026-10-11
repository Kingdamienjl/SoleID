"""Authentication routes for user info and token management."""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.auth import get_current_user, get_optional_user
from app.schemas.auth import LogoutResponse, TokenValidationResponse, UserInfo
from app.services.auth import FirebaseUser, get_auth_service

router = APIRouter()


@router.get("/auth/me", response_model=UserInfo)
async def get_current_user_info(
    user: FirebaseUser = Depends(get_current_user),
) -> UserInfo:
    """
    Get current authenticated user information.

    Requires valid Firebase ID token in Authorization header.
    """
    return UserInfo(
        uid=user.uid,
        email=user.email,
        email_verified=user.email_verified,
        display_name=user.name,
        photo_url=user.picture,
        is_admin=user.is_admin,
    )


@router.post("/auth/validate", response_model=TokenValidationResponse)
async def validate_token(
    user: FirebaseUser | None = Depends(get_optional_user),
) -> TokenValidationResponse:
    """
    Validate the current authorization token.

    Returns token validity and user info if valid.
    Useful for mobile apps to check token status.
    """
    if user:
        return TokenValidationResponse(
            valid=True,
            user=UserInfo(
                uid=user.uid,
                email=user.email,
                email_verified=user.email_verified,
                display_name=user.name,
                photo_url=user.picture,
                is_admin=user.is_admin,
            ),
        )
    return TokenValidationResponse(
        valid=False,
        error="No valid token provided",
    )


@router.post("/auth/logout", response_model=LogoutResponse)
async def logout(
    user: FirebaseUser = Depends(get_current_user),
) -> LogoutResponse:
    """
    Logout endpoint (server-side token revocation).

    Revokes all tokens for the user. The client should
    also clear local tokens and sign out from Firebase.
    """
    try:
        auth_service = get_auth_service()
        auth_service.revoke_tokens(user.uid)
        return LogoutResponse(message="Successfully logged out", uid=user.uid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")
