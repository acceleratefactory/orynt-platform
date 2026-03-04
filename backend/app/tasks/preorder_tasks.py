"""
ORYNT — Preorder Platform Custom Ingestion Tasks

Celery tasks for the founder's preorder commerce platform.
Uses direct MySQL connection. Tables use pop_ prefix exclusively.
Do NOT use wp_posts, wp_woocommerce_order_items, or standard WooCommerce tables.

Table map:
  pop_sellers            → ORYNT brands
  pop_campaigns          → ORYNT products (is_preorder)
  pop_campaign_orders    → ORYNT orders
  pop_campaign_milestones → fulfillment event notes
  pop_customer_tiers     → customer loyalty metadata
  pop_payouts            → (logged, not stored separately)
  pop_reliability_log    → stored in integration metadata on brand

Campaign status → ORYNT order status:
  active        → pending
  funded        → confirmed
  in_production → processing
  shipped       → shipped
  customs       → in_transit
  warehouse     → in_transit
  delivering    → out_for_delivery
  completed     → completed
  cancelled     → cancelled
  refunded      → refunded
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

# Campaign status → ORYNT order status
CAMPAIGN_STATUS_MAP = {
    "active": "pending",
    "funded": "confirmed",
    "in_production": "processing",
    "shipped": "shipped",
    "customs": "in_transit",
    "warehouse": "in_transit",
    "delivering": "out_for_delivery",
    "completed": "completed",
    "cancelled": "cancelled",
    "refunded": "refunded",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _decrypt_creds(encrypted: str) -> dict:
    return json.loads(Fernet(ENCRYPTION_KEY.encode()).decrypt(encrypted.encode()).decode())


def _mysql_conn(creds: dict):
    return pymysql.connect(
        host=creds["db_host"],
        user=creds["db_user"],
        password=creds["db_password"],
        database=creds["db_name"],
        port=int(creds.get("db_port", 3306)),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        read_timeout=60,
    )


def _safe_dt(val) -> datetime:
    """Parse a datetime value from MySQL, return UTC-aware datetime."""
    if isinstance(val, datetime):
        return val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val
    try:
        return datetime.fromisoformat(str(val)).replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _fernet_encrypt(data: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).encrypt(data.encode()).decode()


# ── Task 1: Bulk Create Preorder Brands ──────────────────────────────────────

@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def bulk_create_preorder_brands(self, platform_integration_id: str):
    """
    Create one ORYNT brand per active seller in pop_sellers.
    Stores reliability_score + vendor_id in per-seller integration metadata.
    Queues pull_preorder_seller_data for each new brand.
    """
    logger.info(f"[Preorder] Bulk brand creation start: integration={platform_integration_id}")

    with get_db_session() as db:
        intg = db.get(Integration, platform_integration_id)
        if not intg:
            logger.error(f"[Preorder] Integration {platform_integration_id} not found")
            return
        creds = _decrypt_creds(intg.encrypted_key)
        org_id = creds["organization_id"]

    # Fetch all active sellers
    try:
        conn = _mysql_conn(creds)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, user_id, business_name, phone, total_campaigns, "
                    "successful_campaigns, reliability_score "
                    "FROM pop_sellers WHERE status = 'active'"
                )
                sellers = cur.fetchall()
    except Exception as exc:
        logger.error(f"[Preorder] Failed to fetch sellers: {exc}")
        raise self.retry(exc=exc)

    brands_created = 0
    brand_jobs = []  # (brand_id, sf_intg_id, seller)

    for seller in sellers:
        seller_id = seller["id"]
        business_name = seller["business_name"] or f"Seller #{seller_id}"
        reliability = float(seller.get("reliability_score") or 0)

        with get_db_session() as db:
            # Check if already exists
            existing_intgs = db.query(Integration).filter_by(
                type="preorder_platform_seller"
            ).all()
            already_exists = False
            for ei in existing_intgs:
                try:
                    ec = _decrypt_creds(ei.encrypted_key)
                    if str(ec.get("seller_id")) == str(seller_id):
                        already_exists = True
                        brand_jobs.append((ei.brand_id, ei.id, seller))
                        break
                except Exception:
                    pass

            if already_exists:
                continue

            brand = Brand(
                organization_id=org_id,
                name=business_name,
                category="preorder",
                seller_type="website",
                onboarding_completed=True,
            )
            db.add(brand)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                continue

            seller_creds = {
                **creds,
                "seller_id": seller_id,
                "user_id": seller.get("user_id"),
                "reliability_score": reliability,
                "total_campaigns": seller.get("total_campaigns", 0),
                "successful_campaigns": seller.get("successful_campaigns", 0),
            }
            seller_intg = Integration(
                brand_id=brand.id,
                type="preorder_platform_seller",
                status="connected",
                encrypted_key=_fernet_encrypt(json.dumps(seller_creds)),
            )
            db.add(seller_intg)
            db.commit()
            db.refresh(seller_intg)
            brands_created += 1
            brand_jobs.append((brand.id, seller_intg.id, seller))
            logger.info(f"[Preorder] Created brand '{business_name}' (seller {seller_id})")

    logger.info(f"[Preorder] Created {brands_created} new brands. Queuing data pulls...")
    for brand_id, sellr_intg_id, _ in brand_jobs:
        pull_preorder_seller_data.delay(brand_id, sellr_intg_id)

    with get_db_session() as db:
        intg = db.get(Integration, platform_integration_id)
        if intg:
            intg.last_sync_at = datetime.now(timezone.utc)
            intg.transaction_count = len(brand_jobs)
            intg.status = "connected"
            db.commit()

    return {"brands_created": brands_created, "total_sellers": len(sellers)}


# ── Task 2: Pull Preorder Seller Data ─────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def pull_preorder_seller_data(self, brand_id: str, integration_id: str, since: datetime = None):
    """
    Full data pull for one preorder seller:
    - Campaigns as products (pop_campaigns)
    - Orders (pop_campaign_orders → pop_campaigns status)
    - Customers (wp_users + wp_usermeta + pop_customer_tiers)
    - Milestones as fulfillment notes (pop_campaign_milestones)
    - Reliability data (pop_reliability_log)
    """
    logger.info(f"[Preorder] Pulling data for brand={brand_id}")

    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if not intg:
            logger.error(f"[Preorder] Integration {integration_id} not found")
            return
        creds = _decrypt_creds(intg.encrypted_key)

    seller_id = creds["seller_id"]

    try:
        conn = _mysql_conn(creds)
    except Exception as exc:
        logger.error(f"[Preorder] DB connection failed for seller {seller_id}: {exc}")
        raise self.retry(exc=exc)

    with conn:
        products_count = _sync_campaigns_as_products(conn, brand_id, seller_id)
        orders_count, customer_ids = _sync_preorder_orders(conn, brand_id, seller_id, since)
        customers_count = _sync_preorder_customers(conn, brand_id, customer_ids)
        _sync_milestones(conn, brand_id, seller_id)
        _sync_reliability(conn, integration_id, seller_id)

    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if intg:
            intg.last_sync_at = datetime.now(timezone.utc)
            intg.transaction_count = (intg.transaction_count or 0) + orders_count
            db.commit()

    result = {
        "products": products_count, "orders": orders_count,
        "customers": customers_count, "brand_id": brand_id
    }
    logger.info(f"[Preorder] Done brand={brand_id}: {result}")
    return result


# ── Campaigns as products ──────────────────────────────────────────────────────

def _sync_campaigns_as_products(conn, brand_id: str, seller_id) -> int:
    """Sync pop_campaigns as ORYNT products (is_preorder=True → category='preorder')."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, seller_id, product_name, sku, target_quantity, minimum_quantity,
                   units_ordered, units_delivered, price_early, price_standard, price_final,
                   deadline, status, commission_rate, created_at
            FROM pop_campaigns
            WHERE seller_id = %s ORDER BY created_at DESC
        """, (seller_id,))
        rows = cur.fetchall()

    created = 0
    for row in rows:
        external_id = str(row["id"])
        name = str(row["product_name"] or f"Campaign {external_id}")
        sku = str(row["sku"] or "") or None
        # Use price_final if available, else price_standard, else price_early
        selling_price = round(float(
            row["price_final"] or row["price_standard"] or row["price_early"] or 0
        ), 2)
        # Cost = weighted avg unit_price × (1 - commission_rate/100)
        commission = float(row.get("commission_rate") or 0)
        cost_price = round(selling_price * (1 - commission / 100), 2)
        # Stock = remaining to deliver
        units_ordered = int(row.get("units_ordered") or 0)
        units_delivered = int(row.get("units_delivered") or 0)
        stock = max(units_ordered - units_delivered, 0)

        with get_db_session() as db:
            existing = db.query(Product).filter_by(
                brand_id=brand_id, external_id=external_id, source="preorder_platform"
            ).first()
            if existing:
                existing.name = name
                existing.selling_price = max(selling_price, 0.01)
                existing.cost_price = cost_price
                existing.current_stock = stock
                db.commit()
            else:
                p = Product(
                    brand_id=brand_id, source="preorder_platform",
                    external_id=external_id, name=name, sku_code=sku,
                    category="preorder",
                    selling_price=max(selling_price, 0.01),
                    cost_price=cost_price,
                    current_stock=stock,
                )
                db.add(p)
                try:
                    db.commit()
                    created += 1
                except IntegrityError:
                    db.rollback()
    return created


# ── Orders ────────────────────────────────────────────────────────────────────

def _sync_preorder_orders(conn, brand_id: str, seller_id, since: datetime = None) -> tuple[int, list]:
    """Sync pop_campaign_orders as ORYNT orders. Returns (count, list_of_customer_ids)."""
    since_clause = ""
    params = [seller_id]
    if since:
        since_clause = "AND pco.created_at > %s"
        params.append(since.strftime("%Y-%m-%d %H:%M:%S"))

    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT pco.id, pco.campaign_id, pco.customer_id, pco.quantity,
                   pco.unit_price, pco.total_paid, pco.price_tier,
                   pco.payment_status, pco.created_at,
                   pc.status as campaign_status
            FROM pop_campaign_orders pco
            JOIN pop_campaigns pc ON pc.id = pco.campaign_id
            WHERE pc.seller_id = %s AND pco.payment_status = 'paid'
            {since_clause}
            ORDER BY pco.created_at DESC
        """, params)
        rows = cur.fetchall()

    created = 0
    customer_ids = []

    for row in rows:
        external_id = str(row["id"])
        campaign_status = str(row.get("campaign_status") or "active").lower()
        orynt_status = CAMPAIGN_STATUS_MAP.get(campaign_status, "pending")
        total = round(float(row.get("total_paid") or 0), 2)
        qty = int(row.get("quantity") or 1)
        unit_price = round(float(row.get("unit_price") or 0), 2)
        campaign_id = str(row.get("campaign_id") or "")
        customer_id = row.get("customer_id")
        price_tier = str(row.get("price_tier") or "standard")
        ordered_at = _safe_dt(row.get("created_at"))

        if customer_id and customer_id not in customer_ids:
            customer_ids.append(customer_id)

        with get_db_session() as db:
            if db.query(Order).filter_by(
                brand_id=brand_id, external_id=external_id, source="preorder_platform"
            ).first():
                continue

            # Link to product (campaign)
            product = db.query(Product).filter_by(
                brand_id=brand_id, external_id=campaign_id, source="preorder_platform"
            ).first() if campaign_id else None

            # Customer lookup (set later in _sync_preorder_customers)
            customer = None
            if customer_id:
                customer = db.query(Customer).filter_by(
                    brand_id=brand_id, external_id=str(customer_id)
                ).first()

            new_order = Order(
                brand_id=brand_id,
                customer_id=customer.id if customer else None,
                source="preorder_platform",
                channel="preorder",
                status=orynt_status,
                total_amount=total,
                payment_method="card",
                payment_gateway="preorder_platform",
                external_id=external_id,
                ordered_at=ordered_at,
                notes=f"Preorder campaign #{campaign_id} | tier: {price_tier}",
            )
            db.add(new_order)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                continue

            # Line item
            oi = OrderItem(
                order_id=new_order.id,
                brand_id=brand_id,
                product_id=product.id if product else None,
                external_product_id=campaign_id or None,
                name=product.name if product else f"Campaign #{campaign_id}",
                quantity=qty,
                unit_price=unit_price,
                total_price=round(unit_price * qty, 2),
            )
            db.add(oi)
            db.commit()
            created += 1

    return created, customer_ids


