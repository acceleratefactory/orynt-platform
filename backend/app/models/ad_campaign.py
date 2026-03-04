"""
ORYNT — AdCampaign Model

Stores ad campaign performance data from Meta (Facebook/Instagram),
Google Ads, and future ad platforms.

One row = one campaign on one day (time_increment=1 in Meta Insights API).
"""

import uuid
from datetime import datetime, date, timezone
from sqlalchemy import (
    String, DateTime, Date, ForeignKey, Numeric,
    Integer, BigInteger, UniqueConstraint, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class AdCampaign(Base):
    __tablename__ = "ad_campaigns"
    __table_args__ = (
        # One row per campaign per day per platform
        UniqueConstraint("brand_id", "platform", "external_campaign_id", "date", name="uq_ad_campaign_day"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Platform: 'meta', 'google', etc.
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # External identifiers
    external_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_campaign_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    campaign_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    campaign_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    objective: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Date of metrics (daily granularity)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Spend & reach
    spend: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    impressions: Mapped[int] = mapped_column(BigInteger, default=0)
    clicks: Mapped[int] = mapped_column(BigInteger, default=0)
    reach: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Computed metrics (stored for speed)
    cpm: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)   # cost per 1000 impressions
    cpc: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)   # cost per click
    ctr: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)   # click-through rate
    cpp: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)   # cost per purchase

    # Conversion actions
    purchases: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purchase_value: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    roas: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)   # purchase_value / spend
    leads: Mapped[int | None] = mapped_column(Integer, nullable=True)
    add_to_cart: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Raw actions JSON (serialized for extra fields)
    raw_actions: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    brand: Mapped["Brand"] = relationship("Brand", back_populates="ad_campaigns")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "brand_id": self.brand_id,
            "platform": self.platform,
            "external_account_id": self.external_account_id,
            "external_campaign_id": self.external_campaign_id,
            "campaign_name": self.campaign_name,
            "campaign_status": self.campaign_status,
            "objective": self.objective,
            "date": self.date.isoformat(),
            "spend": float(self.spend),
            "impressions": self.impressions,
            "clicks": self.clicks,
            "reach": self.reach,
            "cpm": float(self.cpm) if self.cpm is not None else None,
            "cpc": float(self.cpc) if self.cpc is not None else None,
            "ctr": float(self.ctr) if self.ctr is not None else None,
            "cpp": float(self.cpp) if self.cpp is not None else None,
            "purchases": self.purchases,
            "purchase_value": float(self.purchase_value) if self.purchase_value is not None else None,
            "roas": float(self.roas) if self.roas is not None else None,
            "leads": self.leads,
            "add_to_cart": self.add_to_cart,
        }
