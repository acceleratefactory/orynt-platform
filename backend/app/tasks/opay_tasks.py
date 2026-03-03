"""
ORYNT — OPay Background Tasks
Celery task: pull_opay_history
OPay Cashier API uses HMAC-SHA512 of the sorted JSON body with the private_key.
Authorization header: Bearer {sha512_hex} MerchantId:{merchant_id}
All three credentials (merchant_id, public_key, private_key) stored as encrypted JSON.
"""

import os
import json
import hmac
import hashlib
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

# OPay uses separate prod/sandbox base URLs
OPAY_BASE_PROD = "https://cashierapi.opayweb.com"
OPAY_BASE_SANDBOX = "https://sandboxapi.opayweb.com"
ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
OPAY_ENV = os.getenv("OPAY_ENV", "sandbox")  # set to 'production' for live


def _get_base_url() -> str:
    return OPAY_BASE_PROD if OPAY_ENV == "production" else OPAY_BASE_SANDBOX


def _decrypt_credentials(encrypted: str) -> dict:
    f = Fernet(ENCRYPTION_KEY.encode())
    return json.loads(f.decrypt(encrypted.encode()).decode())


def _opay_headers(payload: dict, private_key: str, merchant_id: str) -> dict:
    """Build OPay auth headers: HMAC-SHA512 of alphabetically-sorted JSON body."""
    sorted_body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    signature = hmac.new(private_key.encode(), sorted_body.encode(), hashlib.sha512).hexdigest()
    return {
        "Authorization": f"Bearer {signature} MerchantId:{merchant_id}",
        "Content-Type": "application/json",
        "MerchantId": merchant_id,
    }


def _infer_channel(txn: dict) -> str:
    """POS/in-store → 'physical', online → 'website', mobile → 'social'."""
    pay_type = str(txn.get("payChannel", "") or txn.get("channel", "") or "").lower()
    if any(w in pay_type for w in ["pos", "instore", "in_store", "offline", "physical"]):
        return "physical"
    if any(w in pay_type for w in ["mobile", "whatsapp", "social"]):
        return "social"
    return "website"


def _infer_payment_method(txn: dict) -> str:
    pay_type = str(txn.get("payChannel", "") or txn.get("payMethod", "") or "").lower()
    if any(w in pay_type for w in ["card", "visa", "mastercard"]):
        return "card"
    if any(w in pay_type for w in ["transfer", "bank", "ussd", "nuban"]):
        return "bank_transfer"
    return "bank_transfer"


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def pull_opay_history(self, brand_id: str, integration_id: str):
    """
    Pull last 12 months of successful OPay Cashier transactions for a brand.
    """
    logger.info(f"[OPay] Starting history pull for brand={brand_id}")

    with get_db_session() as db:
        integration = db.get(Integration, integration_id)
        if not integration:
            logger.error(f"[OPay] Integration {integration_id} not found")
            return
        creds = _decrypt_credentials(integration.encrypted_key)

    merchant_id = creds["merchant_id"]
    private_key = creds["private_key"]
    base_url = _get_base_url()

    # OPay uses page-based pagination, date range filter
    from_date = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y%m%d")
    to_date = datetime.now(timezone.utc).strftime("%Y%m%d")

    page = 1
    page_size = 100
    total_pulled = 0
    orders_created = 0
    customers_created = 0

    while True:
        payload = {
            "merchantId": merchant_id,
            "startTime": from_date,
            "endTime": to_date,
            "pageNo": page,
            "pageSize": page_size,
        }
        headers = _opay_headers(payload, private_key, merchant_id)

        try:
            resp = httpx.post(
                f"{base_url}/api/v1/international/cashier/queryTransactionList",
                headers=headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.error(f"[OPay] API error page={page}: {exc}")
            raise self.retry(exc=exc)

        # OPay response: {"code": "00000", "message": "SUCCESSFUL", "data": {...}}
        if data.get("code") not in ("00000", "0"):
            logger.error(f"[OPay] API error: {data.get('message')}")
            break

        response_data = data.get("data") or {}
        transactions = response_data.get("transactionList") or response_data.get("list") or []
        if not transactions:
            break

        with get_db_session() as db:
            for txn in transactions:
                status = str(txn.get("status", "") or txn.get("orderStatus", "")).upper()
                if status not in ("SUCCESSFUL", "SUCCESS", "COMPLETED", "PAID"):
                    continue

                total_pulled += 1
                email = str(txn.get("userInfo", {}).get("userEmail", "") or txn.get("email", "")).lower().strip()

                # ── Find or create Customer ──────────────────────────────
                customer = None
                if email:
                    customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()
                    if not customer:
                        user_info = txn.get("userInfo") or {}
                        customer = Customer(
                            brand_id=brand_id,
                            email=email,
                            name=user_info.get("fullName") or user_info.get("userName") or None,
                            phone=user_info.get("phoneNumber") or None,
                        )
                        db.add(customer)
                        try:
                            db.flush()
                            customers_created += 1
                        except IntegrityError:
                            db.rollback()
                            customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()

                # ── Find or create Order ─────────────────────────────────
                external_id = str(txn.get("orderNo") or txn.get("transactionNo") or txn.get("reference") or "")
                if not external_id:
                    continue

                if db.query(Order).filter_by(brand_id=brand_id, external_id=external_id, source="opay").first():
                    continue

                # OPay amounts are in smallest currency unit (kobo for NGN)
                raw_amount = txn.get("amount") or txn.get("orderAmount") or 0
                amount_ngn = round(float(raw_amount) / 100, 2)
                currency = txn.get("currency", "NGN")

                created_at_raw = txn.get("createTime") or txn.get("orderTime") or txn.get("createdAt")
                try:
                    if isinstance(created_at_raw, (int, float)):
                        ordered_at = datetime.fromtimestamp(created_at_raw / 1000, tz=timezone.utc)
                    else:
                        ordered_at = datetime.fromisoformat(str(created_at_raw).replace("Z", "+00:00"))
                except Exception:
                    ordered_at = datetime.now(timezone.utc)

                order = Order(
                    brand_id=brand_id,
                    customer_id=customer.id if customer else None,
                    source="opay",
                    channel=_infer_channel(txn),
                    status="completed",
                    total_amount=amount_ngn,
                    original_amount=amount_ngn if currency != "NGN" else None,
                    original_currency=currency if currency != "NGN" else None,
                    payment_method=_infer_payment_method(txn),
                    payment_gateway="opay",
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

        total_count = response_data.get("totalCount") or response_data.get("total") or 0
        if page * page_size >= int(total_count) or len(transactions) < page_size:
            break
        page += 1

    # Update integration stats
    with get_db_session() as db:
        integration = db.get(Integration, integration_id)
        if integration:
            integration.last_sync_at = datetime.now(timezone.utc)
            integration.transaction_count = orders_created
            db.commit()

    logger.info(f"[OPay] Done brand={brand_id}: pulled={total_pulled}, orders={orders_created}")
    return {"total_pulled": total_pulled, "orders_created": orders_created, "customers_created": customers_created}
