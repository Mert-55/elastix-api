"""RFM segmentation service module.

Computes per-customer Recency, Frequency, Monetary metrics and assigns
quantile-based segment labels (L/M/H for each dimension).
"""
from datetime import date
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.transaction import Transaction


def _parse_date(value) -> date:
    """Parse date from string or date object."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value


def _calculate_recency(last_purchase, reference_date: date) -> int:
    """Calculate recency as days since last purchase."""
    parsed = _parse_date(last_purchase)
    return (reference_date - parsed).days


def _quantile_bin(value: float, q33: float, q66: float) -> str:
    """Assign L/M/H bin based on tertile thresholds."""
    if value <= q33:
        return "L"
    elif value <= q66:
        return "M"
    return "H"


def _quantile_bin_reverse(value: float, q33: float, q66: float) -> str:
    """Assign L/M/H bin with reversed logic (lower value = higher bin)."""
    if value <= q33:
        return "H"
    elif value <= q66:
        return "M"
    return "L"


def _compute_tertiles(values: list[float]) -> tuple[float, float]:
    """Compute 33rd and 66th percentile thresholds."""
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    idx33 = int(n * 0.33)
    idx66 = int(n * 0.66)
    return sorted_vals[idx33], sorted_vals[idx66]


def _build_segment_label(r_bin: str, f_bin: str, m_bin: str) -> str:
    """Combine R/F/M bins into a segment label."""
    return f"R{r_bin}_F{f_bin}_M{m_bin}"


def _bin_customers(
    customers: list[dict], reference_date: date
) -> list[dict]:
    """Assign L/M/H bins to each customer based on tertiles."""
    if not customers:
        return []

    recencies = [c["recency"] for c in customers]
    frequencies = [c["frequency"] for c in customers]
    monetaries = [c["monetary"] for c in customers]

    r_q33, r_q66 = _compute_tertiles(recencies)
    f_q33, f_q66 = _compute_tertiles(frequencies)
    m_q33, m_q66 = _compute_tertiles(monetaries)

    result = []
    for c in customers:
        # Recency: lower is better, so use reverse binning
        r_bin = _quantile_bin_reverse(c["recency"], r_q33, r_q66)
        f_bin = _quantile_bin(c["frequency"], f_q33, f_q66)
        m_bin = _quantile_bin(c["monetary"], m_q33, m_q66)
        segment = _build_segment_label(r_bin, f_bin, m_bin)
        result.append({**c, "segment": segment})
    return result


async def _fetch_customer_metrics(
    db: AsyncSession,
    reference_date: date,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[dict]:
    """Fetch aggregated RFM metrics per customer from DB."""
    filters = [Transaction.customer_id.isnot(None)]
    if start_date:
        filters.append(Transaction.invoice_date >= start_date)
    if end_date:
        filters.append(Transaction.invoice_date <= end_date)

    query = (
        select(
            Transaction.customer_id,
            func.max(func.date(Transaction.invoice_date)).label("last_purchase"),
            func.count(func.distinct(Transaction.invoice_no)).label("invoice_count"),
            func.sum(Transaction.quantity * Transaction.unit_price).label("revenue"),
        )
        .where(*filters)
        .group_by(Transaction.customer_id)
        .having(func.sum(Transaction.quantity * Transaction.unit_price) > 0)
    )
    result = await db.execute(query)
    rows = result.all()

    customers = []
    for row in rows:
        recency = _calculate_recency(row.last_purchase, reference_date)
        customers.append({
            "customer_id": row.customer_id,
            "recency": recency,
            "frequency": row.invoice_count,
            "monetary": float(row.revenue),
        })
    return customers

from api.services.cache import cached


@cached("rfm_data", ttl_seconds=3600)
async def compute_rfm(
    db: AsyncSession,
    reference_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[dict]:
    """
    Compute RFM scores and segment labels for all customers.

    Args:
        db: Database session
        reference_date: Date to calculate recency from (default: today)
        start_date: Start of analysis period
        end_date: End of analysis period

    Returns:
        List of dicts with customer_id, recency, frequency, monetary, segment
    """
    ref = reference_date or date.today()
    customers = await _fetch_customer_metrics(db, ref, start_date, end_date)
    if len(customers) < 3:
        # Not enough data for meaningful tertiles
        for c in customers:
            c["segment"] = "INSUFFICIENT_DATA"
        return customers
    return _bin_customers(customers, ref)
