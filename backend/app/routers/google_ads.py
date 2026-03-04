"""
ORYNT — Google Ads OAuth Router

Endpoints:
  GET  /api/integrations/google-ads/auth       → redirect to Google OAuth consent
  GET  /api/integrations/google-ads/callback   → exchange code for refresh token, store encrypted
  POST /api/integrations/google-ads/customer   → seller enters their Customer ID (XXX-XXX-XXXX)

Google Ads API requires:
  - OAuth 2.0 refresh token (from consent flow)
  - Developer token (apply at ads.google.com → Tools → API Center)
  - Customer ID (the 10-digit account ID from the seller's Google Ads account)

Required env vars:
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
  GOOGLE_ADS_DEVELOPER_TOKEN
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
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.integration import Integration

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Google Ads"])

ENCRYPTION_KEY       = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
BACKEND_BASE_URL     = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
FRONTEND_URL         = os.getenv("FRONTEND_URL", "http://localhost:3000")

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/adwords"


def _encrypt(v: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).encrypt(v.encode()).decode()


def _decrypt(v: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).decrypt(v.encode()).decode()


def _normalize_customer_id(raw: str) -> str:
    """Strip dashes/spaces; store as plain digits, e.g. '1234567890'."""
    return raw.replace("-", "").replace(" ", "").strip()


# ── GET /auth ─────────────────────────────────────────────────────────────────

@router.get("/api/integrations/google-ads/auth")
def google_ads_auth(
    brand_id: str = Query(...),
    user: dict = Depends(get_current_user),
):
    """Redirect to Google OAuth consent screen for Google Ads access."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured.")

    callback_url = f"{BACKEND_BASE_URL}/api/integrations/google-ads/callback"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",   # Required to get a refresh_token
        "prompt": "consent",        # Force consent to always get refresh_token
        "state": brand_id,
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


# ── GET /callback ─────────────────────────────────────────────────────────────

@router.get("/api/integrations/google-ads/callback")
def google_ads_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Exchange auth code for refresh token. Store encrypted.
    Redirect to frontend so the seller can enter their Customer ID.
    """
    if error:
        return RedirectResponse(
            f"{FRONTEND_URL}/dashboard/integrations?google_ads=error&reason={error}"
        )
    if not code or not state:
        return RedirectResponse(
            f"{FRONTEND_URL}/dashboard/integrations?google_ads=error&reason=missing_code"
        )

    brand_id = state
    callback_url = f"{BACKEND_BASE_URL}/api/integrations/google-ads/callback"

    # Exchange code for tokens
    try:
        r = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": callback_url,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        r.raise_for_status()
        token_data = r.json()
    except Exception as exc:
        logger.error(f"[Google Ads] Token exchange failed: {exc}")
        return RedirectResponse(
            f"{FRONTEND_URL}/dashboard/integrations?google_ads=error&reason=token_exchange_failed"
        )

    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        logger.error("[Google Ads] No refresh_token in response — user may need to revoke and re-authorize")
        return RedirectResponse(
            f"{FRONTEND_URL}/dashboard/integrations?google_ads=error&reason=no_refresh_token"
        )

    # Store encrypted refresh token — status = 'pending_customer_id' until seller enters it
    encrypted = _encrypt(refresh_token)
    existing = db.query(Integration).filter_by(brand_id=brand_id, type="google_ads").first()
    if existing:
        existing.encrypted_key = encrypted
        existing.status = "pending_customer_id"
    else:
        intg = Integration(
            brand_id=brand_id,
            type="google_ads",
            status="pending_customer_id",
            encrypted_key=encrypted,
        )
        db.add(intg)
    db.commit()

    logger.info(f"[Google Ads] OAuth complete for brand {brand_id} — awaiting Customer ID")
    # Redirect to integrations page; frontend shows Customer ID input when status=pending_customer_id
    return RedirectResponse(
        f"{FRONTEND_URL}/dashboard/integrations?google_ads=enter_customer_id&brand_id={brand_id}"
    )


# ── POST /customer ────────────────────────────────────────────────────────────

class CustomerIdRequest(BaseModel):
    brand_id: str
    customer_id: str   # seller enters: e.g. "123-456-7890"


@router.post("/api/integrations/google-ads/customer")
def save_customer_id(
    body: CustomerIdRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Seller enters their Google Ads Customer ID after OAuth.
    Validates format, stores on integration, queues history pull.
    """
    cid_raw = _normalize_customer_id(body.customer_id)
    if not cid_raw.isdigit() or len(cid_raw) != 10:
        raise HTTPException(
            status_code=400,
            detail="Customer ID must be a 10-digit number (format: XXX-XXX-XXXX)."
        )

    intg = db.query(Integration).filter_by(brand_id=body.brand_id, type="google_ads").first()
    if not intg:
        raise HTTPException(status_code=404, detail="Google Ads integration not found. Please reconnect.")

    # Store customer_id in config_json (reusing encrypted_key for token; customer_id goes in notes)
    # We'll encode both together as "token::customer_id" in encrypted_key
    current_token = _decrypt(intg.encrypted_key)
    combined = f"{current_token}::{cid_raw}"
    intg.encrypted_key = _encrypt(combined)
    intg.status = "connected"
    db.commit()
    db.refresh(intg)

    # Queue initial 12-month history pull
    try:
        from app.tasks.google_ads_tasks import pull_google_ads_history
        pull_google_ads_history.delay(intg.id)
    except Exception as exc:
        logger.warning(f"[Google Ads] Could not queue initial pull: {exc}")

    logger.info(f"[Google Ads] Customer ID {cid_raw} saved for brand {body.brand_id}")
    return {"status": "connected", "customer_id": f"{cid_raw[:3]}-{cid_raw[3:6]}-{cid_raw[6:]}"}
