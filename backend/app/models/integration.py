"""
ORYNT — Integration Model
Stores connected payment gateway credentials (encrypted) per brand.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)           # 'paystack', 'flutterwave', etc.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="connected")  # connected | error | disconnected
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)       # Fernet-encrypted secret key
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    brand: Mapped["Brand"] = relationship("Brand", back_populates="integrations")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "brand_id": self.brand_id,
            "type": self.type,
            "status": self.status,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "transaction_count": self.transaction_count,
            "created_at": self.created_at.isoformat(),
        }