# ── Customers (wp_users + pop_customer_tiers) ──────────────────────────────────

def _sync_preorder_customers(conn, brand_id: str, customer_ids: list) -> int:
    if not customer_ids:
        return 0
    created = 0
    for wp_user_id in customer_ids:
        with conn.cursor() as cur:
            # Get email from wp_users
            cur.execute(
                "SELECT ID, user_email FROM wp_users WHERE ID = %s",
                (wp_user_id,)
            )
            user_row = cur.fetchone()

            if not user_row:
                continue

            email = str(user_row.get("user_email") or "").lower().strip()
            if not email:
                continue

            # Get billing phone + name from wp_usermeta
            cur.execute("""
                SELECT meta_key, meta_value FROM wp_usermeta
                WHERE user_id = %s AND meta_key IN ('billing_phone', 'billing_first_name', 'billing_last_name')
            """, (wp_user_id,))
            meta_rows = cur.fetchall()
            meta = {r["meta_key"]: r["meta_value"] for r in meta_rows}
            phone = meta.get("billing_phone")
            fname = meta.get("billing_first_name", "")
            lname = meta.get("billing_last_name", "")
            name = f"{fname} {lname}".strip() or None

            # Get loyalty tier from pop_customer_tiers
            cur.execute(
                "SELECT tier_name, total_spent FROM pop_customer_tiers WHERE customer_id = %s",
                (wp_user_id,)
            )
            tier_row = cur.fetchone()
            tier_note = ""
            if tier_row:
                tier_note = f" | Tier: {tier_row.get('tier_name', '')} | Spent: {tier_row.get('total_spent', 0)}"

        with get_db_session() as db:
            customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
            if customer:
                if name and not customer.name:
                    customer.name = name
                if phone and not customer.phone:
                    customer.phone = phone
                db.commit()
            else:
                customer = Customer(
                    brand_id=brand_id,
                    email=email,
                    name=name,
                    phone=phone,
                    external_id=str(wp_user_id),
                )
                db.add(customer)
                try:
                    db.commit()
                    created += 1
                except IntegrityError:
                    db.rollback()
    return created


