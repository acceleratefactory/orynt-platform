"""
ORYNT — Reseller Platform Integration Router
Two-step connection flow:

Step 1: POST /api/integrations/reseller-platform/connect
  - Accepts direct MySQL credentials for the reseller platform DB
  - Validates connection by enumerating wp_storefronts
  - Returns storefront count + requires confirmation
  - Does NOT create brands yet

Step 2: POST /api/integrations/reseller-platform/confirm
  - Founder confirms they want brands created
  - Queues bulk_create_reseller_brands Celery job

Step 3 (GET): /api/integrations/reseller-platform/status
  - Returns current sync status: brands created, pending jobs, etc.

IMPORTANT: Does NOT use WooCommerce REST API. Direct MySQL only.
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
router = APIRouter(prefix="/api/integrations/reseller-platform", tags=["Reseller Platform"])

ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")


def _encrypt(value: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).encrypt(value.encode()).decode()


def _decrypt(value: str) -> dict:
    return json.loads(Fernet(ENCRYPTION_KEY.encode()).decrypt(value.encode()).decode())


def _prefix(db_prefix: str, table: str) -> str:
    bare = table[len("wp_"):]
    return f"{db_prefix}{bare}"


def _test_mysql_and_enumerate(creds: dict) -> list[dict]:
    """Open a MySQL connection and enumerate active storefronts. Returns list of rows."""
    prefix = creds.get("db_prefix", "wp_")
    storefronts_tbl = _prefix(prefix, "wp_storefronts")
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
                    f"SELECT id, reseller_id, store_name, subdomain, domain "
                    f"FROM {storefronts_tbl} WHERE active = 1"
                )
                return cur.fetchall()
    except pymysql.OperationalError as exc:
        errno, msg = exc.args[0], exc.args[1] if len(exc.args) > 1 else str(exc)
        if errno in (1045, 1044):
            raise HTTPException(
                status_code=400,
                detail=f"MySQL access denied: {msg}. Check DB username and password.",
            )
        if errno in (2003, 2005):
            raise HTTPException(
                status_code=502,
                detail=f"Cannot connect to MySQL host '{creds['db_host']}'. Check DB host and port.",
            )
        if errno == 1146:
            raise HTTPException(
                status_code=400,
                detail=f"Table not found ({msg}). Verify db_prefix is correct (e.g. 'wp_').",
            )
        raise HTTPException(status_code=502, detail=f"MySQL error: {msg}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not connect to reseller platform database: {exc}")


# ── Step 1: Connect ───────────────────────────────────────────────────────────

class ResellerConnectRequest(BaseModel):
    db_host: str
    db_name: str
    db_user: str
    db_password: str
    db_port: int = 3306
    db_prefix: str = "wp_"
    brand_id: str  # The founder's master brand (used to find organization_id)


@router.post("/connect")
def connect_reseller_platform(
    body: ResellerConnectRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Step 1: Connect to reseller platform MySQL database.
    Validates credentials, enumerates storefronts, saves encrypted creds.
    Returns storefront count and requires confirmation before creating brands.
    """
    # Look up the founder's organization_id from their master brand
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
        "db_prefix": body.db_prefix,
        "organization_id": org_id,
    }

    # Test connection and enumerate storefronts
    storefronts = _test_mysql_and_enumerate(creds)
    count = len(storefronts)

    if count == 0:
        raise HTTPException(
            status_code=400,
            detail="Connection successful but no active storefronts found in wp_storefronts WHERE active = 1.",
        )

    # Save/update the master integration record with encrypted creds
    encrypted = _encrypt(json.dumps(creds))
    existing = db.query(Integration).filter_by(
        brand_id=body.brand_id, type="reseller_platform"
    ).first()
    if existing:
        existing.encrypted_key = encrypted
        existing.status = "pending_confirmation"
        integration = existing
    else:
        integration = Integration(
            brand_id=body.brand_id,
            type="reseller_platform",
            status="pending_confirmation",
            encrypted_key=encrypted,
        )
        db.add(integration)
    db.commit()
    db.refresh(integration)

    # Return preview of first 5 storefronts for founder to review
    preview = [
        {"id": sf["id"], "store_name": sf["store_name"], "subdomain": sf.get("subdomain")}
        for sf in storefronts[:5]
    ]

    return {
        "status": "pending_confirmation",
        "integration_id": integration.id,
        "storefronts_found": count,
        "confirmation_required": True,
        "message": (
            f"Connected successfully. Found {count} active storefronts. "
            f"Click 'Confirm' to create {count} brands in ORYNT and start syncing."
        ),
        "preview": preview,
    }


# ── Step 2: Confirm ───────────────────────────────────────────────────────────

class ResellerConfirmRequest(BaseModel):
    integration_id: str
    brand_id: str


@router.post("/confirm")
def confirm_reseller_platform(
    body: ResellerConfirmRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Step 2: Founder confirms they want all storefronts created as ORYNT brands.
    Queues the bulk_create_reseller_brands Celery task.
    """
    intg = db.get(Integration, body.integration_id)
    if not intg or intg.brand_id != body.brand_id:
        raise HTTPException(status_code=404, detail="Integration not found.")
    if intg.type != "reseller_platform":
        raise HTTPException(status_code=400, detail="Not a reseller platform integration.")

    intg.status = "syncing"
    db.commit()

    try:
        from app.tasks.reseller_tasks import bulk_create_reseller_brands
        task = bulk_create_reseller_brands.delay(body.integration_id)
    except Exception as exc:
        intg.status = "error"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Could not queue sync job: {exc}")

    return {
        "status": "syncing",
        "task_id": task.id,
        "message": "Brand creation started in the background. Check status in a few minutes.",
    }


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status")
def reseller_platform_status(brand_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Returns status of the reseller platform integration:
    master integration status, number of storefront brands created,
    and last sync time.
    """
    master = db.query(Integration).filter_by(
        brand_id=brand_id, type="reseller_platform"
    ).first()
    if not master:
        return {"connected": False}

    # Count storefront sub-integrations created under this org
    # (they share the same organization, counted separately)
    storefront_count = db.query(Integration).filter_by(
        type="reseller_platform_storefront", status="connected"
    ).count()

    return {
        "connected": master.status in ("connected", "syncing", "pending_confirmation"),
        "status": master.status,
        "integration_id": master.id,
        "storefronts_created": storefront_count,
        "last_sync_at": master.last_sync_at.isoformat() if master.last_sync_at else None,
    }
