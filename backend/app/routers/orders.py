"""
ORYNT — Orders Router
GET  /api/orders/inbox         — list pending_match bank transfer orders for Order Inbox
POST /api/orders/{id}/confirm  — seller confirms a bank credit is a sale
POST /api/orders/{id}/archive  — seller marks a bank credit as not a sale
GET  /api/orders               — general order list (paginated)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.auth import get_current_user
from app.database import get_db
from app.models.order import Order
from app.models.customer import Customer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/orders", tags=["Orders"])


class ConfirmOrderRequest(BaseModel):
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    channel: str = "website"   # website | social | physical


class ArchiveOrderRequest(BaseModel):
    reason: str | None = None


@router.get("/inbox")
def get_inbox(
    brand_id: str,
    page: int = 1,
    page_size: int = 50,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all pending_match bank transfer orders for the Order Inbox.
    These are bank credits awaiting seller confirmation.
    """
    offset = (page - 1) * page_size
    orders = (
        db.query(Order)
        .filter_by(brand_id=brand_id, status="pending_match", source="bank_transfer")
        .order_by(desc(Order.ordered_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )
    total = db.query(Order).filter_by(
        brand_id=brand_id, status="pending_match", source="bank_transfer"
    ).count()

    return {
        "orders": [_inbox_dict(o) for o in orders],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{order_id}/confirm")
def confirm_order(
    order_id: str,
    body: ConfirmOrderRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Seller confirms a pending_match bank transfer is a real sale.
    Optionally creates/links a customer record.
    """
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "pending_match":
        raise HTTPException(status_code=400, detail="Order is not pending match")

    # Optionally find or create customer
    if body.customer_email:
        email = body.customer_email.lower().strip()
        customer = db.query(Customer).filter_by(brand_id=order.brand_id, email=email).first()
        if not customer:
            customer = Customer(
                brand_id=order.brand_id,
                email=email,
                name=body.customer_name or None,
                phone=body.customer_phone or None,
            )
            db.add(customer)
            db.flush()
        order.customer_id = customer.id

    order.status = "completed"
    order.channel = body.channel
    if body.customer_name and not order.customer_id:
        # No email — store name in notes alongside narration
        existing_notes = order.notes or ""
        order.notes = f"{existing_notes} | Customer: {body.customer_name}".strip(" |")

    db.commit()
    logger.info(f"[Orders] Confirmed order {order_id} as sale")
    return {"status": "confirmed", "order": _inbox_dict(order)}


@router.post("/{order_id}/archive")
def archive_order(
    order_id: str,
    body: ArchiveOrderRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Seller marks a pending_match order as 'not a sale' — archived.
    """
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "pending_match":
        raise HTTPException(status_code=400, detail="Order is not pending match")

    order.status = "archived"
    if body.reason:
        order.notes = f"{order.notes or ''} | Archived: {body.reason}".strip(" |")
    db.commit()
    logger.info(f"[Orders] Archived order {order_id}")
    return {"status": "archived"}


@router.get("")
def list_orders(
    brand_id: str,
    status: str | None = None,
    source: str | None = None,
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
    }
