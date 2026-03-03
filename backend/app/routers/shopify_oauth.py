"""
ORYNT — Shopify OAuth Router
GET /api/integrations/shopify/auth     — redirect to Shopify OAuth consent
GET /api/integrations/shopify/callback — exchange code for access token, store, queue sync
GET /api/integrations/shopify/status   — check connection status for a shop

After authorization, registers the 4 required webhooks automatically.
"""

import os
import hmac
import hashlib
import json
import logging
import urllib.parse
from cryptography.fernet import Fernet
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.integration import Integration
from app.models.brand import Brand

logger = logging.getLogger(__name__)

SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY", "")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "")
SHOPIFY_REDIRECT_URI = os.getenv(
    "SHOPIFY_REDIRECT_URI",
    "http://localhost:8000/api/integrations/shopify/callback"
)
FRONTEND_BASE = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
SHOPIFY_API_VERSION = "2024-01"
SHOPIFY_SCOPES = "read_orders,read_products,read_customers,read_inventory"

router = APIRouter(prefix="/api/integrations/shopify", tags=["Shopify"])


def _encrypt(value: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.encrypt(value.encode()).decode()


def _verify_shopify_hmac(params: dict) -> bool:
    """Verify the HMAC from Shopify OAuth callback."""
    if not SHOPIFY_API_SECRET:
        return True  # Skip in dev if not configured
    provided_hmac = params.get("hmac", "")
    sorted_params = "&".join(
        f"{k}={v}" for k, v in sorted(params.items()) if k != "hmac"
    )
    computed = hmac.new(
        SHOPIFY_API_SECRET.encode(), sorted_params.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, provided_hmac)


def _register_shopify_webhooks(shop: str, access_token: str) -> None:
    """Register the 4 required webhooks on the Shopify store after OAuth."""
    webhook_topics = [
        "orders/create",
        "orders/updated",
        "products/update",
        "inventory_levels/update",
    ]
    callback_base = os.getenv(
        "BACKEND_BASE_URL", "http://localhost:8000"
    )
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }
    for topic in webhook_topics:
        try:
            resp = httpx.post(
                f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}/webhooks.json",
                headers=headers,
                json={
                    "webhook": {
                        "topic": topic,
                        "address": f"{callback_base}/api/webhooks/shopify",
                        "format": "json",
                    }
                },
                timeout=10,
            )
            if resp.status_code in (200, 201, 422):  # 422 = already exists
                logger.info(f"[Shopify] Webhook registered: {topic}")
            else:
                logger.warning(f"[Shopify] Webhook {topic} registration failed: {resp.status_code}")
        except Exception as exc:
            logger.warning(f"[Shopify] Could not register webhook {topic}: {exc}")


@router.get("/auth")
def shopify_auth(shop: str, brand_id: str, request: Request):
    """
    Start the Shopify OAuth flow.
    Redirects the user to the Shopify authorization page.
    """
    if not SHOPIFY_API_KEY:
        raise HTTPException(status_code=500, detail="SHOPIFY_API_KEY not configured.")

    # Validate shop domain format
    if not shop.endswith(".myshopify.com") or not shop.replace(".myshopify.com", "").isidentifier():
        raise HTTPException(
            status_code=400,
            detail="Invalid Shopify shop URL. Use format: storename.myshopify.com"
        )

    state = f"{brand_id}:{shop}"  # Pass brand_id through state for callback
    params = {
        "client_id": SHOPIFY_API_KEY,
        "scope": SHOPIFY_SCOPES,
        "redirect_uri": SHOPIFY_REDIRECT_URI,
        "state": state,
        "grant_options[]": "per-user",
    }
    auth_url = f"https://{shop}/admin/oauth/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/callback")
def shopify_callback(
    request: Request,
    code: str = "",
    shop: str = "",
    state: str = "",
    hmac: str = "",
    timestamp: str = "",
):
    """
    Handle Shopify OAuth callback.
    Verifies HMAC, exchanges code for access token, stores credentials,
    registers webhooks, and queues history pull.
    """
    if not code or not shop or not state:
        raise HTTPException(status_code=400, detail="Missing required Shopify OAuth parameters.")

    # Verify HMAC
    query_params = dict(request.query_params)
    if not _verify_shopify_hmac(query_params):
        raise HTTPException(status_code=401, detail="Invalid Shopify HMAC signature.")

    # Extract brand_id from state
    try:
        brand_id, expected_shop = state.split(":", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter.")

    if expected_shop != shop:
        raise HTTPException(status_code=400, detail="Shop mismatch in state.")

    # Exchange code for permanent access token
    try:
        resp = httpx.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id": SHOPIFY_API_KEY,
                "client_secret": SHOPIFY_API_SECRET,
                "code": code,
            },
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Shopify token exchange failed: {exc}")

    token_data = resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Shopify did not return an access token.")

    # Store encrypted credentials
    creds_json = json.dumps({"shop": shop, "access_token": access_token})
    encrypted = _encrypt(creds_json)

    from app.database import get_db_session
    with get_db_session() as db:
        brand = db.get(Brand, brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found.")

        existing = db.query(Integration).filter_by(brand_id=brand_id, type="shopify").first()
        if existing:
            existing.encrypted_key = encrypted
            existing.status = "connected"
            integration = existing
        else:
            integration = Integration(
                brand_id=brand_id, type="shopify",
                status="connected", encrypted_key=encrypted,
            )
            db.add(integration)
        db.commit()
        db.refresh(integration)
        integration_id = integration.id

    # Register webhooks
    _register_shopify_webhooks(shop, access_token)

    # Queue history pull
    try:
        from app.tasks.shopify_tasks import pull_shopify_history
        pull_shopify_history.delay(brand_id, integration_id)
    except Exception as exc:
        logger.warning(f"[Shopify] Could not queue Celery task: {exc}")

    # Redirect to frontend with success
    return RedirectResponse(
        url=f"{FRONTEND_BASE}/dashboard/integrations?shopify=connected&shop={shop}"
    )


@router.get("/status")
def shopify_status(brand_id: str, shop: str):
    """Check if a Shopify shop is already connected for a brand."""
    from app.database import get_db_session
    with get_db_session() as db:
        intg = db.query(Integration).filter_by(brand_id=brand_id, type="shopify", status="connected").first()
    if not intg:
        return {"connected": False}

    try:
        creds = json.loads(Fernet(ENCRYPTION_KEY.encode()).decrypt(intg.encrypted_key.encode()).decode())
        connected_shop = creds.get("shop", "")
    except Exception:
        connected_shop = ""

    return {
        "connected": True,
        "shop": connected_shop,
        "last_sync_at": intg.last_sync_at.isoformat() if intg.last_sync_at else None,
        "transaction_count": intg.transaction_count,
    }
