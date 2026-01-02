"""In-memory cache module for dashboard data.

Provides simple TTL-based caching for expensive computations.
Since transaction data is static (no new imports), cached results
remain valid indefinitely or until server restart.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Optional
from functools import wraps

# Global cache storage
_cache: dict[str, dict] = {}

# Default TTL: 1 hour (can be set to None for permanent cache)
DEFAULT_TTL_SECONDS = 3600


def _make_cache_key(prefix: str, *args, **kwargs) -> str:
    """Create a unique cache key from function arguments."""
    key_parts = [prefix]
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return ":".join(key_parts)


def get_cached(key: str) -> Optional[Any]:
    """Get a value from cache if not expired."""
    if key not in _cache:
        return None
    
    entry = _cache[key]
    expires_at = entry.get("expires_at")
    
    # Check expiration (None = never expires)
    if expires_at and datetime.utcnow() > expires_at:
        del _cache[key]
        return None
    
    return entry["value"]


def set_cached(key: str, value: Any, ttl_seconds: Optional[int] = DEFAULT_TTL_SECONDS) -> None:
    """Store a value in cache with optional TTL."""
    expires_at = None
    if ttl_seconds:
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    
    _cache[key] = {
        "value": value,
        "expires_at": expires_at,
        "created_at": datetime.utcnow(),
    }


def clear_cache(prefix: Optional[str] = None) -> int:
    """Clear cache entries. If prefix given, only clear matching keys."""
    global _cache
    
    if prefix is None:
        count = len(_cache)
        _cache = {}
        return count
    
    keys_to_delete = [k for k in _cache if k.startswith(prefix)]
    for key in keys_to_delete:
        del _cache[key]
    return len(keys_to_delete)


def cached(prefix: str, ttl_seconds: Optional[int] = DEFAULT_TTL_SECONDS):
    """
    Decorator for caching async function results.
    
    Automatically excludes db session objects from cache keys since
    each request creates a new session with different memory address.
    
    Usage:
        @cached("kpi_metrics", ttl_seconds=3600)
        async def compute_kpi_metrics(db, start_date, end_date):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip first arg (usually db session) in cache key
            cache_args = args[1:] if args else ()
            
            # Filter out db session from kwargs (it has unique memory address per request)
            cache_kwargs = {k: v for k, v in kwargs.items() if k != "db"}
            
            key = _make_cache_key(prefix, *cache_args, **cache_kwargs)
            
            # Check cache
            cached_value = get_cached(key)
            if cached_value is not None:
                return cached_value
            
            # Compute and cache
            result = await func(*args, **kwargs)
            set_cached(key, result, ttl_seconds)
            return result
        
        return wrapper
    return decorator
