"""
ORYNT — Redis Cache Connection
Connects to Upstash Redis (or any Redis instance) via REDIS_URL env var.
Used for caching SKU scores, customer segments, and weekly digests.
"""

import os
import redis as redis_client
from dotenv import load_dotenv
from redis.exceptions import RedisError

load_dotenv()  # Ensures .env is loaded in every subprocess context

REDIS_URL = os.getenv("REDIS_URL")

_redis: redis_client.Redis | None = None


def get_redis() -> redis_client.Redis:
    """Return a Redis client, initialising it on first call."""
    global _redis
    if _redis is None:
        if not REDIS_URL:
            raise ValueError(
                "REDIS_URL environment variable is not set. "
                "Copy backend/.env.example to backend/.env and fill in the value."
            )
        _redis = redis_client.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis


def check_cache_connection() -> bool:
    """Health check — returns True if Redis is reachable, False otherwise."""
    try:
        r = get_redis()
        r.ping()
        return True
    except (RedisError, ValueError, Exception):
        return False
