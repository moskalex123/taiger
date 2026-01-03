import os
import logging
from typing import Optional, List

import redis.asyncio as redis

# Redis configuration from environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

logger = logging.getLogger(__name__)

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None
_redis_url_in_use: Optional[str] = None


def _build_candidate_urls() -> List[str]:
    urls: List[str] = [REDIS_URL]

    # Additional hosts from environment (comma separated)
    extra_hosts = os.getenv("REDIS_ADDITIONAL_HOSTS")
    if extra_hosts:
        for host in extra_hosts.split(','):
            host = host.strip()
            if host:
                urls.append(f"redis://{host}:{REDIS_PORT}/{REDIS_DB}")

    # Append local fallbacks if not already primary
    local_hosts = ["127.0.0.1", "localhost"]
    for host in local_hosts:
        candidate = f"redis://{host}:{REDIS_PORT}/{REDIS_DB}"
        if candidate not in urls:
            urls.append(candidate)

    return urls


async def _create_client(url: str) -> redis.Redis:
    client = redis.from_url(
        url,
        encoding="utf-8",
        decode_responses=True,
        retry_on_timeout=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )

    try:
        await client.ping()
        logger.info(f"Connected to Redis at {url}")
        return client
    except Exception as exc:
        await client.close()
        raise exc

async def get_redis_client() -> redis.Redis:
    """Get or create Redis client instance"""
    global _redis_client
    global _redis_url_in_use

    if _redis_client is None:
        errors = []
        for url in _build_candidate_urls():
            try:
                _redis_client = await _create_client(url)
                _redis_url_in_use = url
                break
            except Exception as exc:
                errors.append(f"{url}: {exc}")
                logger.warning(f"Redis connection attempt failed for {url}: {exc}")
                continue

        if _redis_client is None:
            error_message = " | ".join(errors) if errors else "No Redis URLs configured"
            logger.error(f"All Redis connection attempts failed: {error_message}")
            raise ConnectionError(f"Unable to connect to Redis. Attempts: {error_message}")

    return _redis_client

async def close_redis_client():
    """Close Redis client connection"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None

async def redis_ping() -> bool:
    """Test Redis connection"""
    try:
        redis_client = await get_redis_client()
        await redis_client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False

async def redis_set(key: str, value: str, expire: Optional[int] = None) -> bool:
    """Set key-value pair in Redis with optional expiration"""
    try:
        redis_client = await get_redis_client()
        await redis_client.set(key, value, ex=expire)
        return True
    except Exception as e:
        logger.error(f"Redis SET failed: {e}")
        return False

async def redis_get(key: str) -> Optional[str]:
    """Get value by key from Redis"""
    try:
        redis_client = await get_redis_client()
        return await redis_client.get(key)
    except Exception as e:
        logger.error(f"Redis GET failed: {e}")
        return None

async def redis_delete(key: str) -> bool:
    """Delete key from Redis"""
    try:
        redis_client = await get_redis_client()
        await redis_client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Redis DELETE failed: {e}")
        return False

async def redis_exists(key: str) -> bool:
    """Check if key exists in Redis"""
    try:
        redis_client = await get_redis_client()
        return bool(await redis_client.exists(key))
    except Exception as e:
        logger.error(f"Redis EXISTS failed: {e}")
        return False