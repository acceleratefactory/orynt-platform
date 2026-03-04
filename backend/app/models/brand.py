"""
ORYNT — Brand SQLAlchemy Model
A Brand belongs to an Organization and represents a product line or storefront.
One organization can have multiple brands.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


VALID_SELLER_TYPES = ["website", "social_whatsapp", "physical", "digital"]


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Task 1.1: seller type from onboarding flow
    seller_type: Mapped[str] = mapped_column(String(50), nullable=True)
    # Task 1.1: payment methods selected during onboarding (comma-separated)
    payment_methods: Mapped[str] = mapped_column(Text, nullable=True)
    # Onboarding completed flag
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="brands")
    products: Mapped[list["Product"]] = relationship("Product", back_populates="brand", cascade="all, delete-orphan")
    integrations: Mapped[list["Integration"]] = relationship("Integration", back_populates="brand", cascade="all, delete-orphan")
    customers: Mapped[list["Customer"]] = relationship("Customer", back_populates="brand", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="brand", cascade="all, delete-orphan")
    ad_campaigns: Mapped[list["AdCampaign"]] = relationship("AdCampaign", back_populates="brand", cascade="all, delete-orphan")
    social_metrics: Mapped[list["SocialMetric"]] = relationship("SocialMetric", back_populates="brand", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "organization_id": self.organization_id,
            "seller_type": self.seller_type,
            "payment_methods": self.payment_methods.split(",") if self.payment_methods else [],
            "onboarding_completed": self.onboarding_completed,
            "created_at": self.created_at.isoformat(),
        }
