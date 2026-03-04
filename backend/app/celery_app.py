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
        # Nightly reseller platform incremental sync at 02:00 WAT (01:00 UTC)
        "nightly-reseller-sync": {
            "task": "app.tasks.reseller_tasks.nightly_reseller_sync",
            "schedule": 60 * 60 * 24,  # daily — Beat worker picks exact time via crontab below
            "options": {"expires": 3600},
        },
    },
    beat_crontab_timezone="Africa/Lagos",
)

# Import crontab after app is configured
from celery.schedules import crontab  # noqa: E402
celery_app.conf.beat_schedule["nightly-reseller-sync"]["schedule"] = crontab(hour=2, minute=0)
