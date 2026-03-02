"""
ORYNT — Organization SQLAlchemy Model
An Organization represents a business account (e.g. "Kemi's Boutique").
One user owns one organization.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    owner_phone: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationship to brands
    brands: Mapped[list["Brand"]] = relationship("Brand", back_populates="organization", lazy="select")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "owner_email": self.owner_email,
            "owner_phone": self.owner_phone,
            "created_at": self.created_at.isoformat(),
        }
