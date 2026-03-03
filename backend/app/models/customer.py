"""
ORYNT — Customer Model
A customer belongs to a brand (not the org) — same email can exist across brands.
Created from transaction data during Paystack sync and webhook events.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("brand_id", "email", name="uq_customer_brand_email"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    brand: Mapped["Brand"] = relationship("Brand", back_populates="customers")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "brand_id": self.brand_id,
            "email": self.email,
            "name": self.name,
            "phone": self.phone,
            "created_at": self.created_at.isoformat(),
        }
