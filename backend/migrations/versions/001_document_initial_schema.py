"""
Migration: 001 — Document Initial Schema
Revision ID: 001
Revises: —
Create Date: 2026-03-01

PURPOSE: This migration documents the schema that was manually created in
Supabase via the SQL editor (001_initial_schema.sql). It does NOT re-create
any tables — those already exist. Run with --fake to mark as applied:

    alembic stamp 001

Once stamped, future alembic upgrade head commands will pick up from here.
"""

from typing import Sequence, Union
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Schema already exists in Supabase — applied via SQL editor.
    Tables: organizations, brands, integrations, products, customers,
            orders, order_items, sku_scores, customer_segments,
            ad_campaigns, cip_scores, cip_score_access,
            automation_rules, weekly_digests
    This migration is a no-op. Mark as applied with: alembic stamp 001
    """
    pass


def downgrade() -> None:
    """
    Dropping the initial schema in a downgrade would destroy all data.
    This is intentionally a no-op. Never run downgrade on production.
    """
    pass
