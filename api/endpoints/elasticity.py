"""Elasticity endpoint module."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.database import get_db
from api.schemas.elasticity import ElasticityResponse
from api.services.elasticity_service import calculate_elasticity

router = APIRouter(prefix="/elasticity", tags=["elasticity"])


@router.get("", response_model=ElasticityResponse)
async def get_elasticity(
    stock_codes: Optional[list[str]] = Query(
        default=None,
        description="List of product SKUs to analyze. Returns all if empty.",
    ),
    start_date: Optional[date] = Query(
        default=None,
        description="Start of analysis timespan (ISO 8601 format)",
    ),
    end_date: Optional[date] = Query(
        default=None,
        description="End of analysis timespan (ISO 8601 format)",
    ),
    country: Optional[str] = Query(
        default=None,
        description="Filter by country",
    ),
    limit: int = Query(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of products to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of products to skip (for pagination)",
    ),
    db: AsyncSession = Depends(get_db),
) -> ElasticityResponse:
    """
    Calculate price elasticity for products.

    Uses log-log regression to estimate price elasticity of demand
    based on historical transaction data.

    The elasticity coefficient (ε) indicates:
    - ε < -1: Elastic demand (quantity sensitive to price changes)
    - ε > -1: Inelastic demand (quantity less sensitive to price)
    - ε = -1: Unit elastic

    Returns elasticity results with R² goodness-of-fit metric.
    """
    selected_country = country or None

    return await calculate_elasticity(
        db=db,
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        country=selected_country,
        limit=limit,
        offset=offset,
    )
