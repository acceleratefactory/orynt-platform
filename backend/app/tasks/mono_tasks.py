"""
ORYNT — Mono Open Banking Task
Celery task: pull_mono_statements
Pulls 12 months of bank statement credits from Mono API.
Credits become 'pending_match' orders the seller reviews in Order Inbox.
Mono amounts are in kobo (÷100 for NGN).
"""

import os
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
from app.models.order import Order

logger = logging.getLogger(__name__)

MONO_BASE = "https://api.withmono.com/v2"
ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
MONO_SECRET_KEY = os.getenv("MONO_SECRET_KEY", "")


def _decrypt(encrypted: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.decrypt(encrypted.encode()).decode()


def _mono_headers() -> dict:
    return {
        "mono-sec-key": MONO_SECRET_KEY,
        "Content-Type": "application/json",
    }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def pull_mono_statements(self, brand_id: str, integration_id: str):
    """
    Pull last 12 months of bank statement from Mono.
    Credit transactions → pending_match orders in Order Inbox.
    """
    logger.info(f"[Mono] Starting statement pull for brand={brand_id}")

    with get_db_session() as db:
        integration = db.get(Integration, integration_id)
        if not integration:
            logger.error(f"[Mono] Integration {integration_id} not found")
            return
        account_id = _decrypt(integration.encrypted_key)

    orders_created = 0
    has_more = True
    pageid = None

    try:
        while has_more:
            params = {"period": "12months", "output": "json"}
            if pageid:
                params["pageid"] = pageid

            resp = httpx.get(
                f"{MONO_BASE}/accounts/{account_id}/statement",
                headers=_mono_headers(),
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error(f"[Mono] Statement pull failed: {exc}")
        raise self.retry(exc=exc)

    # Mono returns { data: { account: {...}, transactions: [...] }, meta: { next_page: "..." } }
    transactions = data.get("data", {}).get("transactions", [])
    meta = data.get("meta", {})

    with get_db_session() as db:
        for txn in transactions:
            # Only credit (incoming money)
            txn_type = str(txn.get("type", "")).lower()
            if txn_type not in ("credit",):
                continue

            external_id = str(txn.get("_id") or txn.get("id") or "")
            if not external_id:
                continue

            # Dedup
            if db.query(Order).filter_by(
                brand_id=brand_id, external_id=external_id, source="bank_transfer"
            ).first():
                continue

            # Amount: Mono stores in kobo
            raw_amount = txn.get("amount", 0)
            amount_ngn = round(float(raw_amount) / 100, 2)

            # Date
            date_raw = txn.get("date") or txn.get("created_at")
            try:
                if isinstance(date_raw, (int, float)):
                    ordered_at = datetime.fromtimestamp(date_raw / 1000, tz=timezone.utc)
                else:
                    ordered_at = datetime.fromisoformat(str(date_raw).replace("Z", "+00:00"))
            except Exception:
                ordered_at = datetime.now(timezone.utc)

            narration = str(txn.get("narration", "") or txn.get("description", ""))

            order = Order(
                brand_id=brand_id,
                customer_id=None,
                source="bank_transfer",
                channel="website",
                status="pending_match",
                total_amount=amount_ngn,
                payment_method="bank_transfer",
                payment_gateway="bank",
                external_id=external_id,
                ordered_at=ordered_at,
                notes=narration,  # Store raw narration for seller review
            )
            db.add(order)
            try:
                db.flush()
                orders_created += 1
            except IntegrityError:
                db.rollback()

        db.commit()

    # Pagination
    has_more = bool(meta.get("next_page"))
    pageid = meta.get("next_page")

    # Update integration sync stats
    with get_db_session() as db:
        integration = db.get(Integration, integration_id)
        if integration:
            integration.last_sync_at = datetime.now(timezone.utc)
            integration.transaction_count = orders_created
            db.commit()

    logger.info(f"[Mono] Done brand={brand_id}: credits_imported={orders_created}")
    return {"credits_imported": orders_created}
