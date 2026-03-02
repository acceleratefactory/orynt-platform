"""
ORYNT API — Entry Point
FastAPI application for the Commerce Intelligence Platform.
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else imports os.getenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, auth, organizations, brands
from app.database import _get_engine
from app.models.base import Base
# Import models so SQLAlchemy registers them before create_all
from app.models import organization, brand  # noqa: F401

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

# ─── Root ────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    return {"message": "ORYNT API is running. See /api/docs for documentation."}
