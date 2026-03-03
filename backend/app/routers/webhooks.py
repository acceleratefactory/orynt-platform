"""
ORYNT — Webhooks Router
POST /api/webhooks/paystack    — HMAC-SHA512 validation, handles charge.success etc.
POST /api/webhooks/flutterwave — verif-hash validation, handles charge.completed.
Always returns 200.
"""

import os
import hmac
import hashlib
import logging
import json as _json
from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.customer import Customer
from app.models.order import Order

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])

ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")


# ── Shared helpers ────────────────────────────────────────────────────────────

def _decrypt_integration_key(integration) -> str | None:
    if not ENCRYPTION_KEY:
        return None
    try:
        from cryptography.fernet import Fernet
        f = Fernet(ENCRYPTION_KEY.encode())
        return f.decrypt(integration.encrypted_key.encode()).decode()
    except Exception:
        return None


def _find_integration(brand_id: str, gateway: str, db: Session):
    from app.models.integration import Integration
    return db.query(Integration).filter_by(brand_id=brand_id, type=gateway, status="connected").first()


def _all_integrations(gateway: str, db: Session):
    from app.models.integration import Integration
    return db.query(Integration).filter_by(type=gateway, status="connected").all()


def _upsert_customer(brand_id: str, email: str, name: str | None, phone: str | None, db: Session):
    customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
    if not customer:
        customer = Customer(brand_id=brand_id, email=email, name=name or None, phone=phone)
        db.add(customer)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
    return customer


# ── Paystack Webhook ──────────────────────────────────────────────────────────

def _verify_paystack_sig(raw_body: bytes, signature: str, secret_key: str) -> bool:
    computed = hmac.new(secret_key.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature)


def _paystack_infer_channel(txn: dict) -> str:
    metadata = txn.get("metadata") or {}
    custom_fields = metadata.get("custom_fields") or []
    for field in custom_fields:
        val = str(field.get("value", "")).lower()
        if any(w in val for w in ["social", "whatsapp", "instagram"]):
            return "social"
        if any(w in val for w in ["physical", "store", "shop"]):
            return "physical"
    return "website"


def _paystack_infer_payment_method(txn: dict) -> str:
    ch = (txn.get("channel") or "").lower()
    if ch == "card":
        return "card"
    if ch in ("bank_transfer", "dedicated_nuban", "bank"):
        return "bank_transfer"
    return "card"


@router.post("/paystack")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    try:
        payload = _json.loads(raw_body) if raw_body else {}
    except Exception:
        return {"status": "ok"}

    event = payload.get("event", "")
    data = payload.get("data", {})
    metadata = (data.get("metadata") or {})
    brand_id = metadata.get("brand_id")

    # Validate signature
    if brand_id:
        integration = _find_integration(brand_id, "paystack", db)
        secret_key = _decrypt_integration_key(integration) if integration else None
        if secret_key and not _verify_paystack_sig(raw_body, signature, secret_key):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    else:
        matched_brand_id = None
        for intg in _all_integrations("paystack", db):
            sk = _decrypt_integration_key(intg)
            if sk and _verify_paystack_sig(raw_body, signature, sk):
                matched_brand_id = intg.brand_id
                break
        if not matched_brand_id:
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        brand_id = matched_brand_id

    logger.info(f"[Paystack Webhook] event={event} brand={brand_id}")

    if event == "charge.success":
        _paystack_handle_charge(data, brand_id, db)
    elif event == "transfer.success":
        _update_order_status(data.get("reference", ""), brand_id, "transferred", "paystack", db)
    elif event == "refund.processed":
        ref = (data.get("transaction") or {}).get("reference", "")
        _update_order_status(ref, brand_id, "refunded", "paystack", db)

    return {"status": "ok"}


def _paystack_handle_charge(txn: dict, brand_id: str, db: Session):
    external_id = txn.get("reference", "")
    if not external_id:
        return
    if db.query(Order).filter_by(brand_id=brand_id, external_id=external_id, source="paystack").first():
        return

    email = (txn.get("customer") or {}).get("email", "").lower().strip()
    customer = None
    if email:
        cust = txn.get("customer") or {}
        name = f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or None
        customer = _upsert_customer(brand_id, email, name, cust.get("phone"), db)

    amount_ngn = round((txn.get("amount") or 0) / 100, 2)
    paid_at_raw = txn.get("paid_at") or txn.get("created_at")
    try:
        ordered_at = datetime.fromisoformat(paid_at_raw.replace("Z", "+00:00"))
    except Exception:
        ordered_at = datetime.now(timezone.utc)

    order = Order(
        brand_id=brand_id,
        customer_id=customer.id if customer else None,
        source="paystack",
        channel=_paystack_infer_channel(txn),
        status="completed",
        total_amount=amount_ngn,
        payment_method=_paystack_infer_payment_method(txn),
        payment_gateway="paystack",
        external_id=external_id,
        ordered_at=ordered_at,
    )
    db.add(order)
    try:
        db.commit()
        logger.info(f"[Paystack Webhook] Created order {external_id}")
    except IntegrityError:
        db.rollback()


