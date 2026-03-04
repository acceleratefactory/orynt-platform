"""
ORYNT — Celery Application
Background task queue using Redis as the broker and result backend.
"""

import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "orynt",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.tasks.paystack_tasks",
        "app.tasks.flutterwave_tasks",
        "app.tasks.monnify_tasks",
        "app.tasks.opay_tasks",
        "app.tasks.mono_tasks",
        "app.tasks.shopify_tasks",
        "app.tasks.woocommerce_tasks",
        "app.tasks.reseller_tasks",
        "app.tasks.preorder_tasks",
        "app.tasks.selar_tasks",
        "app.tasks.gumroad_tasks",
        "app.tasks.meta_ads_tasks",
        "app.tasks.google_ads_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Lagos",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    # Upstash Redis requires SSL
    broker_use_ssl={"ssl_cert_reqs": None} if REDIS_URL.startswith("rediss://") else None,
    redis_backend_use_ssl={"ssl_cert_reqs": None} if REDIS_URL.startswith("rediss://") else None,
    # Celery Beat schedules
    beat_schedule={
        "nightly-reseller-sync": {
            "task": "app.tasks.reseller_tasks.nightly_reseller_sync",
            "schedule": 60 * 60 * 24,
            "options": {"expires": 3600},
        },
        "nightly-preorder-sync": {
            "task": "app.tasks.preorder_tasks.nightly_preorder_sync",
            "schedule": 60 * 60 * 24,
            "options": {"expires": 3600},
        },
        "nightly-selar-sync": {
            "task": "app.tasks.selar_tasks.nightly_selar_sync",
            "schedule": 60 * 60 * 24,
            "options": {"expires": 3600},
        },
        "nightly-gumroad-sync": {
            "task": "app.tasks.gumroad_tasks.nightly_gumroad_sync",
            "schedule": 60 * 60 * 24,
            "options": {"expires": 3600},
        },
        "nightly-meta-sync": {
            "task": "app.tasks.meta_ads_tasks.nightly_meta_sync",
            "schedule": 60 * 60 * 24,
            "options": {"expires": 3600},
        },
        "nightly-google-ads-sync": {
            "task": "app.tasks.google_ads_tasks.nightly_google_ads_sync",
            "schedule": 60 * 60 * 24,
            "options": {"expires": 3600},
        },
    },
    beat_crontab_timezone="Africa/Lagos",
)

# Import crontab after app is configured
from celery.schedules import crontab  # noqa: E402
celery_app.conf.beat_schedule["nightly-reseller-sync"]["schedule"] = crontab(hour=2, minute=0)
celery_app.conf.beat_schedule["nightly-preorder-sync"]["schedule"] = crontab(hour=2, minute=0)
celery_app.conf.beat_schedule["nightly-selar-sync"]["schedule"] = crontab(hour=2, minute=0)
celery_app.conf.beat_schedule["nightly-gumroad-sync"]["schedule"] = crontab(hour=2, minute=0)
celery_app.conf.beat_schedule["nightly-meta-sync"]["schedule"] = crontab(hour=6, minute=0)  # 6AM WAT
celery_app.conf.beat_schedule["nightly-google-ads-sync"]["schedule"] = crontab(hour=6, minute=30)  # 6:30AM WAT
