"""Stock items endpoint module.

Provides endpoints for stock item search and detail retrieval.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.database import get_db
from api.schemas.dashboard import (
    StockItemGridResponse,
    StockItemDetail,
)
from api.services.stock_items_service import (
    search_stock_items,
    get_stock_item_detail,
)

router = APIRouter(prefix="/stock-items", tags=["stock-items"])


@router.get("", response_model=StockItemGridResponse)
async def list_stock_items(
    query: Optional[str] = Query(
        default=None,
        description="Search query for stock code or description",
    ),
    start_date: Optional[date] = Query(
        default=None,
        description="Start of analysis period (ISO 8601 format)",
    ),
    end_date: Optional[date] = Query(
        default=None,
        description="End of analysis period (ISO 8601 format)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of items to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of items to skip (for pagination)",
    ),
    db: AsyncSession = Depends(get_db),
) -> StockItemGridResponse:
    """
    Search and list stock items with elasticity data.

    Returns for each item:
    - **id**: Stock code / SKU
    - **itemName**: Product description
    - **elasticity**: Price elasticity coefficient
    - **purchaseFrequency**: Number of distinct purchase occasions
    - **revenuePotential**: Estimated revenue potential score
    - **segment**: Primary customer segment for this product
    """
    return await search_stock_items(
        db=db,
        query=query,
        limit=limit,
        offset=offset,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/{code}", response_model=StockItemDetail)
async def get_stock_item(
    code: str,
    start_date: Optional[date] = Query(
        default=None,
        description="Start of analysis period (ISO 8601 format)",
    ),
    end_date: Optional[date] = Query(
        default=None,
        description="End of analysis period (ISO 8601 format)",
    ),
    db: AsyncSession = Depends(get_db),
) -> StockItemDetail:
    """
    Get detailed stock item information with elasticity data.

    Returns:
    - **id**: Stock code / SKU
    - **itemName**: Product description
    - **elasticity**: Price elasticity coefficient
    - **rSquared**: R-squared goodness of fit
    - **avgPrice**: Average unit price
    - **totalQuantity**: Total units sold
    - **totalRevenue**: Total revenue
    - **sampleSize**: Data points used for elasticity calculation
    """
    result = await get_stock_item_detail(
        db=db,
        stock_code=code,
        start_date=start_date,
        end_date=end_date,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock item '{code}' not found",
        )

    return result
