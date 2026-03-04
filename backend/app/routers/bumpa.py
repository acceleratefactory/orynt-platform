"""
ORYNT — Bumpa CSV Import Router

Endpoints:
  GET  /api/integrations/bumpa/template   — download CSV template
  POST /api/integrations/bumpa/upload     — upload, parse, validate, import CSV

CSV columns (Bumpa export format):
  Order ID, Order Date, Customer Name, Customer Phone, Customer Email,
  Product Name, SKU, Quantity, Unit Price, Cost Price, Total Amount,
  Payment Method, Order Status, Delivery State

Deduplication:
  - Orders: (brand_id, external_id='Order ID', source='bumpa') unique
  - Customers: by phone (normalized to +234) → fallback to email
  - Products: by SKU → fallback to name (brand_id + source='bumpa')
"""

import csv
import io
import re
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.auth import get_current_user
from app.database import get_db
from app.models.brand import Brand
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/integrations/bumpa", tags=["Bumpa CSV Import"])

# ── Column spec ───────────────────────────────────────────────────────────────

TEMPLATE_COLUMNS = [
    "Order ID", "Order Date", "Customer Name", "Customer Phone",
    "Customer Email", "Product Name", "SKU", "Quantity", "Unit Price",
    "Cost Price", "Total Amount", "Payment Method", "Order Status", "Delivery State",
]

REQUIRED_COLUMNS = {
    "Order ID", "Order Date", "Product Name", "Quantity",
    "Unit Price", "Total Amount", "Order Status",
}

# Bumpa → ORYNT order status mapping
STATUS_MAP = {
    "delivered": "completed",
    "completed": "completed",
    "pending": "pending",
    "pending payment": "pending",
    "processing": "processing",
    "confirmed": "confirmed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "refunded": "refunded",
    "failed": "failed",
    "shipped": "shipped",
    "in transit": "in_transit",
}

