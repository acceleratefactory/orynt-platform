-- =============================================================
-- ORYNT — Commerce Intelligence Platform
-- Migration 001: Initial Schema
-- Run this in the Supabase SQL Editor FIRST, before RLS policies.
-- =============================================================

-- ---------------------------------------------------------
-- Organizations
-- One organization = one founder/owner. Can have many brands.
-- ---------------------------------------------------------
CREATE TABLE organizations (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          TEXT NOT NULL,
  owner_email   TEXT NOT NULL,
  owner_phone   TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  plan          TEXT DEFAULT 'free' CHECK (plan IN ('free','growth','scale','enterprise'))
);

-- ---------------------------------------------------------
-- Brands
-- Each organization can own multiple brands.
-- Preorder and reseller platform fields included from day one.
-- ---------------------------------------------------------
CREATE TABLE brands (
  id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id             UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name                        TEXT NOT NULL,
  category                    TEXT,
  created_at                  TIMESTAMPTZ DEFAULT NOW(),
  currency                    TEXT DEFAULT 'NGN',
  timezone                    TEXT DEFAULT 'Africa/Lagos',
  is_active                   BOOLEAN DEFAULT TRUE,
  preorder_reliability_score  NUMERIC  -- sourced from pop_sellers.reliability_score (preorder_platform brands only)
);

