"""
ORYNT — Auth Router
Endpoints for verifying session and user metadata.
"""

from fastapi import APIRouter, Depends
from app.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """
    Returns the authenticated user's details.
    Requires a valid Supabase JWT in the Authorization header.
    """
    return {
        "user_id": user.get("sub"),
        "email": user.get("email"),
        "authenticated": True,
    }
