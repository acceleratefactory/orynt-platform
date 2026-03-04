"""
ORYNT — Selar Integration Router

Endpoints:
  POST /api/integrations/selar/connect   → validate API key, queue pull_selar_data
  POST /api/webhooks/selar               → handle order.completed webhook

Selar API key authentication.
Webhook: no signature verification documented — validate via payload structure.
"""

import logging
import os
from cryptography.fernet import Fernet

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.integration import Integration

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Selar Integration"])
ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
SELAR_BASE = "https://selar.co/api/v3"


def _encrypt(value: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).encrypt(value.encode()).decode()


# ── POST /connect ─────────────────────────────────────────────────────────────

class SelarConnectRequest(BaseModel):
    api_key: str
    brand_id: str


@router.post("/api/integrations/selar/connect")
def connect_selar(
    body: SelarConnectRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate Selar API key and queue initial data pull."""
    # Validate key
    try:
        r = httpx.get(
            f"{SELAR_BASE}/products",
            headers={"Authorization": f"Bearer {body.api_key}", "Accept": "application/json"},
            params={"page": 1, "per_page": 1},
            timeout=15,
        )
        if r.status_code == 401:
            raise HTTPException(status_code=400, detail="Invalid Selar API key. Check your Selar dashboard → Settings → API Keys.")
        if r.status_code == 403:
            raise HTTPException(status_code=400, detail="API key does not have permission to read products.")
        r.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=502, detail="Selar API timed out. Try again in a few seconds.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach Selar: {exc}")

    # Store encrypted key
    encrypted = _encrypt(body.api_key)
    existing = db.query(Integration).filter_by(brand_id=body.brand_id, type="selar").first()
    if existing:
        existing.encrypted_key = encrypted
        existing.status = "connected"
        intg = existing
    else:
        intg = Integration(
            brand_id=body.brand_id,
            type="selar",
            status="connected",
            encrypted_key=encrypted,
        )
        db.add(intg)
    db.commit()
    db.refresh(intg)

    # Queue sync
    try:
        from app.tasks.selar_tasks import pull_selar_data
        pull_selar_data.delay(intg.id)
    except Exception as exc:
        logger.warning(f"[Selar] Could not queue initial pull: {exc}")

    return {
        "status": "connected",
        "integration_id": intg.id,
        "message": "Selar connected. Syncing products and orders in the background.",
    }


# ── POST /webhooks/selar ──────────────────────────────────────────────────────

@router.post("/api/webhooks/selar")
async def selar_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Selar webhook events (order.completed).
    Creates order record immediately on new sale.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event") or payload.get("type") or ""
    if event not in ("order.completed", "order.paid", "sale"):
        return {"status": "ignored", "event": event}

    order_data = payload.get("data") or payload.get("order") or payload
    order_id = str(order_data.get("id") or order_data.get("reference") or "")
    if not order_id:
        raise HTTPException(status_code=400, detail="Missing order ID in webhook payload")

    # Find the matching Selar integration by product
    product_id_ext = str(order_data.get("product_id") or "")

    from app.models.product import Product
    product = db.query(Product).filter_by(
        external_id=product_id_ext, source="selar"
    ).first() if product_id_ext else None

    if not product:
        # Try to find any selar integration
        intg = db.query(Integration).filter_by(type="selar", status="connected").first()
        if not intg:
            return {"status": "no_integration"}
        brand_id = intg.brand_id
    else:
        brand_id = product.brand_id

    # Check duplicate
    from app.models.order import Order
    if db.query(Order).filter_by(brand_id=brand_id, external_id=order_id, source="selar").first():
        return {"status": "duplicate"}

    # Build order
    from datetime import datetime, timezone
    from app.models.customer import Customer
    from app.models.order import Order
    from app.models.order_item import OrderItem

    buyer = order_data.get("buyer") or order_data.get("customer") or {}
    email = str(buyer.get("email") or order_data.get("buyer_email") or "").lower().strip()
    name = str(buyer.get("name") or order_data.get("buyer_name") or "").strip() or None
    total = float(order_data.get("amount") or order_data.get("total") or 0)

    customer_id = None
    if email:
        customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
        if not customer:
            customer = Customer(brand_id=brand_id, email=email, name=name)
            db.add(customer)
            try:
                db.flush()
            except Exception:
                db.rollback()
                customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
        customer_id = customer.id if customer else None

    new_order = Order(
        brand_id=brand_id, customer_id=customer_id,
        source="selar", channel="selar", status="completed",
        total_amount=max(total, 0), payment_method="card",
        payment_gateway="selar", external_id=order_id,
        ordered_at=datetime.now(timezone.utc),
    )
    db.add(new_order)
    try:
        db.flush()
    except Exception:
        db.rollback()
        return {"status": "failed", "reason": "Could not save order"}

    if product:
        db.add(OrderItem(
            order_id=new_order.id, brand_id=brand_id,
            product_id=product.id, name=product.name,
            quantity=1, unit_price=total, total_price=total,
        ))

    # Update integration sync count
    intg = db.query(Integration).filter_by(brand_id=brand_id, type="selar").first()
    if intg:
        intg.transaction_count = (intg.transaction_count or 0) + 1
        intg.last_sync_at = datetime.now(timezone.utc)

    db.commit()
    logger.info(f"[Selar Webhook] Created order {order_id} for brand {brand_id}")
    return {"status": "ok", "order_id": new_order.id}
