"""
ORYNT — JWT Authentication Middleware
Validates Supabase JWT tokens on every protected endpoint.

Supabase newer projects use ES256 (elliptic curve) signing.
Tokens are verified using the public key fetched from Supabase's JWKS endpoint:
  https://<project>.supabase.co/auth/v1/.well-known/jwks.json

Usage: add `user = Depends(get_current_user)` to any protected route.
"""

import os
import httpx
from functools import lru_cache
from jose import jwt, JWTError, jwk
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"

security = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def get_jwks() -> dict:
    """
    Fetch and cache Supabase's JSON Web Key Set (JWKS).
    The public keys are used to verify ES256-signed JWTs.
    Cached for the lifetime of the process — restart to refresh.
    """
    try:
        response = httpx.get(JWKS_URL, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch JWKS from {JWKS_URL}: {exc}") from exc


def get_public_key(kid: str):
    """
    Look up the public key that matches the given key ID (kid).
    Returns a jose-compatible key object.
    """
    jwks = get_jwks()
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return jwk.construct(key_data)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"No matching public key found for kid={kid}.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """
    Dependency that validates a Supabase JWT token.
    Returns the decoded payload (contains 'sub' = user UUID, 'email', etc.)
    Raises 401 if the token is missing, invalid or expired.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg", "HS256")

        public_key = get_public_key(kid)

        payload = jwt.decode(
            token,
            public_key,
            algorithms=[alg],
            options={"verify_aud": False},
        )
        return payload

    except (JWTError, RuntimeError) as exc:
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
