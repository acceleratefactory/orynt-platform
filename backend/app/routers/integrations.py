"""
ORYNT — Integrations Router
POST /api/integrations/paystack/connect  — validate key, store encrypted, queue history pull
GET  /api/integrations                    — list integrations for current brand
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
ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")


def _encrypt_key(secret_key: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.encrypt(secret_key.encode()).decode()


class PaystackConnectRequest(BaseModel):
    secret_key: str
    brand_id: str


@router.post("/paystack/connect")
def connect_paystack(
    body: PaystackConnectRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Validate Paystack secret key, encrypt and store it, then queue a
    background job to pull 12 months of transaction history.
    """
    # ── Verify the brand belongs to this user's org ──────────────────────
    brand = db.get(Brand, body.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # ── Validate key against Paystack API ────────────────────────────────
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

    # ── Upsert integration record ─────────────────────────────────────────
    encrypted = _encrypt_key(body.secret_key)
    existing = db.query(Integration).filter_by(brand_id=body.brand_id, type="paystack").first()
    if existing:
        existing.encrypted_key = encrypted
        existing.status = "connected"
        integration = existing
    else:
        integration = Integration(
            brand_id=body.brand_id,
            type="paystack",
            status="connected",
            encrypted_key=encrypted,
        )
        db.add(integration)

    db.commit()
    db.refresh(integration)

    # ── Queue background history pull ────────────────────────────────────
    try:
        from app.tasks.paystack_tasks import pull_paystack_history
        pull_paystack_history.delay(body.brand_id, integration.id)
        logger.info(f"[Paystack] Queued history pull for brand={body.brand_id}")
    except Exception as exc:
        logger.warning(f"[Paystack] Could not queue Celery task: {exc}. Sync will run on next connect.")

    return {
        "status": "connected",
        "integration_id": integration.id,
        "message": "Paystack connected. Historical data sync started in the background.",
    }


@router.get("")
def list_integrations(
    brand_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all integrations for a brand."""
    integrations = db.query(Integration).filter_by(brand_id=brand_id).all()
    return [i.to_dict() for i in integrations]
