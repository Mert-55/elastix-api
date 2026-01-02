"""Dashboard endpoint module.

Provides endpoints for dashboard KPIs, segment treemap, and revenue trends.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.database import get_db
from api.schemas.dashboard import (
    KPIMetricsResponse,
    TreeMapResponse,
    AreaChartResponse,
)
from api.services.dashboard_service import (
    compute_kpi_metrics,
    compute_segment_treemap,
    compute_revenue_trends,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/kpis", response_model=KPIMetricsResponse)
async def get_kpi_metrics(
    start_date: Optional[date] = Query(
        default=None,
        description="Start of analysis period (ISO 8601 format)",
    ),
    end_date: Optional[date] = Query(
        default=None,
        description="End of analysis period (ISO 8601 format)",
    ),
    db: AsyncSession = Depends(get_db),
) -> KPIMetricsResponse:
    """
    Get KPI metrics for each RFM segment.

    Returns per-segment metrics including:
    - **priceSensitivity**: Average absolute elasticity (0-100 scale)
    - **walletShare**: Revenue contribution percentage
    - **churnRisk**: Churn risk score based on recency (0-100 scale)

    Segments: Champion, LoyalCustomers, PotentialLoyalists, AtRisk, Hibernating, Lost
    """
    return await compute_kpi_metrics(
        db=db,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/segments", response_model=TreeMapResponse)
async def get_segment_treemap(
    start_date: Optional[date] = Query(
        default=None,
        description="Start of analysis period (ISO 8601 format)",
    ),
    end_date: Optional[date] = Query(
        default=None,
        description="End of analysis period (ISO 8601 format)",
    ),
    db: AsyncSession = Depends(get_db),
) -> TreeMapResponse:
    """
    Get segment distribution data for treemap visualization.

    Returns per-segment data including:
    - **segment**: Segment name
    - **value**: Total revenue for the segment
    - **score**: Average RFM score (1-5 scale)
    - **customerCount**: Number of customers in segment
    """
    return await compute_segment_treemap(
        db=db,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/trends", response_model=AreaChartResponse)
async def get_revenue_trends(
    start_date: Optional[date] = Query(
        default=None,
        description="Start of analysis period (ISO 8601 format)",
    ),
    end_date: Optional[date] = Query(
        default=None,
        description="End of analysis period (ISO 8601 format)",
    ),
    db: AsyncSession = Depends(get_db),
) -> AreaChartResponse:
    """
    Get time-series revenue data by segment for area chart visualization.

    Returns daily revenue breakdown by segment:
    - Champions, LoyalCustomers, PotentialLoyalists, AtRisk, Hibernating, Lost
    - date: Date in DD/MM/YYYY format
    """
    return await compute_revenue_trends(
        db=db,
        start_date=start_date,
        end_date=end_date,
    )
