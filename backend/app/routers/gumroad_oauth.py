"""
ORYNT — Gumroad OAuth Integration Router

Endpoints:
  GET  /api/integrations/gumroad/auth       → redirect to Gumroad OAuth
  GET  /api/integrations/gumroad/callback   → exchange code for access token
  POST /api/webhooks/gumroad                → handle sale ping webhook

OAuth scopes: view_profile view_sales edit_products
"""

import logging
import os
import json
from urllib.parse import urlencode
from datetime import datetime, timezone

import httpx
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.integration import Integration

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Gumroad Integration"])

ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
GUMROAD_CLIENT_ID = os.getenv("GUMROAD_CLIENT_ID", "")
GUMROAD_CLIENT_SECRET = os.getenv("GUMROAD_CLIENT_SECRET", "")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
GUMROAD_OAUTH_URL = "https://gumroad.com/oauth/authorize"
GUMROAD_TOKEN_URL = "https://api.gumroad.com/oauth/token"


def _encrypt(value: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).encrypt(value.encode()).decode()


def _decrypt(enc: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).decrypt(enc.encode()).decode()


# ── GET /auth ─────────────────────────────────────────────────────────────────

@router.get("/api/integrations/gumroad/auth")
def gumroad_auth(
    brand_id: str = Query(...),
    user: dict = Depends(get_current_user),
):
    """Redirect to Gumroad OAuth consent screen."""
    if not GUMROAD_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GUMROAD_CLIENT_ID not configured.")

    callback_url = f"{BACKEND_BASE_URL}/api/integrations/gumroad/callback"
    params = {
        "client_id": GUMROAD_CLIENT_ID,
        "redirect_uri": callback_url,
        "scope": "view_profile view_sales edit_products",
        # Pass brand_id through state parameter (base64 not needed, simple string)
        "state": brand_id,
    }
    return RedirectResponse(f"{GUMROAD_OAUTH_URL}?{urlencode(params)}")


# ── GET /callback ─────────────────────────────────────────────────────────────

@router.get("/api/integrations/gumroad/callback")
def gumroad_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db),
):
    """Exchange OAuth code for access token and store integration."""
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/dashboard/integrations?gumroad=error&reason={error}")

    if not code or not state:
        return RedirectResponse(f"{FRONTEND_URL}/dashboard/integrations?gumroad=error&reason=missing_code")

    brand_id = state
    callback_url = f"{BACKEND_BASE_URL}/api/integrations/gumroad/callback"

    # Exchange code for token
    try:
        r = httpx.post(
            GUMROAD_TOKEN_URL,
            data={
                "client_id": GUMROAD_CLIENT_ID,
                "client_secret": GUMROAD_CLIENT_SECRET,
                "code": code,
                "redirect_uri": callback_url,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        r.raise_for_status()
        token_data = r.json()
    except Exception as exc:
        logger.error(f"[Gumroad] Token exchange failed: {exc}")
        return RedirectResponse(f"{FRONTEND_URL}/dashboard/integrations?gumroad=error&reason=token_failed")

    access_token = token_data.get("access_token")
    if not access_token:
        return RedirectResponse(f"{FRONTEND_URL}/dashboard/integrations?gumroad=error&reason=no_token")

    # Store encrypted token
    encrypted = _encrypt(access_token)
    existing = db.query(Integration).filter_by(brand_id=brand_id, type="gumroad").first()
    if existing:
        existing.encrypted_key = encrypted
        existing.status = "connected"
        intg = existing
    else:
        intg = Integration(
            brand_id=brand_id,
            type="gumroad",
            status="connected",
            encrypted_key=encrypted,
        )
        db.add(intg)
    db.commit()
    db.refresh(intg)

    # Queue initial pull
    try:
        from app.tasks.gumroad_tasks import pull_gumroad_data
        pull_gumroad_data.delay(intg.id)
    except Exception as exc:
        logger.warning(f"[Gumroad] Could not queue initial pull: {exc}")

    return RedirectResponse(f"{FRONTEND_URL}/dashboard/integrations?gumroad=connected")


# ── POST /webhooks/gumroad ────────────────────────────────────────────────────

@router.post("/api/webhooks/gumroad")
async def gumroad_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Gumroad sale ping webhooks.
    Gumroad sends form-encoded data (not JSON) for sale pings.
    Creates order record immediately on new sale.
    """
    try:
        form = await request.form()
        payload = dict(form)
    except Exception:
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload")

    sale_id = str(payload.get("sale_id") or payload.get("id") or "")
    if not sale_id:
        raise HTTPException(status_code=400, detail="Missing sale_id")

    product_id_ext = str(payload.get("product_id") or "")
    email = str(payload.get("email") or payload.get("buyer_email") or "").lower().strip()
    buyer_name = str(payload.get("full_name") or payload.get("buyer_name") or "").strip() or None

    # Price: Gumroad sends as "price" string like "1000" (cents)
    try:
        price_cents = int(str(payload.get("price", "0")).replace(",", "") or 0)
        total = round(price_cents / 100, 2)
    except ValueError:
        total = 0.0

    # Find brand via product
    from app.models.product import Product
    product = db.query(Product).filter_by(
        external_id=product_id_ext, source="gumroad"
    ).first() if product_id_ext else None

    if not product:
        intg = db.query(Integration).filter_by(type="gumroad", status="connected").first()
        if not intg:
            return {"status": "no_integration"}
        brand_id = intg.brand_id
    else:
        brand_id = product.brand_id

    from app.models.order import Order
    if db.query(Order).filter_by(brand_id=brand_id, external_id=sale_id, source="gumroad").first():
        return {"status": "duplicate"}

    from app.models.customer import Customer
    from app.models.order_item import OrderItem

    customer_id = None
    if email:
        customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
        if not customer:
            customer = Customer(brand_id=brand_id, email=email, name=buyer_name)
            db.add(customer)
            try:
                db.flush()
            except Exception:
                db.rollback()
                customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
        customer_id = customer.id if customer else None

    refunded = str(payload.get("refunded", "false")).lower() == "true"
    status = "refunded" if refunded else "completed"
    country = str(payload.get("ip_country") or payload.get("country") or "?")

    new_order = Order(
        brand_id=brand_id, customer_id=customer_id,
        source="gumroad", channel="gumroad", status=status,
        total_amount=max(total, 0), payment_method="card",
        payment_gateway="gumroad", external_id=sale_id,
        ordered_at=datetime.now(timezone.utc),
        notes=f"Country: {country}",
    )
    db.add(new_order)
    try:
        db.flush()
    except Exception:
        db.rollback()
        return {"status": "failed"}

    if product:
        db.add(OrderItem(
            order_id=new_order.id, brand_id=brand_id,
            product_id=product.id, name=product.name,
            quantity=1, unit_price=total, total_price=total,
        ))

    intg = db.query(Integration).filter_by(brand_id=brand_id, type="gumroad").first()
    if intg:
        intg.transaction_count = (intg.transaction_count or 0) + 1
        intg.last_sync_at = datetime.now(timezone.utc)

    db.commit()
    logger.info(f"[Gumroad Webhook] Created sale {sale_id} for brand {brand_id}")
    return {"status": "ok", "order_id": new_order.id}
