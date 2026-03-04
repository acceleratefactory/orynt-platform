"""
ORYNT — Meta Ads OAuth Router

Endpoints:
  GET  /api/integrations/meta-ads/auth      → redirect to Meta Business Login
  GET  /api/integrations/meta-ads/callback  → exchange code for long-lived token

Meta Business Login OAuth 2.0
App scopes: ads_read, business_management
Long-lived token = 60 days. Refreshed by the nightly task at day 50+.

Required env vars:
  FACEBOOK_APP_ID
  FACEBOOK_APP_SECRET
  BACKEND_BASE_URL   (e.g. https://api.orynt.com)
  FRONTEND_URL       (e.g. https://app.orynt.com)
"""

import logging
import os
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.integration import Integration

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Meta Ads"])

ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

META_AUTH_URL = "https://www.facebook.com/v19.0/dialog/oauth"
META_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
META_LL_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"

SCOPES = "ads_read,business_management"


def _encrypt(value: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).encrypt(value.encode()).decode()


# ── GET /auth ─────────────────────────────────────────────────────────────────

@router.get("/api/integrations/meta-ads/auth")
def meta_ads_auth(
    brand_id: str = Query(...),
    user: dict = Depends(get_current_user),
):
    """Redirect browser to Meta Business Login consent screen."""
    if not FACEBOOK_APP_ID:
        raise HTTPException(status_code=500, detail="FACEBOOK_APP_ID not configured.")

    callback_url = f"{BACKEND_BASE_URL}/api/integrations/meta-ads/callback"
    params = {
        "client_id": FACEBOOK_APP_ID,
        "redirect_uri": callback_url,
        "scope": SCOPES,
        "state": brand_id,
        "response_type": "code",
    }
    return RedirectResponse(f"{META_AUTH_URL}?{urlencode(params)}")


# ── GET /callback ─────────────────────────────────────────────────────────────

@router.get("/api/integrations/meta-ads/callback")
def meta_ads_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    error_description: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Exchange auth code for a short-lived token, then immediately
    exchange for a long-lived token (60-day expiry). Store encrypted.
    """
    if error:
        reason = error_description or error
        return RedirectResponse(
            f"{FRONTEND_URL}/dashboard/integrations?meta_ads=error&reason={reason}"
        )
    if not code or not state:
        return RedirectResponse(
            f"{FRONTEND_URL}/dashboard/integrations?meta_ads=error&reason=missing_code"
        )

    brand_id = state
    callback_url = f"{BACKEND_BASE_URL}/api/integrations/meta-ads/callback"

    # Step 1: Exchange code for short-lived token
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
        logger.error(f"[Meta] Short-lived token exchange failed: {exc}")
        return RedirectResponse(
            f"{FRONTEND_URL}/dashboard/integrations?meta_ads=error&reason=token_exchange_failed"
        )

    if not short_token:
        return RedirectResponse(
            f"{FRONTEND_URL}/dashboard/integrations?meta_ads=error&reason=no_token"
        )

    # Step 2: Exchange for long-lived token (60 days)
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
        ll_data = r2.json()
        long_token = ll_data.get("access_token") or short_token
        expires_in = ll_data.get("expires_in", 5183944)  # ~60 days in seconds
    except Exception as exc:
        logger.warning(f"[Meta] Long-lived token exchange failed, using short token: {exc}")
        long_token = short_token
        expires_in = 3600

    # Store encrypted
    encrypted = _encrypt(long_token)
    existing = db.query(Integration).filter_by(brand_id=brand_id, type="meta_ads").first()
    if existing:
        existing.encrypted_key = encrypted
        existing.status = "connected"
        intg = existing
    else:
        intg = Integration(
            brand_id=brand_id,
            type="meta_ads",
            status="connected",
            encrypted_key=encrypted,
        )
        db.add(intg)
    db.commit()
    db.refresh(intg)

    # Queue initial 30-day history pull
    try:
        from app.tasks.meta_ads_tasks import pull_meta_ads_history
        pull_meta_ads_history.delay(intg.id)
    except Exception as exc:
        logger.warning(f"[Meta] Could not queue initial pull: {exc}")

    logger.info(f"[Meta] Connected brand {brand_id}, token expires in {expires_in}s")
    return RedirectResponse(
        f"{FRONTEND_URL}/dashboard/integrations?meta_ads=connected"
    )
