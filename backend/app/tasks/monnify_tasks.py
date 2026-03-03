"""
ORYNT — Monnify Background Tasks
Celery task: pull_monnify_history
Pulls last 12 months of PAID Monnify transactions.
Monnify uses Basic Auth (base64 apiKey:secretKey) to get a Bearer token,
then uses that token for all subsequent calls.
Stores all three credentials (api_key, secret_key, contract_code) as JSON in encrypted_key.
"""

import os
import json
import logging
import base64
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

MONNIFY_BASE = "https://api.monnify.com"
ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")


def _decrypt_credentials(encrypted: str) -> dict:
    """Decrypt and parse the JSON credentials stored in encrypted_key."""
    f = Fernet(ENCRYPTION_KEY.encode())
    return json.loads(f.decrypt(encrypted.encode()).decode())


def _get_access_token(api_key: str, secret_key: str) -> str:
    """Obtain a Bearer token using Monnify Basic Auth."""
    credentials = base64.b64encode(f"{api_key}:{secret_key}".encode()).decode()
    resp = httpx.post(
        f"{MONNIFY_BASE}/api/v1/auth/login",
        headers={"Authorization": f"Basic {credentials}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("responseBody", {}).get("accessToken")
    if not token:
        raise ValueError("Monnify auth returned no accessToken")
    return token


def _infer_channel(txn: dict) -> str:
    narration = str(txn.get("narration", "") or txn.get("paymentDescription", "")).lower()
    if any(w in narration for w in ["social", "whatsapp", "instagram"]):
        return "social"
    if any(w in narration for w in ["physical", "store", "shop"]):
        return "physical"
    return "website"


def _infer_payment_method(txn: dict) -> str:
    ptype = str(txn.get("paymentMethod", "") or txn.get("paymentSourceInformation", [{}])[0].get("paymentMethod", "")).upper()
    if "CARD" in ptype:
        return "card"
    if "ACCOUNT" in ptype or "TRANSFER" in ptype or "USSD" in ptype:
        return "bank_transfer"
    return "bank_transfer"


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def pull_monnify_history(self, brand_id: str, integration_id: str):
    """
    Pull last 12 months of successful Monnify transactions for a brand.
    """
    logger.info(f"[Monnify] Starting history pull for brand={brand_id}")

    with get_db_session() as db:
        integration = db.get(Integration, integration_id)
        if not integration:
            logger.error(f"[Monnify] Integration {integration_id} not found")
            return
        creds = _decrypt_credentials(integration.encrypted_key)

    api_key = creds["api_key"]
    secret_key = creds["secret_key"]
    contract_code = creds.get("contract_code", "")

    try:
        token = _get_access_token(api_key, secret_key)
    except Exception as exc:
        logger.error(f"[Monnify] Auth failed: {exc}")
        raise self.retry(exc=exc)

    headers = {"Authorization": f"Bearer {token}"}
    from_date = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")

    page = 0
    total_pulled = 0
    orders_created = 0
    customers_created = 0

    while True:
        try:
            resp = httpx.get(
                f"{MONNIFY_BASE}/api/v2/transactions/search",
                params={
                    "paymentStatus": "PAID",
                    "page": page,
                    "size": 100,
                    "dateCreatedAfter": from_date,
                },
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                # Token expired — refresh and retry
                try:
                    token = _get_access_token(api_key, secret_key)
                    headers = {"Authorization": f"Bearer {token}"}
                    continue
                except Exception:
                    pass
            logger.error(f"[Monnify] API error page={page}: {exc}")
            raise self.retry(exc=exc)
        except Exception as exc:
            raise self.retry(exc=exc)

        body = data.get("responseBody", {})
        transactions = body.get("content", [])
        if not transactions:
            break

        with get_db_session() as db:
            for txn in transactions:
                if txn.get("paymentStatus") != "PAID":
                    continue

                total_pulled += 1
                email = str(txn.get("customerEmail", "")).lower().strip()
                if not email:
                    continue

                # ── Find or create Customer ──────────────────────────────
                customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
                if not customer:
                    customer = Customer(
                        brand_id=brand_id,
                        email=email,
                        name=txn.get("customerName") or None,
                        phone=txn.get("customerPhone") or None,
                    )
                    db.add(customer)
                    try:
                        db.flush()
                        customers_created += 1
                    except IntegrityError:
                        db.rollback()
                        customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()

                # ── Find or create Order ─────────────────────────────────
                external_id = str(txn.get("transactionReference", ""))
                if not external_id:
                    continue

                if db.query(Order).filter_by(brand_id=brand_id, external_id=external_id, source="monnify").first():
                    continue

                amount_ngn = round(float(txn.get("amountPaid", 0)), 2)
                currency = txn.get("currencyCode", "NGN")

                created_at_raw = txn.get("createdOn") or txn.get("dateCreated")
                try:
                    # Monnify returns Unix ms timestamp
                    if isinstance(created_at_raw, (int, float)):
                        ordered_at = datetime.fromtimestamp(created_at_raw / 1000, tz=timezone.utc)
                    else:
                        ordered_at = datetime.fromisoformat(str(created_at_raw).replace("Z", "+00:00"))
                except Exception:
                    ordered_at = datetime.now(timezone.utc)

                order = Order(
                    brand_id=brand_id,
                    customer_id=customer.id if customer else None,
                    source="monnify",
                    channel=_infer_channel(txn),
                    status="completed",
                    total_amount=amount_ngn,
                    original_amount=amount_ngn if currency != "NGN" else None,
                    original_currency=currency if currency != "NGN" else None,
                    payment_method=_infer_payment_method(txn),
                    payment_gateway="monnify",
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

        total_elements = body.get("totalElements", 0)
        page_size = body.get("size", 100)
        if (page + 1) * page_size >= total_elements or len(transactions) < 100:
            break
        page += 1

    # Update integration stats
    with get_db_session() as db:
        integration = db.get(Integration, integration_id)
        if integration:
            integration.last_sync_at = datetime.now(timezone.utc)
            integration.transaction_count = orders_created
            db.commit()

    logger.info(
        f"[Monnify] Done brand={brand_id}: pulled={total_pulled}, "
        f"orders={orders_created}, customers={customers_created}"
    )
    return {"total_pulled": total_pulled, "orders_created": orders_created, "customers_created": customers_created}
