"""
ORYNT — Reseller Platform Custom Ingestion Tasks

Celery tasks for the founder's custom WordPress reseller platform.
Uses direct MySQL connection — NOT standard WooCommerce REST API.
Custom tables: wp_storefronts, wp_reseller_products, wp_postmeta,
               wp_woocommerce_order_itemmeta, wp_platform_ledger, wp_fulfillment_events

Task flow:
  1. bulk_create_reseller_brands  — creates one ORYNT brand per active storefront
  2. pull_reseller_storefront_data — syncs products + orders for one storefront brand
  3. nightly_reseller_sync         — runs every night at 2am WAT (incremental orders only)
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
import pymysql
import pymysql.cursors
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

load_dotenv()

from app.celery_app import celery_app
from app.database import get_db_session
from app.models.brand import Brand
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.integration import Integration

logger = logging.getLogger(__name__)
ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _decrypt_creds(encrypted: str) -> dict:
    f = Fernet(ENCRYPTION_KEY.encode())
    return json.loads(f.decrypt(encrypted.encode()).decode())


def _get_mysql_conn(creds: dict):
    """Open a pymysql connection to the reseller platform database."""
    return pymysql.connect(
        host=creds["db_host"],
        user=creds["db_user"],
        password=creds["db_password"],
        database=creds["db_name"],
        port=int(creds.get("db_port", 3306)),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        read_timeout=30,
    )


def _prefix(creds: dict, table: str) -> str:
    """Return prefixed table name."""
    prefix = creds.get("db_prefix", "wp_")
    # Strip the base wp_ and add the actual prefix
    bare = table[len("wp_"):]
    return f"{prefix}{bare}"


def _wc_status_to_orynt(wc_status: str) -> str:
    mapping = {
        "wc-completed": "completed",
        "wc-processing": "completed",
        "wc-pending": "pending",
        "wc-on-hold": "pending",
        "wc-refunded": "refunded",
        "wc-cancelled": "failed",
        "wc-failed": "failed",
        "publish": "completed",
        "completed": "completed",
        "processing": "completed",
        "pending": "pending",
        "refunded": "refunded",
        "cancelled": "failed",
    }
    return mapping.get(wc_status.lower(), "pending")


# ── Task 1: Bulk Create Brands ────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def bulk_create_reseller_brands(self, platform_integration_id: str):
    """
    Create one ORYNT brand per active storefront in wp_storefronts.
    Then queue pull_reseller_storefront_data for each new brand.
    """
    logger.info(f"[Reseller] Starting bulk brand creation for integration={platform_integration_id}")

    with get_db_session() as db:
        intg = db.get(Integration, platform_integration_id)
        if not intg:
            logger.error(f"[Reseller] Integration {platform_integration_id} not found")
            return
        creds = _decrypt_creds(intg.encrypted_key)
        org_id = creds["organization_id"]

    storefronts_tbl = _prefix(creds, "wp_storefronts")
    brands_created = 0
    brand_jobs = []  # (brand_id, integration_id, storefront_row)

    try:
        conn = _get_mysql_conn(creds)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, reseller_id, store_name, subdomain, domain "
                    f"FROM {storefronts_tbl} WHERE active = 1"
                )
                storefronts = cur.fetchall()
    except Exception as exc:
        logger.error(f"[Reseller] Could not fetch storefronts: {exc}")
        raise self.retry(exc=exc)

    for sf in storefronts:
        storefront_id = sf["id"]
        reseller_id = sf["reseller_id"]
        store_name = sf["store_name"] or f"Store {storefront_id}"

        with get_db_session() as db:
            # Check if brand already exists for this storefront
            existing_intg = db.query(Integration).filter_by(
                type="reseller_platform_storefront"
            ).all()
            already_exists = False
            for ei in existing_intg:
                try:
                    ec = _decrypt_creds(ei.encrypted_key)
                    if str(ec.get("storefront_id")) == str(storefront_id):
                        already_exists = True
                        brand_jobs.append((ei.brand_id, ei.id, sf))
                        break
                except Exception:
                    pass

            if already_exists:
                continue

            # Create new brand for this storefront
            brand = Brand(
                organization_id=org_id,
                name=store_name,
                category="reseller",
                seller_type="website",
                onboarding_completed=True,
            )
            db.add(brand)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                continue

            # Build per-storefront credentials (inherit DB creds + storefront metadata)
            sf_creds = {**creds, "storefront_id": storefront_id, "reseller_id": reseller_id}
            encrypted_sf = Fernet(ENCRYPTION_KEY.encode()).encrypt(
                json.dumps(sf_creds).encode()
            ).decode()

            sf_intg = Integration(
                brand_id=brand.id,
                type="reseller_platform_storefront",
                status="connected",
                encrypted_key=encrypted_sf,
            )
            db.add(sf_intg)
            db.commit()
            db.refresh(sf_intg)
            brands_created += 1
            brand_jobs.append((brand.id, sf_intg.id, sf))
            logger.info(f"[Reseller] Created brand '{store_name}' (storefront {storefront_id})")

    logger.info(f"[Reseller] Created {brands_created} new brands. Queuing data pulls...")

    # Queue per-storefront data pull
    for brand_id, sf_intg_id, sf in brand_jobs:
        pull_reseller_storefront_data.delay(brand_id, sf_intg_id)

    # Update platform integration stats
    with get_db_session() as db:
        intg = db.get(Integration, platform_integration_id)
        if intg:
            intg.last_sync_at = datetime.now(timezone.utc)
            intg.transaction_count = len(brand_jobs)
            db.commit()

    return {"brands_created": brands_created, "total_storefronts": len(storefronts)}


# ── Task 2: Pull Storefront Data ──────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def pull_reseller_storefront_data(self, brand_id: str, integration_id: str, since: datetime = None):
    """
    Pull products and orders for one reseller storefront.
    If `since` is provided (incremental sync), only pull orders after that date.
    """
    logger.info(f"[Reseller] Pulling data for brand={brand_id}")

    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if not intg:
            logger.error(f"[Reseller] Integration {integration_id} not found")
            return
        creds = _decrypt_creds(intg.encrypted_key)

    storefront_id = creds["storefront_id"]
    reseller_id = creds["reseller_id"]

    try:
        conn = _get_mysql_conn(creds)
    except Exception as exc:
        logger.error(f"[Reseller] DB connection failed: {exc}")
        raise self.retry(exc=exc)

    with conn:
        products_count = _sync_reseller_products(conn, creds, brand_id, storefront_id)
        orders_count = _sync_reseller_orders(conn, creds, brand_id, reseller_id, since)

    # Update last_sync_at
    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if intg:
            intg.last_sync_at = datetime.now(timezone.utc)
            intg.transaction_count = (intg.transaction_count or 0) + orders_count
            db.commit()

    result = {"products": products_count, "orders": orders_count, "brand_id": brand_id}
    logger.info(f"[Reseller] Done brand={brand_id}: {result}")
    return result


def _sync_reseller_products(conn, creds: dict, brand_id: str, storefront_id) -> int:
    """Sync products for one storefront using the exact SQL from the spec."""
    p = lambda t: _prefix(creds, t)
    query = f"""
        SELECT rp.id, rp.wholesale_product_id, rp.storefront_id, rp.reseller_price,
               COALESCE(rp.reseller_title, p.post_title) as product_name,
               pm_cost.meta_value as cost_price,
               pm_stock.meta_value as stock_quantity,
               pm_sku.meta_value as sku
        FROM {p('wp_reseller_products')} rp
        JOIN {p('wp_posts')} p ON p.ID = rp.wholesale_product_id
        LEFT JOIN {p('wp_postmeta')} pm_cost
            ON pm_cost.post_id = rp.wholesale_product_id AND pm_cost.meta_key = 'base_price'
        LEFT JOIN {p('wp_postmeta')} pm_stock
            ON pm_stock.post_id = rp.wholesale_product_id AND pm_stock.meta_key = 'stock_quantity'
        LEFT JOIN {p('wp_postmeta')} pm_sku
            ON pm_sku.post_id = rp.wholesale_product_id AND pm_sku.meta_key = 'sku'
        WHERE rp.storefront_id = %s AND rp.active = 1
    """
    with conn.cursor() as cur:
        cur.execute(query, (storefront_id,))
        rows = cur.fetchall()

    created = 0
    for row in rows:
        external_id = str(row["id"])
        name = str(row["product_name"] or "Unknown Product")
        selling_price = round(float(row["reseller_price"] or 0), 2)
        cost_price = round(float(row["cost_price"] or 0), 2) if row["cost_price"] else 0.0
        stock = int(row["stock_quantity"] or 0) if row["stock_quantity"] else 0
        sku = str(row["sku"] or "") or None

        with get_db_session() as db:
            existing = db.query(Product).filter_by(
                brand_id=brand_id, external_id=external_id, source="reseller_platform"
            ).first()
            if existing:
                existing.name = name
                existing.selling_price = max(selling_price, 0.01)
                existing.cost_price = cost_price
                existing.current_stock = stock
                db.commit()
            else:
                product = Product(
                    brand_id=brand_id, source="reseller_platform",
                    external_id=external_id, name=name, sku_code=sku,
                    selling_price=max(selling_price, 0.01),
                    cost_price=cost_price, current_stock=stock,
                )
                db.add(product)
                try:
                    db.commit()
                    created += 1
                except IntegrityError:
                    db.rollback()
    return created


def _sync_reseller_orders(conn, creds: dict, brand_id: str, reseller_id, since: datetime = None) -> int:
    """Sync orders for one reseller using the exact SQL from the spec."""
    p = lambda t: _prefix(creds, t)
    since_clause = ""
    params = [str(reseller_id)]
    if since:
        since_clause = "AND o.post_date > %s"
        params.append(since.strftime("%Y-%m-%d %H:%M:%S"))

    query = f"""
        SELECT o.ID as order_id, o.post_date as ordered_at, o.post_status as order_status,
               oi.order_item_id, oi.order_item_name,
               oim_reseller.meta_value as reseller_id,
               oim_cost.meta_value as base_price,
               oim_markup.meta_value as reseller_markup,
               oim_fee.meta_value as platform_fee,
               oim_qty.meta_value as quantity
        FROM {p('wp_posts')} o
        JOIN {p('wp_woocommerce_order_items')} oi ON oi.order_id = o.ID
        LEFT JOIN {p('wp_woocommerce_order_itemmeta')} oim_reseller
            ON oim_reseller.order_item_id = oi.order_item_id AND oim_reseller.meta_key = '_reseller_id'
        LEFT JOIN {p('wp_woocommerce_order_itemmeta')} oim_cost
            ON oim_cost.order_item_id = oi.order_item_id AND oim_cost.meta_key = '_base_price'
        LEFT JOIN {p('wp_woocommerce_order_itemmeta')} oim_markup
            ON oim_markup.order_item_id = oi.order_item_id AND oim_markup.meta_key = '_reseller_markup'
        LEFT JOIN {p('wp_woocommerce_order_itemmeta')} oim_fee
            ON oim_fee.order_item_id = oi.order_item_id AND oim_fee.meta_key = '_platform_fee'
        LEFT JOIN {p('wp_woocommerce_order_itemmeta')} oim_qty
            ON oim_qty.order_item_id = oi.order_item_id AND oim_qty.meta_key = '_qty'
        WHERE o.post_type = 'shop_order'
        AND oim_reseller.meta_value = %s
        {since_clause}
        ORDER BY o.post_date DESC
    """
    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    # Group rows by order_id to build one Order + multiple OrderItems
    orders_map: dict = {}
    for row in rows:
        oid = str(row["order_id"])
        if oid not in orders_map:
            orders_map[oid] = {"row": row, "items": []}
        orders_map[oid]["items"].append(row)

    created = 0
    for order_id, data in orders_map.items():
        row = data["row"]
        items = data["items"]

        # Calculate total: sum of (base_price + markup) * qty per line item
        total = 0.0
        for item in items:
            base = float(item["base_price"] or 0)
            markup = float(item["reseller_markup"] or 0)
            qty = int(item["quantity"] or 1)
            total += (base + markup) * qty

        with get_db_session() as db:
            if db.query(Order).filter_by(brand_id=brand_id, external_id=order_id, source="reseller_platform").first():
                continue

            try:
                ordered_at = row["ordered_at"]
                if isinstance(ordered_at, str):
                    ordered_at = datetime.fromisoformat(ordered_at).replace(tzinfo=timezone.utc)
                elif isinstance(ordered_at, datetime) and ordered_at.tzinfo is None:
                    ordered_at = ordered_at.replace(tzinfo=timezone.utc)
            except Exception:
                ordered_at = datetime.now(timezone.utc)

            status = _wc_status_to_orynt(str(row.get("order_status", "pending")))

            new_order = Order(
                brand_id=brand_id,
                source="reseller_platform",
                channel="website",
                status=status,
                total_amount=round(total, 2),
                payment_method="bank_transfer",  # reseller platform default
                payment_gateway="reseller_platform",
                external_id=order_id,
                ordered_at=ordered_at,
                notes=f"Reseller platform order #{order_id}",
            )
            db.add(new_order)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                continue

            # Line items
            for item in items:
                base = float(item["base_price"] or 0)
                markup = float(item["reseller_markup"] or 0)
                qty = int(item["quantity"] or 1)
                unit_price = round(base + markup, 2)

                oi = OrderItem(
                    order_id=new_order.id,
                    brand_id=brand_id,
                    external_product_id=None,
                    name=str(item["order_item_name"] or "Unknown"),
                    quantity=qty,
                    unit_price=unit_price,
                    total_price=round(unit_price * qty, 2),
                )
                db.add(oi)

            db.commit()
            created += 1

    return created


# ── Task 3: Nightly Sync (2 AM WAT = 1 AM UTC) ───────────────────────────────

@celery_app.task
def nightly_reseller_sync():
    """
    Called by Celery Beat at 01:00 UTC (02:00 WAT) daily.
    For each connected reseller_platform_storefront integration,
    pulls only new orders since last_sync_at.
    NOTE: 'reseller_platform' (master) integration is NOT re-synced here —
    only the per-storefront integrations.
    """
    logger.info("[Reseller] Nightly sync started")
    synced = 0

    with get_db_session() as db:
        storefront_intgs = db.query(Integration).filter_by(
            type="reseller_platform_storefront", status="connected"
        ).all()
        jobs = [(i.brand_id, i.id, i.last_sync_at) for i in storefront_intgs]

    for brand_id, intg_id, last_sync_at in jobs:
        since = last_sync_at or (datetime.now(timezone.utc) - timedelta(days=1))
        try:
            pull_reseller_storefront_data.delay(brand_id, intg_id, since)
            synced += 1
        except Exception as exc:
            logger.warning(f"[Reseller] Could not queue nightly sync for brand={brand_id}: {exc}")

    logger.info(f"[Reseller] Nightly sync queued {synced} storefront jobs")
    return {"queued": synced}
