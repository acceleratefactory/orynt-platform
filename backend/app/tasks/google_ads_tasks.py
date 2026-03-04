"""
ORYNT — Google Ads Celery Tasks

pull_google_ads_history: Full or incremental sync using GAQL.
  - Exchanges refresh_token → access_token
  - Queries campaign metrics via Google Ads Query Language (GAQL)
  - Maps to ad_campaigns table (platform = 'google')
  - cost_micros → NGN (divide by 1,000,000)
  - ROAS = conversions_value / (cost_micros / 1_000_000)

nightly_google_ads_sync: Previous day's data, 6:30 AM WAT.
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

ENCRYPTION_KEY            = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
GOOGLE_CLIENT_ID          = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET      = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")

GOOGLE_TOKEN_URL   = "https://oauth2.googleapis.com/token"
GOOGLE_ADS_API_URL = "https://googleads.googleapis.com/v17"

# GAQL query — pulls daily campaign metrics
GAQL_QUERY = """
SELECT
  campaign.id,
  campaign.name,
  campaign.status,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.average_cpc,
  metrics.ctr,
  metrics.conversions,
  metrics.conversions_value,
  segments.date
FROM campaign
WHERE segments.date DURING {date_range}
  AND campaign.status != 'REMOVED'
ORDER BY segments.date DESC
"""


def _decrypt(v: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).decrypt(v.encode()).decode()


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


def _get_access_token(refresh_token: str) -> str:
    """Exchange Google refresh_token for a short-lived access_token."""
    r = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _gaql_search(access_token: str, customer_id: str, query: str) -> list[dict]:
    """Execute a GAQL search query against the Google Ads API and return all rows."""
    url = f"{GOOGLE_ADS_API_URL}/customers/{customer_id}/googleAds:searchStream"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": GOOGLE_ADS_DEVELOPER_TOKEN,
        "login-customer-id": customer_id,
        "Content-Type": "application/json",
    }
    payload = {"query": query.strip()}
    rows = []

    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        # searchStream returns newline-delimited JSON objects
        for line in r.text.strip().splitlines():
            if not line.strip():
                continue
            try:
                batch = json.loads(line)
                rows.extend(batch.get("results", []))
            except json.JSONDecodeError:
                continue
    except httpx.HTTPStatusError as exc:
        logger.error(
            f"[Google Ads] GAQL HTTP {exc.response.status_code}: {exc.response.text[:300]}"
        )
        raise
    except Exception as exc:
        logger.error(f"[Google Ads] GAQL error: {exc}")
        raise

    return rows


# ── pull_google_ads_history ────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=180)
def pull_google_ads_history(self, integration_id: str, date_range: str = None):
    """
    Pull Google Ads campaign metrics for a brand.
    date_range: GAQL date range literal, e.g. 'LAST_90_DAYS', 'YESTERDAY', 'LAST_30_DAYS'
    Default: LAST_90_DAYS on first pull. Nightly uses 'YESTERDAY'.
    """
    if date_range is None:
        date_range = "LAST_90_DAYS"  # ~12 weeks on first pull; use LAST_365_DAYS for full 12 months

    logger.info(f"[Google Ads] Pulling {date_range} for integration={integration_id}")

    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if not intg:
            logger.error(f"[Google Ads] Integration {integration_id} not found")
            return
        combined = _decrypt(intg.encrypted_key)
        brand_id = intg.brand_id

    # Split combined "refresh_token::customer_id"
    if "::" not in combined:
        logger.error(f"[Google Ads] Missing customer_id for integration {integration_id}")
        return
    refresh_token, customer_id = combined.split("::", 1)

    if not GOOGLE_ADS_DEVELOPER_TOKEN:
        logger.error("[Google Ads] GOOGLE_ADS_DEVELOPER_TOKEN is not set — cannot call API")
        return

    # Get access token
    try:
        access_token = _get_access_token(refresh_token)
    except Exception as exc:
        logger.error(f"[Google Ads] Token refresh failed: {exc}")
        raise self.retry(exc=exc)

    # Execute GAQL query
    query = GAQL_QUERY.format(date_range=date_range)
    try:
        rows = _gaql_search(access_token, customer_id, query)
    except Exception as exc:
        raise self.retry(exc=exc)

    upserted = 0
    for row in rows:
        try:
            campaign   = row.get("campaign", {})
            metrics    = row.get("metrics", {})
            segments   = row.get("segments", {})

            campaign_id   = str(campaign.get("id", ""))
            campaign_name = campaign.get("name")
            campaign_status = campaign.get("status")
            row_date_str  = segments.get("date", "")

            if not campaign_id or not row_date_str:
                continue

            try:
                row_date = datetime.strptime(row_date_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            # cost_micros → NGN (already in local currency from Google Ads)
            cost_micros   = _safe_float(metrics.get("costMicros"), 0)
            spend         = round(cost_micros / 1_000_000, 2)
            impressions   = _safe_int(metrics.get("impressions"), 0)
            clicks        = _safe_int(metrics.get("clicks"), 0)
            avg_cpc_micros = _safe_float(metrics.get("averageCpc"), 0)
            cpc           = round(avg_cpc_micros / 1_000_000, 4) if avg_cpc_micros else None
            ctr           = _safe_float(metrics.get("ctr"))
            conversions   = _safe_float(metrics.get("conversions"), 0)
            conv_value    = _safe_float(metrics.get("conversionsValue"), 0)

            roas = None
            if conv_value and spend and spend > 0:
                roas = round(conv_value / spend, 4)

            # cpm from spend/impressions if available
            cpm = round((spend / impressions) * 1000, 4) if impressions and spend else None

            with get_db_session() as db:
                existing = db.query(AdCampaign).filter_by(
                    brand_id=brand_id, platform="google",
                    external_campaign_id=campaign_id, date=row_date,
                ).first()

                if existing:
                    existing.spend = spend
                    existing.impressions = impressions
                    existing.clicks = clicks
                    existing.cpm = cpm
                    existing.cpc = cpc
                    existing.ctr = ctr
                    existing.purchases = _safe_int(conversions)
                    existing.purchase_value = conv_value
                    existing.roas = roas
                    existing.campaign_status = campaign_status
                    db.commit()
                else:
                    ac = AdCampaign(
                        brand_id=brand_id,
                        platform="google",
                        external_account_id=customer_id,
                        external_campaign_id=campaign_id,
                        campaign_name=campaign_name,
                        campaign_status=campaign_status,
                        date=row_date,
                        spend=spend,
                        impressions=impressions,
                        clicks=clicks,
                        cpm=cpm,
                        cpc=cpc,
                        ctr=ctr,
                        purchases=_safe_int(conversions),
                        purchase_value=conv_value,
                        roas=roas,
                    )
                    db.add(ac)
                    try:
                        db.commit()
                        upserted += 1
                    except IntegrityError:
                        db.rollback()

        except Exception as exc:
            logger.warning(f"[Google Ads] Row error: {exc}")
            continue

    # Update integration stats
    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if intg:
            intg.last_sync_at = datetime.now(timezone.utc)
            intg.status = "connected"
            intg.transaction_count = (intg.transaction_count or 0) + upserted
            db.commit()

    logger.info(f"[Google Ads] Done integration={integration_id}: rows={len(rows)}, new={upserted}")
    return {"rows_fetched": len(rows), "new_rows": upserted}


# ── Nightly daily sync ────────────────────────────────────────────────────────

@celery_app.task
def nightly_google_ads_sync():
    """Pull yesterday's Google Ads data. Runs at 6:30 AM WAT."""
    logger.info("[Google Ads] Nightly sync started")
    queued = 0

    with get_db_session() as db:
        intgs = db.query(Integration).filter_by(type="google_ads", status="connected").all()
        jobs = [i.id for i in intgs]

    for intg_id in jobs:
        pull_google_ads_history.delay(intg_id, date_range="YESTERDAY")
        queued += 1

    logger.info(f"[Google Ads] Nightly sync queued {queued} jobs")
    return {"queued": queued}
