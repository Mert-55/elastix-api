"""Dashboard service module.

Provides KPI metrics, segment treemap, and revenue trends for the dashboard.

Scientific Foundation:
- RFM Segmentation: Recency, Frequency, Monetary analysis (Hughes, 1994)
- Price Elasticity: Log-log regression model (Paczkowski, 2018)
- Segment Classification: Tertile-based binning into L/M/H categories

Performance:
- Results are cached in-memory (TTL: 1 hour)
- Single DB query for elasticity instead of per-segment queries
"""
from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.transaction import Transaction
from api.services.rfm_service import compute_rfm
from api.services.elasticity_service import calculate_elasticity
from api.services.cache import cached
from api.schemas.dashboard import (
    KPIMetricsResponse,
    SegmentMetrics,
    TreeMapResponse,
    SegmentTreeMapItem,
    AreaChartResponse,
    RevenueTrendItem,
)

# =============================================================================
# RFM SEGMENT MAPPING
# =============================================================================
# Maps raw RFM bin combinations (e.g., "RH_FH_MH") to business segments.
# Based on RFM segmentation best practices (Blattberg et al., 2008).

RFM_SEGMENT_MAP = {
    # Champions: High R, High F, High/Medium M → Best customers
    "RH_FH_MH": "Champion", "RH_FH_MM": "Champion", "RH_FM_MH": "Champion",
    # Loyal Customers: High F regardless of R → Consistent buyers
    "RH_FH_ML": "LoyalCustomers", "RM_FH_MH": "LoyalCustomers",
    "RM_FH_MM": "LoyalCustomers", "RL_FH_MH": "LoyalCustomers",
    # Potential Loyalists: Recent but low frequency → Growth opportunity
    "RH_FM_MM": "PotentialLoyalists", "RH_FM_ML": "PotentialLoyalists",
    "RH_FL_MH": "PotentialLoyalists", "RH_FL_MM": "PotentialLoyalists",
    "RH_FL_ML": "PotentialLoyalists",
    # At Risk: Medium R, were good customers → Need re-engagement
    "RM_FH_ML": "AtRisk", "RM_FM_MH": "AtRisk",
    "RM_FM_MM": "AtRisk", "RM_FM_ML": "AtRisk",
    # Hibernating: Low activity, may return
    "RM_FL_MH": "Hibernating", "RM_FL_MM": "Hibernating", "RM_FL_ML": "Hibernating",
    "RL_FH_MM": "Hibernating", "RL_FH_ML": "Hibernating",
    "RL_FM_MH": "Hibernating", "RL_FM_MM": "Hibernating",
    # Lost: Low R, Low F → Likely churned
    "RL_FM_ML": "Lost", "RL_FL_MH": "Lost", "RL_FL_MM": "Lost", "RL_FL_ML": "Lost",
}

# Ordered list of segments for consistent output
SEGMENT_ORDER = ["Champion", "LoyalCustomers", "PotentialLoyalists", "AtRisk", "Hibernating", "Lost"]


def _map_segment_label(raw_segment: str) -> str:
    """Map raw RFM label (e.g., 'RH_FH_MH') to business segment name."""
    return RFM_SEGMENT_MAP.get(raw_segment, "Lost")


# =============================================================================
# KPI METRICS
# =============================================================================

