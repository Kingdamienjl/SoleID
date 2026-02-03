"""Firebase Authentication Service for validating mobile app tokens."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

import firebase_admin
from firebase_admin import auth, credentials

logger = logging.getLogger("soleid.auth")

_auth_service_singleton: Optional["AuthService"] = None


def get_auth_service() -> "AuthService":
    """Get the singleton AuthService instance."""
    global _auth_service_singleton
    if _auth_service_singleton is None:
        _auth_service_singleton = AuthService()
    return _auth_service_singleton


@dataclass
class FirebaseUser:
    """Verified Firebase user information extracted from token."""

    uid: str
    email: Optional[str]
    email_verified: bool
    name: Optional[str]
    picture: Optional[str]
    auth_time: int
    is_admin: bool = False


class AuthService:
    """Service for Firebase token validation and user management."""

    def __init__(self) -> None:
        self._initialize_firebase()

    def _initialize_firebase(self) -> None:
        """Initialize Firebase Admin SDK."""
        if firebase_admin._apps:
            logger.info("Firebase Admin SDK already initialized")
            return

        creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if creds_json:
            logger.info("Initializing Firebase with JSON credentials from environment")
            cred_dict = json.loads(creds_json)
            cred = credentials.Certificate(cred_dict)
        elif cred_path:
            logger.info("Initializing Firebase with credentials file: %s", cred_path)
            cred = credentials.Certificate(cred_path)
        else:
            logger.info("Initializing Firebase with Application Default Credentials")
            cred = credentials.ApplicationDefault()

        project_id = os.getenv("FIREBASE_PROJECT_ID")
        firebase_admin.initialize_app(cred, {"projectId": project_id} if project_id else None)
        logger.info("Firebase Admin SDK initialized successfully")

    def verify_token(self, id_token: str) -> FirebaseUser:
        """
        Verify Firebase ID token and return user info.

        Args:
            id_token: The Firebase ID token from the client.

        Returns:
            FirebaseUser with verified user information.

        Raises:
            firebase_admin.auth.InvalidIdTokenError: Token is invalid.
            firebase_admin.auth.ExpiredIdTokenError: Token has expired.
            firebase_admin.auth.RevokedIdTokenError: Token has been revoked.
        """
        decoded = auth.verify_id_token(id_token, check_revoked=True)

        return FirebaseUser(
            uid=decoded["uid"],
            email=decoded.get("email"),
            email_verified=decoded.get("email_verified", False),
            name=decoded.get("name"),
            picture=decoded.get("picture"),
            auth_time=decoded.get("auth_time", 0),
            is_admin=decoded.get("admin", False),
        )

    def set_admin_claim(self, uid: str, is_admin: bool = True) -> None:
        """
        Set admin custom claim on a user.

        Args:
            uid: Firebase user ID.
            is_admin: Whether to grant or revoke admin status.
        """
        auth.set_custom_user_claims(uid, {"admin": is_admin})
        logger.info("Set admin=%s for user %s", is_admin, uid)

    def revoke_tokens(self, uid: str) -> None:
        """
        Revoke all refresh tokens for a user.

        Args:
            uid: Firebase user ID.
        """
        auth.revoke_refresh_tokens(uid)
        logger.info("Revoked tokens for user %s", uid)

    def get_user(self, uid: str) -> auth.UserRecord:
        """
        Get Firebase user record by UID.

        Args:
            uid: Firebase user ID.

        Returns:
            Firebase UserRecord.
        """
        return auth.get_user(uid)
