"""
ORYNT — Selar Integration Tasks

Celery tasks for Selar digital product platform.
API Key authentication. All products have is_digital = True.

Selar API base: https://selar.co/api/v3/
Headers: Authorization: Bearer {api_key}
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
SELAR_BASE = "https://selar.co/api/v3"

SELAR_STATUS_MAP = {
    "completed": "completed",
    "pending": "pending",
    "failed": "failed",
    "refunded": "refunded",
    "cancelled": "cancelled",
    "processing": "processing",
}


def _decrypt(enc: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).decrypt(enc.encode()).decode()


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }


def _safe_float(val) -> float:
    try:
        return round(float(val or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _safe_dt(val) -> datetime:
    if not val:
        return datetime.now(timezone.utc)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S+00:00", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(val), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


# ── pull_selar_data ────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def pull_selar_data(self, integration_id: str, since: datetime = None):
    """Full (or incremental) sync for one Selar integration."""
    logger.info(f"[Selar] Pulling data for integration={integration_id}")

    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if not intg:
            logger.error(f"[Selar] Integration {integration_id} not found")
            return
        api_key = _decrypt(intg.encrypted_key)
        brand_id = intg.brand_id

    products_count = _sync_selar_products(api_key, brand_id)
    orders_count = _sync_selar_orders(api_key, brand_id, since)

    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if intg:
            intg.last_sync_at = datetime.now(timezone.utc)
            intg.transaction_count = (intg.transaction_count or 0) + orders_count
            intg.status = "connected"
            db.commit()

    logger.info(f"[Selar] Done integration={integration_id}: products={products_count}, orders={orders_count}")
    return {"products": products_count, "orders": orders_count}


def _sync_selar_products(api_key: str, brand_id: str) -> int:
    created = 0
    page = 1
    hdrs = _headers(api_key)
    while True:
        try:
            r = httpx.get(f"{SELAR_BASE}/products", headers=hdrs,
                          params={"page": page, "per_page": 100}, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            logger.warning(f"[Selar] Products page {page} failed: {exc}")
            break

        items = data.get("data", data) if isinstance(data, dict) else data
        if not items:
            break

        for product in items:
            pid = str(product.get("id") or product.get("slug") or "")
            name = str(product.get("name") or product.get("title") or f"Product {pid}")
            price = _safe_float(product.get("price") or product.get("amount"))
            sku = str(product.get("sku") or product.get("slug") or "") or None
            category = str(product.get("category") or product.get("type") or "digital")

            with get_db_session() as db:
                existing = db.query(Product).filter_by(
                    brand_id=brand_id, external_id=pid, source="selar"
                ).first()
                if existing:
                    existing.name = name
                    existing.selling_price = max(price, 0.01)
                    db.commit()
                else:
                    p = Product(
                        brand_id=brand_id, source="selar", external_id=pid,
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

        # Pagination
        next_page = None
        if isinstance(data, dict):
            links = data.get("links", {})
            meta = data.get("meta", {})
            next_page = links.get("next") or (
                page + 1 if meta.get("current_page", page) < meta.get("last_page", page) else None
            )
        if not next_page or len(items) < 100:
            break
        page += 1

    return created


def _sync_selar_orders(api_key: str, brand_id: str, since: datetime = None) -> int:
    created = 0
    page = 1
    hdrs = _headers(api_key)
    params: dict = {"page": page, "per_page": 100}
    if since:
        params["from"] = since.strftime("%Y-%m-%d")

    while True:
        params["page"] = page
        try:
            r = httpx.get(f"{SELAR_BASE}/orders", headers=hdrs, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            logger.warning(f"[Selar] Orders page {page} failed: {exc}")
            break

        items = data.get("data", data) if isinstance(data, dict) else data
        if not items:
            break

        for order in items:
            oid = str(order.get("id") or order.get("reference") or "")
            if not oid:
                continue

            # Duplicate check
            with get_db_session() as db:
                if db.query(Order).filter_by(
                    brand_id=brand_id, external_id=oid, source="selar"
                ).first():
                    continue

            raw_status = str(order.get("status") or "completed").lower()
            status = SELAR_STATUS_MAP.get(raw_status, "completed")
            total = _safe_float(order.get("amount") or order.get("total"))
            ordered_at = _safe_dt(order.get("created_at") or order.get("date"))
            payment_method = str(order.get("payment_method") or "card").lower()

            # Extract customer
            buyer = order.get("buyer") or order.get("customer") or {}
            customer_email = str(buyer.get("email") or order.get("buyer_email") or "").lower().strip()
            customer_name = str(buyer.get("name") or order.get("buyer_name") or "").strip() or None

            # Product
            product_id_ext = str(order.get("product_id") or order.get("product", {}).get("id") or "")

            with get_db_session() as db:
                # Find or create customer
                customer_id = None
                if customer_email:
                    customer = db.query(Customer).filter_by(
                        brand_id=brand_id, email=customer_email
                    ).first()
                    if not customer:
                        customer = Customer(
                            brand_id=brand_id, email=customer_email, name=customer_name
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

                # Find product
                product = db.query(Product).filter_by(
                    brand_id=brand_id, external_id=product_id_ext, source="selar"
                ).first() if product_id_ext else None

                new_order = Order(
                    brand_id=brand_id, customer_id=customer_id,
                    source="selar", channel="selar", status=status,
                    total_amount=max(total, 0), payment_method=payment_method,
                    payment_gateway="selar", external_id=oid, ordered_at=ordered_at,
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
                        product_id=product.id,
                        name=product.name,
                        quantity=int(order.get("quantity") or 1),
                        unit_price=total,
                        total_price=total,
                    )
                    db.add(oi)

                db.commit()
                created += 1

        if len(items) < 100:
            break
        page += 1

    return created


# ── Nightly sync ───────────────────────────────────────────────────────────────

@celery_app.task
def nightly_selar_sync():
    """Pull new Selar orders since last_sync_at for all connected integrations."""
    logger.info("[Selar] Nightly sync started")
    queued = 0
    with get_db_session() as db:
        intgs = db.query(Integration).filter_by(type="selar", status="connected").all()
        jobs = [(i.id, i.last_sync_at) for i in intgs]

    for intg_id, last_sync in jobs:
        since = last_sync or (datetime.now(timezone.utc) - timedelta(days=1))
        pull_selar_data.delay(intg_id, since)
        queued += 1

    logger.info(f"[Selar] Nightly sync queued {queued} jobs")
    return {"queued": queued}
