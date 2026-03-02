"""
ORYNT — JWT Authentication Middleware
Validates Supabase JWT tokens on every protected endpoint.
Usage: add `user = Depends(require_auth)` to any route that needs auth.
"""

import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

# Supabase signs tokens with your project's JWT secret
# Found in: Supabase dashboard → Settings → API → JWT Secret
JWT_SECRET = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """
    Dependency that validates a Supabase JWT token.
    Returns the decoded payload (contains 'sub' = user UUID, 'email', etc.)
    Raises 401 if the token is missing, invalid or expired.
    """
    if not JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET environment variable is not configured.",
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},  # Supabase audience = "authenticated"
        )
        return payload

    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user_email(payload: dict = Depends(get_current_user)) -> str:
    """Returns the authenticated user's email from the JWT payload."""
    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain a valid email claim.",
        )
    return email


def get_current_user_id(payload: dict = Depends(get_current_user)) -> str:
    """Returns the authenticated user's UUID (sub claim) from the JWT payload."""
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain a valid sub claim.",
        )
    return user_id
