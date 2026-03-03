"""
ORYNT — Shopify Background Task
Celery task: pull_shopify_history
Pulls products, customers, and orders (with line items) from Shopify Admin API.
Uses cursor-based pagination (page_info) for all resources.
Shopify amounts are in decimal string (not kobo) — e.g. "1500.00".
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

SHOPIFY_API_VERSION = "2024-01"
ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")


def _decrypt(encrypted: str) -> dict:
    """Decrypt stored credentials JSON: {shop, access_token}"""
    f = Fernet(ENCRYPTION_KEY.encode())
    return json.loads(f.decrypt(encrypted.encode()).decode())


def _shopify_headers(access_token: str) -> dict:
    return {"X-Shopify-Access-Token": access_token, "Content-Type": "application/json"}


def _shop_url(shop: str) -> str:
    return f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}"


def _normalize_nigerian_phone(phone: str | None) -> str | None:
    """Normalize a Nigerian phone number to +234 format."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("234") and len(digits) == 13:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 11:
        return f"+234{digits[1:]}"
    if len(digits) == 10:
        return f"+234{digits}"
    return phone  # Return as-is if unrecognized format


def _paginate_shopify(shop: str, access_token: str, endpoint: str, params: dict):
    """Generator that yields all items from a paginated Shopify endpoint."""
    base = _shop_url(shop)
    headers = _shopify_headers(access_token)
    url = f"{base}{endpoint}"
    next_url = None

    while True:
        req_url = next_url or url
        req_params = {} if next_url else params
        try:
            resp = httpx.get(req_url, headers=headers, params=req_params, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            logger.error(f"[Shopify] Request failed: {exc}")
            break

        data = resp.json()
        # Extract the data key (products, customers, orders, etc.)
        key = [k for k in data.keys() if k != "errors"][0] if data else None
        items = data.get(key, []) if key else []
        yield from items

        # Cursor-based pagination via Link header
        link_header = resp.headers.get("link", "")
        next_match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
        if next_match:
            next_url = next_match.group(1)
        else:
            break


# ── Products ──────────────────────────────────────────────────────────────────

def _sync_products(brand_id: str, shop: str, access_token: str) -> int:
    """Pull all Shopify products and upsert into ORYNT products table."""
    created = 0
    base = _shop_url(shop)
    headers = _shopify_headers(access_token)

    for product in _paginate_shopify(shop, access_token, "/products.json", {"limit": 250}):
        shopify_product_id = str(product.get("id", ""))
        product_name = product.get("title", "Unknown")
        product_type = product.get("product_type") or product.get("vendor") or None

        for variant in (product.get("variants") or []):
            external_id = str(variant.get("id", ""))
            sku = variant.get("sku") or None
            price_str = variant.get("price", "0")
            selling_price = round(float(price_str), 2)

            # Cost price via inventory item (requires read_inventory scope)
            cost_price = None
            inv_item_id = variant.get("inventory_item_id")
            if inv_item_id:
                try:
                    cost_resp = httpx.get(
                        f"{base}/inventory_items/{inv_item_id}.json",
                        headers=headers, timeout=10
                    )
                    if cost_resp.status_code == 200:
                        cost_data = cost_resp.json().get("inventory_item", {})
                        cost_str = cost_data.get("cost")
                        if cost_str:
                            cost_price = round(float(cost_str), 2)
                except Exception:
                    pass

            # Stock level (sum across all locations)
            stock = 0
            try:
                stock_resp = httpx.get(
                    f"{base}/inventory_levels.json",
                    headers=headers, params={"inventory_item_ids": inv_item_id}, timeout=10
                )
                if stock_resp.status_code == 200:
                    levels = stock_resp.json().get("inventory_levels", [])
                    stock = sum(l.get("available", 0) or 0 for l in levels)
            except Exception:
                pass

            # Variant name: "Product Title / Variant Title" or just "Product Title" if default
            variant_title = variant.get("title", "")
            full_name = f"{product_name} — {variant_title}" if variant_title and variant_title != "Default Title" else product_name

            with get_db_session() as db:
                existing = db.query(Product).filter_by(
                    brand_id=brand_id, external_id=external_id, source="shopify"
                ).first()

                if existing:
                    existing.name = full_name
                    existing.sku_code = sku
                    existing.selling_price = selling_price
                    if cost_price is not None:
                        existing.cost_price = cost_price
                    existing.current_stock = stock
                    existing.category = product_type
                    db.commit()
                else:
                    p = Product(
                        brand_id=brand_id,
                        source="shopify",
                        external_id=external_id,
                        name=full_name,
                        sku_code=sku,
                        category=product_type,
                        cost_price=cost_price,
                        selling_price=selling_price,
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

def _sync_customers(brand_id: str, shop: str, access_token: str) -> int:
    """Pull all Shopify customers and upsert into ORYNT customers table."""
    created = 0
    for cust in _paginate_shopify(shop, access_token, "/customers.json", {"limit": 250}):
        email = str(cust.get("email") or "").lower().strip()
        if not email:
            continue
        name = f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or None
        phone = _normalize_nigerian_phone(cust.get("phone"))

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

def _shopify_status_map(financial_status: str, fulfillment_status: str | None) -> str:
    fs = (financial_status or "").lower()
    if fs in ("paid", "partially_paid"):
        return "completed"
    if fs == "pending":
        return "pending"
    if fs in ("refunded", "partially_refunded"):
        return "refunded"
    if fs == "voided":
        return "failed"
    return "pending"


def _sync_orders(brand_id: str, shop: str, access_token: str) -> int:
    """Pull 12 months of Shopify orders + line items."""
    created = 0
    since = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {"limit": 250, "status": "any", "created_at_min": since}

    for order in _paginate_shopify(shop, access_token, "/orders.json", params):
        external_id = str(order.get("id", ""))
        if not external_id:
            continue

        with get_db_session() as db:
            if db.query(Order).filter_by(brand_id=brand_id, external_id=external_id, source="shopify").first():
                continue

            # Customer
            cust_data = order.get("customer") or {}
            email = str(cust_data.get("email") or order.get("email") or "").lower().strip()
            customer = None
            if email:
                customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
                if not customer:
                    name = f"{cust_data.get('first_name', '')} {cust_data.get('last_name', '')}".strip() or None
                    customer = Customer(brand_id=brand_id, email=email, name=name)
                    db.add(customer)
                    try:
                        db.flush()
                    except IntegrityError:
                        db.rollback()
                        customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()

            # Order amounts
            total_price = round(float(order.get("total_price", "0") or 0), 2)
            created_at_raw = order.get("created_at")
            try:
                ordered_at = datetime.fromisoformat(str(created_at_raw).replace("Z", "+00:00"))
            except Exception:
                ordered_at = datetime.now(timezone.utc)

            # Payment method
            gateway = str(order.get("payment_gateway", "shopify") or "shopify").lower()
            if "card" in gateway:
                payment_method = "card"
            elif "bank" in gateway or "transfer" in gateway:
                payment_method = "bank_transfer"
            else:
                payment_method = "card"

            status = _shopify_status_map(
                order.get("financial_status", ""),
                order.get("fulfillment_status")
            )
            currency = order.get("currency", "NGN")

            new_order = Order(
                brand_id=brand_id,
                customer_id=customer.id if customer else None,
                source="shopify",
                channel="website",
                status=status,
                total_amount=total_price,
                original_amount=total_price if currency != "NGN" else None,
                original_currency=currency if currency != "NGN" else None,
                payment_method=payment_method,
                payment_gateway=gateway,
                external_id=external_id,
                ordered_at=ordered_at,
                notes=f"Shopify order #{order.get('name', '')}",
            )
            db.add(new_order)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                continue

            # Line items
            for item in (order.get("line_items") or []):
                ext_variant_id = str(item.get("variant_id") or "")
                ext_product_id = str(item.get("product_id") or "")
                unit_price = round(float(item.get("price", "0") or 0), 2)
                quantity = int(item.get("quantity") or 1)

                # Try to link to ORYNT product
                product = None
                if ext_variant_id:
                    product = db.query(Product).filter_by(
                        brand_id=brand_id, external_id=ext_variant_id, source="shopify"
                    ).first()

                order_item = OrderItem(
                    order_id=new_order.id,
                    brand_id=brand_id,
                    product_id=product.id if product else None,
                    external_product_id=ext_product_id or None,
                    external_variant_id=ext_variant_id or None,
                    name=str(item.get("title") or item.get("name") or "Unknown"),
                    sku=str(item.get("sku") or "") or None,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=round(unit_price * quantity, 2),
                )
                db.add(order_item)

            db.commit()
            created += 1

    return created


# ── Main Task ─────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def pull_shopify_history(self, brand_id: str, integration_id: str):
    """
    Pull full Shopify history: products (with cost/stock), customers, orders (with line items).
    """
    logger.info(f"[Shopify] Starting history pull for brand={brand_id}")

    with get_db_session() as db:
        integration = db.get(Integration, integration_id)
        if not integration:
            logger.error(f"[Shopify] Integration {integration_id} not found")
            return
        creds = _decrypt(integration.encrypted_key)

    shop = creds["shop"]
    access_token = creds["access_token"]

    try:
        products_count = _sync_products(brand_id, shop, access_token)
        logger.info(f"[Shopify] Products done: {products_count}")

        customers_count = _sync_customers(brand_id, shop, access_token)
        logger.info(f"[Shopify] Customers done: {customers_count}")

        orders_count = _sync_orders(brand_id, shop, access_token)
        logger.info(f"[Shopify] Orders done: {orders_count}")
    except Exception as exc:
        logger.error(f"[Shopify] History pull failed: {exc}")
        raise self.retry(exc=exc)

    # Update integration stats
    with get_db_session() as db:
        integration = db.get(Integration, integration_id)
        if integration:
            integration.last_sync_at = datetime.now(timezone.utc)
            integration.transaction_count = orders_count
            db.commit()

    result = {"products": products_count, "customers": customers_count, "orders": orders_count}
    logger.info(f"[Shopify] Done brand={brand_id}: {result}")
    return result
