"""
ORYNT — OrderItem Model
Line items belonging to an Order (e.g. from Shopify orders).
Each item links back to a Product via (brand_id, external_id, source).
"""

import uuid
from decimal import Decimal
from sqlalchemy import String, ForeignKey, Numeric, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Link to product (nullable — product may not exist in ORYNT yet)
    product_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )

    # External identifiers for dedup / linking
    external_product_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_variant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "brand_id": self.brand_id,
            "product_id": self.product_id,
            "external_product_id": self.external_product_id,
            "external_variant_id": self.external_variant_id,
            "name": self.name,
            "sku": self.sku,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "total_price": float(self.total_price),
        }
