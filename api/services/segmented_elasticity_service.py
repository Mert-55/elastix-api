"""Segmented elasticity service module.

Computes price elasticity for products filtered by RFM customer segment.
Reuses _compute_elasticity from elasticity_service.
"""
from datetime import date
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.transaction import Transaction
from api.services.elasticity_service import _compute_elasticity
from api.services.rfm_service import compute_rfm
from api.schemas.elasticity import ElasticityResult


def _filter_customers_by_segment(
    rfm_data: list[dict], segment: str
) -> set[str]:
    """Return customer IDs matching the given segment."""
    return {c["customer_id"] for c in rfm_data if c["segment"] == segment}


async def _fetch_segment_transactions(
    db: AsyncSession,
    customer_ids: set[str],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[tuple]:
    """Fetch transactions for specified customers grouped by day/product."""
    if not customer_ids:
        return []

    filters = [Transaction.customer_id.in_(customer_ids)]
    if start_date:
        filters.append(Transaction.invoice_date >= start_date)
    if end_date:
        filters.append(Transaction.invoice_date <= end_date)

    query = (
        select(
            Transaction.stock_code,
            func.max(Transaction.description).label("description"),
            func.date(Transaction.invoice_date).label("sale_date"),
            func.avg(Transaction.unit_price).label("avg_price"),
            func.sum(Transaction.quantity).label("total_quantity"),
        )
        .where(*filters)
        .group_by(Transaction.stock_code, func.date(Transaction.invoice_date))
        .having(func.sum(Transaction.quantity) > 0)
        .having(func.avg(Transaction.unit_price) > 0)
    )
    result = await db.execute(query)
    return result.all()


def _group_by_product(rows: list[tuple]) -> dict[str, dict]:
    """Group transaction rows by stock_code for elasticity calculation."""
    product_data: dict[str, dict] = {}
    for row in rows:
        code = row.stock_code
        if code not in product_data:
            product_data[code] = {
                "description": row.description,
                "prices": [],
                "quantities": [],
            }
        product_data[code]["prices"].append(float(row.avg_price))
        product_data[code]["quantities"].append(int(row.total_quantity))
    return product_data


def _compute_elasticities(
    product_data: dict[str, dict]
) -> list[ElasticityResult]:
    """Compute elasticity for each product using existing logic."""
    results = []
    for stock_code, data in product_data.items():
        result = _compute_elasticity(
            stock_code=stock_code,
            description=data["description"],
            prices=data["prices"],
            quantities=data["quantities"],
        )
        if result:
            results.append(result)
    return results


async def elasticity_by_segment(
    db: AsyncSession,
    segment: str,
    reference_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[ElasticityResult]:
    """
    Compute elasticity for products purchased by customers in a segment.

    Args:
        db: Database session
        segment: RFM segment label (e.g., "RH_FH_MH")
        reference_date: Date for recency calculation
        start_date: Start of analysis period
        end_date: End of analysis period

    Returns:
        List of ElasticityResult for products in the segment
    """
    rfm_data = await compute_rfm(db, reference_date, start_date, end_date)
    customer_ids = _filter_customers_by_segment(rfm_data, segment)
    rows = await _fetch_segment_transactions(db, customer_ids, start_date, end_date)
    product_data = _group_by_product(rows)
    return _compute_elasticities(product_data)
