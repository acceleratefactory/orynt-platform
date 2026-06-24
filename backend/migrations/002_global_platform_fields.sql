-- =============================================================
-- ORYNT — Commerce Intelligence Platform
-- Migration 002: Global Platform Fields & Schema Additions
-- Run this AFTER 001_initial_schema.sql and 002_rls_policies.sql
-- =============================================================

-- -----------------------------------------------------------
-- 1. Add global fields to organizations table
-- -----------------------------------------------------------
ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS display_currency TEXT DEFAULT 'USD',
  ADD COLUMN IF NOT EXISTS primary_country TEXT DEFAULT 'NG',
  ADD COLUMN IF NOT EXISTS market_tone TEXT DEFAULT 'conversational'
    CHECK (market_tone IN ('conversational', 'structured')),
  ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'Africa/Lagos';

-- -----------------------------------------------------------
-- 2. Fix brands table — add source_currency for backward compat
-- -----------------------------------------------------------
ALTER TABLE brands
  ADD COLUMN IF NOT EXISTS source_currency TEXT DEFAULT 'NGN';

-- -----------------------------------------------------------
-- 3. Add global monetary fields to orders table
-- -----------------------------------------------------------
ALTER TABLE orders
  ADD COLUMN IF NOT EXISTS amount_usd NUMERIC,
  ADD COLUMN IF NOT EXISTS amount_original NUMERIC,
  ADD COLUMN IF NOT EXISTS original_currency TEXT DEFAULT 'NGN';

-- Set amount_usd = total_amount for existing orders (assume NGN = NGN)
UPDATE orders SET amount_usd = total_amount WHERE amount_usd IS NULL;

-- -----------------------------------------------------------
-- 4. Add canonical fields to products table
-- -----------------------------------------------------------
ALTER TABLE products
  ADD COLUMN IF NOT EXISTS source_category TEXT,
  ADD COLUMN IF NOT EXISTS canonical_category TEXT;

-- -----------------------------------------------------------
-- 5. Expand integrations type enum to include global gateways
-- -----------------------------------------------------------
ALTER TABLE integrations
  DROP CONSTRAINT IF EXISTS integrations_type_check;

ALTER TABLE integrations
  ADD CONSTRAINT integrations_type_check CHECK (type IN (
    'shopify', 'woocommerce', 'paystack', 'flutterwave', 'monnify',
    'opay', 'mono', 'meta_ads', 'google_ads', 'tiktok_ads',
    'instagram', 'facebook_page', 'bumpa_csv', 'manual',
    'selar', 'gumroad', 'reseller_platform', 'preorder_platform',
    'stripe', 'paytabs', 'mollie', 'paypal', 'telr',
    'square', 'skinos_platform', 'universal_webhook',
    'skinos_platform_womens', 'skinos_platform_mens', 'skinos_platform_clinic'
  ));

-- -----------------------------------------------------------
-- 6. Create cross_brand_benchmarks table (Sprint 3+)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS cross_brand_benchmarks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category TEXT NOT NULL,
  metric TEXT NOT NULL,
  median_value NUMERIC,
  top_decile_value NUMERIC,
  bottom_decile_value NUMERIC,
  brand_count INTEGER DEFAULT 0,
  market TEXT DEFAULT 'global',
  calculated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE cross_brand_benchmarks ENABLE ROW LEVEL SECURITY;

-- cross_brand_benchmarks is read-only for all authenticated users
CREATE POLICY "cross_brand_benchmarks: authenticated read"
ON cross_brand_benchmarks FOR SELECT
USING (auth.role() = 'authenticated');

-- -----------------------------------------------------------
-- 7. Create stock_movements table (Sprint 1 Task 1.1)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_movements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL REFERENCES products(id),
  brand_id UUID NOT NULL REFERENCES brands(id),
  movement_type TEXT NOT NULL CHECK (movement_type IN ('sale', 'restock', 'adjustment', 'write_off', 'return')),
  quantity_change INTEGER NOT NULL,
  stock_before INTEGER NOT NULL,
  stock_after INTEGER NOT NULL,
  order_id UUID REFERENCES orders(id),
  note TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE stock_movements ENABLE ROW LEVEL SECURITY;

CREATE POLICY "stock_movements_own_brands"
ON stock_movements FOR ALL
USING (
  brand_id IN (
    SELECT b.id FROM brands b
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);

-- -----------------------------------------------------------
-- 8. Create sync_errors table (Sprint 1 Task 1.13)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_errors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  integration_id UUID REFERENCES integrations(id),
  brand_id UUID REFERENCES brands(id),
  error_type TEXT,
  error_message TEXT,
  occurred_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE sync_errors ENABLE ROW LEVEL SECURITY;

CREATE POLICY "sync_errors_own_brands"
ON sync_errors FOR ALL
USING (
  brand_id IN (
    SELECT b.id FROM brands b
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);

-- -----------------------------------------------------------
-- 9. Create social_metrics table (Sprint 1 Task 1.12)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS social_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID NOT NULL REFERENCES brands(id),
  platform TEXT,
  metric_type TEXT,
  metric_value NUMERIC,
  date DATE,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE social_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "social_metrics_own_brands"
ON social_metrics FOR ALL
USING (
  brand_id IN (
    SELECT b.id FROM brands b
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);
