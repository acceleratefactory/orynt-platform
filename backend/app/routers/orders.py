"""
ORYNT — Orders Router
GET  /api/orders/inbox              — pending_match bank transfers + recent manual orders
POST /api/orders/manual             — log a manual order (WhatsApp/physical shop/social)
POST /api/orders/{id}/confirm       — confirm bank transfer as sale (Task 1.6)
POST /api/orders/{id}/confirm-transfer — alias + links customer/product
POST /api/orders/{id}/archive       — mark as not a sale
GET  /api/orders                    — general order list
GET  /api/orders/customers/search   — autocomplete by phone/name
GET  /api/orders/products/search    — autocomplete by name/SKU
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from sqlalchemy.exc import IntegrityError

from app.auth import get_current_user
from app.database import get_db
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/orders", tags=["Orders"])


# ── Request schemas ────────────────────────────────────────────────────────────

class ManualOrderItem(BaseModel):
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    quantity: int = 1
    unit_price: float


class ManualOrderRequest(BaseModel):
    brand_id: str
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    items: list[ManualOrderItem] = []
    total_amount: float
    payment_method: str = "cash"         # cash | bank_transfer | card | opay | palmpay | paystack
    channel: str = "whatsapp"            # whatsapp | instagram | in_person
    delivery_address: Optional[str] = None
    note: Optional[str] = None


class ConfirmOrderRequest(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    channel: str = "website"


class ConfirmTransferRequest(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    product_id: Optional[str] = None
    channel: str = "website"


class ArchiveOrderRequest(BaseModel):
    reason: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _normalize_phone(raw: str) -> Optional[str]:
    if not raw:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if digits.startswith("234") and len(digits) >= 13:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 11:
        return f"+234{digits[1:]}"
    if len(digits) == 10:
        return f"+234{digits}"
    return f"+{digits}" if digits else None


def _find_or_create_customer(
    db: Session, brand_id: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
) -> Optional[Customer]:
    """Find existing customer by phone or email, else create one."""
    phone = _normalize_phone(phone) if phone else None
    email = (email or "").lower().strip() or None

    customer = None
    if phone:
        customer = db.query(Customer).filter_by(brand_id=brand_id, phone=phone).first()
    if not customer and email:
        customer = db.query(Customer).filter_by(brand_id=brand_id, email=email).first()

    if not customer:
        # Generate synthetic email from phone if needed (Customer.email is NOT NULL)
        effective_email = email or (f"{phone.replace('+', '')}@phone.orynt" if phone else None)
        if not effective_email:
            return None
        customer = Customer(
            brand_id=brand_id,
            email=effective_email,
            name=name or None,
            phone=phone or None,
        )
        db.add(customer)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            customer = db.query(Customer).filter_by(brand_id=brand_id, email=effective_email).first()
    else:
        # Update name if we now have one
        if name and not customer.name:
            customer.name = name

    return customer


# ── POST /manual ───────────────────────────────────────────────────────────────

@router.post("/manual")
def create_manual_order(
    body: ManualOrderRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Log a manual order from WhatsApp, physical shop or social media."""
    # Find or create customer
    customer = _find_or_create_customer(
        db, body.brand_id,
        phone=body.customer_phone,
        email=body.customer_email,
        name=body.customer_name,
    )

    notes_parts = []
    if body.delivery_address:
        notes_parts.append(f"Delivery: {body.delivery_address}")
    if body.note:
        notes_parts.append(body.note)

    import uuid as _uuid
    order = Order(
        brand_id=body.brand_id,
        customer_id=customer.id if customer else None,
        source="manual",
        channel=body.channel,
        status="completed",
        total_amount=body.total_amount,
        payment_method=body.payment_method,
        payment_gateway="manual",
        external_id=f"MANUAL-{_uuid.uuid4().hex[:8].upper()}",
        ordered_at=datetime.now(timezone.utc),
        notes=" | ".join(notes_parts) if notes_parts else None,
    )
    db.add(order)
    db.flush()

    # Create line items
    for item in body.items:
        product = db.get(Product, item.product_id) if item.product_id else None
        oi = OrderItem(
            order_id=order.id,
            brand_id=body.brand_id,
            product_id=product.id if product else None,
            name=item.product_name or (product.name if product else "Custom item"),
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=round(item.unit_price * item.quantity, 2),
        )
        db.add(oi)

    db.commit()
    db.refresh(order)
    logger.info(f"[Orders] Manual order {order.id} created for brand {body.brand_id}")

    return {
        "status": "created",
        "order": _inbox_dict(order),
        "customer": customer.to_dict() if customer else None,
    }


# ── GET /inbox ─────────────────────────────────────────────────────────────────

