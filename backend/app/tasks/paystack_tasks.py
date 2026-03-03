"""
ORYNT — Paystack Background Tasks
Celery task: pull_paystack_history
Pulls last 12 months of successful transactions from Paystack API,
creates Customer and Order records, deduplicates on (brand_id, external_id, source).
"""

import os
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

logger = logging.getLogger(__name__)

PAYSTACK_BASE = "https://api.paystack.co"
ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")


def _decrypt_key(encrypted: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.decrypt(encrypted.encode()).decode()


def _infer_channel(txn: dict) -> str:
    """Map Paystack channel field to ORYNT channel enum."""
    ch = (txn.get("channel") or "").lower()
    metadata = txn.get("metadata") or {}
    custom_fields = metadata.get("custom_fields") or []
    for field in custom_fields:
        val = str(field.get("value", "")).lower()
        if "social" in val or "whatsapp" in val or "instagram" in val:
            return "social"
        if "physical" in val or "store" in val or "shop" in val:
            return "physical"
    if ch in ("card", "bank", "ussd", "qr", "mobile_money", "eft"):
        return "website"
    return "website"


def _infer_payment_method(txn: dict) -> str:
    ch = (txn.get("channel") or "").lower()
    if ch == "card":
        return "card"
    if ch in ("bank_transfer", "dedicated_nuban", "bank"):
        return "bank_transfer"
    return "card"


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def pull_paystack_history(self, brand_id: str, integration_id: str):
    """
    Pull last 12 months of successful Paystack transactions for a brand.
    Creates Customer and Order records, updates integration stats.
    """
    logger.info(f"[Paystack] Starting history pull for brand={brand_id}")

    with get_db_session() as db:
        integration = db.get(Integration, integration_id)
        if not integration:
            logger.error(f"[Paystack] Integration {integration_id} not found")
            return

        secret_key = _decrypt_key(integration.encrypted_key)

    headers = {"Authorization": f"Bearer {secret_key}"}
    from_date = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")

    page = 1
    total_pulled = 0
    orders_created = 0
    customers_created = 0

    while True:
        try:
            resp = httpx.get(
                f"{PAYSTACK_BASE}/transaction",
                params={"perPage": 100, "page": page, "from": from_date, "status": "success"},
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.error(f"[Paystack] API error on page {page}: {exc}")
            raise self.retry(exc=exc)

        transactions = data.get("data", [])
        if not transactions:
            break

        with get_db_session() as db:
            for txn in transactions:
                if txn.get("status") != "success":
                    continue

                total_pulled += 1
                email = (txn.get("customer") or {}).get("email", "").lower().strip()
                if not email:
                    continue

                # ── Find or create Customer ──────────────────────────────
                customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
                if not customer:
                    cust_data = txn.get("customer") or {}
                    customer = Customer(
                        brand_id=brand_id,
                        email=email,
                        name=cust_data.get("first_name", "") + " " + cust_data.get("last_name", ""),
                        phone=cust_data.get("phone"),
                    )
                    db.add(customer)
                    try:
                        db.flush()
                        customers_created += 1
                    except IntegrityError:
                        db.rollback()
                        customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()

                # ── Find or create Order (dedup on external_id + source) ─
                external_id = txn.get("reference", "")
                existing = db.query(Order).filter_by(
                    brand_id=brand_id, external_id=external_id, source="paystack"
                ).first()
                if existing:
                    continue

                amount_kobo = txn.get("amount", 0)
                amount_ngn = round(amount_kobo / 100, 2)

                paid_at_raw = txn.get("paid_at") or txn.get("created_at")
                try:
                    ordered_at = datetime.fromisoformat(paid_at_raw.replace("Z", "+00:00"))
                except Exception:
                    ordered_at = datetime.now(timezone.utc)

                currency = txn.get("currency", "NGN")
                order = Order(
                    brand_id=brand_id,
                    customer_id=customer.id if customer else None,
                    source="paystack",
                    channel=_infer_channel(txn),
                    status="completed",
                    total_amount=amount_ngn if currency == "NGN" else amount_ngn,
                    original_amount=amount_kobo / 100 if currency != "NGN" else None,
                    original_currency=currency if currency != "NGN" else None,
                    payment_method=_infer_payment_method(txn),
                    payment_gateway="paystack",
                    external_id=external_id,
                    ordered_at=ordered_at,
                )
                db.add(order)
                try:
                    db.flush()
                    orders_created += 1
                except IntegrityError:
                    db.rollback()

            db.commit()

        if len(transactions) < 100:
            break
        page += 1

    # ── Update integration stats ────────────────────────────────────────
    with get_db_session() as db:
        integration = db.get(Integration, integration_id)
        if integration:
            integration.last_sync_at = datetime.now(timezone.utc)
            integration.transaction_count = orders_created
            db.commit()

    logger.info(
        f"[Paystack] Completed brand={brand_id}: "
        f"pulled={total_pulled}, orders={orders_created}, customers={customers_created}"
    )
    return {
        "total_pulled": total_pulled,
        "orders_created": orders_created,
        "customers_created": customers_created,
    }
