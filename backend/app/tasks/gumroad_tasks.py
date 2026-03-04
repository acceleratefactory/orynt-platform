"""
ORYNT — Gumroad Integration Tasks

Celery tasks for Gumroad digital product platform.
OAuth 2.0 authentication. All products have is_digital = True.

Gumroad API base: https://api.gumroad.com/v2/
Auth: Bearer token (access_token from OAuth)
"""

import logging
import os
from datetime import datetime, timezone, timedelta

import httpx
from cryptography.fernet import Fernet
from sqlalchemy.exc import IntegrityError

from app.celery_app import celery_app
from app.database import get_db_session
from app.models.customer import Customer
from app.models.integration import Integration
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product

logger = logging.getLogger(__name__)
ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
GUMROAD_BASE = "https://api.gumroad.com/v2"


def _decrypt(enc: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).decrypt(enc.encode()).decode()


def _safe_float(val) -> float:
    try:
        return round(float(val or 0) / 100, 2)  # Gumroad amounts are in cents
    except (TypeError, ValueError):
        return 0.0


def _safe_dt(val) -> datetime:
    if not val:
        return datetime.now(timezone.utc)
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S+00:00",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(val), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


# ── pull_gumroad_data ─────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def pull_gumroad_data(self, integration_id: str, since: datetime = None):
    """Full (or incremental) sync for one Gumroad integration."""
    logger.info(f"[Gumroad] Pulling data for integration={integration_id}")

    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if not intg:
            logger.error(f"[Gumroad] Integration {integration_id} not found")
            return
        access_token = _decrypt(intg.encrypted_key)
        brand_id = intg.brand_id

    products_count = _sync_gumroad_products(access_token, brand_id)
    orders_count = _sync_gumroad_sales(access_token, brand_id, since)

    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if intg:
            intg.last_sync_at = datetime.now(timezone.utc)
            intg.transaction_count = (intg.transaction_count or 0) + orders_count
            intg.status = "connected"
            db.commit()

    logger.info(f"[Gumroad] Done integration={integration_id}: products={products_count}, sales={orders_count}")
    return {"products": products_count, "sales": orders_count}