@cached("kpi_metrics", ttl_seconds=3600)
async def compute_kpi_metrics(
    db: AsyncSession,
    reference_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> KPIMetricsResponse:
    """
    Compute KPI metrics for each customer segment.
    
    Metrics Definitions:
    - Price Sensitivity: Average |elasticity| normalized to 0-100 scale
      Higher value = customers more responsive to price changes
    - Wallet Share: Segment revenue / Total revenue × 100
      Represents revenue contribution percentage
    - Churn Risk: Average recency / Max recency × 100
      Higher value = longer since last purchase = higher risk
    
    Args:
        db: Database session
        reference_date: Date for recency calculation (default: today)
        start_date: Filter transactions from this date
        end_date: Filter transactions until this date
    
    Returns:
        KPIMetricsResponse with metrics for all 6 segments
    """
    ref = reference_date or date.today()
    
    # Step 1: Get RFM data for all customers
    rfm_data = await compute_rfm(db, ref, start_date, end_date)
    
    if not rfm_data:
        return _empty_kpi_response()
    
    # Step 2: Group customers by segment
    segment_customers = _group_customers_by_segment(rfm_data)
    
    # Step 3: Calculate global metrics for normalization
    total_revenue = sum(c["monetary"] for c in rfm_data)
    max_recency = max(c["recency"] for c in rfm_data)
    
    # Avoid division by zero
    total_revenue = max(total_revenue, 1.0)
    max_recency = max(max_recency, 1)
    
    # Step 4: Get average elasticity per segment (OPTIMIZED: single query)
    segment_elasticities = await _compute_segment_elasticities(
        db, rfm_data, start_date, end_date
    )
    
    # Step 5: Build response
    def build_metrics(segment: str) -> SegmentMetrics:
        customers = segment_customers.get(segment, [])
        
        if not customers:
            return SegmentMetrics(priceSensitivity=0.0, walletShare=0.0, churnRisk=0.0)
        
        # Wallet Share
        segment_revenue = sum(c["monetary"] for c in customers)
        wallet_share = (segment_revenue / total_revenue) * 100
        
        # Churn Risk
        avg_recency = sum(c["recency"] for c in customers) / len(customers)
        churn_risk = (avg_recency / max_recency) * 100
        
        # Price Sensitivity (elasticity → 0-100 scale)
        elasticity = segment_elasticities.get(segment, 0.0)
        price_sensitivity = min(100.0, abs(elasticity) * 33.33)
        
        return SegmentMetrics(
            priceSensitivity=round(price_sensitivity, 1),
            walletShare=round(wallet_share, 1),
            churnRisk=round(churn_risk, 1),
        )
    
    return KPIMetricsResponse(
        Champion=build_metrics("Champion"),
        LoyalCustomers=build_metrics("LoyalCustomers"),
        PotentialLoyalists=build_metrics("PotentialLoyalists"),
        AtRisk=build_metrics("AtRisk"),
        Hibernating=build_metrics("Hibernating"),
        Lost=build_metrics("Lost"),
    )


def _group_customers_by_segment(rfm_data: list[dict]) -> dict[str, list[dict]]:
    """Group customers by their business segment."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for customer in rfm_data:
        segment = _map_segment_label(customer.get("segment", ""))
        groups[segment].append(customer)
    return groups


async def _compute_segment_elasticities(
    db: AsyncSession,
    rfm_data: list[dict],
    start_date: Optional[date],
    end_date: Optional[date],
) -> dict[str, float]:
    """
    Compute average elasticity per segment using a single optimized query.
    
    Instead of querying elasticity for each of 27 raw segments separately,
    we fetch all elasticities once and aggregate by customer segment.
    """
    # Map customer_id → segment
    customer_segment_map = {
        c["customer_id"]: _map_segment_label(c.get("segment", ""))
        for c in rfm_data
    }
    
    # Fetch all elasticities in one query (limited to top products for speed)
    elasticity_response = await calculate_elasticity(
        db=db,
        start_date=start_date,
        end_date=end_date,
        limit=200,  # Top 200 products is sufficient for segment averages
    )
    
    if not elasticity_response.results:
        return {}
    
    # Get which customers bought which products
    customer_ids = list(customer_segment_map.keys())
    
    filters = [
        Transaction.customer_id.in_(customer_ids),
        Transaction.quantity > 0,
    ]
    if start_date:
        filters.append(Transaction.invoice_date >= start_date)
    if end_date:
        filters.append(Transaction.invoice_date <= end_date)
    
    # Query: customer_id, stock_code pairs
    query = (
        select(Transaction.customer_id, Transaction.stock_code)
        .where(*filters)
        .distinct()
    )
    result = await db.execute(query)
    customer_products = result.all()
    
    # Build product → elasticity map
    product_elasticity = {r.stock_code: r.elasticity for r in elasticity_response.results}
    
    # Aggregate elasticities by segment
    segment_elasticities: dict[str, list[float]] = defaultdict(list)
    
    for customer_id, stock_code in customer_products:
        segment = customer_segment_map.get(customer_id)
        elasticity = product_elasticity.get(stock_code)
        
        if segment and elasticity is not None:
            segment_elasticities[segment].append(abs(elasticity))
    
    # Calculate averages
    return {
        segment: sum(values) / len(values)
        for segment, values in segment_elasticities.items()
        if values
    }


def _empty_kpi_response() -> KPIMetricsResponse:
    """Return empty KPI response when no data available."""
    empty = SegmentMetrics(priceSensitivity=0.0, walletShare=0.0, churnRisk=0.0)
    return KPIMetricsResponse(
        Champion=empty, LoyalCustomers=empty, PotentialLoyalists=empty,
        AtRisk=empty, Hibernating=empty, Lost=empty,
    )


# =============================================================================
# SEGMENT TREEMAP
# =============================================================================

@cached("segment_treemap", ttl_seconds=3600)
async def compute_segment_treemap(
    db: AsyncSession,
    reference_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> TreeMapResponse:
    """
    Compute segment distribution for treemap visualization.
    
    Returns per segment:
    - value: Total revenue (for treemap area sizing)
    - score: Average RFM score (1-5 scale, for color coding)
    - customerCount: Number of customers
    
    Score Calculation:
    - Each R/F/M dimension is scored 1-3 (L=1, M=2, H=3)
    - Average is scaled to 1-5 range: score = (avg - 1) × 2 + 1
    """
    ref = reference_date or date.today()
    rfm_data = await compute_rfm(db, ref, start_date, end_date)
    
    if not rfm_data:
        return TreeMapResponse(total=0, items=[])
    
    # Aggregate by segment
    segment_data: dict[str, dict] = defaultdict(
        lambda: {"revenue": 0.0, "count": 0, "scores": []}
    )
    
    for customer in rfm_data:
        raw_segment = customer.get("segment", "")
        label = _map_segment_label(raw_segment)
        
        segment_data[label]["revenue"] += customer["monetary"]
        segment_data[label]["count"] += 1
        
        # Extract RFM scores from segment string
        rfm_score = _extract_rfm_score(raw_segment)
        if rfm_score:
            segment_data[label]["scores"].append(rfm_score)
    
    # Build response
    items = []
    for segment in SEGMENT_ORDER:
        data = segment_data.get(segment)
        if data and data["count"] > 0:
            # Average RFM score → 1-5 scale
            avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 1.0
            score_1_5 = round((avg_score - 1) * 2 + 1, 1)
            score_1_5 = max(1.0, min(5.0, score_1_5))
            
            items.append(SegmentTreeMapItem(
                segment=segment,
                value=round(data["revenue"], 2),
                score=score_1_5,
                customerCount=data["count"],
            ))
    
    return TreeMapResponse(total=len(rfm_data), items=items)


def _extract_rfm_score(raw_segment: str) -> Optional[float]:
    """
    Extract average RFM score (1-3 scale) from segment string.
    
    Example: "RH_FM_ML" → R=3, F=2, M=1 → avg = 2.0
    """
    if not raw_segment or "_" not in raw_segment:
        return None
    
    parts = raw_segment.split("_")
    if len(parts) != 3:
        return None
    
    score_map = {"H": 3, "M": 2, "L": 1}
    
    r_score = score_map.get(parts[0][1:], 1)  # "RH" → "H" → 3
    f_score = score_map.get(parts[1][1:], 1)  # "FM" → "M" → 2
    m_score = score_map.get(parts[2][1:], 1)  # "ML" → "L" → 1
    
    return (r_score + f_score + m_score) / 3


# =============================================================================
# REVENUE TRENDS
# =============================================================================

@cached("revenue_trends", ttl_seconds=3600)
async def compute_revenue_trends(
    db: AsyncSession,
    reference_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    granularity: str = "daily",
) -> AreaChartResponse:
    """
    Compute time-series revenue by segment for area chart visualization.
    
    Each data point contains revenue breakdown by segment for a given date.
    Customer segment is determined by their RFM classification.
    
    Args:
        db: Database session
        reference_date: Date for RFM recency calculation
        start_date: Start of time series
        end_date: End of time series
        granularity: 'daily', 'weekly', 'monthly' (currently only daily)
    
    Returns:
        AreaChartResponse with time-series data
    """
    ref = reference_date or date.today()
    
    # Get customer → segment mapping
    rfm_data = await compute_rfm(db, ref, start_date, end_date)
    customer_segments = {
        c["customer_id"]: _map_segment_label(c.get("segment", ""))
        for c in rfm_data
    }
    
    # Fetch daily revenue per customer
    filters = [Transaction.customer_id.isnot(None), Transaction.quantity > 0]
    if start_date:
        filters.append(Transaction.invoice_date >= start_date)
    if end_date:
        filters.append(Transaction.invoice_date <= end_date)
    
    query = (
        select(
            func.date(Transaction.invoice_date).label("sale_date"),
            Transaction.customer_id,
            func.sum(Transaction.quantity * Transaction.unit_price).label("revenue"),
        )
        .where(*filters)
        .group_by(func.date(Transaction.invoice_date), Transaction.customer_id)
        .having(func.sum(Transaction.quantity * Transaction.unit_price) > 0)
        .order_by(func.date(Transaction.invoice_date))
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    # Aggregate by date and segment
    date_segment_revenue: dict[date, dict[str, float]] = defaultdict(
        lambda: {s: 0.0 for s in SEGMENT_ORDER}
    )
    
    for row in rows:
        sale_date = row.sale_date
        if isinstance(sale_date, str):
            sale_date = date.fromisoformat(sale_date)
        
        segment = customer_segments.get(row.customer_id, "Lost")
        date_segment_revenue[sale_date][segment] += float(row.revenue)
    
    # Build response
    items = []
    for sale_date in sorted(date_segment_revenue.keys()):
        segments = date_segment_revenue[sale_date]
        items.append(RevenueTrendItem(
            Champions=round(segments["Champion"], 2),
            LoyalCustomers=round(segments["LoyalCustomers"], 2),
            PotentialLoyalists=round(segments["PotentialLoyalists"], 2),
            AtRisk=round(segments["AtRisk"], 2),
            Hibernating=round(segments["Hibernating"], 2),
            Lost=round(segments["Lost"], 2),
            date=sale_date.strftime("%d/%m/%Y"),
        ))
    
    return AreaChartResponse(total=len(items), items=items)
