"""
ORYNT — SocialMetric Model

Stores social media page/post performance metrics from Instagram and Facebook.
One row = one metric type on one day for one platform.

platform: 'instagram' | 'facebook'
metric_type examples:
  Instagram post: 'post_likes', 'post_comments', 'post_reach', 'post_impressions'
  Facebook page:  'page_reach', 'page_engaged_users', 'page_views', 'page_fans'
"""

import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, DateTime, Date, ForeignKey, Numeric, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class SocialMetric(Base):
    __tablename__ = "social_metrics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True
    )

    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)   # 'instagram' | 'facebook'
    metric_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # For post-level metrics: the external post/media ID
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    # Human-readable label (post caption snippet, page name, etc.)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)

    metric_value: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Extra JSON metadata (media_type, permalink, thumbnail_url, etc.)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    brand: Mapped["Brand"] = relationship("Brand", back_populates="social_metrics")

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "brand_id": self.brand_id,
            "platform": self.platform,
            "metric_type": self.metric_type,
            "external_id": self.external_id,
            "label": self.label,
            "metric_value": float(self.metric_value),
            "date": self.date.isoformat(),
            "metadata": json.loads(self.metadata_json) if self.metadata_json else None,
            "created_at": self.created_at.isoformat(),
        }
