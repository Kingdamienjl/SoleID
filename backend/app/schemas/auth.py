"""Authentication schemas for request/response models."""

from typing import Optional

from pydantic import BaseModel


class UserInfo(BaseModel):
    """Authenticated user information."""

    uid: str
    email: Optional[str] = None
    email_verified: bool = False
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    is_admin: bool = False


class TokenValidationResponse(BaseModel):
    """Response from token validation endpoint."""

    valid: bool
    user: Optional[UserInfo] = None
    error: Optional[str] = None


class LogoutResponse(BaseModel):
    """Response from logout endpoint."""

    message: str
    uid: str
