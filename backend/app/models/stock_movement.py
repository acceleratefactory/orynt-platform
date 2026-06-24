import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=False, index=True
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brands.id"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_before: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_after: Mapped[int] = mapped_column(Integer, nullable=False)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.id"), nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    product: Mapped["Product"] = relationship("Product")
    brand: Mapped["Brand"] = relationship("Brand")
    order: Mapped["Order"] = relationship("Order")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "brand_id": self.brand_id,
            "movement_type": self.movement_type,
            "quantity_change": self.quantity_change,
            "stock_before": self.stock_before,
            "stock_after": self.stock_after,
            "order_id": self.order_id,
            "note": self.note,
            "created_at": self.created_at.isoformat(),
        }