# ── Milestones (stored as order notes) ────────────────────────────────────────

def _sync_milestones(conn, brand_id: str, seller_id) -> None:
    """
    Pull completed milestones for this seller's campaigns.
    Updates matching orders' notes with milestone completion info.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT pcm.campaign_id, pcm.milestone_key, pcm.completed_at
            FROM pop_campaign_milestones pcm
            JOIN pop_campaigns pc ON pc.id = pcm.campaign_id
            WHERE pc.seller_id = %s AND pcm.completed = 1
            ORDER BY pcm.completed_at ASC
        """, (seller_id,))
        milestones = cur.fetchall()

    # Group milestones by campaign_id
    by_campaign: dict = {}
    for m in milestones:
        cid = str(m["campaign_id"])
        if cid not in by_campaign:
            by_campaign[cid] = []
        dt = _safe_dt(m["completed_at"]).strftime("%Y-%m-%d") if m["completed_at"] else "?"
        by_campaign[cid].append(f"{m['milestone_key']} ({dt})")

    for campaign_id, milestone_list in by_campaign.items():
        milestone_note = "Milestones: " + ", ".join(milestone_list)
        with get_db_session() as db:
            orders = db.query(Order).filter_by(
                brand_id=brand_id, source="preorder_platform"
            ).filter(Order.notes.like(f"%{campaign_id}%")).all()
            for order in orders:
                if "Milestones:" not in (order.notes or ""):
                    order.notes = f"{order.notes or ''} | {milestone_note}"
            if orders:
                db.commit()


