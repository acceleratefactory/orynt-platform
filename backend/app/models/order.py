"""
ORYNT — Order Model
Represents a completed transaction pulled from a payment gateway or webhook.
Deduplication: (brand_id, external_id, source) must be unique.
Amounts stored in NGN (kobo divided by 100 on ingest).
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Numeric, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("brand_id", "external_id", "source", name="uq_order_brand_external_source"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Source / channel
    source: Mapped[str] = mapped_column(String(50), nullable=False)          # 'paystack', 'flutterwave', etc.
    channel: Mapped[str] = mapped_column(String(50), nullable=False, default="website")  # 'website', 'social', 'physical'

    # Status
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="completed")
    # completed | pending | refunded | transferred | failed

    # Financials — always in NGN
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    original_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)   # before conversion
    original_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    exchange_rate: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)

    # Payment details
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)  # 'card', 'bank_transfer', 'cash'
    payment_gateway: Mapped[str] = mapped_column(String(50), nullable=False)  # 'paystack', 'flutterwave', etc.
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)     # gateway reference / transaction ref

    # Metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    brand: Mapped["Brand"] = relationship("Brand", back_populates="orders")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "brand_id": self.brand_id,
            "customer_id": self.customer_id,
            "source": self.source,
            "channel": self.channel,
            "status": self.status,
            "total_amount": float(self.total_amount),
            "payment_method": self.payment_method,
            "payment_gateway": self.payment_gateway,
            "external_id": self.external_id,
            "ordered_at": self.ordered_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }
