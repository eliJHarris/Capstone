"""
Simple JWT verification dependency used to protect API routes.

Mirrors the core-api behavior by expecting an Authorization header with a
Bearer token signed using the shared JWT secret.
"""

import os
from typing import Any, Dict, Optional

from fastapi import Header, HTTPException, status
from jose import JWTError, jwt


def _read_secret(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except OSError:
        return None


def _get_jwt_secret() -> str:
    """
    Resolve the JWT secret from either *_FILE or direct env var, matching the
    pattern used by other services.
    """
    file_path = os.getenv("JWT_SECRET_FILE") or ""
    secret = _read_secret(file_path)
    if secret:
        return secret
    return os.getenv("JWT_SECRET", "change-me")


JWT_SECRET = _get_jwt_secret()
JWT_ALGO = os.getenv("JWT_ALGO", "HS256")


def require_user(authorization: str = Header(...)) -> Dict[str, Any]:
    """
    Validate the Authorization header and return decoded JWT claims.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
        )

    token = authorization.split(" ", 1)[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc
