"""
================================================================================
REDIS ASYNC CLIENT POOL & UTILITY SERVICES (redis_client.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module sets up an asynchronous Redis client pool using `redis.asyncio` to power
the Pub/Sub backplane for real-time WebSocket messaging and events routing.
"""

import os
import redis.asyncio as redis
from dotenv import load_dotenv
from utils.logger import get_department_logger

load_dotenv()
logger = get_department_logger("redis")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Central connection pool initialization
try:
    redis_pool = redis.ConnectionPool.from_url(
        REDIS_URL, 
        max_connections=50, 
        decode_responses=True
    )
    logger.info(f"Initialized Redis connection pool targeting {REDIS_URL}")
except Exception as e:
    logger.critical(f"Failed to initialize Redis pool: {e}", exc_info=True)
    raise RuntimeError(f"Failed to initialize Redis pool: {e}")


def get_redis_client() -> redis.Redis:
    """
    Returns an async Redis client from the shared connection pool.
    """
    return redis.Redis(connection_pool=redis_pool)