# Bumpa payment method → ORYNT
PAYMENT_MAP = {
    "bank transfer": "bank_transfer",
    "transfer": "bank_transfer",
    "card": "card",
    "cash": "cash",
    "cash on delivery": "cash",
    "cod": "cash",
    "pos": "card",
    "ussd": "bank_transfer",
    "wallet": "card",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_phone(raw: str) -> Optional[str]:
    """Normalize Nigerian phone to +234 format."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if digits.startswith("234") and len(digits) >= 13:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 11:
        return f"+234{digits[1:]}"
    if len(digits) == 10:
        return f"+234{digits}"
    if digits.startswith("234") and len(digits) == 13:
        return f"+{digits}"
    return f"+{digits}" if digits else None


def _parse_date(raw: str) -> datetime:
    """Try common date formats."""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
                "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    raise ValueError(f"Unrecognised date format: '{raw}'")


def _safe_float(val: str, field: str, row_num: int) -> tuple[float, str | None]:
    """Parse float, return (value, error_message|None)."""
    try:
        return round(float(str(val).replace(",", "").strip() or "0"), 2), None
    except ValueError:
        return 0.0, f"Row {row_num}: invalid number in '{field}': '{val}'"


def _safe_int(val: str, field: str, row_num: int) -> tuple[int, str | None]:
    try:
        return int(float(str(val).replace(",", "").strip() or "0")), None
    except ValueError:
        return 1, f"Row {row_num}: invalid integer in '{field}': '{val}'"


# ── GET /template ─────────────────────────────────────────────────────────────

@router.get("/template")
def download_template(user: dict = Depends(get_current_user)):
    """Return a downloadable CSV template with Bumpa's column structure."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(TEMPLATE_COLUMNS)
    # Add one sample row for guidance
    writer.writerow([
        "BMP-001", "2024-01-15", "Amaka Okafor", "08012345678",
        "amaka@example.com", "Ankara Dress (Medium)", "ANK-M-001",
        "2", "15000", "9000", "30000", "Bank Transfer", "Delivered", "Lagos",
    ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bumpa_import_template.csv"},
    )


# ── POST /upload ──────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_bumpa_csv(
    brand_id: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload and import a Bumpa CSV export.
    Returns import summary: orders_imported, products_imported, customers_imported, errors.
    Errors include row numbers so the seller can fix the CSV.
    """
    # Validate file type
    if file.content_type not in ("text/csv", "application/vnd.ms-excel",
                                  "application/csv", "text/plain"):
        if not (file.filename or "").lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    # Validate brand exists
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found.")

    raw = await file.read()
    try:
        content = raw.decode("utf-8-sig")  # handle BOM from Excel
    except UnicodeDecodeError:
        content = raw.decode("latin-1")

    reader = csv.DictReader(io.StringIO(content))

    # Validate columns
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no headers.")

    actual_cols = {c.strip() for c in reader.fieldnames}
    missing = REQUIRED_COLUMNS - actual_cols
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(sorted(missing))}. "
                   f"Download the template to see the correct format.",
        )

    errors: list[str] = []
    orders_imported = 0
    products_imported = 0
    customers_imported = 0

    # Cache to avoid redundant DB lookups per file
    product_cache: dict[str, str] = {}   # (sku or name) → product_id
    customer_cache: dict[str, str] = {}  # phone or email → customer_id

    for row_num, row in enumerate(reader, start=2):  # row 1 = header
        row = {k.strip(): (v or "").strip() for k, v in row.items() if k}

        # ── Required field validation ──────────────────────────────────────────
        order_id = row.get("Order ID", "").strip()
        if not order_id:
            errors.append(f"Row {row_num}: missing Order ID — skipped")
            continue

        raw_date = row.get("Order Date", "")
        try:
            ordered_at = _parse_date(raw_date)
        except ValueError as e:
            errors.append(f"Row {row_num}: {e} — skipped")
            continue

        product_name = row.get("Product Name", "").strip()
        if not product_name:
            errors.append(f"Row {row_num}: missing Product Name — skipped")
            continue

        qty, err = _safe_int(row.get("Quantity", "1"), "Quantity", row_num)
        if err:
            errors.append(err)
        unit_price, err2 = _safe_float(row.get("Unit Price", "0"), "Unit Price", row_num)
        if err2:
            errors.append(err2)
        cost_price, _ = _safe_float(row.get("Cost Price", "0"), "Cost Price", row_num)
        total_amount, _ = _safe_float(row.get("Total Amount", "0"), "Total Amount", row_num)
        if total_amount == 0:
            total_amount = round(unit_price * qty, 2)

        raw_status = row.get("Order Status", "completed").lower().strip()
        orynt_status = STATUS_MAP.get(raw_status, "completed")

        raw_payment = row.get("Payment Method", "bank_transfer").lower().strip()
        payment_method = PAYMENT_MAP.get(raw_payment, "bank_transfer")

        delivery_state = row.get("Delivery State", "").strip()
        sku = row.get("SKU", "").strip() or None
        customer_name = row.get("Customer Name", "").strip() or None
        customer_phone = _normalize_phone(row.get("Customer Phone", ""))
        customer_email = (row.get("Customer Email", "") or "").strip().lower() or None

        # ── Duplicate check for order ──────────────────────────────────────────
        existing_order = db.query(Order).filter_by(
            brand_id=brand_id, external_id=order_id, source="bumpa"
        ).first()
        if existing_order:
            continue  # silently skip duplicates

        # ── Find or create product ─────────────────────────────────────────────
        product_key = sku if sku else product_name.lower()
        if product_key not in product_cache:
            if sku:
                product = db.query(Product).filter_by(
                    brand_id=brand_id, sku_code=sku, source="bumpa"
                ).first()
            else:
                product = db.query(Product).filter_by(
                    brand_id=brand_id, source="bumpa"
                ).filter(Product.name == product_name).first()

            if not product:
                product = Product(
                    brand_id=brand_id,
                    source="bumpa",
                    name=product_name,
                    sku_code=sku,
                    selling_price=max(unit_price, 0.01),
                    cost_price=cost_price,
                    current_stock=0,
                )
                db.add(product)
                try:
                    db.flush()
                    products_imported += 1
                except IntegrityError:
                    db.rollback()
                    product = db.query(Product).filter_by(
                        brand_id=brand_id, source="bumpa"
                    ).filter(Product.name == product_name).first()
            product_cache[product_key] = product.id if product else None
        product_id = product_cache.get(product_key)

        # ── Find or create customer ────────────────────────────────────────────
        customer_id = None
        if customer_phone or customer_email:
            cache_key = customer_phone or customer_email
            if cache_key not in customer_cache:
                customer = None
                if customer_phone:
                    customer = db.query(Customer).filter_by(
                        brand_id=brand_id, phone=customer_phone
                    ).first()
                if not customer and customer_email:
                    customer = db.query(Customer).filter_by(
                        brand_id=brand_id, email=customer_email
                    ).first()
                if not customer:
                    customer = Customer(
                        brand_id=brand_id,
                        name=customer_name,
                        phone=customer_phone,
                        email=customer_email if customer_email else None,
                    )
                    db.add(customer)
                    try:
                        db.flush()
                        customers_imported += 1
                    except IntegrityError:
                        db.rollback()
                        if customer_phone:
                            customer = db.query(Customer).filter_by(
                                brand_id=brand_id, phone=customer_phone
                            ).first()
                customer_cache[cache_key] = customer.id if customer else None
            customer_id = customer_cache.get(cache_key)

        # ── Create order ───────────────────────────────────────────────────────
        new_order = Order(
            brand_id=brand_id,
            customer_id=customer_id,
            source="bumpa",
            channel="website",
            status=orynt_status,
            total_amount=total_amount,
            payment_method=payment_method,
            payment_gateway="bumpa",
            external_id=order_id,
            ordered_at=ordered_at,
            notes=f"Bumpa import | Delivery: {delivery_state}" if delivery_state else "Bumpa import",
        )
        db.add(new_order)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            continue  # duplicate order, skip

        # Line item
        oi = OrderItem(
            order_id=new_order.id,
            brand_id=brand_id,
            product_id=product_id,
            name=product_name,
            quantity=qty,
            unit_price=unit_price,
            total_price=round(unit_price * qty, 2),
        )
        db.add(oi)
        orders_imported += 1

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(f"[Bumpa] Final commit failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Import failed during final save: {exc}")

    return {
        "orders_imported": orders_imported,
        "products_imported": products_imported,
        "customers_imported": customers_imported,
        "errors": errors[:50],  # cap at 50 errors to avoid huge response
        "total_errors": len(errors),
        "success": orders_imported > 0 or len(errors) == 0,
    }
