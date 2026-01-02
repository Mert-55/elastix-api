"""Transaction schemas module for CRUD operations."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TransactionBase(BaseModel):
    """Base transaction schema with common fields."""

    invoice_no: str = Field(..., max_length=20, description="Invoice identifier")
    stock_code: str = Field(..., max_length=20, description="Product SKU")
    description: Optional[str] = Field(None, max_length=256, description="Product description")
    quantity: int = Field(..., description="Units sold (negative for returns)")
    invoice_date: datetime = Field(..., description="Transaction timestamp")
    unit_price: Decimal = Field(..., ge=0, decimal_places=2, description="Price per unit")
    customer_id: Optional[str] = Field(None, max_length=20, description="Customer identifier")
    country: Optional[str] = Field(None, max_length=64, description="Country of sale")


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction."""

    pass


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction (all fields optional)."""

    invoice_no: Optional[str] = Field(None, max_length=20)
    stock_code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=256)
    quantity: Optional[int] = None
    invoice_date: Optional[datetime] = None
    unit_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    customer_id: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=64)


class TransactionResponse(TransactionBase):
    """Schema for transaction response."""

    id: UUID = Field(..., description="Transaction ID")

    class Config:
        from_attributes = True


class TransactionBatchCreate(BaseModel):
    """Schema for batch creating transactions."""

    transactions: list[TransactionCreate] = Field(
        ..., description="List of transactions to create"
    )


class TransactionBatchResponse(BaseModel):
    """Schema for batch operation response."""

    created: int = Field(..., description="Number of transactions created")
    message: str = Field(..., description="Operation result message")


class TransactionListResponse(BaseModel):
    """Schema for paginated transaction list response."""

    items: list[TransactionResponse] = Field(
        default_factory=list, description="List of transactions"
    )
    total: int = Field(..., description="Total number of transactions")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