@router.get("/inbox")
def get_inbox(
    brand_id: str,
    page: int = 1,
    page_size: int = 50,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns:
    - pending_match bank transfer orders (unmatched)
    - Recent manual orders (last 50)
    """
    # Unmatched bank transfers
    unmatched = (
        db.query(Order)
        .filter_by(brand_id=brand_id, status="pending_match", source="bank_transfer")
        .order_by(desc(Order.ordered_at))
        .limit(100)
        .all()
    )

    # Recent manual orders
    manual = (
        db.query(Order)
        .filter_by(brand_id=brand_id, source="manual")
        .order_by(desc(Order.ordered_at))
        .limit(50)
        .all()
    )

    return {
        "unmatched_transfers": [_inbox_dict(o) for o in unmatched],
        "manual_orders": [_inbox_dict(o) for o in manual],
        "unmatched_count": len(unmatched),
    }


# ── POST /{id}/confirm ─────────────────────────────────────────────────────────

@router.post("/{order_id}/confirm")
def confirm_order(
    order_id: str,
    body: ConfirmOrderRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm a pending_match bank transfer as a real sale."""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "pending_match":
        raise HTTPException(status_code=400, detail="Order is not pending match")

    if body.customer_email or body.customer_phone:
        customer = _find_or_create_customer(
            db, order.brand_id,
            phone=body.customer_phone,
            email=body.customer_email,
            name=body.customer_name,
        )
        if customer:
            order.customer_id = customer.id

    order.status = "completed"
    order.channel = body.channel
    if body.customer_name and not order.customer_id:
        existing_notes = order.notes or ""
        order.notes = f"{existing_notes} | Customer: {body.customer_name}".strip(" |")

    db.commit()
    logger.info(f"[Orders] Confirmed order {order_id} as sale")
    return {"status": "confirmed", "order": _inbox_dict(order)}


# ── POST /{id}/confirm-transfer ────────────────────────────────────────────────

@router.post("/{order_id}/confirm-transfer")
def confirm_transfer(
    order_id: str,
    body: ConfirmTransferRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Match a pending bank transfer to a customer and optionally a product."""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "pending_match":
        raise HTTPException(status_code=400, detail="Order is not pending match")

    if body.customer_email or body.customer_phone:
        customer = _find_or_create_customer(
            db, order.brand_id,
            phone=body.customer_phone,
            email=body.customer_email,
            name=body.customer_name,
        )
        if customer:
            order.customer_id = customer.id

    # Optionally link a product as line item
    if body.product_id:
        product = db.get(Product, body.product_id)
        if product:
            existing_item = db.query(OrderItem).filter_by(order_id=order.id).first()
            if not existing_item:
                oi = OrderItem(
                    order_id=order.id,
                    brand_id=order.brand_id,
                    product_id=product.id,
                    name=product.name,
                    quantity=1,
                    unit_price=float(order.total_amount),
                    total_price=float(order.total_amount),
                )
                db.add(oi)

    order.status = "completed"
    order.channel = body.channel
    db.commit()
    logger.info(f"[Orders] Confirmed transfer {order_id}")
    return {"status": "confirmed", "order": _inbox_dict(order)}


# ── POST /{id}/archive ─────────────────────────────────────────────────────────

@router.post("/{order_id}/archive")
def archive_order(
    order_id: str,
    body: ArchiveOrderRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a pending_match order as 'not a sale'."""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "pending_match":
        raise HTTPException(status_code=400, detail="Order is not pending match")

    order.status = "archived"
    if body.reason:
        order.notes = f"{order.notes or ''} | Archived: {body.reason}".strip(" |")
    db.commit()
    return {"status": "archived"}


# ── GET /customers/search ──────────────────────────────────────────────────────

@router.get("/customers/search")
def search_customers(
    brand_id: str = Query(...),
    q: str = Query(..., min_length=3),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Autocomplete customers by phone or name (min 3 chars)."""
    q_lower = q.lower()
    customers = (
        db.query(Customer)
        .filter(Customer.brand_id == brand_id)
        .filter(
            or_(
                Customer.phone.ilike(f"%{q}%"),
                Customer.name.ilike(f"%{q_lower}%"),
                Customer.email.ilike(f"%{q_lower}%"),
            )
        )
        .limit(10)
        .all()
    )
    return {"customers": [c.to_dict() for c in customers]}


# ── GET /products/search ───────────────────────────────────────────────────────

@router.get("/products/search")
def search_products(
    brand_id: str = Query(...),
    q: str = Query("", min_length=0),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search products by name or SKU for the order form."""
    base = db.query(Product).filter(Product.brand_id == brand_id, Product.is_active == True)
    if q:
        base = base.filter(
            or_(Product.name.ilike(f"%{q}%"), Product.sku_code.ilike(f"%{q}%"))
        )
    products = base.order_by(Product.name).limit(30).all()
    return {"products": [
        {
            "id": p.id,
            "name": p.name,
            "sku_code": p.sku_code,
            "selling_price": float(p.selling_price),
            "current_stock": p.current_stock,
            "is_digital": p.is_digital,
        }
        for p in products
    ]}


# ── GET (general list) ─────────────────────────────────────────────────────────

@router.get("")
def list_orders(
    brand_id: str,
    status: Optional[str] = None,
    source: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """General order list with optional status/source filters."""
    offset = (page - 1) * page_size
    q = db.query(Order).filter(Order.brand_id == brand_id)
    if status:
        q = q.filter(Order.status == status)
    if source:
        q = q.filter(Order.source == source)
    orders = q.order_by(desc(Order.ordered_at)).offset(offset).limit(page_size).all()
    total = q.count()
    return {"orders": [o.to_dict() for o in orders], "total": total}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _inbox_dict(order: Order) -> dict:
    return {
        "id": order.id,
        "brand_id": order.brand_id,
        "customer_id": order.customer_id,
        "status": order.status,
        "total_amount": float(order.total_amount),
        "narration": order.notes,
        "ordered_at": order.ordered_at.isoformat(),
        "created_at": order.created_at.isoformat(),
        "source": order.source,
        "payment_gateway": order.payment_gateway,
        "external_id": order.external_id,
        "channel": order.channel,
        "payment_method": order.payment_method,
    }
