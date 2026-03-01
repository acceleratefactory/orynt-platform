"""
ORYNT — Database Connection
Connects to Supabase PostgreSQL via SQLAlchemy using the transaction pooler
(port 6543) for serverless-compatible connection pooling.

Engine is lazy-loaded on first use so missing env vars surface at
runtime (as a health check error) rather than crashing on import.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

load_dotenv()  # Ensures .env is loaded in every subprocess context

_engine = None
_SessionLocal = None


def _get_engine():
    """Lazy-load the SQLAlchemy engine on first call."""
    global _engine
    if _engine is None:
        database_url = os.getenv("SUPABASE_DB_URL")
        if not database_url:
            raise ValueError(
                "SUPABASE_DB_URL environment variable is not set. "
                "Copy backend/.env.example to backend/.env and fill in the value."
            )
        _engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={
                "connect_timeout": 10,
                "options": "-c statement_timeout=30000",
            },
        )
    return _engine


def _get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


def get_db():
    """FastAPI dependency — yields a database session, closes it after request."""
    SessionLocal = _get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Health check — returns True if database is reachable, False otherwise."""
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except (OperationalError, ValueError, Exception):
        return False
