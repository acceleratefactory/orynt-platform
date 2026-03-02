"""
ORYNT API — Entry Point
FastAPI application for the Commerce Intelligence Platform.
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else imports os.getenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, auth

app = FastAPI(
    title="ORYNT API",
    description="Commerce Intelligence Platform for Nigerian SMEs",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ─── CORS Configuration ─────────────────────────────────────────────────────
# Allowed origins (Frontend URL)
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

# ─── Routers ────────────────────────────────────────────────────────────────
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router)

# ─── Root ───────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    return {"message": "ORYNT API is running. See /api/docs for documentation."}