# ── Reliability data ───────────────────────────────────────────────────────────

def _sync_reliability(conn, integration_id: str, seller_id) -> None:
    """
    Pull reliability log and store on the integration record encrypted metadata.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT delivered_on_time, refund_issued_on_time, customer_satisfaction_avg
            FROM pop_reliability_log WHERE seller_id = %s
        """, (seller_id,))
        row = cur.fetchone()

    if not row:
        return

    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if not intg:
            return
        try:
            creds = _decrypt_creds(intg.encrypted_key)
        except Exception:
            return
        creds["reliability_delivered_on_time"] = row.get("delivered_on_time")
        creds["reliability_refund_on_time"] = row.get("refund_issued_on_time")
        creds["reliability_satisfaction_avg"] = float(row.get("customer_satisfaction_avg") or 0)
        intg.encrypted_key = _fernet_encrypt(json.dumps(creds))
        db.commit()


# ── Task 3: Nightly Sync (2 AM WAT = 1 AM UTC) ───────────────────────────────

@celery_app.task
def nightly_preorder_sync():
    """
    Called by Celery Beat at 02:00 WAT daily.
    For each connected preorder_platform_seller integration:
    - Pull new pop_campaign_orders since last_sync_at
    - Also update orders whose campaign status changed (completed campaigns → update all orders)
    """
    logger.info("[Preorder] Nightly sync started")
    synced = 0

    with get_db_session() as db:
        seller_intgs = db.query(Integration).filter_by(
            type="preorder_platform_seller", status="connected"
        ).all()
        jobs = [(i.brand_id, i.id, i.last_sync_at) for i in seller_intgs]

    for brand_id, intg_id, last_sync_at in jobs:
        since = last_sync_at or (datetime.now(timezone.utc) - timedelta(days=1))
        try:
            pull_preorder_seller_data.delay(brand_id, intg_id, since)
            synced += 1
        except Exception as exc:
            logger.warning(f"[Preorder] Could not queue nightly sync for brand={brand_id}: {exc}")

    # Also sync campaign status changes → update existing orders
    nightly_preorder_status_update.delay()

    logger.info(f"[Preorder] Nightly sync queued {synced} seller jobs")
    return {"queued": synced}


