"""
Migration: Add Task 1.1 columns to brands table and create products table.
Run once: python migrate.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from app.database import _get_engine

engine = _get_engine()

migrations = [
    # Add new columns to brands table (IF NOT EXISTS is safe to run multiple times)
    "ALTER TABLE brands ADD COLUMN IF NOT EXISTS seller_type VARCHAR(50)",
    "ALTER TABLE brands ADD COLUMN IF NOT EXISTS payment_methods TEXT",
    "ALTER TABLE brands ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT FALSE",

    # Create products table if it doesn't exist
    """
    CREATE TABLE IF NOT EXISTS products (
        id VARCHAR(36) PRIMARY KEY,
        brand_id VARCHAR(36) NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
        source VARCHAR(50) DEFAULT 'manual',
        external_id VARCHAR(255),
        name VARCHAR(500) NOT NULL,
        sku_code VARCHAR(255),
        category VARCHAR(100),
        cost_price NUMERIC(12, 2),
        selling_price NUMERIC(12, 2) NOT NULL,
        current_stock INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT TRUE,
        is_digital BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # Index for fast brand queries
    "CREATE INDEX IF NOT EXISTS ix_products_brand_id ON products(brand_id)",
]

with engine.connect() as conn:
    for sql in migrations:
        print(f"Running: {sql.strip()[:60]}...")
        conn.execute(text(sql))
    conn.commit()
    print("\n✅ Migration complete.")
