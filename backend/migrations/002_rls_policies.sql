-- =============================================================
-- ORYNT — Commerce Intelligence Platform
-- Migration 002: Row Level Security Policies
-- Run this AFTER 001_initial_schema.sql.
-- Every table must be locked down. A brand can NEVER see
-- another brand's data — even if the API has a bug.
-- =============================================================

-- ---------------------------------------------------------
-- Enable RLS on every table
-- ---------------------------------------------------------
ALTER TABLE organizations      ENABLE ROW LEVEL SECURITY;
ALTER TABLE brands             ENABLE ROW LEVEL SECURITY;
ALTER TABLE integrations       ENABLE ROW LEVEL SECURITY;
ALTER TABLE products           ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers          ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders             ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items        ENABLE ROW LEVEL SECURITY;
ALTER TABLE sku_scores         ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_segments  ENABLE ROW LEVEL SECURITY;
ALTER TABLE ad_campaigns       ENABLE ROW LEVEL SECURITY;
ALTER TABLE cip_scores         ENABLE ROW LEVEL SECURITY;
ALTER TABLE cip_score_access   ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_rules   ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_digests     ENABLE ROW LEVEL SECURITY;

-- =============================================================
-- ORGANIZATIONS
-- A user can only read/write their own organization.
-- Owner is identified by owner_email matching the JWT claim.
-- =============================================================

CREATE POLICY "org_select_own"
ON organizations FOR SELECT
USING (owner_email = auth.jwt() ->> 'email');

CREATE POLICY "org_insert_own"
ON organizations FOR INSERT
WITH CHECK (owner_email = auth.jwt() ->> 'email');

CREATE POLICY "org_update_own"
ON organizations FOR UPDATE
USING (owner_email = auth.jwt() ->> 'email');

-- =============================================================
-- BRANDS
-- A user can only see brands that belong to their organization.
-- =============================================================

CREATE POLICY "brands_select_own"
ON brands FOR SELECT
USING (
  organization_id IN (
    SELECT id FROM organizations
    WHERE owner_email = auth.jwt() ->> 'email'
  )
);

CREATE POLICY "brands_insert_own"
ON brands FOR INSERT
WITH CHECK (
  organization_id IN (
    SELECT id FROM organizations
    WHERE owner_email = auth.jwt() ->> 'email'
  )
);

CREATE POLICY "brands_update_own"
ON brands FOR UPDATE
USING (
  organization_id IN (
    SELECT id FROM organizations
    WHERE owner_email = auth.jwt() ->> 'email'
  )
);

CREATE POLICY "brands_delete_own"
ON brands FOR DELETE
USING (
  organization_id IN (
    SELECT id FROM organizations
    WHERE owner_email = auth.jwt() ->> 'email'
  )
);

-- =============================================================
-- HELPER: reusable CTE pattern for brand isolation
-- All tables below use the same two-hop check:
--   table.brand_id → brands.organization_id → organizations.owner_email
-- =============================================================

-- INTEGRATIONS
CREATE POLICY "integrations_own_brands"
ON integrations FOR ALL
USING (
  brand_id IN (
    SELECT b.id FROM brands b
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);

-- PRODUCTS
CREATE POLICY "products_own_brands"
ON products FOR ALL
USING (
  brand_id IN (
    SELECT b.id FROM brands b
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);

-- CUSTOMERS
CREATE POLICY "customers_own_brands"
ON customers FOR ALL
USING (
  brand_id IN (
    SELECT b.id FROM brands b
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);

-- ORDERS
CREATE POLICY "orders_own_brands"
ON orders FOR ALL
USING (
  brand_id IN (
    SELECT b.id FROM brands b
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);

-- ORDER ITEMS (three-hop: order_items → orders → brands → organizations)
CREATE POLICY "order_items_own_brands"
ON order_items FOR ALL
USING (
  order_id IN (
    SELECT ord.id FROM orders ord
    JOIN brands b ON b.id = ord.brand_id
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);

-- SKU SCORES
CREATE POLICY "sku_scores_own_brands"
ON sku_scores FOR ALL
USING (
  brand_id IN (
    SELECT b.id FROM brands b
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);

-- CUSTOMER SEGMENTS
CREATE POLICY "customer_segments_own_brands"
ON customer_segments FOR ALL
USING (
  brand_id IN (
    SELECT b.id FROM brands b
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);

-- AD CAMPAIGNS
CREATE POLICY "ad_campaigns_own_brands"
ON ad_campaigns FOR ALL
USING (
  brand_id IN (
    SELECT b.id FROM brands b
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);

-- CIP SCORES
CREATE POLICY "cip_scores_own_brands"
ON cip_scores FOR ALL
USING (
  brand_id IN (
    SELECT b.id FROM brands b
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);

-- CIP SCORE ACCESS
CREATE POLICY "cip_score_access_own_brands"
ON cip_score_access FOR ALL
USING (
  brand_id IN (
    SELECT b.id FROM brands b
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);

-- AUTOMATION RULES
CREATE POLICY "automation_rules_own_brands"
ON automation_rules FOR ALL
USING (
  brand_id IN (
    SELECT b.id FROM brands b
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);

-- WEEKLY DIGESTS
CREATE POLICY "weekly_digests_own_brands"
ON weekly_digests FOR ALL
USING (
  brand_id IN (
    SELECT b.id FROM brands b
    JOIN organizations o ON o.id = b.organization_id
    WHERE o.owner_email = auth.jwt() ->> 'email'
  )
);
