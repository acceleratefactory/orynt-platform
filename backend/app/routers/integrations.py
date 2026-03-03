"""
ORYNT — Integrations Router
All payment gateway connect endpoints + list.
Paystack, Flutterwave, Monnify, OPay.
"""

import os
import json
import base64
import hmac
import hashlib
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
OPAY_BASE_PROD = "https://cashierapi.opayweb.com"
OPAY_BASE_SANDBOX = "https://sandboxapi.opayweb.com"

ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
OPAY_ENV = os.getenv("OPAY_ENV", "sandbox")


def _opay_base() -> str:
    return OPAY_BASE_PROD if OPAY_ENV == "production" else OPAY_BASE_SANDBOX


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
            brand_id=brand_id, type=gateway, status="connected", encrypted_key=encrypted_value,
        )
        db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


def _opay_auth_headers(payload: dict, private_key: str, merchant_id: str) -> dict:
    sorted_body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    sig = hmac.new(private_key.encode(), sorted_body.encode(), hashlib.sha512).hexdigest()
    return {
        "Authorization": f"Bearer {sig} MerchantId:{merchant_id}",
        "Content-Type": "application/json",
        "MerchantId": merchant_id,
    }


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

class OpayConnectRequest(BaseModel):
    merchant_id: str
    public_key: str
    private_key: str
    brand_id: str


# ── Paystack ──────────────────────────────────────────────────────────────────

@router.post("/paystack/connect")
def connect_paystack(body: PaystackConnectRequest, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    brand = db.get(Brand, body.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    try:
        resp = httpx.get(f"{PAYSTACK_BASE}/transaction", params={"perPage": 1},
                         headers={"Authorization": f"Bearer {body.secret_key}"}, timeout=15)
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
def connect_flutterwave(body: FlutterwaveConnectRequest, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    brand = db.get(Brand, body.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    try:
        resp = httpx.get(f"{FLW_BASE}/transactions", params={"status": "successful", "limit": 1},
                         headers={"Authorization": f"Bearer {body.secret_key}"}, timeout=15)
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
def connect_monnify(body: MonnifyConnectRequest, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    brand = db.get(Brand, body.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    try:
        credentials = base64.b64encode(f"{body.api_key}:{body.secret_key}".encode()).decode()
        resp = httpx.post(f"{MONNIFY_BASE}/api/v1/auth/login",
                          headers={"Authorization": f"Basic {credentials}"}, timeout=15)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach Monnify: {exc}")
    if resp.status_code != 200 or not resp.json().get("responseBody", {}).get("accessToken"):
        raise HTTPException(status_code=400, detail="Invalid Monnify credentials — validation failed.")
    creds_json = json.dumps({"api_key": body.api_key, "secret_key": body.secret_key, "contract_code": body.contract_code})
    integration = _upsert_integration(db, body.brand_id, "monnify", _encrypt(creds_json))
    try:
        from app.tasks.monnify_tasks import pull_monnify_history
        pull_monnify_history.delay(body.brand_id, integration.id)
    except Exception as exc:
        logger.warning(f"[Monnify] Could not queue Celery task: {exc}")
    return {"status": "connected", "integration_id": integration.id,
            "message": "Monnify connected. Historical data sync started in the background."}


# ── OPay ─────────────────────────────────────────────────────────────────────

@router.post("/opay/connect")
def connect_opay(body: OpayConnectRequest, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Validate OPay credentials via transaction inquiry, then store encrypted and queue sync.
    OPay auth: HMAC-SHA512 of sorted JSON body with private_key.
    Authorization: Bearer {signature} MerchantId:{merchant_id}
    """
    brand = db.get(Brand, body.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Validate via a minimal balance/account inquiry call
    payload = {"merchantId": body.merchant_id}
    headers = _opay_auth_headers(payload, body.private_key, body.merchant_id)

    try:
        resp = httpx.post(
            f"{_opay_base()}/api/v1/international/cashier/queryMerchantBalance",
            headers=headers,
            json=payload,
            timeout=15,
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach OPay: {exc}")

    resp_data = resp.json() if resp.content else {}
    opay_code = str(resp_data.get("code", ""))

    # Accept 00000 (success) or 02000 (no merchant balance — still valid credentials)
    if resp.status_code not in (200, 201) or opay_code not in ("00000", "0", "02000"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid OPay credentials — validation failed (code: {opay_code}).",
        )

    creds_json = json.dumps({
        "merchant_id": body.merchant_id,
        "public_key": body.public_key,
        "private_key": body.private_key,
    })
    integration = _upsert_integration(db, body.brand_id, "opay", _encrypt(creds_json))

    try:
        from app.tasks.opay_tasks import pull_opay_history
        pull_opay_history.delay(body.brand_id, integration.id)
    except Exception as exc:
        logger.warning(f"[OPay] Could not queue Celery task: {exc}")

    return {"status": "connected", "integration_id": integration.id,
            "message": "OPay connected. Historical data sync started in the background."}


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("")
def list_integrations(brand_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    integrations = db.query(Integration).filter_by(brand_id=brand_id).all()
    return [i.to_dict() for i in integrations]
