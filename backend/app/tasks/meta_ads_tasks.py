"""
ORYNT — Meta Ads Celery Tasks

pull_meta_ads_history: Full or incremental sync of Meta ad campaigns.
  - GET /v19.0/me/adaccounts
  - For each account → GET campaigns
  - For each campaign → GET daily insights (time_increment=1)
  - Maps to ad_campaigns table (platform = 'meta')
  - Calculates ROAS from purchase actions

nightly_meta_sync: Pulls previous day's data at 6:00 AM WAT.

Token refreshing: Meta long-lived tokens last 60 days.
  - Refreshes token if created > 50 days ago using the same endpoint.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta, date

import httpx
from cryptography.fernet import Fernet
from sqlalchemy.exc import IntegrityError

from app.celery_app import celery_app
from app.database import get_db_session
from app.models.ad_campaign import AdCampaign
from app.models.integration import Integration

logger = logging.getLogger(__name__)
ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")
GRAPH_BASE = "https://graph.facebook.com/v19.0"

META_INSIGHTS_FIELDS = ",".join([
    "spend", "impressions", "clicks", "reach",
    "cpm", "cpc", "ctr", "cpp",
    "actions", "action_values",
    "cost_per_action_type",
])


def _decrypt(enc: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).decrypt(enc.encode()).decode()


def _encrypt(value: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).encrypt(value.encode()).decode()


def _safe_float(val, default=None):
    try:
        return round(float(val), 4) if val is not None else default
    except (TypeError, ValueError):
        return default


def _safe_int(val, default=None):
    try:
        return int(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _extract_action(actions: list, action_type: str, field="value") -> int | float | None:
    """Pull a specific action type from Meta's actions array."""
    for a in (actions or []):
        if a.get("action_type") == action_type:
            try:
                return float(a.get(field, 0))
            except (TypeError, ValueError):
                pass
    return None


def _maybe_refresh_token(intg: Integration, access_token: str) -> str:
    """
    Extend the token if it was created more than 50 days ago.
    Meta allows extending long-lived tokens before they expire.
    Returns the (possibly new) token.
    """
    if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:
        return access_token
    # Check age
    age = datetime.now(timezone.utc) - (intg.created_at or datetime.now(timezone.utc))
    if age.days < 50:
        return access_token

    try:
        r = httpx.get(
            f"{GRAPH_BASE}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": FACEBOOK_APP_ID,
                "client_secret": FACEBOOK_APP_SECRET,
                "fb_exchange_token": access_token,
            },
            timeout=15,
        )
        r.raise_for_status()
        new_token = r.json().get("access_token")
        if new_token and new_token != access_token:
            with get_db_session() as db:
                db_intg = db.get(Integration, intg.id)
                if db_intg:
                    db_intg.encrypted_key = _encrypt(new_token)
                    db.commit()
            logger.info(f"[Meta] Refreshed access token for integration {intg.id}")
            return new_token
    except Exception as exc:
        logger.warning(f"[Meta] Token refresh failed: {exc}")
    return access_token


# ── pull_meta_ads_history ──────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def pull_meta_ads_history(self, integration_id: str, since: date = None, until: date = None):
    """Pull Meta ad accounts → campaigns → daily insights."""
    logger.info(f"[Meta] Pulling data for integration={integration_id}")

    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if not intg:
            logger.error(f"[Meta] Integration {integration_id} not found")
            return
        access_token = _decrypt(intg.encrypted_key)
        brand_id = intg.brand_id
        # Maybe refresh
        access_token = _maybe_refresh_token(intg, access_token)

    # Date range
    if not until:
        until = date.today() - timedelta(days=1)
    if not since:
        since = until - timedelta(days=29)  # 30-day history on first pull

    total_campaigns = 0
    total_rows = 0

    # 1. List ad accounts
    try:
        r = httpx.get(
            f"{GRAPH_BASE}/me/adaccounts",
            params={"fields": "id,name,account_status", "access_token": access_token},
            timeout=30,
        )
        r.raise_for_status()
        accounts = r.json().get("data", [])
    except Exception as exc:
        logger.error(f"[Meta] Failed to fetch ad accounts: {exc}")
        raise self.retry(exc=exc)

    for account in accounts:
        account_id = account.get("id", "")
        if not account_id:
            continue
        rows = _sync_account(access_token, brand_id, account_id, since, until)
        total_rows += rows
        total_campaigns += 1

    # Update integration
    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if intg:
            intg.last_sync_at = datetime.now(timezone.utc)
            intg.status = "connected"
            intg.transaction_count = (intg.transaction_count or 0) + total_rows
            db.commit()

    logger.info(f"[Meta] Done integration={integration_id}: accounts={total_campaigns}, daily_rows={total_rows}")
    return {"accounts": total_campaigns, "daily_rows": total_rows}


