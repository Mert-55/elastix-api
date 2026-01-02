"""FastAPI application setup module."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.settings import settings
from api.endpoints.elasticity import router as elasticity_router
from api.endpoints.simulation import router as simulation_router
from api.endpoints.transactions import router as transactions_router
from api.endpoints.dashboard import router as dashboard_router
from api.endpoints.stock_items import router as stock_items_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ElastiCom API",
    description="Price elasticity calculation service for e-commerce data",
    version="1.0.0",
    debug=settings.DEBUG,
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure via settings.CORS_ORIGINS in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(elasticity_router)
app.include_router(simulation_router)
app.include_router(transactions_router)
app.include_router(dashboard_router)
app.include_router(stock_items_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/cache/clear", tags=["admin"])
async def clear_cache():
    """Clear all cached data. Use after data imports."""
    from api.services.cache import clear_cache as _clear_cache
    count = _clear_cache()
    return {"cleared": count, "message": f"Cleared {count} cached entries"}


@app.get("/cache/stats", tags=["admin"])
async def cache_stats():
    """Get cache statistics for debugging."""
    from api.services.cache import _cache
    return {
        "total_keys": len(_cache),
        "keys": list(_cache.keys()),
    }
