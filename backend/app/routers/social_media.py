"""
ORYNT — Social Media OAuth Router

Handles Instagram + Facebook Page connection.
Reuses the Meta access token from 'meta_ads' integration if available.
Only starts a new OAuth flow if no Meta token exists.

Scopes: instagram_basic, pages_read_engagement
(business_management is also requested so we can discover page and IG account IDs)

Endpoints:
  GET  /api/integrations/social/status     → check if connected (meta or dedicated)
  GET  /api/integrations/social/auth       → redirect to Meta OAuth (social scopes)
  GET  /api/integrations/social/callback   → exchange code, store, trigger pull
  POST /api/integrations/social/sync       → manually trigger data pull
"""

import logging
import os
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.integration import Integration

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Social Media"])

ENCRYPTION_KEY   = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
FACEBOOK_APP_ID  = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
FRONTEND_URL     = os.getenv("FRONTEND_URL", "http://localhost:3000")

META_AUTH_URL  = "https://www.facebook.com/v19.0/dialog/oauth"
META_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
META_LL_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"

# Scopes for social-only connection
SOCIAL_SCOPES = "instagram_basic,pages_read_engagement,business_management"


def _encrypt(v: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).encrypt(v.encode()).decode()


def _decrypt(v: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).decrypt(v.encode()).decode()


# ── GET /status ────────────────────────────────────────────────────────────────

@router.get("/api/integrations/social/status")
def social_status(
    brand_id: str = Query(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check if brand has a usable social media connection.
    Returns which connection is active: 'meta_ads' (reused) or 'social_media' (dedicated).
    """
    # Prefer reusing meta_ads token
    meta = db.query(Integration).filter_by(brand_id=brand_id, type="meta_ads", status="connected").first()
    if meta:
        return {
            "connected": True,
            "source": "meta_ads",
            "last_sync_at": meta.last_sync_at.isoformat() if meta.last_sync_at else None,
        }
    social = db.query(Integration).filter_by(brand_id=brand_id, type="social_media").first()
    if social:
        return {
            "connected": social.status == "connected",
            "source": "social_media",
            "status": social.status,
            "last_sync_at": social.last_sync_at.isoformat() if social.last_sync_at else None,
        }
    return {"connected": False, "source": None}


# ── GET /auth ─────────────────────────────────────────────────────────────────

@router.get("/api/integrations/social/auth")
def social_auth(
    brand_id: str = Query(...),
    user: dict = Depends(get_current_user),
):
    """Redirect to Meta OAuth for social scopes."""
    if not FACEBOOK_APP_ID:
        raise HTTPException(status_code=500, detail="FACEBOOK_APP_ID not configured.")

    callback_url = f"{BACKEND_BASE_URL}/api/integrations/social/callback"
    params = {
        "client_id": FACEBOOK_APP_ID,
        "redirect_uri": callback_url,
        "scope": SOCIAL_SCOPES,
        "state": brand_id,
        "response_type": "code",
    }
    return RedirectResponse(f"{META_AUTH_URL}?{urlencode(params)}")


# ── GET /callback ─────────────────────────────────────────────────────────────

@router.get("/api/integrations/social/callback")
def social_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    error_description: str = Query(None),
    db: Session = Depends(get_db),
):
    """Exchange code for long-lived token, store as 'social_media' integration, queue pull."""
    if error:
        reason = error_description or error
        return RedirectResponse(
            f"{FRONTEND_URL}/dashboard/integrations?social=error&reason={reason}"
        )
    if not code or not state:
        return RedirectResponse(
            f"{FRONTEND_URL}/dashboard/integrations?social=error&reason=missing_code"
        )

    brand_id = state
    callback_url = f"{BACKEND_BASE_URL}/api/integrations/social/callback"

    # Step 1: Short-lived token
    try:
        r = httpx.get(
            META_TOKEN_URL,
            params={
                "client_id": FACEBOOK_APP_ID,
                "client_secret": FACEBOOK_APP_SECRET,
                "redirect_uri": callback_url,
                "code": code,
            },
            timeout=15,
        )
        r.raise_for_status()
        short_token = r.json().get("access_token")
    except Exception as exc:
        logger.error(f"[Social] Token exchange failed: {exc}")
        return RedirectResponse(
            f"{FRONTEND_URL}/dashboard/integrations?social=error&reason=token_exchange_failed"
        )

    if not short_token:
        return RedirectResponse(
            f"{FRONTEND_URL}/dashboard/integrations?social=error&reason=no_token"
        )

    # Step 2: Long-lived token (60 days)
    try:
        r2 = httpx.get(
            META_LL_TOKEN_URL,
            params={
                "grant_type": "fb_exchange_token",
                "client_id": FACEBOOK_APP_ID,
                "client_secret": FACEBOOK_APP_SECRET,
                "fb_exchange_token": short_token,
            },
            timeout=15,
        )
        r2.raise_for_status()
        long_token = r2.json().get("access_token") or short_token
    except Exception:
        long_token = short_token

    # Store as 'social_media' integration
    encrypted = _encrypt(long_token)
    existing = db.query(Integration).filter_by(brand_id=brand_id, type="social_media").first()
    if existing:
        existing.encrypted_key = encrypted
        existing.status = "connected"
        intg = existing
    else:
        intg = Integration(
            brand_id=brand_id,
            type="social_media",
            status="connected",
            encrypted_key=encrypted,
        )
        db.add(intg)
    db.commit()
    db.refresh(intg)

    # Queue initial 30-day pull
    try:
        from app.tasks.social_media_tasks import pull_social_media_data
        pull_social_media_data.delay(intg.id, days_back=30)
    except Exception as exc:
        logger.warning(f"[Social] Could not queue initial pull: {exc}")

    logger.info(f"[Social] Connected brand {brand_id}")
    return RedirectResponse(
        f"{FRONTEND_URL}/dashboard/integrations?social=connected"
    )


# ── POST /sync ────────────────────────────────────────────────────────────────

@router.post("/api/integrations/social/sync")
def trigger_social_sync(
    brand_id: str = Query(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger social data pull. Tries meta_ads token first."""
    from app.tasks.social_media_tasks import pull_social_media_data

    # Prefer meta_ads integration
    intg = db.query(Integration).filter_by(brand_id=brand_id, type="meta_ads", status="connected").first()
    if not intg:
        intg = db.query(Integration).filter_by(brand_id=brand_id, type="social_media", status="connected").first()

    if not intg:
        raise HTTPException(
            status_code=400,
            detail="No Meta Ads or Social Media integration connected. Please connect first."
        )

    pull_social_media_data.delay(intg.id, days_back=30)
    return {"queued": True, "integration_id": intg.id, "source": intg.type}
