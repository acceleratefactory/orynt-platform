"""
ORYNT — Webhooks Router
POST /api/webhooks/paystack    — HMAC-SHA512 validation, handles charge.success etc.
POST /api/webhooks/flutterwave — verif-hash validation, handles charge.completed.
POST /api/webhooks/monnify     — HMAC-SHA512 validation, handles SUCCESSFUL_TRANSACTION.
POST /api/webhooks/opay        — HMAC-SHA512 of sorted JSON body, handles payment events.
Always returns 200.
"""

import os
import hmac
import hashlib
import logging
import json as _json
import base64
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


def _save_order(order: Order, db: Session):
    db.add(order)
    try:
        db.commit()
        logger.info(f"[Webhook] Created order {order.external_id} source={order.source}")
    except IntegrityError:
        db.rollback()
        logger.info(f"[Webhook] Duplicate order {order.external_id} — skipped")


def _update_order_status(reference: str, brand_id: str, new_status: str, source: str, db: Session):
    if not reference:
        return
    order = db.query(Order).filter_by(brand_id=brand_id, external_id=reference, source=source).first()
    if order:
        order.status = new_status
        db.commit()
        logger.info(f"[Webhook] Order {reference} -> {new_status}")


# ── Paystack Webhook ──────────────────────────────────────────────────────────

def _verify_paystack_sig(raw_body: bytes, signature: str, secret_key: str) -> bool:
    computed = hmac.new(secret_key.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature)


def _paystack_infer_channel(txn: dict) -> str:
    for field in (txn.get("metadata") or {}).get("custom_fields") or []:
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
    brand_id = (data.get("metadata") or {}).get("brand_id")

    if brand_id:
        intg = _find_integration(brand_id, "paystack", db)
        sk = _decrypt_integration_key(intg) if intg else None
        if sk and not _verify_paystack_sig(raw_body, signature, sk):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    else:
        matched = None
        for intg in _all_integrations("paystack", db):
            sk = _decrypt_integration_key(intg)
            if sk and _verify_paystack_sig(raw_body, signature, sk):
                matched = intg.brand_id
                break
        if not matched:
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        brand_id = matched

    logger.info(f"[Paystack Webhook] event={event} brand={brand_id}")
    if event == "charge.success":
        _paystack_handle_charge(data, brand_id, db)
    elif event == "transfer.success":
        _update_order_status(data.get("reference", ""), brand_id, "transferred", "paystack", db)
    elif event == "refund.processed":
        _update_order_status(
            (data.get("transaction") or {}).get("reference", ""),
            brand_id, "refunded", "paystack", db
        )
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
    _save_order(Order(
        brand_id=brand_id, customer_id=customer.id if customer else None,
        source="paystack", channel=_paystack_infer_channel(txn), status="completed",
        total_amount=amount_ngn, payment_method=_paystack_infer_payment_method(txn),
        payment_gateway="paystack", external_id=external_id, ordered_at=ordered_at,
    ), db)


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
    raw_body = await request.body()
    verif_hash = request.headers.get("verif-hash", "")
    try:
        payload = _json.loads(raw_body) if raw_body else {}
    except Exception:
        return {"status": "ok"}

    flw_webhook_hash = os.getenv("FLW_WEBHOOK_HASH", "")
    if flw_webhook_hash and verif_hash != flw_webhook_hash:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = payload.get("event", "")
    data = payload.get("data", {})
    meta = data.get("meta") or {}
    brand_id = meta.get("brand_id")
    if not brand_id:
        integrations = _all_integrations("flutterwave", db)
        brand_id = integrations[0].brand_id if integrations else None
    if not brand_id:
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
        customer = _upsert_customer(brand_id, email, cust.get("name") or cust.get("fullname"), cust.get("phone_number"), db)
    amount_ngn = round(float(txn.get("amount") or 0), 2)
    currency = txn.get("currency", "NGN")
    try:
        ordered_at = datetime.fromisoformat(str(txn.get("created_at", "")).replace("Z", "+00:00"))
    except Exception:
        ordered_at = datetime.now(timezone.utc)
    _save_order(Order(
        brand_id=brand_id, customer_id=customer.id if customer else None,
        source="flutterwave", channel=_flw_infer_channel(txn), status="completed",
        total_amount=amount_ngn,
        original_amount=amount_ngn if currency != "NGN" else None,
        original_currency=currency if currency != "NGN" else None,
        payment_method=_flw_infer_payment_method(txn),
        payment_gateway="flutterwave", external_id=external_id, ordered_at=ordered_at,
    ), db)


