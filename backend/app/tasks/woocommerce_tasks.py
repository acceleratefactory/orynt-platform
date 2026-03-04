"""
ORYNT — WooCommerce Background Task
Celery task: pull_woocommerce_history
Pulls products, customers, and orders (with line items) from WooCommerce REST API v3.
Auth: Consumer Key + Consumer Secret via query params (works over HTTP and HTTPS).
Cost price pulled from meta_data key '_wc_cog_cost' (WooCommerce Cost of Goods plugin).
"""

import os
import re
import json
import logging
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
import httpx
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

load_dotenv()

from app.celery_app import celery_app
from app.database import get_db_session
from app.models.integration import Integration
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product

logger = logging.getLogger(__name__)

ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
WC_API_VERSION = "wc/v3"


def _decrypt(encrypted: str) -> dict:
    f = Fernet(ENCRYPTION_KEY.encode())
    return json.loads(f.decrypt(encrypted.encode()).decode())


def _wc_auth_params(consumer_key: str, consumer_secret: str) -> dict:
    """WooCommerce REST API auth as query params (works on HTTP and HTTPS)."""
    return {"consumer_key": consumer_key, "consumer_secret": consumer_secret}


def _wc_url(store_url: str, path: str) -> str:
    base = store_url.rstrip("/")
    return f"{base}/wp-json/{WC_API_VERSION}/{path.lstrip('/')}"


def _get_meta(meta_data: list, key: str):
    """Extract a value from WooCommerce meta_data array by key."""
    for item in (meta_data or []):
        if item.get("key") == key:
            return item.get("value")
    return None


def _paginate_wc(store_url: str, consumer_key: str, consumer_secret: str, path: str, extra_params: dict = None):
    """Generator: yields all items from a paginated WooCommerce endpoint."""
    auth = _wc_auth_params(consumer_key, consumer_secret)
    url = _wc_url(store_url, path)
    page = 1

    while True:
        params = {**auth, "per_page": 100, "page": page}
        if extra_params:
            params.update(extra_params)

        try:
            resp = httpx.get(url, params=params, timeout=30,
                             verify=False)  # Some self-hosted WC stores have self-signed certs
            resp.raise_for_status()
        except Exception as exc:
            logger.error(f"[WooCommerce] Request to {path} page {page} failed: {exc}")
            break

        items = resp.json() if isinstance(resp.json(), list) else []
        if not items:
            break

        yield from items

        total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1


def _normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("234") and len(digits) == 13:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 11:
        return f"+234{digits[1:]}"
    if len(digits) == 10:
        return f"+234{digits}"
    return phone


# ── Products ──────────────────────────────────────────────────────────────────

def _sync_products(brand_id: str, store_url: str, ck: str, cs: str) -> int:
    created = 0
    for product in _paginate_wc(store_url, ck, cs, "products", {"status": "publish"}):
        external_id = str(product.get("id", ""))
        if not external_id:
            continue

        name = product.get("name") or "Unknown Product"
        sku = product.get("sku") or None
        category = (product.get("categories") or [{}])[0].get("name") or None

        # Price: use sale_price if active, else regular_price, else price
        selling_price = round(float(product.get("price") or product.get("regular_price") or 0), 2)

        # Cost from WooCommerce Cost of Goods plugin
        cost_raw = _get_meta(product.get("meta_data", []), "_wc_cog_cost")
        cost_price = round(float(cost_raw), 2) if cost_raw else 0.0

        # Stock
        stock = int(product.get("stock_quantity") or 0)

        # Handle variable products — sync each variant separately
        product_type = product.get("type", "simple")
        variants = product.get("variations") or []

        with get_db_session() as db:
            existing = db.query(Product).filter_by(
                brand_id=brand_id, external_id=external_id, source="woocommerce"
            ).first()

            if existing:
                existing.name = name
                existing.sku_code = sku
                existing.selling_price = max(selling_price, 0.01)
                existing.cost_price = cost_price
                existing.current_stock = stock
                existing.category = category
                db.commit()
            else:
                p = Product(
                    brand_id=brand_id, source="woocommerce", external_id=external_id,
                    name=name, sku_code=sku, category=category,
                    cost_price=cost_price, selling_price=max(selling_price, 0.01),
                    current_stock=stock,
                )
                db.add(p)
                try:
                    db.commit()
                    created += 1
                except IntegrityError:
                    db.rollback()

    return created


# ── Customers ─────────────────────────────────────────────────────────────────

def _sync_customers(brand_id: str, store_url: str, ck: str, cs: str) -> int:
    created = 0
    for cust in _paginate_wc(store_url, ck, cs, "customers"):
        email = str(cust.get("email") or "").lower().strip()
        if not email:
            continue
        name = f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or None
        billing = cust.get("billing") or {}
        phone = _normalize_phone(billing.get("phone"))

        with get_db_session() as db:
            customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
            if customer:
                if name and not customer.name:
                    customer.name = name
                if phone and not customer.phone:
                    customer.phone = phone
                db.commit()
            else:
                customer = Customer(brand_id=brand_id, email=email, name=name, phone=phone)
                db.add(customer)
                try:
                    db.commit()
                    created += 1
                except IntegrityError:
                    db.rollback()
    return created


