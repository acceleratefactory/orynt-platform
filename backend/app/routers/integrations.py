"""
ORYNT — Integrations Router
POST /api/integrations/paystack/connect    — validate key, store encrypted, queue history pull
POST /api/integrations/flutterwave/connect — same pattern for Flutterwave
GET  /api/integrations                     — list integrations for current brand
"""

import os
import logging
from cryptography.fernet import Fernet
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.brand import Brand
from app.models.integration import Integration

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/integrations", tags=["Integrations"])

PAYSTACK_BASE = "https://api.paystack.co"
FLW_BASE = "https://api.flutterwave.com/v3"
ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")


def _encrypt_key(secret_key: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.encrypt(secret_key.encode()).decode()


def _upsert_integration(db: Session, brand_id: str, gateway: str, secret_key: str) -> Integration:
    encrypted = _encrypt_key(secret_key)
    existing = db.query(Integration).filter_by(brand_id=brand_id, type=gateway).first()
    if existing:
        existing.encrypted_key = encrypted
        existing.status = "connected"
        integration = existing
    else:
        integration = Integration(
            brand_id=brand_id,
            type=gateway,
            status="connected",
            encrypted_key=encrypted,
        )
        db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


class PaystackConnectRequest(BaseModel):
    secret_key: str
    brand_id: str


class FlutterwaveConnectRequest(BaseModel):
    secret_key: str
    brand_id: str


# ── Paystack ──────────────────────────────────────────────────────────────────

@router.post("/paystack/connect")
def connect_paystack(
    body: PaystackConnectRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    brand = db.get(Brand, body.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    try:
        resp = httpx.get(
            f"{PAYSTACK_BASE}/transaction",
            params={"perPage": 1},
            headers={"Authorization": f"Bearer {body.secret_key}"},
            timeout=15,
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach Paystack: {exc}")

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Paystack secret key — validation failed.",
        )

    integration = _upsert_integration(db, body.brand_id, "paystack", body.secret_key)

    try:
        from app.tasks.paystack_tasks import pull_paystack_history
        pull_paystack_history.delay(body.brand_id, integration.id)
    except Exception as exc:
        logger.warning(f"[Paystack] Could not queue Celery task: {exc}")

    return {
        "status": "connected",
        "integration_id": integration.id,
        "message": "Paystack connected. Historical data sync started in the background.",
    }


# ── Flutterwave ───────────────────────────────────────────────────────────────

@router.post("/flutterwave/connect")
def connect_flutterwave(
    body: FlutterwaveConnectRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    brand = db.get(Brand, body.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Validate key against Flutterwave API
    try:
        resp = httpx.get(
            f"{FLW_BASE}/transactions",
            params={"status": "successful", "limit": 1},
            headers={"Authorization": f"Bearer {body.secret_key}"},
            timeout=15,
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach Flutterwave: {exc}")

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Flutterwave secret key — validation failed.",
        )

    resp_json = resp.json()
    if resp_json.get("status") != "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Flutterwave secret key — validation failed.",
        )

    integration = _upsert_integration(db, body.brand_id, "flutterwave", body.secret_key)

    try:
        from app.tasks.flutterwave_tasks import pull_flutterwave_history
        pull_flutterwave_history.delay(body.brand_id, integration.id)
    except Exception as exc:
        logger.warning(f"[Flutterwave] Could not queue Celery task: {exc}")

    return {
        "status": "connected",
        "integration_id": integration.id,
        "message": "Flutterwave connected. Historical data sync started in the background.",
    }


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("")
def list_integrations(
    brand_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all integrations for a brand."""
    integrations = db.query(Integration).filter_by(brand_id=brand_id).all()
    return [i.to_dict() for i in integrations]