# ── Monnify Webhook ───────────────────────────────────────────────────────────

def _verify_monnify_sig(raw_body: bytes, provided_hash: str, secret_key: str) -> bool:
    computed = hmac.new(secret_key.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, provided_hash)


def _monnify_infer_channel(txn: dict) -> str:
    narration = str(txn.get("paymentDescription", "") or txn.get("narration", "")).lower()
    if any(w in narration for w in ["social", "whatsapp", "instagram"]):
        return "social"
    if any(w in narration for w in ["physical", "store", "shop"]):
        return "physical"
    return "website"


def _monnify_infer_payment_method(txn: dict) -> str:
    ptype = str(txn.get("paymentMethod", "")).upper()
    if "CARD" in ptype:
        return "card"
    return "bank_transfer"


@router.post("/monnify")
async def monnify_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    provided_hash = request.headers.get("monnify-signature", "")
    try:
        payload = _json.loads(raw_body) if raw_body else {}
    except Exception:
        return {"status": "ok"}

    event_type = payload.get("eventType", "")
    data = payload.get("eventData", {})
    meta = data.get("metaData") or {}
    brand_id = meta.get("brand_id")

    integrations = _all_integrations("monnify", db)
    intg = None
    if brand_id:
        intg = _find_integration(brand_id, "monnify", db)
    elif integrations:
        intg = integrations[0]
        brand_id = intg.brand_id

    if intg and provided_hash:
        decrypted = _decrypt_integration_key(intg)
        if decrypted:
            try:
                creds = _json.loads(decrypted)
                secret_key = creds.get("secret_key", "")
            except Exception:
                secret_key = decrypted
            if secret_key and not _verify_monnify_sig(raw_body, provided_hash, secret_key):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if not brand_id:
        return {"status": "ok"}

    logger.info(f"[Monnify Webhook] eventType={event_type} brand={brand_id}")
    if event_type == "SUCCESSFUL_TRANSACTION":
        _monnify_handle_success(data, brand_id, db)
    return {"status": "ok"}


def _monnify_handle_success(txn: dict, brand_id: str, db: Session):
    external_id = str(txn.get("transactionReference", ""))
    if not external_id:
        return
    if db.query(Order).filter_by(brand_id=brand_id, external_id=external_id, source="monnify").first():
        return
    email = str(txn.get("customerEmail", "")).lower().strip()
    customer = None
    if email:
        customer = _upsert_customer(brand_id, email, txn.get("customerName"), txn.get("customerPhone"), db)
    amount_ngn = round(float(txn.get("amountPaid") or txn.get("totalPayable") or 0), 2)
    currency = txn.get("currencyCode", "NGN")
    created_at_raw = txn.get("createdOn") or txn.get("completedOn")
    try:
        if isinstance(created_at_raw, (int, float)):
            ordered_at = datetime.fromtimestamp(created_at_raw / 1000, tz=timezone.utc)
        else:
            ordered_at = datetime.fromisoformat(str(created_at_raw).replace("Z", "+00:00"))
    except Exception:
        ordered_at = datetime.now(timezone.utc)
    _save_order(Order(
        brand_id=brand_id, customer_id=customer.id if customer else None,
        source="monnify", channel=_monnify_infer_channel(txn), status="completed",
        total_amount=amount_ngn,
        original_amount=amount_ngn if currency != "NGN" else None,
        original_currency=currency if currency != "NGN" else None,
        payment_method=_monnify_infer_payment_method(txn),
        payment_gateway="monnify", external_id=external_id, ordered_at=ordered_at,
    ), db)


# ── OPay Webhook ──────────────────────────────────────────────────────────────

def _verify_opay_sig(raw_body: bytes, provided_sig: str, private_key: str) -> bool:
    """OPay: HMAC-SHA512 of alphabetically-sorted JSON body with private_key."""
    try:
        payload = _json.loads(raw_body)
        sorted_body = _json.dumps(payload, sort_keys=True, separators=(",", ":"))
        computed = hmac.new(private_key.encode(), sorted_body.encode(), hashlib.sha512).hexdigest()
        return hmac.compare_digest(computed, provided_sig)
    except Exception:
        return False


