"""
ORYNT — Flutterwave Background Tasks
Celery task: pull_flutterwave_history
Pulls last 12 months of successful Flutterwave transactions,
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

FLW_BASE = "https://api.flutterwave.com/v3"
ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")  # shared key


def _decrypt_key(encrypted: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.decrypt(encrypted.encode()).decode()


def _infer_channel(txn: dict) -> str:
    """Infer ORYNT channel from Flutterwave transaction metadata."""
    meta = txn.get("meta") or {}
    narration = str(txn.get("narration", "")).lower()
    payment_type = str(txn.get("payment_type", "")).lower()

    if any(w in narration for w in ["social", "whatsapp", "instagram", "tiktok"]):
        return "social"
    if any(w in narration for w in ["physical", "store", "shop", "walk"]):
        return "physical"
    return "website"


def _infer_payment_method(txn: dict) -> str:
    payment_type = str(txn.get("payment_type", "")).lower()
    if payment_type in ("card", "credit card", "debit card"):
        return "card"
    if payment_type in ("banktransfer", "bank_transfer", "account"):
        return "bank_transfer"
    if payment_type == "ussd":
        return "bank_transfer"
    return "card"


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def pull_flutterwave_history(self, brand_id: str, integration_id: str):
    """
    Pull last 12 months of successful Flutterwave transactions for a brand.
    Creates Customer and Order records, updates integration stats.
    """
    logger.info(f"[Flutterwave] Starting history pull for brand={brand_id}")

    with get_db_session() as db:
        integration = db.get(Integration, integration_id)
        if not integration:
            logger.error(f"[Flutterwave] Integration {integration_id} not found")
            return
        secret_key = _decrypt_key(integration.encrypted_key)

    headers = {"Authorization": f"Bearer {secret_key}"}
    from_date = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S")
    to_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    page = 1
    total_pulled = 0
    orders_created = 0
    customers_created = 0

    while True:
        try:
            resp = httpx.get(
                f"{FLW_BASE}/transactions",
                params={
                    "status": "successful",
                    "from": from_date,
                    "to": to_date,
                    "page": page,
                    "limit": 100,
                },
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.error(f"[Flutterwave] API error on page {page}: {exc}")
            raise self.retry(exc=exc)

        transactions = (data.get("data") or {}).get("transactions") if isinstance(data.get("data"), dict) else data.get("data", [])
        if not transactions:
            break

        with get_db_session() as db:
            for txn in transactions:
                if txn.get("status") != "successful":
                    continue

                total_pulled += 1
                email = str(txn.get("customer", {}).get("email", "")).lower().strip()
                if not email:
                    continue

                # ── Find or create Customer ──────────────────────────────
                customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
                if not customer:
                    cust = txn.get("customer") or {}
                    full_name = cust.get("name") or cust.get("fullname") or ""
                    customer = Customer(
                        brand_id=brand_id,
                        email=email,
                        name=full_name or None,
                        phone=cust.get("phone_number"),
                    )
                    db.add(customer)
                    try:
                        db.flush()
                        customers_created += 1
                    except IntegrityError:
                        db.rollback()
                        customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()

                # ── Find or create Order ─────────────────────────────────
                # Flutterwave uses tx_ref as the merchant reference, id as internal
                external_id = str(txn.get("tx_ref") or txn.get("id") or "")
                if not external_id:
                    continue

                existing = db.query(Order).filter_by(
                    brand_id=brand_id, external_id=external_id, source="flutterwave"
                ).first()
                if existing:
                    continue

                # Flutterwave stores amounts in full currency units (NGN), not kobo
                amount_ngn = round(float(txn.get("amount", 0)), 2)
                currency = txn.get("currency", "NGN")

                created_at_raw = txn.get("created_at") or txn.get("createdAt")
                try:
                    ordered_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                except Exception:
                    ordered_at = datetime.now(timezone.utc)

                order = Order(
                    brand_id=brand_id,
                    customer_id=customer.id if customer else None,
                    source="flutterwave",
                    channel=_infer_channel(txn),
                    status="completed",
                    total_amount=amount_ngn,
                    original_amount=amount_ngn if currency != "NGN" else None,
                    original_currency=currency if currency != "NGN" else None,
                    payment_method=_infer_payment_method(txn),
                    payment_gateway="flutterwave",
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

        # Flutterwave paginates differently — if we got < 100 we're on the last page
        if not transactions or len(transactions) < 100:
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
        f"[Flutterwave] Completed brand={brand_id}: "
        f"pulled={total_pulled}, orders={orders_created}, customers={customers_created}"
    )
    return {
        "total_pulled": total_pulled,
        "orders_created": orders_created,
        "customers_created": customers_created,
    }
