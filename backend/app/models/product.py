"""
ORYNT — Product SQLAlchemy Model
Products are scoped to a brand. Supports manual entry, CSV import,
and future integrations (Shopify, WooCommerce, etc).
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Numeric, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Source platform (manual, csv, shopify, woocommerce, etc)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    # External ID for deduplication (external_id + source must be unique per brand)
    external_id: Mapped[str] = mapped_column(String(255), nullable=True)

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    sku_code: Mapped[str] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True)

    cost_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    selling_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    current_stock: Mapped[int] = mapped_column(Integer, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_digital: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    brand: Mapped["Brand"] = relationship("Brand", back_populates="products")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "brand_id": self.brand_id,
            "source": self.source,
            "external_id": self.external_id,
            "name": self.name,
            "sku_code": self.sku_code,
            "category": self.category,
            "cost_price": float(self.cost_price) if self.cost_price is not None else None,
            "selling_price": float(self.selling_price),
            "current_stock": self.current_stock,
            "is_active": self.is_active,
            "is_digital": self.is_digital,
            "created_at": self.created_at.isoformat(),
        }
