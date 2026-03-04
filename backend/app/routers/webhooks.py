"""
ORYNT — Webhooks Router
POST /api/webhooks/paystack    — HMAC-SHA512 validation, handles charge.success etc.
POST /api/webhooks/flutterwave — verif-hash validation, handles charge.completed.
POST /api/webhooks/monnify     — HMAC-SHA512 validation, handles SUCCESSFUL_TRANSACTION.
POST /api/webhooks/opay        — HMAC-SHA512 of sorted JSON body, handles payment events.
POST /api/webhooks/mono        — HMAC-SHA512 validation, handles account_updated.
POST /api/webhooks/shopify     — HMAC-SHA256 (Shopify-specific), handles orders/products/inventory.
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


# ── Mono Webhook ──────────────────────────────────────────────────────────────

MONO_SECRET_KEY = os.getenv("MONO_SECRET_KEY", "")


def _verify_mono_sig(raw_body: bytes, provided_sig: str) -> bool:
    """Mono uses HMAC-SHA512 of raw body with the app's MONO_SECRET_KEY."""
    if not MONO_SECRET_KEY:
        return True  # Skip signature check if not configured
    try:
        computed = hmac.new(MONO_SECRET_KEY.encode(), raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(computed, provided_sig)
    except Exception:
        return False


@router.post("/mono")
async def mono_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive Mono Open Banking webhook events.
    Handles mono.events.account_updated — triggers incremental statement pull.
    Always returns 200.
    """
    raw_body = await request.body()
    provided_sig = request.headers.get("mono-webhook-secret", "")

    try:
        payload = _json.loads(raw_body) if raw_body else {}
    except Exception:
        return {"status": "ok"}

    if provided_sig and not _verify_mono_sig(raw_body, provided_sig):
        logger.warning("[Mono Webhook] Invalid signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = payload.get("event", "")
    data = payload.get("data", {})
    account_id = data.get("account", {}).get("_id") or data.get("account_id", "")

    logger.info(f"[Mono Webhook] event={event} account={account_id}")

    if event in ("mono.events.account_updated", "account_updated"):
        # Find the integration by account_id
        from app.models.integration import Integration
        from cryptography.fernet import Fernet

        for intg in _all_integrations("mono", db):
            raw = _decrypt_integration_key(intg)
            if raw and raw == account_id:
                try:
                    from app.tasks.mono_tasks import pull_mono_statements
                    pull_mono_statements.delay(intg.brand_id, intg.id)
                    logger.info(f"[Mono Webhook] Queued statement pull for brand={intg.brand_id}")
                except Exception as exc:
                    logger.warning(f"[Mono Webhook] Could not queue task: {exc}")
                break

    return {"status": "ok"}


# ── Shopify Webhook ──────────────────────────────────────────────────────────────

SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "")


def _verify_shopify_webhook_sig(raw_body: bytes, provided_sig: str) -> bool:
    """Shopify uses HMAC-SHA256 (base64-encoded) with SHOPIFY_API_SECRET."""
    if not SHOPIFY_API_SECRET:
        return True  # Skip in dev if not configured
    import base64
    computed = hmac.new(SHOPIFY_API_SECRET.encode(), raw_body, hashlib.sha256).digest()
    computed_b64 = base64.b64encode(computed).decode()
    return hmac.compare_digest(computed_b64, provided_sig)


def _shopify_find_integration(shop_domain: str, db: Session):
    """Find a Shopify integration by matching the stored shop domain."""
    from app.models.integration import Integration
    from cryptography.fernet import Fernet
    for intg in db.query(Integration).filter_by(type="shopify", status="connected").all():
        raw = _decrypt_integration_key(intg)
        if raw:
            try:
                creds = _json.loads(raw)
                if creds.get("shop") == shop_domain:
                    return intg, creds.get("access_token", "")
            except Exception:
                pass
    return None, None


@router.post("/shopify")
async def shopify_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive Shopify webhook events.
    Validates X-Shopify-Hmac-Sha256 header (HMAC-SHA256 of raw body).
    Handles: orders/create, orders/updated, products/update, inventory_levels/update.
    Always returns 200.
    """
    raw_body = await request.body()
    provided_sig = request.headers.get("x-shopify-hmac-sha256", "")
    topic = request.headers.get("x-shopify-topic", "")
    shop_domain = request.headers.get("x-shopify-shop-domain", "")

    if provided_sig and not _verify_shopify_webhook_sig(raw_body, provided_sig):
        logger.warning(f"[Shopify Webhook] Invalid signature from {shop_domain}")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = _json.loads(raw_body) if raw_body else {}
    except Exception:
        return {"status": "ok"}

    intg, access_token = _shopify_find_integration(shop_domain, db)
    if not intg:
        logger.warning(f"[Shopify Webhook] No integration found for shop {shop_domain}")
        return {"status": "ok"}

    brand_id = intg.brand_id
    logger.info(f"[Shopify Webhook] topic={topic} brand={brand_id}")

    if topic in ("orders/create", "orders/updated"):
        _shopify_handle_order(payload, brand_id, shop_domain, db)
    elif topic == "products/update":
        _shopify_handle_product_update(payload, brand_id, access_token, shop_domain, db)
    elif topic == "inventory_levels/update":
        _shopify_handle_inventory_update(payload, brand_id, db)

    return {"status": "ok"}


def _shopify_handle_order(order: dict, brand_id: str, shop: str, db: Session):
    from app.models.order_item import OrderItem
    from app.models.product import Product

    external_id = str(order.get("id", ""))
    if not external_id:
        return

    # Map financial status
    fs = str(order.get("financial_status", "")).lower()
    status_map = {"paid": "completed", "partially_paid": "completed",
                  "pending": "pending", "refunded": "refunded",
                  "partially_refunded": "refunded", "voided": "failed"}
    status = status_map.get(fs, "pending")

    existing = db.query(Order).filter_by(
        brand_id=brand_id, external_id=external_id, source="shopify"
    ).first()

    if existing:
        # Update status only if changed
        if existing.status != status:
            existing.status = status
            db.commit()
        return

    # New order — find/create customer
    cust_data = order.get("customer") or {}
    email = str(cust_data.get("email") or order.get("email") or "").lower().strip()
    customer = None
    if email:
        customer = _upsert_customer(
            brand_id, email,
            f"{cust_data.get('first_name', '')} {cust_data.get('last_name', '')}".strip() or None,
            cust_data.get("phone"), db
        )

    total_price = round(float(order.get("total_price", "0") or 0), 2)
    currency = order.get("currency", "NGN")
    gateway = str(order.get("payment_gateway", "shopify") or "shopify").lower()

    try:
        ordered_at = datetime.fromisoformat(
            str(order.get("created_at", "")).replace("Z", "+00:00")
        )
    except Exception:
        ordered_at = datetime.now(timezone.utc)

    new_order = Order(
        brand_id=brand_id, customer_id=customer.id if customer else None,
        source="shopify", channel="website", status=status,
        total_amount=total_price,
        original_amount=total_price if currency != "NGN" else None,
        original_currency=currency if currency != "NGN" else None,
        payment_method="card" if "card" in gateway else "bank_transfer",
        payment_gateway=gateway,
        external_id=external_id, ordered_at=ordered_at,
        notes=f"Shopify order #{order.get('name', '')}",
    )
    db.add(new_order)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return

    for item in (order.get("line_items") or []):
        ext_variant_id = str(item.get("variant_id") or "")
        ext_product_id = str(item.get("product_id") or "")
        unit_price = round(float(item.get("price", "0") or 0), 2)
        quantity = int(item.get("quantity") or 1)
        product = None
        if ext_variant_id:
            product = db.query(Product).filter_by(
                brand_id=brand_id, external_id=ext_variant_id, source="shopify"
            ).first()
        oi = OrderItem(
            order_id=new_order.id, brand_id=brand_id,
            product_id=product.id if product else None,
            external_product_id=ext_product_id or None,
            external_variant_id=ext_variant_id or None,
            name=str(item.get("title") or item.get("name") or "Unknown"),
            sku=str(item.get("sku") or "") or None,
            quantity=quantity, unit_price=unit_price,
            total_price=round(unit_price * quantity, 2),
        )
        db.add(oi)
    db.commit()
    logger.info(f"[Shopify Webhook] Created order {external_id}")


def _shopify_handle_product_update(product: dict, brand_id: str, access_token: str, shop: str, db: Session):
    from app.models.product import Product
    for variant in (product.get("variants") or []):
        external_id = str(variant.get("id", ""))
        if not external_id:
            continue
        selling_price = round(float(variant.get("price", "0") or 0), 2)
        existing = db.query(Product).filter_by(
            brand_id=brand_id, external_id=external_id, source="shopify"
        ).first()
        if existing:
            existing.selling_price = selling_price
            variant_title = variant.get("title", "")
            full_name = f"{product.get('title', '')} — {variant_title}" if variant_title and variant_title != "Default Title" else product.get("title", existing.name)
            existing.name = full_name
            db.commit()
            logger.info(f"[Shopify Webhook] Updated product variant {external_id}")


def _shopify_handle_inventory_update(payload: dict, brand_id: str, db: Session):
    from app.models.product import Product
    inventory_item_id = str(payload.get("inventory_item_id", ""))
    available = payload.get("available", 0)
    if not inventory_item_id:
        return
    # Find product by inventory_item_id (stored in notes or look up by external_id pattern)
    # Shopify inventory_items link to variants — we store variant_id as external_id
    # Use a direct update via inventory item if we can match
    logger.info(f"[Shopify Webhook] Inventory update: item={inventory_item_id} available={available}")
    # Best-effort: update all products with matching brand if we stored inv_item_id
    # (Full matching requires storing inv_item_id in product record - future enhancement)


# ── WooCommerce Webhook ───────────────────────────────────────────────────────

def _verify_wc_webhook_sig(raw_body: bytes, provided_sig: str, secret: str) -> bool:
    """WooCommerce uses base64-encoded HMAC-SHA256 with the webhook secret."""
    if not secret:
        return True
    import base64
    computed = hmac.new(secret.encode(), raw_body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(computed).decode(), provided_sig)


def _wc_find_integration(source_url: str, db: Session):
    """Find a WooCommerce integration by matching the stored store_url."""
    from app.models.integration import Integration
    for intg in db.query(Integration).filter_by(type="woocommerce", status="connected").all():
        raw = _decrypt_integration_key(intg)
        if raw:
            try:
                creds = _json.loads(raw)
                stored = creds.get("store_url", "").rstrip("/").replace("https://", "").replace("http://", "")
                src = source_url.rstrip("/").replace("https://", "").replace("http://", "")
                if stored == src:
                    return intg, creds
            except Exception:
                pass
    return None, None


@router.post("/woocommerce")
async def woocommerce_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive WooCommerce webhook events.
    Validates X-WC-Webhook-Signature (base64 HMAC-SHA256).
    Handles: order.created, order.updated, product.updated.
    Always returns 200.
    """
    raw_body = await request.body()
    provided_sig = request.headers.get("x-wc-webhook-signature", "")
    topic = request.headers.get("x-wc-webhook-topic", "")
    source = request.headers.get("x-wc-webhook-source", "")

    try:
        payload = _json.loads(raw_body) if raw_body else {}
    except Exception:
        return {"status": "ok"}

    intg, creds = _wc_find_integration(source, db)
    if not intg:
        logger.warning(f"[WC Webhook] No integration found for {source}")
        return {"status": "ok"}

    webhook_secret = (creds.get("consumer_secret") or "")[:40]
    if provided_sig and not _verify_wc_webhook_sig(raw_body, provided_sig, webhook_secret):
        logger.warning(f"[WC Webhook] Invalid signature from {source}")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    brand_id = intg.brand_id
    logger.info(f"[WC Webhook] topic={topic} brand={brand_id}")

    if topic in ("order.created", "order.updated"):
        _wc_handle_order(payload, brand_id, db)
    elif topic == "product.updated":
        _wc_handle_product(payload, brand_id, db)

    return {"status": "ok"}


def _wc_handle_order(order: dict, brand_id: str, db: Session):
    from app.models.order_item import OrderItem
    from app.models.product import Product

    external_id = str(order.get("id", ""))
    if not external_id:
        return

    status_map = {"processing": "completed", "completed": "completed", "pending": "pending",
                  "on-hold": "pending", "refunded": "refunded", "cancelled": "failed", "failed": "failed"}
    status = status_map.get(str(order.get("status", "")).lower(), "pending")

    existing = db.query(Order).filter_by(brand_id=brand_id, external_id=external_id, source="woocommerce").first()
    if existing:
        if existing.status != status:
            existing.status = status
            db.commit()
        return

    billing = order.get("billing") or {}
    email = str(billing.get("email") or "").lower().strip()
    customer = None
    if email:
        customer = _upsert_customer(
            brand_id, email,
            f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip() or None,
            billing.get("phone"), db,
        )

    total = round(float(order.get("total") or 0), 2)
    currency = order.get("currency", "NGN")
    pm_raw = str(order.get("payment_method_title") or order.get("payment_method") or "other").lower()
    payment_method = "card" if any(x in pm_raw for x in ("card", "stripe", "paystack")) else "bank_transfer" if "bank" in pm_raw else "cash" if "cash" in pm_raw else "card"

    try:
        ordered_at = datetime.fromisoformat(str(order.get("date_created", "")).replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    except Exception:
        ordered_at = datetime.now(timezone.utc)

    new_order = Order(
        brand_id=brand_id, customer_id=customer.id if customer else None,
        source="woocommerce", channel="website", status=status,
        total_amount=total,
        original_amount=total if currency != "NGN" else None,
        original_currency=currency if currency != "NGN" else None,
        payment_method=payment_method,
        payment_gateway=order.get("payment_method") or "woocommerce",
        external_id=external_id, ordered_at=ordered_at,
        notes=f"WooCommerce order #{order.get('number', external_id)}",
    )
    db.add(new_order)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return

    for item in (order.get("line_items") or []):
        ext_pid = str(item.get("product_id") or "")
        unit_price = round(float(item.get("price") or 0), 2)
        quantity = int(item.get("quantity") or 1)
        product = db.query(Product).filter_by(brand_id=brand_id, external_id=ext_pid, source="woocommerce").first() if ext_pid else None
        oi = OrderItem(
            order_id=new_order.id, brand_id=brand_id,
            product_id=product.id if product else None,
            external_product_id=ext_pid or None,
            external_variant_id=str(item.get("variation_id") or "") or None,
            name=str(item.get("name") or "Unknown"),
            sku=str(item.get("sku") or "") or None,
            quantity=quantity, unit_price=unit_price,
            total_price=round(unit_price * quantity, 2),
        )
        db.add(oi)
    db.commit()
    logger.info(f"[WC Webhook] Created order {external_id}")


def _wc_handle_product(product: dict, brand_id: str, db: Session):
    from app.models.product import Product
    external_id = str(product.get("id", ""))
    if not external_id:
        return
    selling_price = round(float(product.get("price") or product.get("regular_price") or 0), 2)
    existing = db.query(Product).filter_by(brand_id=brand_id, external_id=external_id, source="woocommerce").first()
    if existing:
        existing.name = product.get("name") or existing.name
        existing.selling_price = max(selling_price, 0.01)
        existing.current_stock = int(product.get("stock_quantity") or existing.current_stock or 0)
        db.commit()
        logger.info(f"[WC Webhook] Updated product {external_id}")

