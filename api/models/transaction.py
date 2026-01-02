"""Transaction model module."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Integer, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database.database import Base


class Transaction(Base):
    """Sales transaction model for e-commerce data."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    invoice_no: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(256), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    invoice_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    country: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
