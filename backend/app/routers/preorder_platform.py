"""
ORYNT — Preorder Platform Integration Router

Two-step connect flow (same pattern as reseller_platform):
  POST /api/integrations/preorder-platform/connect   → validate DB + enumerate sellers
  POST /api/integrations/preorder-platform/confirm   → queue bulk brand creation
  GET  /api/integrations/preorder-platform/status    → sync status

Tables used: pop_sellers ONLY for enumeration.
No standard WooCommerce tables queried here.
"""

import os
import json
import logging
from cryptography.fernet import Fernet
import pymysql
import pymysql.cursors
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.integration import Integration

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/integrations/preorder-platform", tags=["Preorder Platform"])

ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")


def _encrypt(value: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).encrypt(value.encode()).decode()


def _enumerate_sellers(creds: dict) -> list[dict]:
    """Connect and enumerate active sellers from pop_sellers."""
    try:
        conn = pymysql.connect(
            host=creds["db_host"],
            user=creds["db_user"],
            password=creds["db_password"],
            database=creds["db_name"],
            port=int(creds.get("db_port", 3306)),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, user_id, business_name, phone, total_campaigns, "
                    "successful_campaigns, reliability_score "
                    "FROM pop_sellers WHERE status = 'active'"
                )
                return cur.fetchall()
    except pymysql.OperationalError as exc:
        errno = exc.args[0]
        msg = exc.args[1] if len(exc.args) > 1 else str(exc)
        if errno in (1045, 1044):
            raise HTTPException(status_code=400, detail=f"MySQL access denied: {msg}. Check DB username and password.")
        if errno in (2003, 2005):
            raise HTTPException(status_code=502, detail=f"Cannot connect to MySQL host '{creds['db_host']}'. Check host and port.")
        if errno == 1146:
            raise HTTPException(status_code=400, detail=f"Table 'pop_sellers' not found ({msg}). Verify this is the correct preorder platform database.")
        raise HTTPException(status_code=502, detail=f"MySQL error {errno}: {msg}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not connect to preorder platform database: {exc}")


# ── Step 1: Connect ───────────────────────────────────────────────────────────

class PreorderConnectRequest(BaseModel):
    db_host: str
    db_name: str
    db_user: str
    db_password: str
    db_port: int = 3306
    brand_id: str  # Founder's master brand → used to find organization_id


@router.post("/connect")
def connect_preorder_platform(
    body: PreorderConnectRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Step 1: Validate MySQL connection and enumerate active sellers.
    Does NOT create brands. Returns seller count + preview for founder review.
    """
    from app.models.brand import Brand
    master_brand = db.get(Brand, body.brand_id)
    if not master_brand:
        raise HTTPException(status_code=404, detail="Master brand not found.")
    org_id = master_brand.organization_id

    creds = {
        "db_host": body.db_host,
        "db_name": body.db_name,
        "db_user": body.db_user,
        "db_password": body.db_password,
        "db_port": body.db_port,
        "organization_id": org_id,
    }

    sellers = _enumerate_sellers(creds)
    count = len(sellers)

    if count == 0:
        raise HTTPException(
            status_code=400,
            detail="Connection successful but no active sellers found in pop_sellers WHERE status = 'active'.",
        )

    encrypted = _encrypt(json.dumps(creds))
    existing = db.query(Integration).filter_by(
        brand_id=body.brand_id, type="preorder_platform"
    ).first()
    if existing:
        existing.encrypted_key = encrypted
        existing.status = "pending_confirmation"
        integration = existing
    else:
        integration = Integration(
            brand_id=body.brand_id,
            type="preorder_platform",
            status="pending_confirmation",
            encrypted_key=encrypted,
        )
        db.add(integration)
    db.commit()
    db.refresh(integration)

    preview = [
        {
            "id": s["id"],
            "business_name": s["business_name"],
            "total_campaigns": s.get("total_campaigns", 0),
            "reliability_score": float(s.get("reliability_score") or 0),
        }
        for s in sellers[:5]
    ]

    return {
        "status": "pending_confirmation",
        "integration_id": integration.id,
        "sellers_found": count,
        "confirmation_required": True,
        "message": (
            f"Connected. Found {count} active sellers. "
            f"Click Confirm to create {count} brands and start syncing."
        ),
        "preview": preview,
    }


# ── Step 2: Confirm ───────────────────────────────────────────────────────────

class PreorderConfirmRequest(BaseModel):
    integration_id: str
    brand_id: str


@router.post("/confirm")
def confirm_preorder_platform(
    body: PreorderConfirmRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Step 2: Queue bulk_create_preorder_brands Celery task.
    """
    intg = db.get(Integration, body.integration_id)
    if not intg or intg.brand_id != body.brand_id:
        raise HTTPException(status_code=404, detail="Integration not found.")
    if intg.type != "preorder_platform":
        raise HTTPException(status_code=400, detail="Not a preorder platform integration.")

    intg.status = "syncing"
    db.commit()

    try:
        from app.tasks.preorder_tasks import bulk_create_preorder_brands
        task = bulk_create_preorder_brands.delay(body.integration_id)
    except Exception as exc:
        intg.status = "error"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Could not queue sync job: {exc}")

    return {
        "status": "syncing",
        "task_id": task.id,
        "message": "Brand creation started. Check back in a few minutes.",
    }


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status")
def preorder_platform_status(
    brand_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    master = db.query(Integration).filter_by(
        brand_id=brand_id, type="preorder_platform"
    ).first()
    if not master:
        return {"connected": False}

    seller_count = db.query(Integration).filter_by(
        type="preorder_platform_seller", status="connected"
    ).count()

    return {
        "connected": master.status in ("connected", "syncing", "pending_confirmation"),
        "status": master.status,
        "integration_id": master.id,
        "sellers_created": seller_count,
        "last_sync_at": master.last_sync_at.isoformat() if master.last_sync_at else None,
    }
