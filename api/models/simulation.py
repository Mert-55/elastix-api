"""Simulation model module."""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, ARRAY, INTEGER
from sqlalchemy.orm import Mapped, mapped_column

from api.database.database import Base


class Simulation(Base):
    """Saved simulation configuration model."""

    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    stock_item_ref: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # price_range stored as [from, to, step]
    price_range: Mapped[list[int]] = mapped_column(ARRAY(INTEGER), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