-- ---------------------------------------------------------
-- Integrations
-- Every brand's connected data source. One row per connection.
-- vendor_id / reseller_id / platform_installation support
-- the reseller_platform and preorder_platform custom integrations.
-- ---------------------------------------------------------
CREATE TABLE integrations (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id              UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  type                  TEXT NOT NULL CHECK (type IN (
                          'shopify','woocommerce','paystack','flutterwave','monnify',
                          'opay','mono','meta_ads','google_ads','tiktok_ads',
                          'instagram','facebook_page','bumpa_csv','manual',
                          'selar','gumroad','reseller_platform','preorder_platform'
                        )),
  credentials           JSONB,    -- encrypted API keys / tokens
  status                TEXT DEFAULT 'connected' CHECK (status IN ('connected','error','disconnected')),
  last_sync_at          TIMESTAMPTZ,
  metadata              JSONB,    -- store URL, account ID, etc.
  vendor_id             TEXT,     -- wp_storefronts.id (reseller_platform) or pop_sellers.id (preorder_platform)
  reseller_id           TEXT,     -- wp_users.ID of storefront owner (reseller_platform only)
  platform_installation TEXT,     -- which WordPress installation this came from
  created_at            TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------
-- Products / SKUs
-- is_digital   → Selar / Gumroad products (no inventory scoring)
-- is_preorder  → pop_campaigns records (no stock; uses funded_rate)
-- UNIQUE on (brand_id, external_id, source) prevents duplicate ingestion.
-- ---------------------------------------------------------
CREATE TABLE products (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id      UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  external_id   TEXT,
  source        TEXT,
  name          TEXT NOT NULL,
  sku_code      TEXT,
  category      TEXT,
  cost_price    NUMERIC DEFAULT 0,
  selling_price NUMERIC DEFAULT 0,
  current_stock INTEGER DEFAULT 0,
  is_active     BOOLEAN DEFAULT TRUE,
  is_digital    BOOLEAN DEFAULT FALSE,  -- Selar / Gumroad products
  is_preorder   BOOLEAN DEFAULT FALSE,  -- preorder_platform campaigns
  metadata      JSONB,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (brand_id, external_id, source)
);

-- ---------------------------------------------------------
-- Customers
-- Phone normalized to +234XXXXXXXXXX on ingest.
-- UNIQUE on (brand_id, external_id, source).
-- ---------------------------------------------------------
CREATE TABLE customers (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id          UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  external_id       TEXT,
  source            TEXT,
  name              TEXT,
  email             TEXT,
  phone             TEXT,
  state             TEXT,
  lga               TEXT,
  first_purchase_at TIMESTAMPTZ,
  last_purchase_at  TIMESTAMPTZ,
  total_orders      INTEGER DEFAULT 0,
  total_spend       NUMERIC DEFAULT 0,
  metadata          JSONB,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (brand_id, external_id, source)
);

-- ---------------------------------------------------------
-- Orders
-- status covers both standard e-commerce AND preorder campaign lifecycle.
-- UNIQUE on (brand_id, external_id, source) prevents duplicate ingestion.
-- ---------------------------------------------------------
CREATE TABLE orders (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id          UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  customer_id       UUID REFERENCES customers(id),
  external_id       TEXT,
  source            TEXT,  -- paystack | shopify | manual | preorder_platform | reseller_platform | etc.
  channel           TEXT,  -- website | whatsapp | instagram | preorder | physical | marketplace
  status            TEXT DEFAULT 'pending' CHECK (status IN (
                      'pending','confirmed','processing','shipped',
                      'in_transit','out_for_delivery','completed','refunded','cancelled'
                    )),
  total_amount      NUMERIC DEFAULT 0,    -- always NGN
  original_amount   NUMERIC,
  original_currency TEXT DEFAULT 'NGN',
  exchange_rate     NUMERIC DEFAULT 1,
  payment_method    TEXT,
  payment_gateway   TEXT,
  delivery_state    TEXT,
  delivery_lga      TEXT,
  logistics_partner TEXT,
  ordered_at        TIMESTAMPTZ,
  completed_at      TIMESTAMPTZ,
  metadata          JSONB,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (brand_id, external_id, source)
);

-- ---------------------------------------------------------
-- Order Line Items
-- ---------------------------------------------------------
CREATE TABLE order_items (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id    UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id  UUID REFERENCES products(id),
  quantity    INTEGER NOT NULL DEFAULT 1,
  unit_price  NUMERIC DEFAULT 0,
  total_price NUMERIC DEFAULT 0,
  cost_price  NUMERIC DEFAULT 0,  -- snapshot at time of sale
  metadata    JSONB
);

-- ---------------------------------------------------------
-- SKU Scores (computed nightly by Celery at 3:00 AM WAT)
-- funded_rate and delivery_completion_rate are preorder-specific.
-- NULL for non-preorder products.
-- ---------------------------------------------------------
CREATE TABLE sku_scores (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id              UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  brand_id                UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  score                   NUMERIC CHECK (score >= 1 AND score <= 10),
  verdict                 TEXT CHECK (verdict IN ('scale','monitor','fix','kill')),
  trend                   TEXT CHECK (trend IN ('improving','stable','declining')),
  reason                  TEXT,
  velocity_7d             NUMERIC DEFAULT 0,
  velocity_30d            NUMERIC DEFAULT 0,
  velocity_90d            NUMERIC DEFAULT 0,
  return_rate             NUMERIC DEFAULT 0,
  repeat_purchase_rate    NUMERIC DEFAULT 0,
  days_of_inventory       INTEGER,              -- NULL for digital and preorder products
  margin_percent          NUMERIC DEFAULT 0,
  capital_locked          NUMERIC DEFAULT 0,    -- current_stock * cost_price
  funded_rate             NUMERIC,              -- preorder: units_ordered / target_quantity
  delivery_completion_rate NUMERIC,             -- preorder: units_delivered / units_ordered
  scored_at               TIMESTAMPTZ DEFAULT NOW(),
  created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------
-- Customer Segments (computed nightly by Celery at 3:30 AM WAT)
-- ---------------------------------------------------------
CREATE TABLE customer_segments (
  id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id                 UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  brand_id                    UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  segment                     TEXT CHECK (segment IN (
                                'champion','loyal','promising','at_risk','lost','one_and_done'
                              )),
  churn_probability_14d       NUMERIC DEFAULT 0,
  churn_probability_30d       NUMERIC DEFAULT 0,
  predicted_next_purchase_at  TIMESTAMPTZ,
  ltv_90d                     NUMERIC DEFAULT 0,
  ltv_365d                    NUMERIC DEFAULT 0,
  segmented_at                TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------
-- Ad Campaigns (from Meta / Google / TikTok)
-- ---------------------------------------------------------
CREATE TABLE ad_campaigns (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id             UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  platform             TEXT CHECK (platform IN ('meta','google','tiktok','twitter')),
  external_campaign_id TEXT,
  name                 TEXT,
  status               TEXT,
  spend                NUMERIC DEFAULT 0,
  impressions          INTEGER DEFAULT 0,
  clicks               INTEGER DEFAULT 0,
  cpm                  NUMERIC DEFAULT 0,
  cpc                  NUMERIC DEFAULT 0,
  date                 DATE,
  metadata             JSONB
);

-- ---------------------------------------------------------
-- CIP Scores (computed after 6+ months of data, Sprint 9)
-- ---------------------------------------------------------
CREATE TABLE cip_scores (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id                  UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  score                     NUMERIC CHECK (score >= 0 AND score <= 100),
  revenue_trend_score       NUMERIC,
  consistency_score         NUMERIC,
  inventory_health_score    NUMERIC,
  customer_retention_score  NUMERIC,
  payment_reliability_score NUMERIC,
  channel_diversity_score   NUMERIC,
  trajectory_score          NUMERIC,
  computed_at               TIMESTAMPTZ DEFAULT NOW(),
  data_months               INTEGER DEFAULT 0
);

-- ---------------------------------------------------------
-- CIP Score Access Log (consent + institutional access)
-- ---------------------------------------------------------
CREATE TABLE cip_score_access (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id         UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  institution_id   UUID,
  institution_name TEXT,
  access_type      TEXT CHECK (access_type IN (
                     'credit_check','supplier_prequalification','investor_report'
                   )),
  consented_at     TIMESTAMPTZ,
  accessed_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------
-- Automation Rules
-- ---------------------------------------------------------
CREATE TABLE automation_rules (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id           UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name               TEXT NOT NULL,
  is_active          BOOLEAN DEFAULT TRUE,
  trigger_type       TEXT,
  trigger_conditions JSONB,
  action_type        TEXT,
  action_config      JSONB,
  last_triggered_at  TIMESTAMPTZ,
  created_at         TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------
-- Weekly Digests
-- ---------------------------------------------------------
CREATE TABLE weekly_digests (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id            UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  week_start          DATE NOT NULL,
  revenue_this_week   NUMERIC DEFAULT 0,
  revenue_last_week   NUMERIC DEFAULT 0,
  top_sku_to_scale    UUID REFERENCES products(id),
  top_sku_at_risk     UUID REFERENCES products(id),
  churn_risk_count    INTEGER DEFAULT 0,
  champion_count      INTEGER DEFAULT 0,
  recommendations     JSONB,
  delivered_whatsapp  BOOLEAN DEFAULT FALSE,
  delivered_email     BOOLEAN DEFAULT FALSE,
  created_at          TIMESTAMPTZ DEFAULT NOW()
);
