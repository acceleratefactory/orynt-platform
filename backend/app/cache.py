"""
ORYNT — Redis Cache Connection
Connects to Upstash Redis (or any Redis instance) via REDIS_URL env var.
Used for caching SKU scores, customer segments, and weekly digests.
"""

import json
import os
from typing import Any

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


def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    """
    Write a value to Redis with an expiry.

    - key:         Redis key (e.g. "orynt:sku:score:123")
    - value:       Any JSON-serialisable value
    - ttl_seconds: Time-to-live in seconds (default 5 minutes)

    Returns True on success, False on error.
    """
    try:
        r = get_redis()
        serialised = json.dumps(value) if not isinstance(value, str) else value
        r.setex(key, ttl_seconds, serialised)
        return True
    except (RedisError, ValueError, Exception):
        return False


def cache_get(key: str) -> Any | None:
    """
    Read a value from Redis by key.

    Returns the deserialised value, or None if the key does not exist
    or an error occurs.
    """
    try:
        r = get_redis()
        raw = r.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return raw  # Return raw string if not valid JSON
    except (RedisError, ValueError, Exception):
        return None


def check_cache_connection() -> bool:
    """
    Health check — writes a test key then reads it back.
    Returns True only if both write AND read succeed (full round-trip).
    """
    try:
        wrote = cache_set("orynt:health:test", "ok", ttl_seconds=60)
        if not wrote:
            return False
        result = cache_get("orynt:health:test")
        return result == "ok"
    except (RedisError, ValueError, Exception):
        return False