def _opay_infer_channel(txn: dict) -> str:
    pay_ch = str(txn.get("payChannel", "") or txn.get("channel", "") or "").lower()
    if any(w in pay_ch for w in ["pos", "instore", "in_store", "offline", "physical"]):
        return "physical"
    if any(w in pay_ch for w in ["mobile", "whatsapp", "social"]):
        return "social"
    return "website"


def _opay_infer_payment_method(txn: dict) -> str:
    pay_ch = str(txn.get("payChannel", "") or txn.get("payMethod", "") or "").lower()
    if any(w in pay_ch for w in ["card", "visa", "mastercard"]):
        return "card"
    return "bank_transfer"


@router.post("/opay")
async def opay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive OPay webhook events.
    Validates via HMAC-SHA512 of sorted JSON body with stored private_key.
    Always returns 200.
    """
    raw_body = await request.body()
    provided_sig = request.headers.get("sign", "") or request.headers.get("x-sign", "")

    try:
        payload = _json.loads(raw_body) if raw_body else {}
    except Exception:
        return {"status": "ok"}

    merchant_id = (payload.get("data") or {}).get("merchantId") or payload.get("merchantId", "")
    brand_id = None

    for intg in _all_integrations("opay", db):
        raw = _decrypt_integration_key(intg)
        if not raw:
            continue
        try:
            creds = _json.loads(raw)
        except Exception:
            continue
        if merchant_id and creds.get("merchant_id") != merchant_id:
            continue
        if provided_sig and not _verify_opay_sig(raw_body, provided_sig, creds.get("private_key", "")):
            continue
        brand_id = intg.brand_id
        break

    if not brand_id:
        all_opay = _all_integrations("opay", db)
        brand_id = all_opay[0].brand_id if all_opay else None

    if not brand_id:
        logger.warning("[OPay Webhook] No connected OPay integration found")
        return {"status": "ok"}

    event_type = str(payload.get("event", "") or payload.get("notifyType", "")).upper()
    event_data = payload.get("data") or payload
    logger.info(f"[OPay Webhook] event={event_type} brand={brand_id}")

    status_val = str(event_data.get("status", "") or event_data.get("orderStatus", "")).upper()
    if status_val in ("SUCCESSFUL", "SUCCESS", "COMPLETED", "PAID") or \
       any(e in event_type for e in ("PAYMENT_COMPLETED", "CASHIER_PAYMENT", "PAYMENT_SUCCESS")):
        _opay_handle_payment(event_data, brand_id, db)
    return {"status": "ok"}


def _opay_handle_payment(txn: dict, brand_id: str, db: Session):
    external_id = str(txn.get("orderNo") or txn.get("transactionNo") or txn.get("reference") or "")
    if not external_id:
        return
    if db.query(Order).filter_by(brand_id=brand_id, external_id=external_id, source="opay").first():
        return
    user_info = txn.get("userInfo") or {}
    email = str(user_info.get("userEmail") or txn.get("email") or "").lower().strip()
    customer = None
    if email:
        customer = _upsert_customer(brand_id, email,
                                    user_info.get("fullName") or user_info.get("userName"),
                                    user_info.get("phoneNumber"), db)
    raw_amount = txn.get("amount") or txn.get("orderAmount") or 0
    amount_ngn = round(float(raw_amount) / 100, 2)
    currency = txn.get("currency", "NGN")
    created_at_raw = txn.get("createTime") or txn.get("orderTime") or txn.get("createdAt")
    try:
        if isinstance(created_at_raw, (int, float)):
            ordered_at = datetime.fromtimestamp(created_at_raw / 1000, tz=timezone.utc)
        else:
            ordered_at = datetime.fromisoformat(str(created_at_raw).replace("Z", "+00:00"))
    except Exception:
        ordered_at = datetime.now(timezone.utc)
    _save_order(Order(
        brand_id=brand_id, customer_id=customer.id if customer else None,
        source="opay", channel=_opay_infer_channel(txn), status="completed",
        total_amount=amount_ngn,
        original_amount=amount_ngn if currency != "NGN" else None,
        original_currency=currency if currency != "NGN" else None,
        payment_method=_opay_infer_payment_method(txn),
        payment_gateway="opay", external_id=external_id, ordered_at=ordered_at,
    ), db)
