"""
ORYNT — Health Check Router
GET /health — used by monitoring and deployment scripts to confirm the
backend and all its dependencies are reachable.
"""

import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.database import check_db_connection
from app.cache import check_cache_connection

router = APIRouter()


@router.get("/health")
def health_check():
    """
    Returns the operational status of the API, database, and cache.
    HTTP 200 if all systems are connected.
    HTTP 500 if any dependency is unreachable.
    """
    db_ok = check_db_connection()
    cache_ok = check_cache_connection()
    environment = os.getenv("ENVIRONMENT", "development")

    payload = {
        "status": "ok" if (db_ok and cache_ok) else "degraded",
        "service": "orynt-api",
        "database": "connected" if db_ok else "error",
        "cache": "connected" if cache_ok else "error",
        "environment": environment,
    }

    status_code = 200 if (db_ok and cache_ok) else 500
    return JSONResponse(status_code=status_code, content=payload)
