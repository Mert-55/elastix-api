"""Simulation schemas module."""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    """Request schema for price simulation (quick simulation)."""

    stock_code: str = Field(..., description="Product SKU to simulate")
    price_change_percent: float = Field(
        ...,
        description="Planned price change in percent (e.g., 5.0 for +5%)",
        ge=-99.0,
        le=1000.0,
    )


class SimulationResult(BaseModel):
    """Response schema for price simulation."""

    stock_code: str = Field(..., description="Product SKU")
    description: str | None = Field(None, description="Product description")

    # Current state
    current_price: float = Field(..., description="Current average unit price")
    current_quantity: int = Field(..., description="Current total quantity sold")
    current_revenue: float = Field(..., description="Current total revenue")

    # Simulation parameters
    price_change_percent: float = Field(..., description="Applied price change in %")
    elasticity: float = Field(..., description="Price elasticity used")
    r_squared: float = Field(..., description="R-squared of elasticity model")

    # Projected state
    projected_price: float = Field(..., description="Projected new price")
    projected_quantity: int = Field(..., description="Projected quantity after change")
    projected_revenue: float = Field(..., description="Projected revenue after change")

    # Changes
    quantity_change_percent: float = Field(
        ..., description="Expected quantity change in %"
    )
    revenue_change_percent: float = Field(
        ..., description="Expected revenue change in %"
    )
    revenue_delta: float = Field(..., description="Absolute revenue difference")


# --- CRUD Schemas for Saved Simulations ---


class SimulationCreate(BaseModel):
    """Request schema for creating a saved simulation."""

    name: str = Field(..., description="Simulation name", min_length=1, max_length=256)
    description: Optional[str] = Field(None, description="Optional description")
    stock_item_ref: str = Field(
        ...,
        alias="stockItemRef",
        description="Stock code / SKU reference",
    )
    price_range: list[int] = Field(
        ...,
        alias="priceRange",
        description="Price range as [from, to, step] percentage values",
        min_length=3,
        max_length=3,
    )

    class Config:
        populate_by_name = True


class SimulationUpdate(BaseModel):
    """Request schema for updating a saved simulation."""

    name: Optional[str] = Field(
        None, description="Simulation name", min_length=1, max_length=256
    )
    description: Optional[str] = Field(None, description="Optional description")
    price_range: Optional[list[int]] = Field(
        None,
        alias="priceRange",
        description="Price range as [from, to, step] percentage values",
        min_length=3,
        max_length=3,
    )

    class Config:
        populate_by_name = True


class SimulationResponse(BaseModel):
    """Response schema for a saved simulation."""

    simulation_id: UUID = Field(..., alias="simulationId", description="Simulation UUID")
    name: str = Field(..., description="Simulation name")
    description: Optional[str] = Field(None, description="Optional description")
    stock_item_ref: str = Field(
        ...,
        alias="stockItemRef",
        description="Stock code / SKU reference",
    )
    price_range: list[int] = Field(
        ...,
        alias="priceRange",
        description="Price range as [from, to, step]",
    )

    class Config:
        populate_by_name = True
        from_attributes = True


class SimulationListResponse(BaseModel):
    """Response schema for listing saved simulations."""

    total: int = Field(..., description="Total number of simulations")
    items: list[SimulationResponse] = Field(
        default_factory=list, description="List of simulations"
    )


# --- Segment Metrics for Simulation ---


class SegmentSimulationMetrics(BaseModel):
    """Metrics for a single segment in simulation results."""

    price_change_percent: float = Field(
        ...,
        alias="priceChangePercent",
        description="Applied price change percentage",
    )
    quantity: int = Field(..., description="Projected quantity for this segment")
    revenue: float = Field(..., description="Projected revenue for this segment")
    delta_quantity_percent: float = Field(
        ...,
        alias="deltaQuantityPercent",
        description="Quantity change percentage",
    )
    delta_revenue_percent: float = Field(
        ...,
        alias="deltaRevenuePercent",
        description="Revenue change percentage",
    )

    class Config:
        populate_by_name = True


class SimulationMetricsResponse(BaseModel):
    """Response schema for segment-based simulation metrics."""

    Champions: SegmentSimulationMetrics
    LoyalCustomers: SegmentSimulationMetrics
    PotentialLoyalists: SegmentSimulationMetrics
    AtRisk: SegmentSimulationMetrics
    Hibernating: SegmentSimulationMetrics
    Lost: SegmentSimulationMetrics
