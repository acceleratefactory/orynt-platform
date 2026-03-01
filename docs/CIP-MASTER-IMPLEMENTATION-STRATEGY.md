# CIP — Commerce Intelligence Platform
# MASTER IMPLEMENTATION STRATEGY
## Complete Sprint-by-Sprint Build Document

**For Claude Code:** This is the single source of truth for everything we are building. Read this entire document before writing any code. Every sprint references back here. Every technical decision is documented here. Do not deviate from the architecture without flagging it first.

**For the Founder:** This is the war plan. Every sprint is a discrete unit of work. We complete one sprint fully before starting the next. No exceptions.

---

## WHAT WE ARE BUILDING

CIP is a Commerce Intelligence Platform for Nigerian SMEs. It is not a store builder, not a payment gateway, not a CRM. It is the intelligence layer that sits on top of everything a brand already uses — collecting their data, scoring their products and customers, predicting what will happen next, and automating the right actions.

**Product North Star:** CIP tells brand owners exactly what to do next with their money, products, and customers — then automates as much of it as possible.

**Business Model:** Free for brands. Revenue from institutions — fintechs, FMCG companies, suppliers — who pay for the commerce intelligence and credit scoring data the platform generates across thousands of Nigerian businesses. This is not SaaS. This is a data network.

**Primary Market:** Nigerian SMEs — from Shopify stores to WhatsApp sellers to kiosk operators. Every seller with any digital payment trail can use CIP.

**The Moat:** Not the technology. The dataset. Twelve months of Nigerian commerce behavior data across thousands of brands, trained into a CIP Score that fintechs embed into their underwriting. Once embedded, the moat is permanent.

---

## WHAT WE ARE NOT BUILDING

Hard boundaries. Never cross these regardless of how good the idea sounds:

- Not a website builder (Bumpa and Shopify exist)
- Not a payment gateway (Paystack and Flutterwave exist)
- Not a logistics platform (GIG and Sendbox exist)
- Not a full accounting system (Xero and Sage exist)
- Not a social media scheduling tool (Buffer exists)
- Not a customer support chatbot (Intercom exists)
- Not a competitor to Bumpa or Shopify
- Not a no-code platform

---

## TECH STACK — FINAL DECISIONS

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Styling:** Tailwind CSS
- **Charts:** Recharts
- **State management:** Zustand
- **API calls:** TanStack Query (React Query)
- **UI components:** shadcn/ui built on Radix

### Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Task queue:** Celery with Redis as broker
- **Scheduling:** APScheduler (for periodic jobs — runs inside FastAPI, no separate Airflow until scale requires it)
- **ORM:** SQLAlchemy with Alembic for migrations

### Database
- **Primary:** PostgreSQL via Supabase (managed Postgres + auth + storage in one)
- **Cache:** Redis (via Upstash — serverless Redis, no server to manage)
- **File storage:** Supabase Storage (for CSV uploads, PDF exports)

### Infrastructure
- **Application hosting:** Railway.app (frontend + backend deployed here)
- **Database:** Supabase (separate from Railway)
- **Cache:** Upstash Redis
- **Migration to AWS:** When first fintech contract is signed and data residency in Africa is required

### Authentication
- Supabase Auth (handles signup, login, session management, 2FA)
- JWT tokens passed to FastAPI backend
- Row Level Security (RLS) in Supabase for data isolation between brands

### Notifications
- **WhatsApp:** AfricasTalking WhatsApp Business API
- **Email:** Resend (simple, developer-friendly email API)
- **In-app:** Supabase Realtime

