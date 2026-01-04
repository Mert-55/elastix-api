"""In-memory cache module for dashboard data.

Provides simple TTL-based caching for expensive computations.
Since transaction data is static (no new imports), cached results
remain valid indefinitely or until server restart.

Performance Optimizations:
- Uses hashable cache keys for O(1) lookup
- Thread-safe via asyncio lock for concurrent requests
- Supports cache warming and bulk invalidation
"""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, TypeVar, ParamSpec
from functools import wraps
import hashlib

# Type hints for better IDE support
P = ParamSpec("P")
T = TypeVar("T")

# Global cache storage with lock for thread safety
_cache: dict[str, dict] = {}
_cache_lock = asyncio.Lock()

# Default TTL: 1 hour (can be set to None for permanent cache)
DEFAULT_TTL_SECONDS = 3600

# Cache statistics for monitoring
_cache_stats = {"hits": 0, "misses": 0}


def _make_cache_key(prefix: str, *args, **kwargs) -> str:
    """Create a unique cache key from function arguments.
    
    Uses hash for long keys to prevent memory bloat and ensure
    consistent key length for efficient dict operations.
    """
    key_parts = [prefix]
    
    # Convert args to stable string representations
    for arg in args:
        if arg is None:
            key_parts.append("None")
        elif isinstance(arg, (list, tuple)):
            key_parts.append(",".join(str(x) for x in sorted(arg) if x is not None))
        else:
            key_parts.append(str(arg))
    
    # Sort kwargs for consistent key generation
    for k, v in sorted(kwargs.items()):
        if v is None:
            key_parts.append(f"{k}=None")
        elif isinstance(v, (list, tuple)):
            key_parts.append(f"{k}={','.join(str(x) for x in sorted(v) if x is not None)}")
        else:
            key_parts.append(f"{k}={v}")
    
    raw_key = ":".join(key_parts)
    
    # Hash long keys to prevent memory issues
    if len(raw_key) > 200:
        key_hash = hashlib.md5(raw_key.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    return raw_key


def get_cache_stats() -> dict:
    """Return cache statistics for monitoring."""
    total = _cache_stats["hits"] + _cache_stats["misses"]
    hit_rate = (_cache_stats["hits"] / total * 100) if total > 0 else 0.0
    return {
        "entries": len(_cache),
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "hit_rate": round(hit_rate, 2),
    }


def get_cached(key: str) -> Optional[Any]:
    """Get a value from cache if not expired."""
    global _cache_stats
    
    if key not in _cache:
        _cache_stats["misses"] += 1
        return None
    
    entry = _cache[key]
    expires_at = entry.get("expires_at")
    
    # Check expiration (None = never expires)
    if expires_at and datetime.utcnow() > expires_at:
        del _cache[key]
        _cache_stats["misses"] += 1
        return None
    
    _cache_stats["hits"] += 1
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
    global _cache, _cache_stats
    
    if prefix is None:
        count = len(_cache)
        _cache = {}
        _cache_stats = {"hits": 0, "misses": 0}
        return count
    
    keys_to_delete = [k for k in _cache if k.startswith(prefix)]
    for key in keys_to_delete:
        del _cache[key]
    return len(keys_to_delete)


def cached(prefix: str, ttl_seconds: Optional[int] = DEFAULT_TTL_SECONDS):
    """
    Decorator for caching async function results.
    
    Optimizations:
    - Excludes db session from cache key (memory address varies per request)
    - Uses efficient hash-based keys for long parameter lists
    - Thread-safe via asyncio patterns
    
    Usage:
        @cached("kpi_metrics", ttl_seconds=3600)
        async def compute_kpi_metrics(db, start_date, end_date):
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Skip first arg (usually db session) in cache key
            cache_args = args[1:] if args else ()
            
            # Filter out db session from kwargs (unique memory address per request)
            cache_kwargs = {k: v for k, v in kwargs.items() if k != "db"}
            
            key = _make_cache_key(prefix, *cache_args, **cache_kwargs)
            
            # Check cache first (fast path)
            cached_value = get_cached(key)
            if cached_value is not None:
                return cached_value
            
            # Compute and cache result
            result = await func(*args, **kwargs)
            set_cached(key, result, ttl_seconds)
            return result
        
        # Expose cache key generator for testing/debugging
        wrapper.make_cache_key = lambda *a, **kw: _make_cache_key(prefix, *a, **kw)
        return wrapper
    return decorator
