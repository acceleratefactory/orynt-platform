"""
ORYNT — Integrations Router
POST /api/integrations/paystack/connect    — validate key, store encrypted, queue history pull
POST /api/integrations/flutterwave/connect — same pattern for Flutterwave
POST /api/integrations/monnify/connect     — Basic Auth, 3 credentials, queue history pull
GET  /api/integrations                     — list integrations for current brand
"""

import os
import json
import base64
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
MONNIFY_BASE = "https://api.monnify.com"
ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")


def _encrypt(value: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.encrypt(value.encode()).decode()


def _upsert_integration(db: Session, brand_id: str, gateway: str, encrypted_value: str) -> Integration:
    existing = db.query(Integration).filter_by(brand_id=brand_id, type=gateway).first()
    if existing:
        existing.encrypted_key = encrypted_value
        existing.status = "connected"
        integration = existing
    else:
        integration = Integration(
            brand_id=brand_id,
            type=gateway,
            status="connected",
            encrypted_key=encrypted_value,
        )
        db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


# ── Request models ────────────────────────────────────────────────────────────

class PaystackConnectRequest(BaseModel):
    secret_key: str
    brand_id: str

class FlutterwaveConnectRequest(BaseModel):
    secret_key: str
    brand_id: str

class MonnifyConnectRequest(BaseModel):
    api_key: str
    secret_key: str
    contract_code: str
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
        raise HTTPException(status_code=400, detail="Invalid Paystack secret key — validation failed.")

    integration = _upsert_integration(db, body.brand_id, "paystack", _encrypt(body.secret_key))

    try:
        from app.tasks.paystack_tasks import pull_paystack_history
        pull_paystack_history.delay(body.brand_id, integration.id)
    except Exception as exc:
        logger.warning(f"[Paystack] Could not queue Celery task: {exc}")

    return {"status": "connected", "integration_id": integration.id,
            "message": "Paystack connected. Historical data sync started in the background."}


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

    try:
        resp = httpx.get(
            f"{FLW_BASE}/transactions",
            params={"status": "successful", "limit": 1},
            headers={"Authorization": f"Bearer {body.secret_key}"},
            timeout=15,
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach Flutterwave: {exc}")

    if resp.status_code not in (200, 201) or resp.json().get("status") != "success":
        raise HTTPException(status_code=400, detail="Invalid Flutterwave secret key — validation failed.")

    integration = _upsert_integration(db, body.brand_id, "flutterwave", _encrypt(body.secret_key))

    try:
        from app.tasks.flutterwave_tasks import pull_flutterwave_history
        pull_flutterwave_history.delay(body.brand_id, integration.id)
    except Exception as exc:
        logger.warning(f"[Flutterwave] Could not queue Celery task: {exc}")

    return {"status": "connected", "integration_id": integration.id,
            "message": "Flutterwave connected. Historical data sync started in the background."}


# ── Monnify ───────────────────────────────────────────────────────────────────

@router.post("/monnify/connect")
def connect_monnify(
    body: MonnifyConnectRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    brand = db.get(Brand, body.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Validate via Monnify Basic Auth login
    try:
        credentials = base64.b64encode(f"{body.api_key}:{body.secret_key}".encode()).decode()
        resp = httpx.post(
            f"{MONNIFY_BASE}/api/v1/auth/login",
            headers={"Authorization": f"Basic {credentials}"},
            timeout=15,
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach Monnify: {exc}")

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid Monnify credentials — validation failed.")

    resp_json = resp.json()
    if not resp_json.get("responseBody", {}).get("accessToken"):
        raise HTTPException(status_code=400, detail="Invalid Monnify credentials — no token returned.")

    # Encrypt all three credentials together as JSON
    creds_json = json.dumps({
        "api_key": body.api_key,
        "secret_key": body.secret_key,
        "contract_code": body.contract_code,
    })
    integration = _upsert_integration(db, body.brand_id, "monnify", _encrypt(creds_json))

    try:
        from app.tasks.monnify_tasks import pull_monnify_history
        pull_monnify_history.delay(body.brand_id, integration.id)
    except Exception as exc:
        logger.warning(f"[Monnify] Could not queue Celery task: {exc}")

    return {"status": "connected", "integration_id": integration.id,
            "message": "Monnify connected. Historical data sync started in the background."}


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("")
def list_integrations(
    brand_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    integrations = db.query(Integration).filter_by(brand_id=brand_id).all()
    return [i.to_dict() for i in integrations]