def _update_order_status(reference: str, brand_id: str, new_status: str, source: str, db: Session):
    if not reference:
        return
    order = db.query(Order).filter_by(brand_id=brand_id, external_id=reference, source=source).first()
    if order:
        order.status = new_status
        db.commit()
        logger.info(f"[Webhook] Order {reference} -> {new_status}")


# ── Flutterwave Webhook ───────────────────────────────────────────────────────

def _flw_infer_channel(txn: dict) -> str:
    narration = str(txn.get("narration", "")).lower()
    if any(w in narration for w in ["social", "whatsapp", "instagram", "tiktok"]):
        return "social"
    if any(w in narration for w in ["physical", "store", "shop"]):
        return "physical"
    return "website"


def _flw_infer_payment_method(txn: dict) -> str:
    pt = str(txn.get("payment_type", "")).lower()
    if pt == "card":
        return "card"
    if pt in ("banktransfer", "bank_transfer", "account", "ussd"):
        return "bank_transfer"
    return "card"


@router.post("/flutterwave")
async def flutterwave_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive Flutterwave webhook events.
    Validates using verif-hash header against FLW_WEBHOOK_HASH env var.
    Processes charge.completed events. Always returns 200.
    """
    raw_body = await request.body()
    verif_hash = request.headers.get("verif-hash", "")

    try:
        payload = _json.loads(raw_body) if raw_body else {}
    except Exception:
        return {"status": "ok"}

    # Validate hash if env var is set
    flw_webhook_hash = os.getenv("FLW_WEBHOOK_HASH", "")
    if flw_webhook_hash and verif_hash != flw_webhook_hash:
        logger.warning(f"[FLW Webhook] Invalid verif-hash received")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = payload.get("event", "")
    data = payload.get("data", {})

    # Determine brand_id from meta or first connected integration
    meta = data.get("meta") or {}
    brand_id = meta.get("brand_id")

    if not brand_id:
        integrations = _all_integrations("flutterwave", db)
        brand_id = integrations[0].brand_id if integrations else None

    if not brand_id:
        logger.warning("[FLW Webhook] Cannot determine brand_id")
        return {"status": "ok"}

    logger.info(f"[FLW Webhook] event={event} brand={brand_id}")

    if event in ("charge.completed", "payment.completed"):
        _flw_handle_charge(data, brand_id, db)

    return {"status": "ok"}


def _flw_handle_charge(txn: dict, brand_id: str, db: Session):
    if txn.get("status") != "successful":
        return

    external_id = str(txn.get("tx_ref") or txn.get("id") or "")
    if not external_id:
        return
    if db.query(Order).filter_by(brand_id=brand_id, external_id=external_id, source="flutterwave").first():
        return

    email = str((txn.get("customer") or {}).get("email", "")).lower().strip()
    customer = None
    if email:
        cust = txn.get("customer") or {}
        name = cust.get("name") or cust.get("fullname") or None
        customer = _upsert_customer(brand_id, email, name, cust.get("phone_number"), db)

    amount_ngn = round(float(txn.get("amount") or 0), 2)
    currency = txn.get("currency", "NGN")
    created_at_raw = txn.get("created_at") or txn.get("createdAt")
    try:
        ordered_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
    except Exception:
        ordered_at = datetime.now(timezone.utc)

    order = Order(
        brand_id=brand_id,
        customer_id=customer.id if customer else None,
        source="flutterwave",
        channel=_flw_infer_channel(txn),
        status="completed",
        total_amount=amount_ngn,
        original_amount=amount_ngn if currency != "NGN" else None,
        original_currency=currency if currency != "NGN" else None,
        payment_method=_flw_infer_payment_method(txn),
        payment_gateway="flutterwave",
        external_id=external_id,
        ordered_at=ordered_at,
    )
    db.add(order)
    try:
        db.commit()
        logger.info(f"[FLW Webhook] Created order {external_id}")
    except IntegrityError:
        db.rollback()
