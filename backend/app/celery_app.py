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
    include=["app.tasks.paystack_tasks"],
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
)