### Integrations (by priority)
**Payment Gateways (Priority 1):**
- Paystack — REST API + webhooks
- Flutterwave — REST API + webhooks
- Monnify (Moniepoint's gateway) — REST API
- OPay Merchant API — REST API

**Open Banking (Priority 1):**
- Mono — Open Banking API for bank account statement access (solves the bank transfer data problem)

**E-commerce Platforms (Priority 1):**
- Shopify — GraphQL Admin API + webhooks
- WooCommerce — REST API + webhooks
- Bumpa — CSV import (no public API yet; build API connection when partnership is established)
- Paystack Commerce / Flutterwave Storefront — via their payment APIs

**POS Systems (Priority 2):**
- Moniepoint POS — API for registered business accounts
- OPay POS — API for registered business accounts

**Advertising (Priority 2):**
- Meta Ads (Facebook + Instagram) — Meta Marketing API
- Google Ads — Google Ads API
- TikTok Ads — TikTok Marketing API

**Social Media Analytics (Priority 2):**
- Instagram Business — Instagram Graph API (post/story performance, NOT transaction data)
- Facebook Page — Page Insights API
- TikTok Business — TikTok Business API

**Communications (Priority 2):**
- WhatsApp Business — AfricasTalking BSP
- AfricasTalking SMS — for SMS fallback

**Logistics (Priority 3):**
- GIG Logistics API
- Sendbox API
- Kwik Delivery API

---

## DATABASE SCHEMA — DESIGN FIRST

This is the most important technical decision in the entire project. Every feature is built on top of this schema. Get it wrong and we rebuild everything in 6 months.

### Core Tables

```sql
-- Organizations (the brand owners — one person can own multiple brands)
organizations
  id: uuid PRIMARY KEY
  name: text
  owner_email: text
  owner_phone: text (Nigerian format: 080XXXXXXXX)
  created_at: timestamptz
  plan: text (free | growth | scale | enterprise)

-- Brands (each organization can have multiple brands)
brands
  id: uuid PRIMARY KEY
  organization_id: uuid REFERENCES organizations
  name: text
  category: text (fashion | food | beauty | electronics | etc)
  created_at: timestamptz
  currency: text DEFAULT 'NGN'
  timezone: text DEFAULT 'Africa/Lagos'
  is_active: boolean

-- Integrations (each brand's connected data sources)
integrations
  id: uuid PRIMARY KEY
  brand_id: uuid REFERENCES brands
  type: text (shopify | woocommerce | paystack | flutterwave | monnify | opay | mono | meta_ads | google_ads | tiktok_ads | instagram | facebook_page | bumpa_csv | manual)
  credentials: jsonb (encrypted — API keys, tokens, etc)
  status: text (connected | error | disconnected)
  last_sync_at: timestamptz
  metadata: jsonb (store URL, account ID, etc)
  created_at: timestamptz

-- Products / SKUs
products
  id: uuid PRIMARY KEY
  brand_id: uuid REFERENCES brands
  external_id: text (ID from Shopify/WooCommerce/etc)
  source: text (shopify | woocommerce | manual | csv)
  name: text
  sku_code: text
  category: text
  cost_price: numeric (in NGN)
  selling_price: numeric (in NGN)
  current_stock: integer
  is_active: boolean
  metadata: jsonb (images, variants, tags from source platform)
  created_at: timestamptz
  updated_at: timestamptz

-- Customers
customers
  id: uuid PRIMARY KEY
  brand_id: uuid REFERENCES brands
  external_id: text
  source: text
  name: text
  email: text
  phone: text (normalized Nigerian format)
  state: text (Lagos | Abuja | Rivers | etc)
  lga: text
  first_purchase_at: timestamptz
  last_purchase_at: timestamptz
  total_orders: integer DEFAULT 0
  total_spend: numeric DEFAULT 0
  metadata: jsonb
  created_at: timestamptz

-- Orders
orders
  id: uuid PRIMARY KEY
  brand_id: uuid REFERENCES brands
  customer_id: uuid REFERENCES customers
  external_id: text
  source: text (shopify | woocommerce | paystack | manual | whatsapp | instagram | etc)
  channel: text (website | whatsapp | instagram | facebook | physical | marketplace)
  status: text (pending | completed | refunded | cancelled)
  total_amount: numeric (in NGN)
  original_amount: numeric
  original_currency: text DEFAULT 'NGN'
  exchange_rate: numeric DEFAULT 1
  payment_method: text (card | bank_transfer | ussd | pos | cash | opay | palmpay | wallet)
  payment_gateway: text (paystack | flutterwave | monnify | opay | bank | cash | etc)
  delivery_state: text
  delivery_lga: text
  logistics_partner: text
  ordered_at: timestamptz
  completed_at: timestamptz
  metadata: jsonb
  created_at: timestamptz

-- Order Line Items
order_items
  id: uuid PRIMARY KEY
  order_id: uuid REFERENCES orders
  product_id: uuid REFERENCES products
  quantity: integer
  unit_price: numeric
  total_price: numeric
  cost_price: numeric (snapshot at time of sale)
  metadata: jsonb

-- SKU Scores (computed nightly)
sku_scores
  id: uuid PRIMARY KEY
  product_id: uuid REFERENCES products
  brand_id: uuid REFERENCES brands
  score: numeric (1.0 - 10.0)
  verdict: text (scale | monitor | fix | kill)
  trend: text (improving | stable | declining)
  reason: text (plain English explanation)
  velocity_7d: numeric
  velocity_30d: numeric
  velocity_90d: numeric
  return_rate: numeric
  repeat_purchase_rate: numeric
  days_of_inventory: integer
  margin_percent: numeric
  capital_locked: numeric (current_stock * cost_price)
  scored_at: timestamptz
  created_at: timestamptz

-- Customer Segments (computed nightly)
customer_segments
  id: uuid PRIMARY KEY
  customer_id: uuid REFERENCES customers
  brand_id: uuid REFERENCES brands
  segment: text (champion | loyal | promising | at_risk | lost | one_and_done)
  churn_probability_14d: numeric
  churn_probability_30d: numeric
  predicted_next_purchase_at: timestamptz
  ltv_90d: numeric
  ltv_365d: numeric
  segmented_at: timestamptz

-- Ad Performance (from Meta/Google/TikTok)
ad_campaigns
  id: uuid PRIMARY KEY
  brand_id: uuid REFERENCES brands
  platform: text (meta | google | tiktok | twitter)
  external_campaign_id: text
  name: text
  status: text
  spend: numeric
  impressions: integer
  clicks: integer
  cpm: numeric
  cpc: numeric
  date: date
  metadata: jsonb

-- CIP Score (computed after 6+ months of data)
cip_scores
  id: uuid PRIMARY KEY
  brand_id: uuid REFERENCES brands
  score: numeric (0 - 100)
  revenue_trend_score: numeric
  consistency_score: numeric
  inventory_health_score: numeric
  customer_retention_score: numeric
  payment_reliability_score: numeric
  channel_diversity_score: numeric
  trajectory_score: numeric
  computed_at: timestamptz
  data_months: integer (how many months of data the score is based on)

-- CIP Score Access Log (consent and institutional access tracking)
cip_score_access
  id: uuid PRIMARY KEY
  brand_id: uuid REFERENCES brands
  institution_id: uuid
  institution_name: text
  access_type: text (credit_check | supplier_prequalification | investor_report)
  consented_at: timestamptz
  accessed_at: timestamptz

-- Automation Rules
automation_rules
  id: uuid PRIMARY KEY
  brand_id: uuid REFERENCES brands
  name: text
  is_active: boolean
  trigger_type: text (sku_score_drop | low_inventory | customer_inactive | return_rate_spike | etc)
  trigger_conditions: jsonb
  action_type: text (whatsapp_alert | email_alert | pause_ads | generate_reorder | etc)
  action_config: jsonb
  last_triggered_at: timestamptz
  created_at: timestamptz

-- Weekly Digests (stored for history)
weekly_digests
  id: uuid PRIMARY KEY
  brand_id: uuid REFERENCES brands
  week_start: date
  revenue_this_week: numeric
  revenue_last_week: numeric
  top_sku_to_scale: uuid REFERENCES products
  top_sku_at_risk: uuid REFERENCES products
  churn_risk_count: integer
  champion_count: integer
  recommendations: jsonb
  delivered_whatsapp: boolean
  delivered_email: boolean
  created_at: timestamptz
```

### Critical Schema Rules
- Every brand's data is completely isolated. Every query must filter by `brand_id`.
- Supabase Row Level Security (RLS) enforces this at the database level — even if the API has a bug, a brand cannot see another brand's data.
- All monetary values stored in NGN. Original currency and exchange rate stored alongside.
- `external_id` + `source` combination must be unique per brand to prevent duplicate ingestion.
- `metadata: jsonb` columns store source-platform-specific data without schema changes.
- Nigerian phone numbers normalized to `+234XXXXXXXXXX` format on ingest.
- All timestamps in UTC. Display in WAT (Africa/Lagos, UTC+1) in the frontend.

---

## SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                    │
│  Dashboard | SKU View | Customer View | Automation | Settings│
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTPS REST API calls
┌─────────────────▼───────────────────────────────────────────┐
│                     BACKEND (FastAPI)                         │
│  /api/auth | /api/brands | /api/skus | /api/customers        │
│  /api/integrations | /api/automation | /api/cip-score        │
└──────┬────────────────────────┬────────────────────────────┬─┘
       │                        │                            │
┌──────▼──────┐    ┌────────────▼──────────┐    ┌──────────▼──┐
│  PostgreSQL  │    │   Celery Workers       │    │    Redis    │
│  (Supabase)  │    │   (Background Tasks)   │    │  (Upstash)  │
│              │    │                        │    │             │
│  All brand   │    │  Nightly: Pull data    │    │  Cache SKU  │
│  data lives  │    │  from all integrations │    │  scores,    │
│  here        │    │  Run SKU scoring       │    │  segments,  │
│              │    │  Update segments       │    │  digests    │
│              │    │  Generate digests      │    │             │
└──────────────┘    │  Fire automations      │    └─────────────┘
                    └────────────┬───────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                       │
   ┌──────▼───────┐   ┌─────────▼──────┐   ┌──────────▼──────┐
   │  Payment APIs │   │  Social/Ad APIs │   │  WhatsApp/Email │
   │  Paystack     │   │  Meta Ads       │   │  AfricasTalking │
   │  Flutterwave  │   │  Google Ads     │   │  Resend         │
   │  Monnify      │   │  TikTok Ads     │   │                 │
   │  Mono         │   │  Instagram      │   │                 │
   │  OPay         │   │  Facebook Page  │   │                 │
   └───────────────┘   └────────────────┘   └─────────────────┘
```

---

## HOW TO WORK WITH CLAUDE CODE (MANDATORY READING)

**Rule 1: One task per session.** Never ask Claude Code to build two features at once. One endpoint, one component, one migration at a time. Test it. Then ask for the next thing.

**Rule 2: Always provide context.** Every session starts with: here is what already exists (paste relevant files or describe current state), here is what I need you to build now, here is what it must connect to, here is what I do NOT want you to build.

**Rule 3: Schema first, always.** Before building any feature, the database migration must exist and be tested. Never build an API endpoint for data that doesn't have a confirmed table.

**Rule 4: Test before committing.** Run the endpoint with Postman or curl. Load the frontend page. Confirm it works with real data before ending the session.

**Rule 5: Git commit after every working feature.** Never accumulate more than one feature worth of uncommitted code. If something breaks, you need to be able to revert cleanly.

**Rule 6: Never build the next sprint during the current sprint.** The discipline of this rule is what makes the project finish.

---

# THE SPRINTS

---

## SPRINT 0 — FOUNDATION
**Goal:** Everything needed to write code exists and works. No product features. Pure infrastructure.

### 0.1 Repository Setup
- Create GitHub repository: `cip-platform`
- Create two folders: `/frontend` (Next.js) and `/backend` (FastAPI)
- Create `.env.example` files documenting every required environment variable
- Create `README.md` with setup instructions
- Set up `.gitignore` for both Python and Node projects
- Never commit `.env` files. Never commit API keys. Ever.

### 0.2 Supabase Setup
- Create Supabase project
- Enable Row Level Security globally
- Run the complete schema migration (all tables from the schema section above)
- Write RLS policies: users can only read/write data for brands their organization owns
- Test: confirm two different organization accounts cannot access each other's data
- Set up Supabase Auth with email/password and magic link

### 0.3 Backend Setup
- Initialize FastAPI project in `/backend`
- Install dependencies: fastapi, uvicorn, sqlalchemy, alembic, psycopg2, python-jose, passlib, httpx, celery, redis, python-dotenv
- Connect to Supabase PostgreSQL via SQLAlchemy
- Create health check endpoint: `GET /health` returns `{"status": "ok", "database": "connected"}`
- Set up Alembic for database migrations
- Deploy to Railway. Confirm health check returns 200 from Railway URL.

### 0.4 Frontend Setup
- Initialize Next.js 14 project in `/frontend` with App Router
- Install dependencies: tailwindcss, shadcn/ui, recharts, zustand, @tanstack/react-query, axios
- Initialize shadcn/ui component library
- Create environment variable for backend API URL
- Create a single test page that calls the backend health check and displays "Connected"
- Deploy to Railway. Confirm it loads and shows "Connected".

### 0.5 Redis Setup
- Create Upstash Redis instance
- Connect FastAPI backend to Redis
- Test: write a key, read it back, confirm it works

### 0.6 Authentication Flow (End to End)
- Supabase Auth handles the auth itself
- Backend: create middleware that validates Supabase JWT tokens on every protected endpoint
- Frontend: create login page, signup page, and auth state management
- Test: create an account, log in, make an authenticated API call, log out
- This must work completely before Sprint 1 starts

### 0.7 Basic Organization + Brand Setup
- API endpoints: `POST /organizations`, `GET /organizations/me`, `POST /brands`, `GET /brands`
- Frontend: after login, if no organization exists, show setup flow (organization name → first brand name → category)
- Test: create an org, create a brand, confirm it's stored and returned correctly

**Sprint 0 is complete when:** A real user can sign up, create their organization and first brand, and the infrastructure is deployed and stable on Railway.

---

## SPRINT 1 — DATA INGESTION
**Goal:** Brands can connect their data sources and we have their data in the database. No intelligence features yet. Just data flowing in.

### 1.1 Onboarding Flow (Seller Type Branching)
The onboarding branches based on how the seller sells. This determines which integrations to show first.

**Step 1:** How do you sell?
- Option A: I have a website (Shopify / WooCommerce / Bumpa)
- Option B: I sell on social media and WhatsApp
- Option C: I have a physical shop or kiosk

**Step 2:** How do you collect payment? (shown for all seller types)
- Paystack
- Flutterwave
- Monnify (Moniepoint)
- OPay
- Bank transfer
- Cash

**Step 3:** Connect your product catalog (for Option B and C sellers who have no website)
- Manual product entry form: name, selling price, cost price, current stock
- Bulk CSV upload template

**Step 4:** Optional — connect social/ads accounts
- Instagram Business
- Facebook Page
- Meta Ads Account

### 1.2 Paystack Integration
- UI: settings page with "Connect Paystack" button → API key entry form
- Backend: store encrypted API key in integrations table
- Background job: on connection, pull last 12 months of transactions from Paystack API
- Map Paystack transaction to our `orders` table:
  - `source = 'paystack'`
  - `channel` = infer from metadata (if payment link → likely social commerce)
  - customer identified by email from Paystack transaction
  - `status` maps from Paystack status codes
- Set up Paystack webhook: register our webhook URL in Paystack dashboard, receive new transactions in real time
- Webhook endpoint: `POST /webhooks/paystack` — validate signature, process event, store order
- Test: connect a real Paystack account, confirm transactions appear in orders table

### 1.3 Flutterwave Integration
- Same pattern as Paystack
- Flutterwave REST API: pull transaction history
- Flutterwave webhook for real-time new transactions
- Map to orders table with `source = 'flutterwave'`
- Test with real Flutterwave account

### 1.4 Monnify Integration
- Monnify REST API (Moniepoint's payment gateway)
- API key authentication
- Pull transaction history from Monnify collections API
- Webhook for real-time events
- Map to orders table with `source = 'monnify'`

### 1.5 OPay Merchant Integration
- OPay Checkout merchant API
- API key authentication
- Pull merchant transaction history
- Map to orders table with `source = 'opay'`

### 1.6 Mono Open Banking Integration (Bank Transfer Solution)
- Mono Connect widget embedded in frontend (their prebuilt bank connection UI)
- User clicks "Connect Bank Account", Mono widget opens, user selects their bank and authenticates
- Mono returns an account code → exchange for access token via Mono API
- Pull 12 months of bank statement via Mono Statements API
- Filter for credits (incoming transfers) — these are potential sales
- Store as orders with `source = 'bank_transfer'`, `payment_gateway = 'bank'`, `status = 'pending_match'`
- Seller sees unmatched bank credits in their CIP Order Inbox and confirms which ones are sales
- Webhook: Mono sends new transactions in real time after initial sync

### 1.7 Shopify Integration
- OAuth flow: seller enters their store URL → redirect to Shopify OAuth → Shopify redirects back with access token
- Store access token in integrations table
- GraphQL Admin API: pull last 12 months of orders, products, customers
- Map to our normalized schema:
  - orders → orders table
  - line items → order_items table
  - products → products table
  - customers → customers table
- Register Shopify webhooks: `orders/create`, `orders/updated`, `products/update`, `inventory_levels/update`
- Real-time sync via webhooks from that point forward

### 1.8 WooCommerce Integration
- Consumer Key / Consumer Secret entry form
- WooCommerce REST API v3: pull orders, products, customers
- Same mapping pattern as Shopify
- Set up WooCommerce webhooks for real-time sync

#### 1.8a WooCommerce Reseller Platform — Custom Ingestion Layer (CORRECTED)
**Context:** The founder operates a custom-built WooCommerce reseller platform — a single WordPress installation hosting approximately 500 independent vendor storefronts (resellers, creators, wholesalers, SME brands), each with their own subdomain or custom domain. This platform is NOT built on Dokan, WCFM, or WC Vendors. It uses a fully custom database architecture. The standard WooCommerce REST API sees all data as one store. ORYNT must split it by storefront using the exact custom table structure documented below.

**IMPORTANT FOR CLAUDE CODE: Do NOT query wp_options for multivendor plugins. Do NOT reference Dokan, WCFM, or WC Vendors tables. This platform has its own custom tables. Use only the table names and fields specified here.**

**This is a custom integration, not a standard WooCommerce connection. It has its own integration type in the UI: `reseller_platform`.**

---

**Exact database tables and fields (confirmed from platform source code):**

**Storefront registry — `wp_storefronts`**
```
id              — storefront's unique ID (this is the brand identifier in ORYNT)
reseller_id     — WordPress user ID of the storefront owner
subdomain       — e.g. "fashionbrand" (maps to fashionbrand.platform.com)
domain          — custom domain if set (e.g. "www.fashionbrand.com"), NULL if not set
store_name      — the brand's display name
template_id     — which theme template the store uses
active          — 1 = active, 0 = inactive
created_at      — storefront creation date
```

**Product-to-storefront mapping — `wp_reseller_products`**
```
id                    — record ID
reseller_id           — WordPress user ID of storefront owner
wholesale_product_id  — ID of the base product (wp_posts.ID where post_type = 'wholesale_product')
storefront_id         — foreign key to wp_storefronts.id
reseller_price        — the selling price set by this storefront (this is the revenue figure)
reseller_title        — custom product title (NULL means use wholesale title)
reseller_description  — custom description (NULL means use wholesale description)
active                — 1 = listed, 0 = removed from storefront
created_at / updated_at
```

**Cost price — `wp_postmeta` on the wholesale product**
```
meta_key = 'base_price'         — cost price (what the wholesale product costs)
meta_key = 'stock_quantity'     — current stock level
meta_key = 'sku'                — product SKU code
```
Query: `SELECT meta_value FROM wp_postmeta WHERE post_id = [wholesale_product_id] AND meta_key = 'base_price'`

**Order financial splits — `wp_woocommerce_order_itemmeta`**
Each WooCommerce order item carries these meta fields written at checkout:
```
_reseller_id        — which reseller/storefront this item belongs to
_wholesaler_id      — which wholesaler supplied this item
_base_price         — cost price snapshot at time of sale
_reseller_markup    — reseller's net profit on this item (after platform fee)
_platform_fee       — platform's commission on this item
```
These are set via `wc_update_order_item_meta()` during `woocommerce_checkout_order_processed` hook.

**Financial ledger — `wp_platform_ledger`**
```
id                — record ID
order_id          — WooCommerce order ID
actor_id          — WordPress user ID (wholesaler, reseller, or platform admin)
actor_type        — 'wholesaler' | 'reseller' | 'platform'
amount            — amount in NGN
transaction_type  — 'charge' | 'hold' | 'release' | 'refund' | 'payout' | 'fee'
status            — 'pending' | 'completed' | 'failed' | 'reversed'
reference         — payment reference string
created_at
```

**Fulfillment tracking — `wp_fulfillment_events`**
```
id               — record ID
order_id         — WooCommerce order ID
order_item_id    — specific item ID
wholesaler_id    — who is fulfilling
status           — 'pending' | 'accepted' | 'processing' | 'shipped' | 'delivered' | 'failed' | 'cancelled'
tracking_number  — courier tracking number
carrier          — logistics company name
created_at
```

**Payout requests — `wp_payout_requests`**
```
id              — record ID
user_id         — WordPress user ID (reseller or wholesaler)
user_type       — 'wholesaler' | 'reseller'
amount          — requested payout amount
status          — 'pending' | 'approved' | 'processing' | 'paid' | 'rejected'
bank_name       — seller's bank
account_number  — seller's account number
account_name    — seller's account name
requested_at / processed_at
```

---

**What Claude Code must build for this integration:**

Step 1 — Storefront enumeration:
```sql
SELECT id, reseller_id, store_name, subdomain, domain, active
FROM wp_storefronts
WHERE active = 1
ORDER BY created_at ASC
```
Present list to founder: "We found 500 active storefronts. Each will be created as a separate brand in ORYNT. Confirm to proceed."

Step 2 — Bulk brand creation:
Create one ORYNT `brands` record per storefront row. Store `wp_storefronts.id` as `vendor_id` and `reseller_platform` as the `source` in the integrations metadata. Store `reseller_id` as the brand owner's external user reference.

Step 3 — Product ingestion per storefront:
```sql
SELECT rp.id, rp.wholesale_product_id, rp.storefront_id, rp.reseller_price,
       rp.reseller_title, p.post_title as wholesale_title,
       pm_cost.meta_value as cost_price,
       pm_stock.meta_value as stock_quantity,
       pm_sku.meta_value as sku
FROM wp_reseller_products rp
JOIN wp_posts p ON p.ID = rp.wholesale_product_id
LEFT JOIN wp_postmeta pm_cost ON pm_cost.post_id = rp.wholesale_product_id AND pm_cost.meta_key = 'base_price'
LEFT JOIN wp_postmeta pm_stock ON pm_stock.post_id = rp.wholesale_product_id AND pm_stock.meta_key = 'stock_quantity'
LEFT JOIN wp_postmeta pm_sku ON pm_sku.post_id = rp.wholesale_product_id AND pm_sku.meta_key = 'sku'
WHERE rp.storefront_id = [storefront_id] AND rp.active = 1
```
Map to ORYNT `products` table: `cost_price = base_price`, `selling_price = reseller_price`, `is_digital = false`, `source = 'reseller_platform'`

Step 4 — Order ingestion per storefront:
```sql
SELECT o.ID as order_id, o.post_date as ordered_at, o.post_status as order_status,
       oi.order_item_id, oi.order_item_name,
       oim_reseller.meta_value as reseller_id,
       oim_cost.meta_value as base_price,
       oim_markup.meta_value as reseller_markup,
       oim_fee.meta_value as platform_fee,
       oim_qty.meta_value as quantity
FROM wp_posts o
JOIN wp_woocommerce_order_items oi ON oi.order_id = o.ID
LEFT JOIN wp_woocommerce_order_itemmeta oim_reseller ON oim_reseller.order_item_id = oi.order_item_id AND oim_reseller.meta_key = '_reseller_id'
LEFT JOIN wp_woocommerce_order_itemmeta oim_cost ON oim_cost.order_item_id = oi.order_item_id AND oim_cost.meta_key = '_base_price'
LEFT JOIN wp_woocommerce_order_itemmeta oim_markup ON oim_markup.order_item_id = oi.order_item_id AND oim_markup.meta_key = '_reseller_markup'
LEFT JOIN wp_woocommerce_order_itemmeta oim_fee ON oim_fee.order_item_id = oi.order_item_id AND oim_fee.meta_key = '_platform_fee'
LEFT JOIN wp_woocommerce_order_itemmeta oim_qty ON oim_qty.order_item_id = oi.order_item_id AND oim_qty.meta_key = '_qty'
WHERE o.post_type = 'shop_order'
AND oim_reseller.meta_value = [reseller_id_for_this_storefront]
ORDER BY o.post_date DESC
```

Step 5 — Customer ingestion per storefront:
Pull billing details from `wp_postmeta` on shop_order posts where `_reseller_id` matches. Normalize phone numbers to `+234XXXXXXXXXX` format.

Step 6 — Ongoing sync:
No webhook is available from this platform to ORYNT directly. Schedule a nightly Celery job to pull new orders placed since `last_sync_at` for each reseller_platform brand. Poll interval: nightly at 2:00 AM WAT.

Step 7 — Multi-brand overview:
The founder (platform owner) gets an "Installation Owner" role in ORYNT. They see all 500 storefront brands in their multi-brand overview. Each storefront reseller can optionally receive their own ORYNT login to see only their brand's intelligence.

**Database fields to add to ORYNT `integrations` table for this integration type:**
- `vendor_id` — stores `wp_storefronts.id`
- `reseller_id` — stores `wp_users.ID` of the storefront owner
- `platform_installation` — identifier for which WordPress installation this came from

**Note on the 200 separate WooCommerce sites:** Each of the founder's 200 individually hosted WooCommerce websites connects to ORYNT as a standard single-brand WooCommerce integration (section 1.8 above). They each have their own Consumer Key and Consumer Secret. The reseller platform uses this custom `reseller_platform` integration path. These are two completely separate integration types.

---

#### 1.8b Preorder Platform — Custom Ingestion Layer (NEW)
**Context:** The founder operates a second custom platform — a pre-order commerce system where sellers/influencers/brands run pre-order campaigns. Customers pay upfront, the campaign runs until a minimum quantity is reached, then the product is manufactured and delivered. This platform has its own entirely separate custom database using the `pop_` table prefix. It is NOT a standard WooCommerce store. It has its own order system (`pop_campaign_orders`), its own seller system (`pop_sellers`), and its own campaign lifecycle with milestone tracking.

**This is a completely separate integration type from WooCommerce. Integration type in ORYNT UI: `preorder_platform`.**

**IMPORTANT FOR CLAUDE CODE: The preorder platform does NOT use `wp_posts` for orders, does NOT use `wp_woocommerce_order_items`, and does NOT use standard WooCommerce product tables. Every order lives in `pop_campaign_orders`. Every product is a `pop_campaigns` record. Read only from `pop_` prefixed tables for this integration.**

---

**Exact database tables and fields (confirmed from platform source code):**

**Campaigns (these are the products/SKUs in ORYNT) — `pop_campaigns`**
```
id                — campaign ID (maps to ORYNT product ID)
post_id           — linked WordPress post (for media and description)
seller_id         — wp_users ID of the seller running this campaign
product_name      — campaign/product name
sku               — product SKU
target_quantity   — how many units the seller hopes to sell
minimum_quantity  — below this = auto-cancel and refund
units_ordered     — total orders placed so far
units_produced    — confirmed manufactured
units_shipped     — confirmed shipped from origin
units_delivered   — confirmed delivered to customers
price_early       — early bird price (NGN)
price_standard    — standard price (NGN)
price_final       — final price, highest (reverse countdown pricing)
early_bird_limit  — how many orders get the early price
deadline          — campaign close datetime
status            — 'draft'|'active'|'funded'|'in_production'|'shipped'|'customs'|'warehouse'|'delivering'|'completed'|'cancelled'|'refunding'|'refunded'
commission_rate   — platform's cut as percentage
created_at / updated_at
```

**Orders — `pop_campaign_orders`**
```
id              — order ID
campaign_id     — links to pop_campaigns.id
woo_order_id    — linked WooCommerce order (for payment processing)
customer_id     — wp_users ID of buyer
quantity        — units ordered
unit_price      — price paid per unit (NGN)
total_paid      — total amount paid (NGN)
price_tier      — 'early' | 'standard' | 'final' (which pricing tier was active)
payment_ref     — Paystack payment reference
payment_status  — 'pending' | 'paid' | 'refund_pending' | 'refunded'
referral_code   — referral code used (if any)
referred_by     — customer_id of referrer
created_at
```

**Sellers — `pop_sellers`**
```
id                    — seller record ID
user_id               — wp_users ID (maps to ORYNT brand owner)
business_name         — brand/business name (this is the ORYNT brand name)
phone / whatsapp_number / instagram_handle
bank_name / bank_account_number / bank_account_name
verified              — 1 = verified seller, 0 = pending
commission_rate       — this seller's platform commission rate
total_campaigns       — lifetime campaigns run
successful_campaigns  — campaigns that reached funded status and delivered
total_revenue         — lifetime GMV
reliability_score     — platform-calculated reliability score
status                — 'pending' | 'active' | 'suspended'
created_at
```

**Campaign milestones (delivery proof) — `pop_campaign_milestones`**
```
id              — record ID
campaign_id     — links to pop_campaigns.id
milestone_key   — 'funded'|'production_start'|'quality_check'|'shipped'|'customs'|'warehouse'|'delivering'|'completed'
milestone_label — human-readable label
completed       — 1 = done, 0 = pending
completed_at    — when it was marked complete
proof_media_url — Cloudinary URL of photo/video proof (critical for trust)
notes           — admin notes
```

**Customer loyalty tiers — `pop_customer_tiers`**
```
user_id                 — wp_users ID
campaigns_participated  — total campaigns joined
tier                    — 'new' | 'verified' | 'priority'
referral_code           — this customer's unique referral code
total_referrals         — how many people they referred
total_spent             — lifetime spend in NGN
```

**Payouts — `pop_payouts`**
```
id                — record ID
seller_id         — pop_sellers.id
campaign_id       — pop_campaigns.id
gross_amount      — total revenue from campaign
commission_amount — platform fee deducted
net_amount        — what seller receives
status            — 'pending' | 'processing' | 'paid' | 'failed'
payout_ref        — Paystack transfer reference
paid_at / created_at
```

**Reliability tracking — `pop_reliability_log`**
```
campaign_id               — pop_campaigns.id
seller_id                 — pop_sellers.id (= pop_sellers.user_id)
delivered_on_time         — 1 = yes, 0 = no
refund_issued_on_time     — 1 = yes (within 72hrs), 0 = no
customer_satisfaction_avg — average rating
recorded_at
```

---

**How preorder platform data maps to ORYNT concepts:**

| Preorder Platform | ORYNT Equivalent | Notes |
|---|---|---|
| `pop_sellers` record | One ORYNT `brand` | Each seller = one brand |
| `pop_campaigns` record | One ORYNT `product` | Each campaign = one SKU event |
| `pop_campaign_orders` record | One ORYNT `order` | Direct mapping |
| `price_early / standard / final` | `selling_price` | Use actual price paid (`unit_price`) |
| `commission_rate` | Platform fee | Cost = `unit_price × (1 - commission_rate/100)` |
| `campaign.status` | Order fulfillment status | Map to ORYNT order status |
| `units_delivered / units_ordered` | Fulfillment rate | Feeds CIP Score delivery reliability dimension |
| `reliability_score` on pop_sellers | CIP Score input | Direct feed into CIP Score calculation |
| `pop_customer_tiers.total_spent` | Customer LTV | Enriches customer intelligence |

**Campaign status → ORYNT order status mapping:**
```
active       → pending
funded       → confirmed
in_production → processing
shipped      → shipped
customs      → in_transit
warehouse    → in_transit
delivering   → out_for_delivery
completed    → completed
cancelled    → cancelled
refunded     → refunded
```

**SKU scoring for preorder campaigns:**
Preorder campaigns are a unique product type — they have no physical stock to track until delivery. The SKU scoring algorithm must be adjusted for `source = 'preorder_platform'`:
- Remove: `days_of_inventory`, `current_stock` dimensions
- Add: `funded_rate` (units_ordered / target_quantity), `delivery_completion_rate` (units_delivered / units_ordered)
- Reweight: velocity (30%), margin (25%), repeat participation rate (20%), funded rate (15%), delivery completion rate (10%)
- A campaign that cancelled (minimum not met) scores 1 — Kill verdict — automatically
- A campaign that completed with 100% delivery scores 8–10 depending on margin and repeat buyer rate

**CIP Score enrichment from preorder platform:**
The preorder platform provides the strongest reliability signal of any integration:
- `pop_sellers.successful_campaigns / pop_sellers.total_campaigns` = fulfilment reliability ratio
- `pop_reliability_log.delivered_on_time` = verified on-time delivery history with proof media
- `pop_reliability_log.refund_issued_on_time` = refund reliability
- These three signals feed directly into the CIP Score's `payment_reliability` and `trajectory` dimensions
- A preorder seller with 10 completed campaigns, all delivered on time, with proof photos, has the most credible CIP Score of any seller type on the platform

**What Claude Code must build for this integration:**

Step 1 — Seller enumeration:
```sql
SELECT ps.id, ps.user_id, ps.business_name, ps.phone, ps.whatsapp_number,
       ps.verified, ps.total_campaigns, ps.successful_campaigns,
       ps.total_revenue, ps.reliability_score, ps.status
FROM pop_sellers ps
WHERE ps.status = 'active'
ORDER BY ps.created_at ASC
```
Create one ORYNT `brand` per active seller. Store `pop_sellers.id` as `vendor_id` in integration metadata.

Step 2 — Campaign/product ingestion per seller:
```sql
SELECT id, seller_id, product_name, sku, target_quantity, minimum_quantity,
       units_ordered, units_delivered, price_early, price_standard, price_final,
       early_bird_limit, deadline, status, commission_rate, created_at
FROM pop_campaigns
WHERE seller_id = [pop_sellers.user_id]
ORDER BY created_at DESC
```
Map each campaign to ORYNT `products` table. Set `is_digital = false`. Set `is_preorder = true` (add this flag to products table). `cost_price` = `unit_price × (1 - commission_rate/100)` — derived at ingestion time.

Step 3 — Order ingestion per seller:
```sql
SELECT pco.id, pco.campaign_id, pco.customer_id, pco.quantity,
       pco.unit_price, pco.total_paid, pco.price_tier,
       pco.payment_ref, pco.payment_status, pco.created_at,
       pc.seller_id, pc.status as campaign_status
FROM pop_campaign_orders pco
JOIN pop_campaigns pc ON pc.id = pco.campaign_id
WHERE pc.seller_id = [pop_sellers.user_id]
AND pco.payment_status = 'paid'
ORDER BY pco.created_at DESC
```
Map to ORYNT `orders` table: `source = 'preorder_platform'`, `channel = 'preorder'`, `status` = mapped from campaign_status above.

Step 4 — Customer ingestion:
Pull customer records from `wp_users` + `wp_usermeta` (billing_phone, billing_email) for each `customer_id` found in orders. Also pull `pop_customer_tiers` for loyalty tier and total_spent enrichment.

Step 5 — Milestone and reliability data:
```sql
SELECT pcm.campaign_id, pcm.milestone_key, pcm.completed, pcm.completed_at
FROM pop_campaign_milestones pcm
JOIN pop_campaigns pc ON pc.id = pcm.campaign_id
WHERE pc.seller_id = [seller_id] AND pcm.completed = 1
```
Store milestone completion data as order fulfillment events in ORYNT. Use `completed_at` timestamps to calculate actual vs promised delivery timelines for CIP Score.

Step 6 — Reliability score sync:
```sql
SELECT delivered_on_time, refund_issued_on_time, customer_satisfaction_avg
FROM pop_reliability_log
WHERE seller_id = [seller_id]
```
Store as a dedicated reliability dimension on the ORYNT brand record. Feed directly into CIP Score calculation — do not recalculate what the preorder platform has already calculated.

Step 7 — Ongoing sync:
Nightly Celery job pulls new `pop_campaign_orders` where `created_at > last_sync_at` for each preorder_platform brand. Also pulls campaign status changes (a campaign moving from `shipped` to `completed` must update all associated orders in ORYNT).

**Database additions required for preorder platform support:**
- Add `is_preorder = boolean` flag to ORYNT `products` table
- Add `funded_rate` and `delivery_completion_rate` fields to `sku_scores` table for preorder-specific scoring
- Add `preorder_reliability_score` field to `brands` table — sourced directly from `pop_sellers.reliability_score`

**Note on pricing for preorder campaigns in ORYNT:**
Preorder campaigns use reverse countdown pricing — early buyers pay less, late buyers pay more. In ORYNT, each order stores the actual `unit_price` paid. The SKU score uses the weighted average price across all orders as the effective selling price. Revenue reporting uses actual amounts paid, not campaign list prices.

### 1.9 Bumpa Integration (CSV Import)
- Download template: Bumpa-formatted CSV structure
- Upload CSV endpoint: `POST /integrations/bumpa/upload`
- Parse CSV, map to normalized schema, ingest into orders/products/customers tables
- Show upload status: "1,247 orders imported, 89 products imported, 3,421 customers imported"
- Note: pursuing Bumpa API partnership in parallel. When API access is granted, replace CSV with real-time sync.

### 1.9a Selar and Digital Product Platform Integration
**Context:** A significant segment of Nigerian SME sellers are digital product creators — they sell ebooks, online courses, templates, software licenses, Lightroom presets, Notion dashboards, audio files, and similar non-physical products. These sellers are valid CIP users. Their SKU scoring, customer intelligence, and CIP Score are equally meaningful. The only structural difference is that digital products have no physical inventory — stock is always unlimited and days-of-inventory is irrelevant.

**Platforms to integrate:**
- **Selar** — Nigeria's dominant digital product marketplace. Selar provides a REST API for sellers to pull their product sales, customer data, and transaction records. This is Priority 1 for digital product sellers because Selar is the most common platform for Nigerian digital creators.
- **Gumroad** — Used by Nigerian creators targeting international buyers. Gumroad has a REST API (v2) for pulling sales, products, and subscriber data.
- **Paystack Commerce / Paystack Storefront** — Many Nigerian digital sellers use Paystack's native storefront feature to sell digital downloads. Their data flows through the Paystack integration already in Sprint 1.1, but product metadata (digital product details) needs to be pulled separately via Paystack Commerce API.
- **Flutterwave Storefront** — Same as above. Flutterwave's storefront product is used by digital sellers. Captured via the Flutterwave integration in Sprint 1.2 with product metadata enrichment.

**What Claude Code must build:**

Selar Integration:
1. API key entry form (Selar uses API key authentication)
2. Pull all products from Selar API: `GET /api/v3/products` — store in CIP `products` table with `source = 'selar'`
3. Pull all orders: `GET /api/v3/orders` — map to CIP `orders` table with `source = 'selar'`, `channel = 'selar'`
4. Pull customer data from orders (Selar includes buyer email and name in order records)
5. Set `is_digital = true` flag on all products ingested from Selar
6. Webhook registration: Selar sends `order.completed` events — register CIP webhook endpoint for real-time order capture
7. Daily sync job for new orders

Gumroad Integration:
1. OAuth flow: seller authorizes CIP via Gumroad OAuth
2. Pull products: `GET /v2/products` — store with `source = 'gumroad'`, `is_digital = true`
3. Pull sales: `GET /v2/sales` — map to orders table
4. Real-time: Gumroad sends sale ping webhooks — register and handle

**SKU Scoring adjustment for digital products:**
When `is_digital = true` on a product, the SKU scoring algorithm drops the inventory dimension entirely and redistributes its weight:
- Remove: days_of_inventory, stock level, capital_locked calculations
- Reweight: velocity (40%), margin (30%), repeat purchase rate (20%), return/refund rate (10%)
- The Dead Inventory Dashboard excludes all digital products (they cannot go dead)
- The Reorder Assistant excludes all digital products
- Everything else — customer segmentation, cohort analysis, churn prediction, channel intelligence, CIP Score — works identically for digital product sellers

**Onboarding branch addition:** The Sprint 1.1 onboarding flow "How do you sell?" must add a fourth option:
- Option D: I sell digital products (ebooks, courses, templates, software)

Selecting Option D routes to Selar and Gumroad connection first, then Paystack/Flutterwave as the payment layer, then product catalog setup if selling on their own site.

**Sprint 1 completion note update:** The three test brands for Sprint 1 completion should now include one digital product seller (Selar-connected) in addition to the Shopify seller and WhatsApp/manual seller originally specified.

### 1.10 CIP Order Inbox (Social Sellers + WhatsApp Sellers)
This is the manual order logging feature for sellers who receive orders via WhatsApp, Instagram DM, or in person.

- Mobile-first interface (most users will be on phone)
- New Order form:
  - Customer name (autocomplete from existing customers)
  - Customer phone number
  - Products (multi-select from their product catalog)
  - Quantity per product
  - Total amount (auto-calculated but editable)
  - Payment method (WhatsApp transfer / Paystack / Bank transfer / Cash / OPay / PalmPay)
  - Delivery address (optional)
  - Note (optional)
- Submit in under 60 seconds
- Order saved to orders table with `source = 'manual'`, `channel = 'whatsapp'` or `channel = 'instagram'` based on seller's selection
- Quick-add customer: if customer phone is new, auto-create customer record
- WhatsApp forward parsing: seller forwards a customer's WhatsApp order message to our CIP WhatsApp number → our system parses the message using LLM (Claude API call) → creates draft order in their inbox → seller confirms with one tap

### 1.11 Meta Ads Integration
- Meta Business Login OAuth flow
- Access Meta Marketing API
- Pull ad account performance: campaigns, ad sets, ads, spend, impressions, clicks, CPM, CPC, ROAS per day
- Store in `ad_campaigns` table
- Daily sync job (ads data doesn't need real-time, daily is sufficient)

### 1.12 Instagram Business + Facebook Page Integration
- Via Meta Graph API
- Pull post/story performance, follower demographics, page insights
- Store as separate metrics (not orders — this is marketing performance, not transaction data)
- Daily sync

### 1.13 Data Sync Jobs (Background Processing)
- Celery worker running nightly at 2:00 AM WAT
- For each active integration: pull any new data since last sync
- Deduplication: check `external_id + source` before inserting to prevent duplicates
- Log sync results: records pulled, records inserted, errors
- Alert: if any integration fails to sync for 48 hours, send WhatsApp alert to brand owner

### 1.14 Data Ingestion Dashboard
- Settings → Integrations page shows:
  - All connected integrations with status (green = syncing, red = error)
  - Last sync timestamp
  - Records count (orders, products, customers pulled)
  - "Reconnect" button if integration is in error state
- Data summary per brand: total orders ingested, date range covered, total customers, total products

**Sprint 1 is complete when:** A real brand (Shopify seller, Paystack-only seller, and a WhatsApp/manual seller) can all connect their data sources and we can confirm their historical data is in the database. Test with three different real brands.

---

## SPRINT 2 — SKU INTELLIGENCE (THE WEDGE)
**Goal:** Every product gets a score. Brand owners see their first insight that makes them say "I need this."

### 2.1 SKU Scoring Algorithm
Python function: `calculate_sku_score(product_id, brand_id, as_of_date)`

**Inputs pulled from database:**
- Sales in last 7, 30, 90 days (from order_items)
- Current stock level (from products table)
- Cost price (from products table)
- Selling price (from products table)
- Return/refund rate (from orders where status = refunded)
- Number of distinct customers who bought this product more than once (repeat purchase rate)
- Revenue contribution: this product's revenue / brand's total revenue

**Score calculation:**
```
velocity_score = weighted_avg(7d_velocity * 0.5 + 30d_velocity * 0.3 + 90d_velocity * 0.2)
margin_score = gross_margin_percent / 10  (normalized 0-10)
return_penalty = return_rate * -2  (high returns hurt the score)
repeat_score = repeat_purchase_rate * 2
inventory_score = (1 / max(days_of_inventory, 1)) * 10  (lower days = healthier)

raw_score = (velocity_score * 0.35) + (margin_score * 0.25) + (repeat_score * 0.20) + (inventory_score * 0.10) + return_penalty
final_score = clamp(raw_score, 1.0, 10.0)
```

**Verdict mapping:**
- 8.0–10.0 → "Scale"
- 6.0–7.9 → "Monitor"
- 4.0–5.9 → "Fix"
- 1.0–3.9 → "Kill"

**Trend:** compare today's score to score from 14 days ago → improving / stable / declining

**Plain-English reason generation:** Construct reason from the dominant factors:
- If score is high: "Strong sales velocity and healthy margin. Repeat purchase rate of X% shows customer loyalty."
- If score is low: "Sales velocity has dropped 60% in 30 days and return rate is 18%. Stock is aging — X days since last sale."
- Always specific numbers. Never vague.

### 2.2 Nightly SKU Scoring Job
- Celery scheduled task: runs at 3:00 AM WAT every night
- For every active brand: loop through all products, run `calculate_sku_score`, upsert result into `sku_scores` table
- Log: brands processed, products scored, errors

### 2.3 SKU Dashboard Page
Frontend page: `/dashboard/skus`

**Layout:**
- Summary row at top: total products, count by verdict (Scale: X | Monitor: X | Fix: X | Kill: X)
- Sortable table columns: Product Name | Score | Verdict | Trend | Velocity (30d) | Margin % | Days of Stock | Return Rate
- Color coding: Scale = green, Monitor = yellow, Fix = orange, Kill = red
- Click a row → expand to show full reason + recommended action
- Filter by verdict (show only "Kill" products, etc)
- Search by product name
- "Last scored: X hours ago" timestamp

### 2.4 Dead Inventory Dashboard
Section on the SKU page (or separate tab):

- Total capital locked in dead inventory: sum of (stock × cost_price) for all SKUs with score < 4 and days_since_last_sale > 30
- Show in naira: "₦847,000 locked in 12 products that haven't sold in 30+ days"
- Table: Product | Days Sitting | Stock Units | Capital Locked | Suggested Clearance Price (cost price + 10% margin minimum)
- Sort by capital locked (largest first)

### 2.5 SKU Opportunity Flag
- Products where velocity is accelerating but stock is running low (days_of_inventory < 14 and velocity trending up)
- Banner on SKU page: "3 products are selling fast but running low on stock. Reorder now to avoid stockout."
- Click → shows the specific products

### 2.6 SKU Death Alert Logic
Triggers when any of these conditions are met:
- A product that scored 7+ last week now scores below 5
- Return rate spikes above 15% in 7 days for any product
- Days_of_inventory exceeds 90 with declining velocity (compare 7d vs 30d velocity)
- Zero sales for 21 days on a product with active stock

Alert delivery: WhatsApp message to brand owner + in-app notification

**Sprint 2 is complete when:** A brand with connected data can see every product scored, sorted, and color-coded. A brand with dead inventory can see exactly how much capital is locked and in which products. SKU death alerts fire correctly. Test with a real brand's actual product catalog.

---

## SPRINT 3 — CUSTOMER INTELLIGENCE
**Goal:** Every customer is automatically segmented. Churn risk is identified before it happens.

### 3.1 Customer Segmentation Algorithm
Python function: `segment_customer(customer_id, brand_id)`

**RFM Scoring (Recency, Frequency, Monetary):**
```
recency_days = days since last purchase
frequency = total number of orders
monetary = total spend (NGN)

# Score each 1-5 relative to all customers in the brand
recency_score = percentile_rank(recency_days, all_customers) inverted
frequency_score = percentile_rank(frequency, all_customers)
monetary_score = percentile_rank(monetary, all_customers)

rfm_score = (recency_score + frequency_score + monetary_score) / 3
```

**Segment assignment:**
- Champion: recency_score ≥ 4, frequency_score ≥ 4, monetary_score ≥ 4
- Loyal: frequency_score ≥ 4 and monetary_score ≥ 3
- Promising: recency_score ≥ 4 and frequency = 1 or 2 (new but recently active)
- At Risk: was Champion or Loyal, recency_score now ≤ 2
- Lost: recency_days > 180
- One-and-Done: frequency = 1 and recency_days > 60

### 3.2 Churn Prediction
Simple rule-based churn risk (no ML needed at this stage — insufficient data):
- 14-day churn probability: based on how many customers with similar RFM patterns churned in historical data
- 30-day churn probability: same approach with wider window
- Flag customer as "At Risk" when churn probability > 60%

### 3.3 Nightly Segmentation Job
- Celery scheduled task: runs at 3:30 AM WAT (after SKU scoring)
- For every active brand: loop through all customers, run `segment_customer`, upsert into `customer_segments` table
- Calculate brand-level stats: champion count, at-risk count, lost count, one-and-done count

### 3.4 Customer Dashboard Page
Frontend page: `/dashboard/customers`

**Segment overview:**
- Cards showing count and percentage in each segment
- Champions: X customers | ₦X total spend | Growing/Shrinking (trend vs last month)
- At Risk: X customers | ₦X at stake | Requires action
- Lost: X customers | ₦X historical spend | Recovery potential
- One-and-Done: X customers | Conversion opportunity

**Customer list per segment:**
- Click any segment card → see individual customers
- Table: Customer Name | Phone | Total Spend | Orders | Last Purchase | Days Since Last Purchase
- Click customer → customer profile page (all orders, purchase history, segment history)

**Churn risk list:**
- Dedicated section: customers with churn probability > 60%
- Shows: name, phone, last purchase date, total historical spend, days inactive
- One-click action: add to WhatsApp reactivation sequence (when Sprint 5 is live)

### 3.5 Cohort Analysis
Frontend page: `/dashboard/cohorts`

- Group customers by month of first purchase (January cohort, February cohort, etc.)
- Show for each cohort: initial customers, % still purchasing in month 2, month 3, month 6, month 12
- Visual: retention curve chart (x-axis = months since first purchase, y-axis = % still buying)
- Insight: "Your January cohort retains better than February — they were likely acquired through a different channel"

### 3.6 High-Value Buyer Profile
- Composite profile of top 20% of customers by lifetime spend
- Shows: most common location (state), most common first product bought, most common acquisition channel (from which payment gateway or order source), average time between purchases
- Purpose: use this to brief ad targeting and influencer selection

**Sprint 3 is complete when:** All customers are automatically segmented, churn risk customers are identified, and the cohort retention curve is visible and accurate. Test with a brand that has at least 6 months of order history.

---

## SPRINT 4 — WEEKLY INTELLIGENCE DIGEST
**Goal:** Every Monday, brand owners receive their week in review on WhatsApp. This is the feature that creates habit and kills churn.

### 4.1 AfricasTalking WhatsApp Setup
- Create AfricasTalking account
- Register as WhatsApp Business Solution Provider
- Get a WhatsApp Business phone number assigned to CIP
- Set up message templates (WhatsApp requires pre-approved templates for outbound messages)
- Templates needed:
  - Weekly digest template
  - SKU death alert template
  - Churn risk alert template
  - Reorder alert template
  - General notification template

### 4.2 Digest Generation Engine
Python function: `generate_weekly_digest(brand_id, week_start_date)`

**Pulls:**
- Revenue this week vs last week vs same week last year
- Top 3 SKUs by revenue this week
- SKU that dropped the most in score this week (alert)
- Customers who moved from Active to At Risk this week
- Champion count change vs last week
- Top recommended action (one thing, not a list)

**Formats into WhatsApp message:**
```
📊 *[Brand Name] Weekly Report*
Week of [Date]

💰 Revenue: ₦X,XXX,XXX
[Up/Down] X% vs last week

🔥 Top SKU this week: [Product Name]
⚠️ Needs attention: [Product Name] — score dropped from X to X

👥 Customers at churn risk: X
🏆 Champions this week: X

✅ This week's priority: [One specific action]

View full report → [link to dashboard]
```

### 4.3 Digest Delivery Job
- Celery scheduled task: Sunday night at 10:00 PM WAT
- For every active brand: generate digest, store in `weekly_digests` table, send via AfricasTalking WhatsApp API
- Fallback: if WhatsApp delivery fails, send via Resend email
- Track delivery status: update `delivered_whatsapp` and `delivered_email` fields

### 4.4 Digest History in Dashboard
- Frontend page: `/dashboard/digest-history`
- Shows all past weekly digests in reverse chronological order
- Click any digest → see full details for that week
- Allows founders to track business trajectory over time

### 4.5 Notification Preferences
- Settings page: brand owner can configure:
  - WhatsApp number for alerts
  - Email for alerts
  - Which alert types to receive via WhatsApp vs email vs in-app only
  - Digest delivery time preference (Monday morning vs Sunday night)

**Sprint 4 is complete when:** A real brand receives their first weekly digest on WhatsApp and it contains accurate data for their business. The digest should be indistinguishable from something written by a smart analyst who spent an hour reviewing their data.

---

## SPRINT 5 — AUTOMATION ENGINE
**Goal:** The platform takes action automatically when conditions are met. No more manual monitoring.

### 5.1 Automation Rules Engine (Backend)
Python service: `automation_engine.py`

- Runs after nightly data processing jobs (3:00 AM SKU scoring → 3:30 AM segmentation → 4:00 AM automation evaluation)
- For each active brand: load all active automation rules, evaluate each rule's conditions, if triggered: execute the action, log the trigger event

**Rule evaluation:**
```python
def evaluate_rule(rule, brand_data):
    trigger_type = rule['trigger_type']
    conditions = rule['trigger_conditions']
    
    if trigger_type == 'sku_score_drop':
        # Find any SKU where score dropped below threshold
        # Check against conditions: threshold, drop_percentage
    elif trigger_type == 'low_inventory':
        # Find any SKU where days_of_inventory < threshold
    elif trigger_type == 'customer_inactive':
        # Find customers inactive for X days who are not already in reactivation
    elif trigger_type == 'return_rate_spike':
        # Find any SKU where return_rate > threshold in last 7 days
    # ... etc
```

### 5.2 Built-in Automation Templates (Pre-built Rules)
These are one-click setup rules that cover the most common use cases:

**Inventory alerts:**
- "Alert me when any product has less than 14 days of stock" → WhatsApp alert
- "Alert me when a product hasn't sold in 21 days and I still have stock" → WhatsApp alert + flag for review

**SKU performance:**
- "Alert me when any SKU score drops below 5" → WhatsApp alert
- "Alert me when a product's return rate goes above 15%" → WhatsApp alert + flag product

**Customer retention:**
- "Alert me when a Champion customer goes 45 days without buying" → WhatsApp alert
- "Add at-risk customers to reactivation sequence automatically" → trigger WhatsApp sequence

**Ad spend:**
- "Alert me if I'm spending on ads for a product with a Kill score" → WhatsApp alert

### 5.3 Rule Builder UI
Frontend page: `/dashboard/automation`

**Rule list view:**
- All active and inactive rules
- Toggle to enable/disable
- "Last triggered: X days ago" for each rule
- "Triggered X times this month" count

**New rule form:**
- Step 1: Choose trigger (dropdown of trigger types)
- Step 2: Set conditions (dynamic form based on trigger type)
- Step 3: Choose action (WhatsApp alert | Email alert | In-app notification)
- Step 4: Configure action (message template with variables)
- Save and activate

**Quick templates:**
- "Start with a template" section showing the 8 pre-built rules above
- One click to activate with default settings, or customize first

### 5.4 WhatsApp Automation Sequences
For customer reactivation (triggered automatically):

- Sequence 1: Day 45 of inactivity
  - Message: "Hi [Name], it's been a while! [Brand Name] has some new arrivals you might love. Reply to browse or visit [link]"
- Sequence 2: Day 60 of inactivity (if no purchase after Sequence 1)
  - Message: "[Brand Name] misses you. Here's 10% off your next order: [code]. Valid for 7 days."
- Sequence 3: Day 75 (final attempt)
  - Message: "Last chance offer from [Brand Name]: [specific product they bought before] is back in stock. [link]"

All sequences respect opt-out. If customer replies STOP, remove from all sequences.

### 5.5 Reorder Assistant
When low inventory automation triggers:

- WhatsApp message includes: Product name | Current stock | Days of inventory remaining | 30-day sales velocity | Suggested reorder quantity
- "Confirm reorder" button (links to reorder page in dashboard)
- Reorder page shows: product details, last supplier info (if previously entered), suggested quantity, option to mark reorder as placed
- When reorder is marked as placed, system tracks expected restock date and alerts when inventory is critically low before restock arrives

### 5.6 Automation Activity Log
- Every automation trigger logged with: timestamp, rule that triggered, condition values, action taken, delivery status
- Visible in dashboard: "/dashboard/automation/activity"
- Allows founder to see what the system did and verify it was correct

**Sprint 5 is complete when:** At least 5 different automation rules are running on a live brand and firing correctly. The reactivation sequence sends successfully. The alert system delivers to WhatsApp reliably.

---

## SPRINT 6 — CHANNEL INTELLIGENCE + ADS INTELLIGENCE
**Goal:** Brand owners understand exactly which channels are making them money and which are burning it.

### 6.1 Channel Performance Engine
Python function: `calculate_channel_performance(brand_id, date_range)`

**For each acquisition channel (website, whatsapp, instagram, facebook, physical, marketplace):**
- Total orders and total revenue
- Unique customers acquired
- Average order value
- Return rate of orders from this channel
- Repeat purchase rate of customers from this channel
- Estimated LTV: track what customers from each channel spend over 90 days and 365 days
- Contribution margin: revenue minus estimated CAC (from ad spend data if available)

**Key insight generated:** "Your WhatsApp channel has a 42% repeat purchase rate vs 18% for Instagram. WhatsApp buyers are more loyal even if Instagram drives more first purchases."

### 6.2 Meta Ads Intelligence
**Connects to Sprint 1.11 (Meta Ads data already ingested)**

**Cross-reference with transaction data:**
- If ad spend increases and Paystack transactions increase in same period → positive correlation
- If ad spend is high but transaction velocity is flat → ad spend efficiency is low
- Calculate approximate ROAS: (transaction revenue in period) / (Meta ad spend in period)
- Note: this is approximate attribution, not exact. We cannot track individual ad click → WhatsApp DM → Paystack payment. We are showing correlation, not causation. Be honest about this in the UI.

**SKU-level ad intelligence:**
- If a brand is running ads for a specific product (identified by product mention in ad copy/creative name), compare ad spend on that product to its SKU score
- Alert: "You are spending ₦45,000/week advertising [Product X] but its SKU score is 3 (Kill). You are paying to sell a product that is hurting your brand."

### 6.3 Influencer ROI Tracker
**The Nigeria-specific feature that no analytics platform here offers.**

- Add influencer record: name, platform (Instagram/TikTok), content type, fee paid, campaign dates
- Add tracking method: UTM link (if they drove to website) or promo code (if discount code used)
- Pull UTM traffic from analytics if website is connected
- Pull promo code usage from Paystack/Flutterwave order references
- Calculate: revenue generated / fee paid = ROI multiple
- Show: "Influencer A: ₦200,000 fee → ₦680,000 in tracked sales = 3.4x ROI"
- Show: "Influencer B: ₦150,000 fee → ₦89,000 in tracked sales = 0.6x ROI (loss)"
- Build a ranked database of influencer performance over time

### 6.4 Regional Intelligence
**Available because we capture delivery state/LGA from all order sources**

- Revenue heatmap by Nigerian state (chart)
- Top 5 states by revenue
- Top 5 states by order count
- Average order value by state
- Delivery performance by logistics partner per state (using order completion data)
- "Your highest average order value is in Abuja but 70% of your orders come from Lagos"

### 6.5 Channel Performance Dashboard
Frontend page: `/dashboard/channels`

- Tab navigation: Overview | Meta Ads | Influencers | Regional
- Overview: all channels side by side with key metrics
- Meta Ads: spend vs performance chart, SKU-level ad alert
- Influencers: tracked campaigns list, ROI table
- Regional: state heatmap, top regions table

**Sprint 6 is complete when:** A brand can see their channel performance breakdown, their Meta Ads approximate ROAS, their influencer ROI, and their regional sales distribution — all from one page.

---

## SPRINT 7 — MULTI-BRAND DASHBOARD + BRAND HEALTH SCORE
**Goal:** House-of-brand operators and serious founders can manage multiple brands from one view and see business health at a glance.

### 7.1 Brand Health Score
Python function: `calculate_brand_health_score(brand_id)`

**Composite score (0–100):**
```
revenue_momentum = compare 30d revenue to previous 30d (trending up/flat/down) → 0-20 points
customer_retention = champion_count / total_active_customers → 0-20 points
inventory_health = % of products with score ≥ 6 → 0-20 points
margin_health = avg margin across all products → 0-20 points
channel_diversity = number of active acquisition channels → 0-10 points
data_completeness = % of data fields filled (helps us track data quality) → 0-10 points
```

- Updates weekly (run during Sunday night digest generation job)
- Trend: compare to last 4 weeks (improving / stable / declining)

### 7.2 Command Center (Default Dashboard)
Frontend page: `/dashboard` (home page after login)

**Above the fold (no scrolling needed):**
- Brand Health Score (large number, color coded: 70+ green, 40-69 yellow, below 40 red) + trend arrow
- Revenue this week / this month in large text + % change vs last period
- 3 Priority Actions (never more than 3): "Scale [Product X]" | "Reactivate 14 at-risk customers" | "Kill [Product Y] — ₦120k locked"

**Below the fold:**
- SKU spotlight: highest scoring SKU (scale) + lowest scoring SKU (review)
- Customer pulse: champion count + at-risk count + churn risk this week
- Recent alerts (last 5 automations that fired)
- Quick links to all dashboard sections

### 7.3 Multi-Brand Selector
- If organization has multiple brands: show brand selector in top navigation
- Switch between brands with one click
- All dashboard data updates to selected brand instantly

### 7.4 Multi-Brand Overview Page
Frontend page: `/dashboard/brands`

Only visible if organization has 2+ brands.

- Side-by-side cards for each brand
- Each card shows: Brand Health Score, revenue this month, top SKU, customer count, one priority action
- Sort brands by: health score, revenue, growth rate
- "Which brand needs attention this week" — highlight the lowest health score brand

### 7.5 Capital Allocation View
- For house-of-brands operators: which brand should get more ad spend this month?
- Shows: each brand's revenue per ₦1 spent on ads (capital efficiency)
- Shows: each brand's inventory turnover rate
- Shows: each brand's customer LTV trend
- Recommendation: "Brand X has the highest capital efficiency and growing LTV — allocate more resources here"

### 7.6 Investor-Ready Export
- One-click PDF export of brand performance report
- Contents: Brand Health Score trend, revenue growth (MoM/YoY), cohort retention curves, LTV by channel, contribution margin trend, SKU portfolio health summary
- Formatted for sharing with investors, partners, or for personal business reviews

**Sprint 7 is complete when:** A founder managing two brands can see both from one screen, see their Brand Health Scores, and export a clean performance report.

---

## SPRINT 8 — DEMAND INTELLIGENCE + FINANCIAL INTELLIGENCE
**Goal:** Forward-looking insights. Not just what happened — what will happen and what it costs.

### 8.1 Demand Forecast
Python function: `forecast_sku_demand(product_id, brand_id, days_ahead)`

**Method:**
- Calculate average daily velocity for last 30, 60, 90 days
- Apply seasonality multiplier: if current month is historically high/low for this category (Detty December boost, post-holiday dip, Sallah spike, etc.)
- Multiply base velocity by seasonality multiplier
- Output: predicted units sold in next 30/60/90 days
- Compare to current stock: if predicted demand > current stock → reorder alert

**Nigerian seasonality patterns to hardcode:**
- December: +40% for fashion, beauty, gifting categories
- January: -20% post-holiday
- April (Sallah period): +30% for food, fabric, fashion
- August/September (back to school): varies by category
- February (Valentine's): +50% for beauty, jewelry, gifting
- These will be refined as we accumulate real platform data

### 8.2 Reorder Recommendation Engine
- For each SKU with days_of_inventory < 30: calculate reorder quantity
- Reorder quantity = (predicted 60-day demand) - current stock (if positive)
- Display in dashboard with: suggested quantity, last supplier info, estimated cost at last cost price
- One-click: mark as "Reorder placed" with expected delivery date

### 8.3 Contribution Margin Calculator
Python function: `calculate_contribution_margin(product_id, date_range)`

For each SKU:
```
revenue = units_sold × selling_price
cogs = units_sold × cost_price
gross_margin = revenue - cogs
fulfillment_cost = estimated shipping cost (if logistics data available, else manual entry)
payment_processing_fee = revenue × 0.015 (Paystack/Flutterwave standard rate)
attributable_ad_spend = (Meta ad spend in period × product's share of active ads) — approximation
return_cost = refunded_orders × (cost_price + fulfillment_cost)

contribution_margin = gross_margin - fulfillment_cost - payment_processing_fee - return_cost
contribution_margin_percent = contribution_margin / revenue
```

**Critical insight:** Many brands discover their "bestseller" has the lowest contribution margin. This is the moment they realize gross margin and profit are different things.

### 8.4 Brand P&L View
Frontend page: `/dashboard/financials`

Not full accounting. Operational profit visibility.

- Total revenue (period selector: week/month/quarter)
- Less: COGS (from cost price × units sold)
- Less: Estimated fulfillment cost
- Less: Payment processing fees (calculated from transaction data)
- Less: Refund cost
- Less: Ad spend (from Meta Ads data)
- = Operational contribution margin

- Comparison to previous period
- Breakdown by product category
- Note: "This is not a substitute for formal accounting. For tax and compliance purposes, use a qualified accountant."

### 8.5 Working Capital Intelligence
- Capital locked in inventory: sum of (stock × cost_price) for all active products
- Expected revenue from existing orders in fulfilment (orders completed but not yet settled)
- Reorder cost forecast for next 30 days (based on demand forecast)
- Cash position implication: "If you restock your top 5 SKUs as recommended, estimated outflow is ₦X"

### 8.6 Category Trend Tracking
- Google Trends API integration: track search volume trends for product categories (fashion, beauty, electronics, food, etc.)
- Show: is your category trending up or down nationally in Nigeria?
- Nigerian-specific seasonal context in the UI
- "Searches for [your category] in Lagos are up 34% compared to this time last year"

**Sprint 8 is complete when:** A brand can see their demand forecast for the next 60 days, their contribution margin per product (not just gross margin), their operational P&L for the month, and their category trend data.

---

## SPRINT 9 — CIP SCORE + FINTECH API
**Goal:** Activate the business model. The platform starts generating institutional revenue.

**Prerequisite: Do not start this sprint until we have 1,000+ brands with 6+ months of data. The CIP Score is worthless without a meaningful training dataset.**

### 9.1 CIP Score Model
Python function: `calculate_cip_score(brand_id)`

**Seven dimensions, each scored 0–100, then weighted:**

```
1. Revenue Trend (20%):
   - Compare last 3 months to previous 3 months
   - Growing: 70-100 | Stable: 40-69 | Declining: 0-39

2. Revenue Consistency (15%):
   - Coefficient of variation of monthly revenue
   - Low variance (predictable): 70-100 | Medium: 40-69 | High variance: 0-39

3. Inventory Health (15%):
   - % of products with SKU score ≥ 6
   - High inventory turnover rate
   - Low dead stock ratio

4. Customer Retention (20%):
   - Repeat purchase rate
   - Champion customer % of customer base
   - 90-day retention rate

5. Payment Reliability (15%):
   - Refund rate
   - Payment completion rate (initiated vs completed)
   - Payment method diversity

6. Channel Diversity (5%):
   - Number of active sales channels
   - Single-channel dependence is risk

7. Business Trajectory (10%):
   - Brand Health Score trend over last 6 months
   - Is the business getting better or worse?
```

**CIP Score = weighted_average of all 7 dimensions**

**Data requirements:**
- Minimum 6 months of connected transaction data
- Minimum 50 orders to have statistical significance
- If requirements not met: show "Building your CIP Score — X months of data remaining"

### 9.2 Brand-Facing CIP Score View
Frontend page: `/dashboard/cip-score`

- Large score display (0–100) with color coding
- "Your CIP Score qualifies you for [credit range] inventory financing from our lending partners"
- Score breakdown: each of the 7 dimensions shown with their individual score and explanation
- "What's improving your score" vs "What's pulling your score down"
- Historical score chart: how the score has changed over time
- "Share your score with a lender" button (leads to consent flow)

### 9.3 Consent and Access Control System
This is legally critical. Build it carefully.

- Brand explicitly authorizes sharing their CIP Score with a specific institution
- Consent record stored with: institution name, access type, timestamp, brand's explicit confirmation
- Brand can see who has accessed their score and when
- Brand can revoke consent (institution loses API access for that brand)
- Terms are explicit: "By sharing your score, you authorize [Institution] to access your CIP business health score. They will NOT receive access to your individual transaction records or customer data."

### 9.4 Fintech API Endpoints
**Authenticated, rate-limited, fully documented REST API:**

```
POST /api/v1/cip-score/request
  Authorization: Bearer {institution_api_key}
  Body: { phone_number: "+2348012345678" }  // brand owner's phone
  
  Process:
  1. Look up brand by phone number
  2. Check if brand has given consent for this institution
  3. If yes: return CIP Score + dimension breakdown + data_months
  4. If no: return 403 with message "Brand has not authorized access"
  5. Log the access in cip_score_access table

Response:
{
  "brand_reference": "CIP-XXXXXX",  // anonymized ID, not brand name
  "score": 74,
  "grade": "B",
  "data_months": 11,
  "dimensions": {
    "revenue_trend": 82,
    "revenue_consistency": 71,
    "inventory_health": 68,
    "customer_retention": 79,
    "payment_reliability": 88,
    "channel_diversity": 60,
    "trajectory": 73
  },
  "score_date": "2026-02-27",
  "valid_until": "2026-03-27"
}
```

### 9.5 Institution Management (Internal Admin)
Internal admin panel (not public facing):

- Register institutions (fintechs, suppliers, investors)
- Generate API keys per institution
- Set rate limits per institution (e.g., 1,000 score checks per month)
- View API usage logs: which institution checked which brand's score, when
- Revoke institution access

### 9.6 API Documentation
- Auto-generated FastAPI docs at `/api/docs` (Swagger UI)
- Supplementary human-readable documentation
- Authentication guide
- Integration examples in Python, JavaScript, and cURL
- Sandbox environment with test brand scores for integration testing

**Sprint 9 is complete when:** One real fintech institution has integrated the CIP Score API, checked a consented brand's score successfully, and the access is logged. This is the first institutional revenue event.

---

## SPRINT 10 — MARKETPLACE + LOGISTICS INTELLIGENCE
**Goal:** Capture the Jumia/Konga seller and the logistics data that changes the regional intelligence layer.

### 10.1 Marketplace Integrations
- Jumia Seller Center API (if available) or CSV export
- Konga Seller API or CSV export
- Jiji (primarily classifieds, CSV only)

**What we capture:**
- Orders from marketplace channel
- Product performance on marketplace vs own website
- Marketplace fees per order
- Contribution margin on marketplace (often negative after fees)

**Key insight:** "Your margin on Jumia is 8% after fees. Your margin selling direct through WhatsApp is 34%. Jumia drives volume but kills profit."

### 10.2 Logistics Intelligence
- GIG Logistics API integration
- Sendbox API integration
- Kwik Delivery API integration

**What we capture:**
- Delivery status per order
- Delivery time: order placed → delivered
- Failed delivery rate per logistics partner per state
- Cost per delivery per partner

**Insights:**
- "GIG delivers to Abuja in 2.1 days on average. Sendbox delivers the same route in 3.8 days. For Abuja orders, use GIG."
- "Your failed delivery rate in Rivers State is 18% — higher than the 8% national average. Consider local courier for that state."

**Sprint 10 is complete when:** A brand that sells on Jumia and their own website can see the profitability comparison, and a brand using multiple logistics partners can see which partner performs best per region.

---

## SPRINT 11 — AI PRODUCT LAUNCH ASSISTANT
**Goal:** Before launching a new product, brands get data-driven launch intelligence.**

### 11.1 Launch Intelligence Engine
Triggered when a seller is considering a new product.

**Input from seller:**
- Product category
- Target price
- Target cost price (target margin)
- Target customer segment

**What CIP generates:**
- Category demand trend (from Google Trends data)
- How similar products in our dataset perform (anonymized, aggregated)
- What price points convert best for this category
- Which channel drives most revenue for this category
- Best time to launch (seasonality)
- Estimated launch difficulty score

### 11.2 SKU Launch Tracker
- After launching a new product: track its velocity week by week vs expected
- "Your new product is tracking 40% below the expected velocity for this category. Consider: different pricing, different channel, or different audience."
- Alert if new product shows early warning signs of becoming a Kill SKU

**Sprint 11 is complete when:** A seller can input a product idea and receive a data-driven launch assessment. A launched product's performance is tracked against benchmarks.

---

## SPRINT 12 — SUPPLIER INTELLIGENCE
**Goal:** Track where products come from and whether suppliers are reliable.**

### 12.1 Supplier Records
- Add supplier: name, contact, products supplied, lead time, payment terms
- Add purchase records: date ordered, quantity, cost, expected delivery date, actual delivery date
- Track: lead time reliability (on time % per supplier)

### 12.2 Reorder Workflow with Supplier Context
- When reorder alert fires: show supplier options for that product with their reliability scores
- "Supplier A: 4-day lead time, 94% on-time. Supplier B: 6-day lead time, 72% on-time."
- One-click: generate reorder note (pre-filled WhatsApp message or email to supplier)

### 12.3 Supplier Pre-qualification API (Institutional Feature)
- Suppliers can check if a brand is creditworthy before extending trade credit
- Same consent system as fintech CIP Score access
- Supplier-specific view: inventory management score, payment reliability score, revenue trend
- Charge suppliers per pre-qualification check (separate revenue stream)

---

## FUTURE SPRINTS (Document Now, Build Later)

### Future Sprint A: Ad Creative Intelligence
- Connect ad creative performance data (image/video ID → CTR, conversion rate)
- Identify creative fatigue (CTR declining week over week on same creative)
- Pattern: what visual style or copy elements correlate with best performance for this brand's audience

### Future Sprint B: Open Banking Expansion
- As CBN Open Banking framework matures: direct bank connections beyond Mono
- OPay/PalmPay wallet history if APIs open up
- Moniepoint personal banking data

### Future Sprint C: Embedded Lending
- Partner with a licensed Microfinance Bank
- CIP Score becomes the underwriting signal
- Offer inventory financing directly inside the platform
- Loan offer triggered when: brand has CIP Score 65+, has connected inventory, and has a high-scoring SKU they're running low on
- Repayment tracked against incoming Paystack/Flutterwave sales

### Future Sprint D: FMCG Intelligence Product
- Aggregate, anonymized category-level data across all CIP brands
- Package as quarterly intelligence reports for FMCG companies
- Nestle, Unilever, PZ Cussons: what is selling in which category in which region in real time
- Annual subscription product ($10M–$50M naira per year per client)

### Future Sprint E: Multi-country Expansion
- Ghana (similar market dynamics, GhIPSS payment infrastructure)
- Kenya (M-Pesa dominance changes the payment integration priority)
- Each market requires: local payment gateway integrations, local logistics partners, local Open Banking connectors

---

## RULES FOR EVERY SPRINT

**Before starting any sprint:**
1. The previous sprint is fully complete and tested with real data
2. Database migrations for this sprint are written before any API code
3. API endpoints are designed before frontend components

**During every sprint:**
1. One task at a time. Test before moving to the next.
2. Commit to GitHub after every working feature.
3. Never build features from future sprints even if they seem related.

**After every sprint:**
1. Test with a real brand (not just synthetic test data)
2. Document what is live and working in a sprint completion note
3. Review: what was harder than expected? What changed?

---

## ENVIRONMENT VARIABLES (Complete List)

```bash
# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
DATABASE_URL=

# Redis (Upstash)
UPSTASH_REDIS_URL=
UPSTASH_REDIS_TOKEN=

# AfricasTalking (WhatsApp + SMS)
AFRICASTALKING_USERNAME=
AFRICASTALKING_API_KEY=
AFRICASTALKING_WHATSAPP_NUMBER=

# Resend (Email)
RESEND_API_KEY=

# Payment Gateway Integrations
PAYSTACK_SECRET_KEY=
FLUTTERWAVE_SECRET_KEY=
MONNIFY_API_KEY=
MONNIFY_SECRET_KEY=
OPAY_APP_ID=
OPAY_PUBLIC_KEY=
OPAY_PRIVATE_KEY=

# Open Banking
MONO_SECRET_KEY=
MONO_PUBLIC_KEY=

# Shopify (OAuth App)
SHOPIFY_API_KEY=
SHOPIFY_API_SECRET=
SHOPIFY_SCOPES=read_orders,read_products,read_customers,read_inventory

# WooCommerce (per brand, stored encrypted in DB)
# Meta Ads
META_APP_ID=
META_APP_SECRET=

# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=
GOOGLE_ADS_CLIENT_ID=
GOOGLE_ADS_CLIENT_SECRET=

# TikTok Ads
TIKTOK_APP_ID=
TIKTOK_APP_SECRET=

# Google Trends
GOOGLE_TRENDS_API_KEY=

# Internal
JWT_SECRET=
ENCRYPTION_KEY= (for encrypting API keys stored in DB)
ENVIRONMENT=development | production
FRONTEND_URL=
BACKEND_URL=
```

---

## HOW TO INTRODUCE THIS PROJECT TO CLAUDE CODE

When starting a new Claude Code session, paste the following:

---

**"We are building CIP — Commerce Intelligence Platform, a data platform for Nigerian SMEs. This is the master document with the full architecture and sprint plan: [paste this document]. We are currently on Sprint [X]. The current state of the codebase is: [describe what's done]. Today we are building: [specific task from current sprint]. Do not build anything from future sprints. Ask me before making any architecture decisions not covered in the master document."**

---

*CIP Master Implementation Strategy*
*Version: 1.0 — Complete*
*Classification: Internal — Co-Founder + Claude Code Reference Document*