def _sync_account(access_token: str, brand_id: str, account_id: str,
                  since: date, until: date) -> int:
    """Sync all campaigns + insights for one ad account."""
    total = 0

    # Fetch campaigns for account
    try:
        r = httpx.get(
            f"{GRAPH_BASE}/{account_id}/campaigns",
            params={
                "fields": "id,name,status,objective",
                "access_token": access_token,
                "limit": 200,
            },
            timeout=30,
        )
        r.raise_for_status()
        campaigns = r.json().get("data", [])
    except Exception as exc:
        logger.warning(f"[Meta] Failed campaigns for {account_id}: {exc}")
        return 0

    for campaign in campaigns:
        campaign_id = campaign.get("id", "")
        if not campaign_id:
            continue
        rows = _sync_campaign_insights(
            access_token, brand_id, account_id, campaign, since, until
        )
        total += rows

    return total


def _sync_campaign_insights(
    access_token: str, brand_id: str, account_id: str,
    campaign: dict, since: date, until: date
) -> int:
    """Pull daily insights for one campaign and upsert to ad_campaigns."""
    campaign_id = campaign.get("id", "")
    created = 0

    try:
        r = httpx.get(
            f"{GRAPH_BASE}/{campaign_id}/insights",
            params={
                "level": "campaign",
                "time_increment": 1,
                "fields": META_INSIGHTS_FIELDS,
                "time_range": json.dumps({
                    "since": since.strftime("%Y-%m-%d"),
                    "until": until.strftime("%Y-%m-%d"),
                }),
                "access_token": access_token,
                "limit": 100,
            },
            timeout=60,
        )
        r.raise_for_status()
        insights_data = r.json().get("data", [])
    except Exception as exc:
        logger.warning(f"[Meta] Insights failed for campaign {campaign_id}: {exc}")
        return 0

    for row in insights_data:
        try:
            row_date = datetime.strptime(row["date_start"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue

        spend = _safe_float(row.get("spend"), 0.0)
        impressions = _safe_int(row.get("impressions"), 0)
        clicks = _safe_int(row.get("clicks"), 0)
        reach = _safe_int(row.get("reach"))
        cpm = _safe_float(row.get("cpm"))
        cpc = _safe_float(row.get("cpc"))
        ctr = _safe_float(row.get("ctr"))
        cpp = _safe_float(row.get("cpp"))

        # Unpack actions
        actions = row.get("actions", [])
        action_values = row.get("action_values", [])
        purchases = _safe_int(_extract_action(actions, "purchase"))
        purchase_value = _safe_float(_extract_action(action_values, "purchase"))
        leads = _safe_int(_extract_action(actions, "lead"))
        add_to_cart = _safe_int(_extract_action(actions, "add_to_cart"))

        roas = None
        if purchase_value and spend and spend > 0:
            roas = round(purchase_value / spend, 4)

        with get_db_session() as db:
            existing = db.query(AdCampaign).filter_by(
                brand_id=brand_id, platform="meta",
                external_campaign_id=campaign_id, date=row_date,
            ).first()

            if existing:
                # Update in-place
                existing.spend = spend
                existing.impressions = impressions
                existing.clicks = clicks
                existing.reach = reach
                existing.cpm = cpm; existing.cpc = cpc
                existing.ctr = ctr; existing.cpp = cpp
                existing.purchases = purchases
                existing.purchase_value = purchase_value
                existing.roas = roas
                existing.leads = leads
                existing.add_to_cart = add_to_cart
                existing.raw_actions = json.dumps(actions)
                db.commit()
            else:
                ac = AdCampaign(
                    brand_id=brand_id, platform="meta",
                    external_account_id=account_id,
                    external_campaign_id=campaign_id,
                    campaign_name=campaign.get("name"),
                    campaign_status=campaign.get("status"),
                    objective=campaign.get("objective"),
                    date=row_date,
                    spend=spend, impressions=impressions, clicks=clicks, reach=reach,
                    cpm=cpm, cpc=cpc, ctr=ctr, cpp=cpp,
                    purchases=purchases, purchase_value=purchase_value, roas=roas,
                    leads=leads, add_to_cart=add_to_cart,
                    raw_actions=json.dumps(actions),
                )
                db.add(ac)
                try:
                    db.commit()
                    created += 1
                except IntegrityError:
                    db.rollback()

    return created


# ── Nightly sync ───────────────────────────────────────────────────────────────

@celery_app.task
def nightly_meta_sync():
    """Pull previous day's Meta ads data for all connected integrations. Runs 6AM WAT."""
    logger.info("[Meta] Nightly sync started")
    queued = 0
    yesterday = date.today() - timedelta(days=1)

    with get_db_session() as db:
        intgs = db.query(Integration).filter_by(type="meta_ads", status="connected").all()
        jobs = [i.id for i in intgs]

    for intg_id in jobs:
        pull_meta_ads_history.delay(intg_id, since=yesterday, until=yesterday)
        queued += 1

    logger.info(f"[Meta] Nightly sync queued {queued} jobs")
    return {"queued": queued}
