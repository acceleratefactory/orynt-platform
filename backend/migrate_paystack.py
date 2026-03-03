"""
Migration: Add missing columns from Task 1.2 to existing tables.
Run once: .venv\Scripts\python migrate_paystack.py
"""
from dotenv import load_dotenv
load_dotenv()

from app.database import _get_engine
from sqlalchemy import text

engine = _get_engine()

migrations = [
    # ── integrations table ─────────────────────────────────────────────────
    "ALTER TABLE integrations ADD COLUMN IF NOT EXISTS encrypted_key TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE integrations ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'connected'",
    "ALTER TABLE integrations ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMPTZ",
    "ALTER TABLE integrations ADD COLUMN IF NOT EXISTS transaction_count INTEGER NOT NULL DEFAULT 0",
    # Remove default after adding (encrypted_key can't stay blank forever, just needed for ADD)

    # ── customers table (may not exist yet) ────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS customers (
        id VARCHAR(36) PRIMARY KEY,
        brand_id VARCHAR(36) NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
        email VARCHAR(255) NOT NULL,
        name VARCHAR(255),
        phone VARCHAR(50),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_customer_brand_email UNIQUE (brand_id, email)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_customers_brand_id ON customers (brand_id)",
    "CREATE INDEX IF NOT EXISTS ix_customers_email ON customers (email)",

    # ── orders table (may not exist yet) ─────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS orders (
        id VARCHAR(36) PRIMARY KEY,
        brand_id VARCHAR(36) NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
        customer_id VARCHAR(36) REFERENCES customers(id) ON DELETE SET NULL,
        source VARCHAR(50) NOT NULL,
        channel VARCHAR(50) NOT NULL DEFAULT 'website',
        status VARCHAR(30) NOT NULL DEFAULT 'completed',
        total_amount NUMERIC(12,2) NOT NULL,
        original_amount NUMERIC(12,2),
        original_currency VARCHAR(10),
        exchange_rate NUMERIC(12,6),
        payment_method VARCHAR(50) NOT NULL,
        payment_gateway VARCHAR(50) NOT NULL,
        external_id VARCHAR(255) NOT NULL,
        notes TEXT,
        ordered_at TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_order_brand_external_source UNIQUE (brand_id, external_id, source)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_orders_brand_id ON orders (brand_id)",
    "CREATE INDEX IF NOT EXISTS ix_orders_customer_id ON orders (customer_id)",
]

with engine.begin() as conn:
    for sql in migrations:
        sql = sql.strip()
        if sql:
            print(f"Running: {sql[:80]}...")
            conn.execute(text(sql))
            print("  OK")

print("\nAll migrations complete.")
