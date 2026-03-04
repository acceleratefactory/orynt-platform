"""
ORYNT API — Entry Point
FastAPI application for the Commerce Intelligence Platform.
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else imports os.getenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, auth, organizations, brands
from app.routers import integrations, webhooks, orders
from app.routers import shopify_oauth
from app.routers import reseller_platform
from app.routers import preorder_platform
from app.routers import bumpa
from app.routers import selar
from app.routers import gumroad_oauth
from app.routers import whatsapp_parser
from app.routers import meta_ads
from app.database import _get_engine
from app.models.base import Base
# Import models so SQLAlchemy registers them before create_all
from app.models import organization, brand, product                          # noqa: F401
from app.models import integration, customer, order, order_item              # noqa: F401
from app.models import ad_campaign                                           # noqa: F401

app = FastAPI(
    title="ORYNT API",
    description="Commerce Intelligence Platform for Nigerian SMEs",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ─── CORS Configuration ─────────────────────────────────────────────────────
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Create DB tables on startup ─────────────────────────────────────────────
@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=_get_engine())

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router)
app.include_router(organizations.router, prefix="/api")
app.include_router(brands.router, prefix="/api")
app.include_router(integrations.router)          # prefix already set in router: /api/integrations
app.include_router(shopify_oauth.router)         # prefix: /api/integrations/shopify
app.include_router(reseller_platform.router)     # prefix: /api/integrations/reseller-platform
app.include_router(preorder_platform.router)     # prefix: /api/integrations/preorder-platform
app.include_router(bumpa.router)                 # prefix: /api/integrations/bumpa
app.include_router(selar.router)                 # /api/integrations/selar + /api/webhooks/selar
app.include_router(gumroad_oauth.router)         # /api/integrations/gumroad + /api/webhooks/gumroad
app.include_router(webhooks.router)              # prefix: /api/webhooks
app.include_router(orders.router)                # prefix: /api/orders
app.include_router(whatsapp_parser.router)       # /api/orders/parse-whatsapp
app.include_router(meta_ads.router)              # /api/integrations/meta-ads

# ─── Root ────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    return {"message": "ORYNT API is running. See /api/docs for documentation."}