def _gumroad_headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def _sync_gumroad_products(access_token: str, brand_id: str) -> int:
    created = 0
    try:
        r = httpx.get(
            f"{GUMROAD_BASE}/products",
            headers=_gumroad_headers(access_token),
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        logger.warning(f"[Gumroad] Products fetch failed: {exc}")
        return 0

    if not data.get("success"):
        logger.warning(f"[Gumroad] Products API returned success=false: {data}")
        return 0

    for product in data.get("products", []):
        pid = str(product.get("id") or "")
        name = str(product.get("name") or f"Product {pid}")
        price_cents = int(product.get("price", 0) or 0)
        price = round(price_cents / 100, 2)
        sku = str(product.get("custom_permalink") or pid)
        category = "digital"
        currency = str(product.get("currency") or "USD").upper()
        description = str(product.get("description") or "")[:500]

        with get_db_session() as db:
            existing = db.query(Product).filter_by(
                brand_id=brand_id, external_id=pid, source="gumroad"
            ).first()
            if existing:
                existing.name = name
                existing.selling_price = max(price, 0.01)
                db.commit()
            else:
                p = Product(
                    brand_id=brand_id, source="gumroad", external_id=pid,
                    name=name, sku_code=sku, category=category,
                    selling_price=max(price, 0.01), cost_price=0,
                    current_stock=0, is_digital=True,
                )
                db.add(p)
                try:
                    db.commit()
                    created += 1
                except IntegrityError:
                    db.rollback()

    return created


def _sync_gumroad_sales(access_token: str, brand_id: str, since: datetime = None) -> int:
    created = 0
    page_key = None
    hdrs = _gumroad_headers(access_token)

    while True:
        params: dict = {}
        if since:
            params["after"] = since.strftime("%Y-%m-%d")
        if page_key:
            params["page_key"] = page_key

        try:
            r = httpx.get(f"{GUMROAD_BASE}/sales", headers=hdrs, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            logger.warning(f"[Gumroad] Sales fetch failed: {exc}")
            break

        if not data.get("success"):
            logger.warning(f"[Gumroad] Sales API returned success=false: {data}")
            break

        sales = data.get("sales", [])
        if not sales:
            break

        for sale in sales:
            sid = str(sale.get("id") or "")
            if not sid:
                continue

            # Duplicate check
            with get_db_session() as db:
                if db.query(Order).filter_by(
                    brand_id=brand_id, external_id=sid, source="gumroad"
                ).first():
                    continue

            # Map fields
            refunded = bool(sale.get("refunded"))
            disputed = bool(sale.get("disputed"))
            chargebacked = bool(sale.get("chargebacked"))
            if chargebacked or disputed:
                status = "failed"
            elif refunded:
                status = "refunded"
            else:
                status = "completed"

            price_cents = int(sale.get("price", 0) or 0)
            total = round(price_cents / 100, 2)
            ordered_at = _safe_dt(sale.get("created_at") or sale.get("sale_timestamp"))
            customer_email = str(sale.get("email") or sale.get("buyer_email") or "").lower().strip()
            customer_name = str(sale.get("full_name") or sale.get("buyer_name") or "").strip() or None
            product_id_ext = str(sale.get("product_id") or "")
            payment_method = "card"

            with get_db_session() as db:
                # Find or create customer
                customer_id = None
                if customer_email:
                    customer = db.query(Customer).filter_by(
                        brand_id=brand_id, email=customer_email
                    ).first()
                    if not customer:
                        customer = Customer(
                            brand_id=brand_id,
                            email=customer_email,
                            name=customer_name,
                            external_id=str(sale.get("buyer_id") or ""),
                        )
                        db.add(customer)
                        try:
                            db.flush()
                        except IntegrityError:
                            db.rollback()
                            customer = db.query(Customer).filter_by(
                                brand_id=brand_id, email=customer_email
                            ).first()
                    customer_id = customer.id if customer else None

                product = db.query(Product).filter_by(
                    brand_id=brand_id, external_id=product_id_ext, source="gumroad"
                ).first() if product_id_ext else None

                new_order = Order(
                    brand_id=brand_id, customer_id=customer_id,
                    source="gumroad", channel="gumroad", status=status,
                    total_amount=max(total, 0), payment_method=payment_method,
                    payment_gateway="gumroad", external_id=sid, ordered_at=ordered_at,
                    notes=f"Country: {sale.get('ip_country', '?')}",
                )
                db.add(new_order)
                try:
                    db.flush()
                except IntegrityError:
                    db.rollback()
                    continue

                if product:
                    oi = OrderItem(
                        order_id=new_order.id, brand_id=brand_id,
                        product_id=product.id, name=product.name,
                        quantity=int(sale.get("quantity") or 1),
                        unit_price=total,
                        total_price=total,
                    )
                    db.add(oi)

                db.commit()
                created += 1

        page_key = data.get("next_page_key")
        if not page_key or len(sales) < 10:
            break

    return created


# ── Nightly sync ───────────────────────────────────────────────────────────────

@celery_app.task
def nightly_gumroad_sync():
    """Pull new Gumroad sales since last_sync_at for all connected integrations."""
    logger.info("[Gumroad] Nightly sync started")
    queued = 0
    with get_db_session() as db:
        intgs = db.query(Integration).filter_by(type="gumroad", status="connected").all()
        jobs = [(i.id, i.last_sync_at) for i in intgs]

    for intg_id, last_sync in jobs:
        since = last_sync or (datetime.now(timezone.utc) - timedelta(days=1))
        pull_gumroad_data.delay(intg_id, since)
        queued += 1

    logger.info(f"[Gumroad] Nightly sync queued {queued} jobs")
    return {"queued": queued}
