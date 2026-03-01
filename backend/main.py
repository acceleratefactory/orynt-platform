"""
ORYNT API — Entry Point
FastAPI application for the Commerce Intelligence Platform.
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else imports os.getenv()

from fastapi import FastAPI
from app.routers import health

app = FastAPI(
    title="ORYNT API",
    description="Commerce Intelligence Platform for Nigerian SMEs",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ─── Routers ────────────────────────────────────────────────────────────────
app.include_router(health.router, tags=["Health"])

# ─── Root ───────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    return {"message": "ORYNT API is running. See /api/docs for documentation."}
