"""Elasticity schemas module."""
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ElasticityResult(BaseModel):
    """Individual product elasticity result."""

    stock_code: str = Field(..., description="Product SKU")
    description: Optional[str] = Field(None, description="Product description")
    elasticity: float = Field(..., description="Price elasticity coefficient")
    sample_size: int = Field(..., description="Number of data points used")
    avg_price: float = Field(..., description="Average unit price")
    total_quantity: int = Field(..., description="Total quantity sold")
    r_squared: float = Field(..., description="R-squared value of regression")


class ElasticityMeta(BaseModel):
    """Metadata for elasticity response."""

    start_date: date = Field(..., description="Start of analysis period")
    end_date: date = Field(..., description="End of analysis period")
    total_products: int = Field(..., description="Total number of products available for the current filter set")
    returned_products: int = Field(..., description="Number of products included in this response page")
    limit: int = Field(..., description="Max number of products requested per page")
    offset: int = Field(..., description="Number of products skipped (for pagination)")
    available_countries: list[str] = Field(
        default_factory=list,
        description="Distinct countries available for filtering",
    )


class ElasticityResponse(BaseModel):
    """Response schema for elasticity endpoint."""

    results: list[ElasticityResult] = Field(
        default_factory=list, description="List of elasticity results"
    )
    meta: ElasticityMeta = Field(..., description="Response metadata")
