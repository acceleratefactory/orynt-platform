"""
ORYNT — Sync Scheduler Tasks

sync_all_integrations  — 2:00 AM WAT
  Dispatches each connected integration to its appropriate pull task.
  Logs a SyncError on failure.

check_stale_integrations — 3:30 AM WAT
  Marks integrations with last_sync_at > 48h old as 'error'.
  Logs to sync_errors table.
  Placeholder: logs stale integrations (WhatsApp alert queued in Sprint 3).

DISPATCHER maps integration type → the nightly sync task that handles it.
This is the single source of truth for "what runs what".
"""

import logging
import traceback
from datetime import datetime, timezone, timedelta

from app.celery_app import celery_app
from app.database import get_db_session
from app.models.integration import Integration
from app.models.sync_error import SyncError

logger = logging.getLogger(__name__)

# ── Dispatcher map: integration type → celery task path ───────────────────────
#
# Each entry calls the individual nightly sync task for that platform.
# We import lazily inside the task to avoid circular imports.
#
INTEGRATION_TASK_MAP = {
    # Payment gateways
    "paystack":          "app.tasks.paystack_tasks.pull_paystack_transactions",
    "flutterwave":       "app.tasks.flutterwave_tasks.pull_flutterwave_transactions",
    "monnify":           "app.tasks.monnify_tasks.pull_monnify_transactions",
    "opay":              "app.tasks.opay_tasks.pull_opay_transactions",
    # Open banking
    "mono":              "app.tasks.mono_tasks.pull_mono_transactions",
    # E-commerce
    "shopify":           "app.tasks.shopify_tasks.pull_shopify_orders",
    "woocommerce":       "app.tasks.woocommerce_tasks.pull_woocommerce_orders",
    "reseller_platform": "app.tasks.reseller_tasks.pull_reseller_orders",
    "preorder_platform": "app.tasks.preorder_tasks.pull_preorder_orders",
    "selar":             "app.tasks.selar_tasks.pull_selar_data",
    "gumroad":           "app.tasks.gumroad_tasks.pull_gumroad_data",
    # Ads
    "meta_ads":          "app.tasks.meta_ads_tasks.pull_meta_ads_history",
    "google_ads":        "app.tasks.google_ads_tasks.pull_google_ads_history",
    # Social
    "social_media":      "app.tasks.social_media_tasks.pull_social_media_data",
}


def _log_error(integration_id: str | None, brand_id: str | None,
               error_type: str, message: str, detail: str = None):
    """Write a row to sync_errors."""
    try:
        with get_db_session() as db:
            err = SyncError(
                integration_id=integration_id,
                brand_id=brand_id,
                error_type=error_type,
                error_message=message,
                detail=detail,
            )
            db.add(err)
            db.commit()
    except Exception as e:
        logger.error(f"[Sync] Could not write SyncError: {e}")


def _get_task(dotted_path: str):
    """Import a Celery task by dotted module.task_name string."""
    module_path, task_name = dotted_path.rsplit(".", 1)
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, task_name)


# ── sync_all_integrations ──────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_scheduler.sync_all_integrations")
def sync_all_integrations():
    """
    Dispatches every connected integration to its pull task.
    Runs at 2:00 AM WAT.
    This is the master scheduler — individual nightly tasks also run
    at staggered times (2-7 AM), so this handles any that were missed.
    """
    logger.info("[SyncAll] sync_all_integrations started")
    started_at = datetime.now(timezone.utc)
    total = 0
    errors = 0

    with get_db_session() as db:
        integrations = (
            db.query(Integration)
            .filter(Integration.status == "connected")
            .all()
        )
        # Snapshot: list of (id, brand_id, type)
        jobs = [(i.id, i.brand_id, i.type) for i in integrations]

    logger.info(f"[SyncAll] Dispatching {len(jobs)} connected integrations")

    for intg_id, brand_id, intg_type in jobs:
        task_path = INTEGRATION_TASK_MAP.get(intg_type)
        if not task_path:
            logger.debug(f"[SyncAll] No task for type={intg_type}, skipping")
            continue
        try:
            task = _get_task(task_path)
            task.delay(intg_id)
            total += 1
            logger.debug(f"[SyncAll] Queued {intg_type} for integration {intg_id}")
        except Exception as exc:
            errors += 1
            tb = traceback.format_exc()
            logger.error(f"[SyncAll] Failed to queue {intg_type}/{intg_id}: {exc}")
            _log_error(intg_id, brand_id, "sync_failure",
                       f"Failed to queue task for {intg_type}: {exc}", tb)

    duration = (datetime.now(timezone.utc) - started_at).total_seconds()
    logger.info(f"[SyncAll] Done: queued={total}, errors={errors}, duration={duration:.1f}s")
    return {"queued": total, "errors": errors, "duration_seconds": duration}


# ── check_stale_integrations ───────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_scheduler.check_stale_integrations")
def check_stale_integrations():
    """
    Find integrations where last_sync_at is > 48 hours old.
    Mark them status='error' and log to sync_errors.
    Placeholder: Sprint 3 will send WhatsApp/email alerts.
    Runs at 3:30 AM WAT.
    """
    logger.info("[StaleCheck] check_stale_integrations started")
    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    stale_count = 0
    skipped_count = 0

    with get_db_session() as db:
        stale_integrations = (
            db.query(Integration)
            .filter(
                Integration.status == "connected",
                Integration.last_sync_at < stale_cutoff,
            )
            .all()
        )
        stale_data = [
            {"id": i.id, "brand_id": i.brand_id, "type": i.type,
             "last_sync_at": i.last_sync_at.isoformat() if i.last_sync_at else None}
            for i in stale_integrations
        ]

    logger.info(f"[StaleCheck] Found {len(stale_data)} stale integrations")

    for item in stale_data:
        intg_id = item["id"]
        brand_id = item["brand_id"]
        intg_type = item["type"]
        last_sync = item["last_sync_at"]

        logger.warning(
            f"[StaleCheck] STALE: type={intg_type} integration={intg_id} "
            f"brand={brand_id} last_sync_at={last_sync}"
        )

        # Mark as error
        try:
            with get_db_session() as db:
                intg = db.get(Integration, intg_id)
                if intg and intg.status == "connected":
                    intg.status = "error"
                    db.commit()
                    stale_count += 1
                else:
                    skipped_count += 1
        except Exception as exc:
            logger.error(f"[StaleCheck] Could not update status for {intg_id}: {exc}")

        # Log to sync_errors
        _log_error(
            intg_id, brand_id,
            "stale_integration",
            f"{intg_type} integration has not synced since {last_sync} (>48h ago)",
            f"Stale cutoff: {stale_cutoff.isoformat()}",
        )

        # TODO Sprint 3: Queue WhatsApp/email notification to brand owner
        # notify_brand_owner.delay(brand_id, f"Your {intg_type} integration is disconnected.")

    logger.info(
        f"[StaleCheck] Done: marked_error={stale_count}, skipped={skipped_count}"
    )
    return {"stale_found": len(stale_data), "marked_error": stale_count, "skipped": skipped_count}
