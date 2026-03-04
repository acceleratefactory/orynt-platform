"""
ORYNT — Integrations Router
All payment gateway connect endpoints + Mono Open Banking + WooCommerce + list.
Paystack, Flutterwave, Monnify, OPay, Mono, WooCommerce.
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
MONO_BASE = "https://api.withmono.com/v2"

ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
OPAY_ENV = os.getenv("OPAY_ENV", "sandbox")
MONO_SECRET_KEY = os.getenv("MONO_SECRET_KEY", "")


def _opay_base() -> str:
    return OPAY_BASE_PROD if OPAY_ENV == "production" else OPAY_BASE_SANDBOX


def _encrypt(value: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.decrypt(value.encode()).decode()


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


def _mono_headers() -> dict:
    return {"mono-sec-key": MONO_SECRET_KEY, "Content-Type": "application/json"}


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

class MonoInitiateRequest(BaseModel):
    brand_id: str
    redirect_url: str | None = None

class MonoExchangeRequest(BaseModel):
    code: str
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
        logger.warning(f"[Flutterwave] Could not queue task: {exc}")
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
        logger.warning(f"[Monnify] Could not queue task: {exc}")
    return {"status": "connected", "integration_id": integration.id,
            "message": "Monnify connected. Historical data sync started in the background."}


# ── OPay ─────────────────────────────────────────────────────────────────────

@router.post("/opay/connect")
def connect_opay(body: OpayConnectRequest, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    brand = db.get(Brand, body.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    payload = {"merchantId": body.merchant_id}
    headers = _opay_auth_headers(payload, body.private_key, body.merchant_id)
    try:
        resp = httpx.post(f"{_opay_base()}/api/v1/international/cashier/queryMerchantBalance",
                          headers=headers, json=payload, timeout=15)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach OPay: {exc}")
    resp_data = resp.json() if resp.content else {}
    opay_code = str(resp_data.get("code", ""))
    if resp.status_code not in (200, 201) or opay_code not in ("00000", "0", "02000"):
        raise HTTPException(status_code=400, detail=f"Invalid OPay credentials (code: {opay_code}).")
    creds_json = json.dumps({"merchant_id": body.merchant_id, "public_key": body.public_key, "private_key": body.private_key})
    integration = _upsert_integration(db, body.brand_id, "opay", _encrypt(creds_json))
    try:
        from app.tasks.opay_tasks import pull_opay_history
        pull_opay_history.delay(body.brand_id, integration.id)
    except Exception as exc:
        logger.warning(f"[OPay] Could not queue task: {exc}")
    return {"status": "connected", "integration_id": integration.id,
            "message": "OPay connected. Historical data sync started in the background."}


# ── Mono ──────────────────────────────────────────────────────────────────────

@router.post("/mono/initiate")
def mono_initiate(body: MonoInitiateRequest, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Start the Mono Connect flow. Returns a mono_url to open in the Connect widget.
    POST https://api.withmono.com/v2/accounts/initiate
    """
    brand = db.get(Brand, body.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    if not MONO_SECRET_KEY:
        raise HTTPException(status_code=500, detail="MONO_SECRET_KEY not configured.")

    redirect_url = body.redirect_url or "http://localhost:3000/dashboard/integrations"

    try:
        resp = httpx.post(
            f"{MONO_BASE}/accounts/initiate",
            headers=_mono_headers(),
            json={
                "app": MONO_SECRET_KEY,
                "scope": "statements",
                "redirect_url": redirect_url,
                "meta": {"ref": body.brand_id},
            },
            timeout=15,
        )
        resp.raise_for_status()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach Mono: {exc}")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=400, detail=f"Mono initiate failed: {exc.response.text}")

    data = resp.json()
    mono_url = data.get("data", {}).get("mono_url") or data.get("mono_url")
    token = data.get("data", {}).get("token") or data.get("token")

    return {"mono_url": mono_url, "token": token}


@router.post("/mono/exchange")
def mono_exchange(body: MonoExchangeRequest, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Exchange the Mono Connect code for an account_id, store it, and queue history pull.
    POST https://api.withmono.com/v2/accounts/auth
    """
    brand = db.get(Brand, body.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    try:
        resp = httpx.post(
            f"{MONO_BASE}/accounts/auth",
            headers=_mono_headers(),
            json={"code": body.code},
            timeout=15,
        )
        resp.raise_for_status()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach Mono: {exc}")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=400, detail=f"Mono code exchange failed: {exc.response.text}")

    data = resp.json()
    account_id = data.get("id") or data.get("data", {}).get("id")
    if not account_id:
        raise HTTPException(status_code=400, detail="Mono did not return an account ID.")

    integration = _upsert_integration(db, body.brand_id, "mono", _encrypt(account_id))

    try:
        from app.tasks.mono_tasks import pull_mono_statements
        pull_mono_statements.delay(body.brand_id, integration.id)
    except Exception as exc:
        logger.warning(f"[Mono] Could not queue task: {exc}")

    return {"status": "connected", "integration_id": integration.id,
            "message": "Bank account connected. Statement sync started in the background."}


# ── List ──────────────────────────────────────────────────────────────────────

class WooCommerceConnectRequest(BaseModel):
    store_url: str
    consumer_key: str
    consumer_secret: str
    brand_id: str


@router.post("/woocommerce/connect")
def connect_woocommerce(
    body: WooCommerceConnectRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Connect a WooCommerce store via Consumer Key + Consumer Secret."""
    store_url = body.store_url.rstrip("/")
    if not store_url.startswith("http"):
        store_url = f"https://{store_url}"

    # Try standard URL first, then fallback for sites with "Plain" permalinks
    auth_params = {
        "consumer_key": body.consumer_key,
        "consumer_secret": body.consumer_secret,
        "per_page": 1,
    }
    candidate_urls = [
        f"{store_url}/wp-json/wc/v3/orders",
        f"{store_url}/?rest_route=/wc/v3/orders",
    ]
    resp = None
    for url in candidate_urls:
        try:
            resp = httpx.get(url, params=auth_params, timeout=15, verify=False)
            if resp.status_code in (200, 201):
                break  # found working URL
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not reach '{store_url}'. Double-check the store URL includes https://.",
            )

    status = getattr(resp, "status_code", None)
    if status not in (200, 201):
        if status == 404:
            raise HTTPException(
                status_code=400,
                detail=(
                    "WooCommerce REST API not found (404). "
                    "Fix: WordPress Admin → Settings → Permalinks → select 'Post name' → Save. Then try again."
                ),
            )
        elif status in (401, 403):
            raise HTTPException(
                status_code=400,
                detail="Invalid Consumer Key or Consumer Secret. Make sure the key has Read/Write permissions.",
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"WooCommerce validation failed (HTTP {status}). Check the store URL and credentials.",
            )

    creds_json = json.dumps({
        "store_url": store_url,
        "consumer_key": body.consumer_key,
        "consumer_secret": body.consumer_secret,
    })
    integration = _upsert_integration(db, body.brand_id, "woocommerce", _encrypt(creds_json))

    # Auto-register WooCommerce webhooks
    _register_woocommerce_webhooks(store_url, body.consumer_key, body.consumer_secret)

    try:
        from app.tasks.woocommerce_tasks import pull_woocommerce_history
        pull_woocommerce_history.delay(body.brand_id, integration.id)
    except Exception as exc:
        logger.warning(f"[WooCommerce] Could not queue task: {exc}")

    return {"status": "connected", "integration_id": integration.id,
            "message": "WooCommerce connected. Historical sync started in the background."}


def _register_woocommerce_webhooks(store_url: str, ck: str, cs: str) -> None:
    """Register order.created, order.updated, product.updated webhooks."""
    backend_base = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
    webhook_secret = cs[:40]
    for topic in ["order.created", "order.updated", "product.updated"]:
        try:
            resp = httpx.post(
                f"{store_url}/wp-json/wc/v3/webhooks",
                params={"consumer_key": ck, "consumer_secret": cs},
                json={"name": f"ORYNT {topic}", "topic": topic,
                      "delivery_url": f"{backend_base}/api/webhooks/woocommerce",
                      "secret": webhook_secret, "status": "active"},
                timeout=10, verify=False,
            )
            logger.info(f"[WooCommerce] Webhook {topic}: {resp.status_code}")
        except Exception as exc:
            logger.warning(f"[WooCommerce] Webhook {topic} failed: {exc}")


@router.get("")
def list_integrations(brand_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    integrations = db.query(Integration).filter_by(brand_id=brand_id).all()
    return [i.to_dict() for i in integrations]
