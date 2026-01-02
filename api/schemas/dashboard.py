"""Dashboard schemas module.

Defines response schemas for the dashboard KPIs, segmentation treemap,
and revenue trends endpoints.
"""
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# --- Metrics KPI Component ---

class SegmentMetrics(BaseModel):
    """Metrics for a single RFM segment."""

    price_sensitivity: float = Field(
        ...,
        alias="priceSensitivity",
        description="Average absolute elasticity for the segment (0-100 scale)",
    )
    wallet_share: float = Field(
        ...,
        alias="walletShare",
        description="Revenue contribution percentage of this segment",
    )
    churn_risk: float = Field(
        ...,
        alias="churnRisk",
        description="Churn risk score based on recency (0-100 scale)",
    )

    class Config:
        populate_by_name = True


class KPIMetricsResponse(BaseModel):
    """Response schema for segment KPI metrics endpoint."""

    Champion: SegmentMetrics
    LoyalCustomers: SegmentMetrics
    PotentialLoyalists: SegmentMetrics
    AtRisk: SegmentMetrics
    Hibernating: SegmentMetrics
    Lost: SegmentMetrics


# --- TreeMap Segmentation Component ---

class SegmentTreeMapItem(BaseModel):
    """Single item for the treemap segmentation chart."""

    segment: str = Field(..., description="Segment name")
    value: float = Field(..., description="Total revenue for the segment")
    score: float = Field(..., description="Average RFM score (1-5)")
    customer_count: int = Field(
        ...,
        alias="customerCount",
        description="Number of customers in segment",
    )

    class Config:
        populate_by_name = True


class TreeMapResponse(BaseModel):
    """Response schema for treemap segmentation endpoint."""

    total: int = Field(..., description="Total number of customers")
    items: list[SegmentTreeMapItem] = Field(
        default_factory=list,
        description="List of segment items",
    )


# --- Area Chart Revenue Trends Component ---

class RevenueTrendItem(BaseModel):
    """Single data point for revenue trends area chart."""

    Champions: float = 0.0
    LoyalCustomers: float = 0.0
    PotentialLoyalists: float = 0.0
    AtRisk: float = 0.0
    Hibernating: float = 0.0
    Lost: float = 0.0
    date: str = Field(..., description="Date in DD/MM/YYYY format")


class AreaChartResponse(BaseModel):
    """Response schema for revenue trends area chart endpoint."""

    total: int = Field(..., description="Total number of data points")
    items: list[RevenueTrendItem] = Field(
        default_factory=list,
        description="Time-series revenue data by segment",
    )


# --- Stock Item Grid Component ---

class StockItemGridItem(BaseModel):
    """Single item for the stock item grid."""

    id: str = Field(..., description="Stock code / SKU")
    item_name: str = Field(
        ...,
        alias="itemName",
        description="Product name/description",
    )
    elasticity: float = Field(..., description="Price elasticity coefficient")
    purchase_frequency: int = Field(
        ...,
        alias="purchaseFrequency",
        description="Number of distinct purchase occasions",
    )
    revenue_potential: float = Field(
        ...,
        alias="revenuePotential",
        description="Estimated revenue potential score",
    )
    segment: str = Field(
        ...,
        description="Primary customer segment for this product",
    )

    class Config:
        populate_by_name = True


class StockItemGridResponse(BaseModel):
    """Response schema for stock item grid endpoint."""

    total: int = Field(..., description="Total number of stock items")
    items: list[StockItemGridItem] = Field(
        default_factory=list,
        description="List of stock items with elasticity data",
    )


# --- Stock Item Detail ---

class StockItemDetail(BaseModel):
    """Detailed stock item with full elasticity info."""

    id: str = Field(..., description="Stock code / SKU")
    item_name: str = Field(
        ...,
        alias="itemName",
        description="Product name/description",
    )
    elasticity: float = Field(..., description="Price elasticity coefficient")
    r_squared: float = Field(
        ...,
        alias="rSquared",
        description="R-squared goodness of fit",
    )
    avg_price: float = Field(
        ...,
        alias="avgPrice",
        description="Average unit price",
    )
    total_quantity: int = Field(
        ...,
        alias="totalQuantity",
        description="Total units sold",
    )
    total_revenue: float = Field(
        ...,
        alias="totalRevenue",
        description="Total revenue",
    )
    sample_size: int = Field(
        ...,
        alias="sampleSize",
        description="Data points used for elasticity calculation",
    )

    class Config:
        populate_by_name = True
