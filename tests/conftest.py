"""Pytest fixtures for async SQLite test database."""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import String, Integer, DateTime, Numeric
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

Base = declarative_base()


class Transaction(Base):
    """Test transaction model (mirrors production model)."""

    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    invoice_no: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(256), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    invoice_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(64), nullable=True)


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory SQLite async session for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def sample_transactions(db_session):
    """Create sample transactions for testing RFM and elasticity."""
    base_date = datetime(2024, 1, 15)
    transactions = [
        # Customer C1: Recent, frequent, high monetary (RH_FH_MH expected)
        Transaction(
            id=str(uuid.uuid4()),
            invoice_no="INV001",
            stock_code="PROD_A",
            description="Product A",
            quantity=10,
            invoice_date=base_date - timedelta(days=1),
            unit_price=Decimal("100.00"),
            customer_id="C1",
            country="US",
        ),
        Transaction(
            id=str(uuid.uuid4()),
            invoice_no="INV002",
            stock_code="PROD_A",
            description="Product A",
            quantity=8,
            invoice_date=base_date - timedelta(days=2),
            unit_price=Decimal("105.00"),
            customer_id="C1",
            country="US",
        ),
        Transaction(
            id=str(uuid.uuid4()),
            invoice_no="INV003",
            stock_code="PROD_A",
            description="Product A",
            quantity=12,
            invoice_date=base_date - timedelta(days=3),
            unit_price=Decimal("95.00"),
            customer_id="C1",
            country="US",
        ),
        # Customer C2: Medium recency, medium frequency, medium monetary
        Transaction(
            id=str(uuid.uuid4()),
            invoice_no="INV004",
            stock_code="PROD_B",
            description="Product B",
            quantity=5,
            invoice_date=base_date - timedelta(days=15),
            unit_price=Decimal("50.00"),
            customer_id="C2",
            country="US",
        ),
        Transaction(
            id=str(uuid.uuid4()),
            invoice_no="INV005",
            stock_code="PROD_B",
            description="Product B",
            quantity=4,
            invoice_date=base_date - timedelta(days=20),
            unit_price=Decimal("55.00"),
            customer_id="C2",
            country="US",
        ),
        # Customer C3: Old, infrequent, low monetary (RL_FL_ML expected)
        Transaction(
            id=str(uuid.uuid4()),
            invoice_no="INV006",
            stock_code="PROD_C",
            description="Product C",
            quantity=2,
            invoice_date=base_date - timedelta(days=60),
            unit_price=Decimal("20.00"),
            customer_id="C3",
            country="US",
        ),
        # Additional transactions for C1 to boost frequency/monetary
        Transaction(
            id=str(uuid.uuid4()),
            invoice_no="INV007",
            stock_code="PROD_A",
            description="Product A",
            quantity=15,
            invoice_date=base_date - timedelta(days=4),
            unit_price=Decimal("98.00"),
            customer_id="C1",
            country="US",
        ),
        Transaction(
            id=str(uuid.uuid4()),
            invoice_no="INV008",
            stock_code="PROD_A",
            description="Product A",
            quantity=11,
            invoice_date=base_date - timedelta(days=5),
            unit_price=Decimal("102.00"),
            customer_id="C1",
            country="US",
        ),
    ]
    db_session.add_all(transactions)
    await db_session.commit()
    return transactions