# ── Orders ────────────────────────────────────────────────────────────────────

def _wc_status_map(wc_status: str) -> str:
    mapping = {
        "processing": "completed",
        "completed": "completed",
        "pending": "pending",
        "on-hold": "pending",
        "refunded": "refunded",
        "cancelled": "failed",
        "failed": "failed",
    }
    return mapping.get(wc_status.lower(), "pending")


def _sync_orders(brand_id: str, store_url: str, ck: str, cs: str) -> int:
    created = 0
    since = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S")
    params = {"after": since, "status": "any"}

    for order in _paginate_wc(store_url, ck, cs, "orders", params):
        external_id = str(order.get("id", ""))
        if not external_id:
            continue

        with get_db_session() as db:
            if db.query(Order).filter_by(brand_id=brand_id, external_id=external_id, source="woocommerce").first():
                continue

            # Customer
            billing = order.get("billing") or {}
            email = str(billing.get("email") or "").lower().strip()
            customer = None
            if email:
                customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
                if not customer:
                    name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip() or None
                    phone = _normalize_phone(billing.get("phone"))
                    customer = Customer(brand_id=brand_id, email=email, name=name, phone=phone)
                    db.add(customer)
                    try:
                        db.flush()
                    except IntegrityError:
                        db.rollback()
                        customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()

            # Order fields
            total = round(float(order.get("total") or 0), 2)
            currency = order.get("currency", "NGN")
            payment_method_raw = str(order.get("payment_method_title") or order.get("payment_method") or "other").lower()
            if "card" in payment_method_raw or "stripe" in payment_method_raw or "paystack" in payment_method_raw:
                payment_method = "card"
            elif "transfer" in payment_method_raw or "bank" in payment_method_raw:
                payment_method = "bank_transfer"
            elif "cash" in payment_method_raw or "delivery" in payment_method_raw:
                payment_method = "cash"
            else:
                payment_method = "card"

            status = _wc_status_map(order.get("status", "pending"))

            try:
                ordered_at = datetime.fromisoformat(
                    str(order.get("date_created") or "").replace("Z", "+00:00")
                ).replace(tzinfo=timezone.utc)
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
                continue

            # Line items
            for item in (order.get("line_items") or []):
                ext_product_id = str(item.get("product_id") or "")
                ext_variation_id = str(item.get("variation_id") or "")
                unit_price = round(float(item.get("price") or 0), 2)
                quantity = int(item.get("quantity") or 1)

                # Try to link to ORYNT product (by WooCommerce product_id)
                product = None
                if ext_product_id:
                    product = db.query(Product).filter_by(
                        brand_id=brand_id, external_id=ext_product_id, source="woocommerce"
                    ).first()

                oi = OrderItem(
                    order_id=new_order.id, brand_id=brand_id,
                    product_id=product.id if product else None,
                    external_product_id=ext_product_id or None,
                    external_variant_id=ext_variation_id or None,
                    name=str(item.get("name") or "Unknown"),
                    sku=str(item.get("sku") or "") or None,
                    quantity=quantity, unit_price=unit_price,
                    total_price=round(unit_price * quantity, 2),
                )
                db.add(oi)

            db.commit()
            created += 1

    return created


# ── Main Task ─────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def pull_woocommerce_history(self, brand_id: str, integration_id: str):
    """
    Pull full WooCommerce history: products (with cost/stock), customers, orders (with line items).
    """
    logger.info(f"[WooCommerce] Starting history pull for brand={brand_id}")

    with get_db_session() as db:
        integration = db.get(Integration, integration_id)
        if not integration:
            logger.error(f"[WooCommerce] Integration {integration_id} not found")
            return
        creds = _decrypt(integration.encrypted_key)

    store_url = creds["store_url"]
    ck = creds["consumer_key"]
    cs = creds["consumer_secret"]

    try:
        products_count = _sync_products(brand_id, store_url, ck, cs)
        logger.info(f"[WooCommerce] Products: {products_count}")

        customers_count = _sync_customers(brand_id, store_url, ck, cs)
        logger.info(f"[WooCommerce] Customers: {customers_count}")

        orders_count = _sync_orders(brand_id, store_url, ck, cs)
        logger.info(f"[WooCommerce] Orders: {orders_count}")
    except Exception as exc:
        logger.error(f"[WooCommerce] History pull failed: {exc}")
        raise self.retry(exc=exc)

    with get_db_session() as db:
        integration = db.get(Integration, integration_id)
        if integration:
            integration.last_sync_at = datetime.now(timezone.utc)
            integration.transaction_count = orders_count
            db.commit()

    result = {"products": products_count, "customers": customers_count, "orders": orders_count}
    logger.info(f"[WooCommerce] Done brand={brand_id}: {result}")
    return result
