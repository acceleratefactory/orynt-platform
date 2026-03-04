"""
ORYNT — SyncError Model

Logs errors from integration sync jobs.
Written when:
  - A sync task raises an unhandled exception
  - check_stale_integrations marks an integration as stale
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class SyncError(Base):
    __tablename__ = "sync_errors"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    integration_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("integrations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    brand_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # 'sync_failure' | 'stale_integration' | 'token_expired' | 'api_error'
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Additional context (stack trace, API response snippet, etc.)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "integration_id": self.integration_id,
            "brand_id": self.brand_id,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "occurred_at": self.occurred_at.isoformat(),
        }
