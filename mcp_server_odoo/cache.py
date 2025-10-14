"""Caching layer for Odoo data."""

import json
from typing import Optional, Any
import structlog

logger = structlog.get_logger()


class CacheManager:
    """Manages caching with optional Redis backend."""
    
    def __init__(self, redis_client=None, ttl: int = 300):
        self.redis_client = redis_client
        self.ttl = ttl
        self.local_cache = {}
    
    def _make_key(self, prefix: str, *args) -> str:
        """Create a cache key."""
        parts = [prefix] + [str(arg) for arg in args]
        return ":".join(parts)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if self.redis_client:
                value = await self.redis_client.get(key)
                if value:
                    logger.debug("cache_hit_redis", key=key)
                    return json.loads(value)
            else:
                if key in self.local_cache:
                    logger.debug("cache_hit_local", key=key)
                    return self.local_cache[key]
            
            logger.debug("cache_miss", key=key)
            return None
        except Exception as e:
            logger.error("cache_get_error", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        try:
            ttl = ttl or self.ttl
            
            if self.redis_client:
                serialized = json.dumps(value)
                await self.redis_client.setex(key, ttl, serialized)
                logger.debug("cache_set_redis", key=key, ttl=ttl)
            else:
                self.local_cache[key] = value
                logger.debug("cache_set_local", key=key)
            
            return True
        except Exception as e:
            logger.error("cache_set_error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if self.redis_client:
                await self.redis_client.delete(key)
            else:
                self.local_cache.pop(key, None)
            
            logger.debug("cache_delete", key=key)
            return True
        except Exception as e:
            logger.error("cache_delete_error", key=key, error=str(e))
            return False
    
    async def clear(self) -> bool:
        """Clear all cache."""
        try:
            if self.redis_client:
                await self.redis_client.flushdb()
            else:
                self.local_cache.clear()
            
            logger.info("cache_cleared")
            return True
        except Exception as e:
            logger.error("cache_clear_error", error=str(e))
            return False
