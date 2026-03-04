"""
ORYNT — Social Media Celery Tasks

Pulls Instagram post metrics and Facebook Page insights.
Reuses the Meta access token from the 'meta_ads' integration if connected.
Falls back to 'social_media' integration type for standalone social-only connections.

Tasks:
  pull_social_media_data(integration_id)
    - Identifies IG Business Account and Facebook Page IDs
    - Instagram: GET /v19.0/{ig_user_id}/media → pulls post performance
    - Facebook:  GET /v19.0/{page_id}/insights → pulls page-level metrics
    - Stores in social_metrics table

  nightly_social_sync() — 7:00 AM WAT
    - Runs for all brands that have meta_ads or social_media integration connected
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
from app.models.social_metric import SocialMetric
from app.models.integration import Integration

logger = logging.getLogger(__name__)

ENCRYPTION_KEY = os.getenv("PAYSTACK_ENCRYPTION_KEY", "")
GRAPH_BASE = "https://graph.facebook.com/v19.0"

# Instagram post fields we want to pull
IG_MEDIA_FIELDS = "id,caption,media_type,timestamp,like_count,comments_count,permalink,thumbnail_url"
IG_INSIGHTS_FIELDS = "impressions,reach"  # per-post insights require separate calls

# Facebook Page insight metrics (period=day)
FB_PAGE_METRICS = "page_impressions,page_reach,page_engaged_users,page_views_total,page_fans"


def _decrypt(v: str) -> str:
    return Fernet(ENCRYPTION_KEY.encode()).decrypt(v.encode()).decode()


def _safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _graph_get(path: str, token: str, params: dict = None) -> dict:
    """Simple Graph API GET helper."""
    p = {"access_token": token, **(params or {})}
    r = httpx.get(f"{GRAPH_BASE}/{path}", params=p, timeout=30)
    r.raise_for_status()
    return r.json()


def _upsert_metric(db, brand_id: str, platform: str, metric_type: str,
                   value: float, metric_date: date,
                   external_id: str = None, label: str = None, meta: dict = None):
    """Insert or ignore a social metric row. Unique on (brand_id, platform, metric_type, external_id, date)."""
    existing = (
        db.query(SocialMetric)
        .filter_by(
            brand_id=brand_id, platform=platform, metric_type=metric_type,
            external_id=external_id or "", date=metric_date,
        )
        .first()
    )
    if existing:
        existing.metric_value = value
        if meta:
            existing.metadata_json = json.dumps(meta)
    else:
        sm = SocialMetric(
            brand_id=brand_id, platform=platform,
            metric_type=metric_type, metric_value=value,
            date=metric_date, external_id=external_id or "",
            label=label, metadata_json=json.dumps(meta) if meta else None,
        )
        db.add(sm)


# ── Instagram data pull ────────────────────────────────────────────────────────

def _pull_instagram(access_token: str, brand_id: str, ig_user_id: str,
                    since: date, until: date) -> int:
    """Pull Instagram media posts and their metrics."""
    saved = 0

    # Fetch recent media (last 50 posts — Graph API doesn't paginate by date natively)
    try:
        result = _graph_get(
            f"{ig_user_id}/media",
            access_token,
            {"fields": IG_MEDIA_FIELDS, "limit": 50},
        )
        media_items = result.get("data", [])
    except Exception as exc:
        logger.warning(f"[Social] IG media fetch failed for {ig_user_id}: {exc}")
        return 0

    with get_db_session() as db:
        for post in media_items:
            post_id = post.get("id", "")
            ts_str = post.get("timestamp", "")
            if not post_id or not ts_str:
                continue

            try:
                post_date = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).date()
            except ValueError:
                continue

            if not (since <= post_date <= until):
                continue

            caption = (post.get("caption") or "")[:120]
            meta = {
                "media_type": post.get("media_type"),
                "permalink": post.get("permalink"),
                "thumbnail_url": post.get("thumbnail_url"),
            }

            # Post-level metrics
            for metric_type, value in [
                ("post_likes", _safe_float(post.get("like_count"))),
                ("post_comments", _safe_float(post.get("comments_count"))),
            ]:
                _upsert_metric(db, brand_id, "instagram", metric_type,
                               value, post_date, post_id, caption, meta)
                saved += 1

            # Per-post insights: impressions + reach
            try:
                ins = _graph_get(
                    f"{post_id}/insights",
                    access_token,
                    {"metric": IG_INSIGHTS_FIELDS},
                )
                for insight in ins.get("data", []):
                    m_name = insight.get("name")  # 'impressions' or 'reach'
                    m_val = _safe_float(insight.get("values", [{}])[0].get("value"))
                    _upsert_metric(db, brand_id, "instagram",
                                   f"post_{m_name}", m_val, post_date, post_id, caption, meta)
                    saved += 1
            except Exception:
                pass  # Insights not always available (e.g. old posts)

        db.commit()
    return saved


# ── Facebook Page data pull ────────────────────────────────────────────────────

def _pull_facebook_page(access_token: str, brand_id: str, page_id: str,
                        since: date, until: date) -> int:
    """Pull daily Facebook Page insights."""
    saved = 0

    try:
        result = _graph_get(
            f"{page_id}/insights",
            access_token,
            {
                "metric": FB_PAGE_METRICS,
                "period": "day",
                "since": since.strftime("%Y-%m-%d"),
                "until": (until + timedelta(days=1)).strftime("%Y-%m-%d"),
            },
        )
        metrics_data = result.get("data", [])
    except Exception as exc:
        logger.warning(f"[Social] FB page insights failed for {page_id}: {exc}")
        return 0

    with get_db_session() as db:
        for metric in metrics_data:
            m_name = metric.get("name", "")
            for value_item in metric.get("values", []):
                try:
                    end_time = datetime.fromisoformat(
                        value_item["end_time"].replace("Z", "+00:00")
                    ).date()
                except (KeyError, ValueError):
                    continue
                val = _safe_float(value_item.get("value"))
                _upsert_metric(db, brand_id, "facebook",
                               m_name, val, end_time, page_id)
                saved += 1
        db.commit()
    return saved


# ── Resolve IG user ID and Page ID from token ─────────────────────────────────

def _get_ig_and_page_ids(access_token: str) -> tuple[str | None, str | None]:
    """Find the Instagram Business Account ID and Facebook Page ID for this token."""
    ig_user_id = None
    page_id = None

    try:
        # Get Facebook Pages this token has access to
        pages = _graph_get("me/accounts", access_token, {"fields": "id,name,instagram_business_account"})
        for page in pages.get("data", []):
            if not page_id:
                page_id = page.get("id")
            ib = page.get("instagram_business_account")
            if ib and not ig_user_id:
                ig_user_id = ib.get("id")
    except Exception as exc:
        logger.warning(f"[Social] Could not resolve IG/page IDs: {exc}")

    return ig_user_id, page_id


# ── Main task ─────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def pull_social_media_data(self, integration_id: str, days_back: int = 30):
    """
    Pull Instagram post metrics and Facebook Page insights for a brand.
    integration_id can be a meta_ads integration or social_media integration.
    """
    logger.info(f"[Social] Pulling for integration={integration_id}, days_back={days_back}")

    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if not intg:
            logger.error(f"[Social] Integration {integration_id} not found")
            return
        access_token = _decrypt(intg.encrypted_key)
        brand_id = intg.brand_id

    until = date.today() - timedelta(days=1)
    since = until - timedelta(days=days_back)

    # Resolve IG user ID and Facebook Page ID
    ig_user_id, page_id = _get_ig_and_page_ids(access_token)
    logger.info(f"[Social] ig_user_id={ig_user_id}, page_id={page_id}")

    total = 0

    if ig_user_id:
        saved = _pull_instagram(access_token, brand_id, ig_user_id, since, until)
        logger.info(f"[Social] Instagram: saved {saved} metric rows")
        total += saved
    else:
        logger.warning(f"[Social] No Instagram Business Account found for integration {integration_id}")

    if page_id:
        saved = _pull_facebook_page(access_token, brand_id, page_id, since, until)
        logger.info(f"[Social] Facebook Page: saved {saved} metric rows")
        total += saved
    else:
        logger.warning(f"[Social] No Facebook Page found for integration {integration_id}")

    # Update integration
    with get_db_session() as db:
        intg = db.get(Integration, integration_id)
        if intg:
            intg.last_sync_at = datetime.now(timezone.utc)
            intg.transaction_count = (intg.transaction_count or 0) + total
            db.commit()

    logger.info(f"[Social] Done integration={integration_id}: total_rows={total}")
    return {"ig_user_id": ig_user_id, "page_id": page_id, "metric_rows": total}


# ── Nightly sync ───────────────────────────────────────────────────────────────

@celery_app.task
def nightly_social_sync():
    """
    Pull yesterday's social metrics for all brands with meta_ads or social_media integration.
    Runs at 7:00 AM WAT.
    """
    logger.info("[Social] Nightly sync started")
    queued = 0

    with get_db_session() as db:
        # Reuse meta_ads token if connected — it has the right scopes
        intgs = db.query(Integration).filter(
            Integration.type.in_(["meta_ads", "social_media"]),
            Integration.status == "connected",
        ).all()
        jobs = [i.id for i in intgs]

    for intg_id in jobs:
        pull_social_media_data.delay(intg_id, days_back=1)
        queued += 1

    logger.info(f"[Social] Nightly sync queued {queued} jobs")
    return {"queued": queued}