@celery_app.task
def nightly_preorder_status_update():
    """
    Update ORYNT order statuses for any campaigns that changed status since last sync.
    A completed campaign must update all its orders to 'completed'.
    """
    with get_db_session() as db:
        seller_intgs = db.query(Integration).filter_by(
            type="preorder_platform_seller", status="connected"
        ).all()
        jobs = [(i.brand_id, i.id) for i in seller_intgs]

    for brand_id, intg_id in jobs:
        try:
            with get_db_session() as db:
                intg = db.get(Integration, intg_id)
                if not intg:
                    continue
                creds = _decrypt_creds(intg.encrypted_key)

            seller_id = creds["seller_id"]
            conn = _mysql_conn(creds)
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, status FROM pop_campaigns WHERE seller_id = %s",
                        (seller_id,)
                    )
                    campaigns = cur.fetchall()

            for campaign in campaigns:
                campaign_id = str(campaign["id"])
                orynt_status = CAMPAIGN_STATUS_MAP.get(
                    str(campaign["status"] or "active").lower(), "pending"
                )
                with get_db_session() as db:
                    orders = db.query(Order).filter_by(
                        brand_id=brand_id, source="preorder_platform"
                    ).filter(Order.notes.like(f"%{campaign_id}%")).all()
                    updated = 0
                    for order in orders:
                        if order.status != orynt_status:
                            order.status = orynt_status
                            updated += 1
                    if updated:
                        db.commit()
                        logger.info(f"[Preorder] Updated {updated} orders for campaign {campaign_id} → {orynt_status}")
        except Exception as exc:
            logger.warning(f"[Preorder] Status update failed for brand={brand_id}: {exc}")
