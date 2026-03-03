"""
ORYNT — Webhooks Router
POST /api/webhooks/paystack — receives real-time events from Paystack.
Validates HMAC-SHA512 signature, processes charge.success, transfer.success,
refund.processed events. Always returns 200 immediately.
"""

import os
import hmac
import hashlib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.customer import Customer
from app.models.order import Order

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


def _verify_paystack_signature(raw_body: bytes, signature: str, secret_key: str) -> bool:
    """Compute HMAC-SHA512 of raw body using secret key and compare to header."""
    computed = hmac.new(secret_key.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature)


def _infer_channel(txn: dict) -> str:
    ch = (txn.get("channel") or "").lower()
    metadata = txn.get("metadata") or {}
    custom_fields = metadata.get("custom_fields") or []
    for field in custom_fields:
        val = str(field.get("value", "")).lower()
        if any(w in val for w in ["social", "whatsapp", "instagram"]):
            return "social"
        if any(w in val for w in ["physical", "store", "shop"]):
            return "physical"
    return "website"


def _infer_payment_method(txn: dict) -> str:
    ch = (txn.get("channel") or "").lower()
    if ch == "card":
        return "card"
    if ch in ("bank_transfer", "dedicated_nuban", "bank"):
        return "bank_transfer"
    return "card"


def _get_secret_key_for_brand(brand_id: str, db: Session) -> str | None:
    """Decrypt stored Paystack key for a brand."""
    from app.models.integration import Integration
    from cryptography.fernet import Fernet

    integration = db.query(Integration).filter_by(brand_id=brand_id, type="paystack").first()
    if not integration:
        return None

    enc_key = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
    if not enc_key:
        return None

    try:
        f = Fernet(enc_key.encode())
        return f.decrypt(integration.encrypted_key.encode()).decode()
    except Exception:
        return None


@router.post("/paystack")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive Paystack webhook events.
    Validates HMAC-SHA512 signature, then processes the event.
    Always returns 200 — Paystack retries on non-200 responses.
    """
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    payload = await request.json() if raw_body else {}
    event = payload.get("event", "")
    data = payload.get("data", {})

    # ── Determine brand from event metadata ──────────────────────────────
    # Paystack metadata.brand_id injected at transaction creation, or fall
    # back to finding brand via integration record matching the key.
    metadata = (data.get("metadata") or {})
    brand_id = metadata.get("brand_id")

    # ── Validate HMAC signature ─────────────────────────────────────────
    if brand_id:
        secret_key = _get_secret_key_for_brand(brand_id, db)
        if secret_key and not _verify_paystack_signature(raw_body, signature, secret_key):
            logger.warning(f"[Webhook] Invalid Paystack signature for brand={brand_id}")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    else:
        # Try all connected Paystack integrations to find a matching signature
        from app.models.integration import Integration
        integrations = db.query(Integration).filter_by(type="paystack", status="connected").all()
        matched_brand_id = None
        for integration in integrations:
            secret_key = _get_secret_key_for_brand(integration.brand_id, db)
            if secret_key and _verify_paystack_signature(raw_body, signature, secret_key):
                matched_brand_id = integration.brand_id
                break

        if not matched_brand_id:
            logger.warning("[Webhook] Could not validate Paystack signature — no matching integration")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        brand_id = matched_brand_id

    logger.info(f"[Webhook] Paystack event={event} brand={brand_id}")

    # ── Handle events ────────────────────────────────────────────────────
    if event == "charge.success":
        _handle_charge_success(data, brand_id, db)

    elif event == "transfer.success":
        _handle_status_update(data.get("reference", ""), brand_id, "transferred", db)

    elif event == "refund.processed":
        _handle_status_update(
            (data.get("transaction") or {}).get("reference", ""),
            brand_id, "refunded", db
        )

    return {"status": "ok"}


def _handle_charge_success(txn: dict, brand_id: str, db: Session):
    """Create Customer + Order from a charge.success event."""
    external_id = txn.get("reference", "")
    if not external_id:
        return

    # Dedup check
    existing = db.query(Order).filter_by(
        brand_id=brand_id, external_id=external_id, source="paystack"
    ).first()
    if existing:
        return

    email = (txn.get("customer") or {}).get("email", "").lower().strip()
    customer = None
    if email:
        customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
        if not customer:
            cust = txn.get("customer") or {}
            customer = Customer(
                brand_id=brand_id,
                email=email,
                name=f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or None,
                phone=cust.get("phone"),
            )
            db.add(customer)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()

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
        channel=_infer_channel(txn),
        status="completed",
        total_amount=amount_ngn,
        payment_method=_infer_payment_method(txn),
        payment_gateway="paystack",
        external_id=external_id,
        ordered_at=ordered_at,
    )
    db.add(order)
    try:
        db.commit()
        logger.info(f"[Webhook] Created order {external_id} for brand={brand_id}")
    except IntegrityError:
        db.rollback()
        logger.info(f"[Webhook] Duplicate order {external_id} — skipped")


def _handle_status_update(reference: str, brand_id: str, new_status: str, db: Session):
    """Update order status for transfer.success or refund.processed."""
    if not reference:
        return
    order = db.query(Order).filter_by(
        brand_id=brand_id, external_id=reference, source="paystack"
    ).first()
    if order:
        order.status = new_status
        db.commit()
        logger.info(f"[Webhook] Updated order {reference} → {new_status}")
