"""Stock items service module.

Provides business logic for stock item search and detail retrieval
with elasticity data and customer segment analysis.
"""
from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy import select, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.transaction import Transaction
from api.services.elasticity_service import calculate_elasticity
from api.services.rfm_service import compute_rfm
from api.services.dashboard_service import _map_segment_label
from api.schemas.dashboard import (
    StockItemGridResponse,
    StockItemGridItem,
    StockItemDetail,
)


async def search_stock_items(
    db: AsyncSession,
    query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort_by: Optional[str] = None,
    segment_filter: Optional[str] = None,
) -> StockItemGridResponse:
    """
    Search stock items with elasticity and segment data.

    For each stock item, computes:
    - Elasticity coefficient
    - Purchase frequency (distinct invoices)
    - Revenue potential (elasticity * avg_revenue, normalized)
    - Primary customer segment
    - Total Quantity and Revenue

    Args:
        db: Database session
        query: Optional search query for stock code or description
        limit: Maximum items to return
        offset: Pagination offset
        start_date: Start of analysis period
        end_date: End of analysis period
        sort_by: Sort order (quantity_asc, quantity_desc, revenue_asc, revenue_desc)
        segment_filter: Filter by primary customer segment

    Returns:
        StockItemGridResponse with matching items
    """
    sanitized_limit = max(1, min(limit, 1000))
    sanitized_offset = max(0, offset)

    # Build filters
    filters = []
    if start_date:
        filters.append(Transaction.invoice_date >= start_date)
    if end_date:
        filters.append(Transaction.invoice_date <= end_date)
    if query:
        search_pattern = f"%{query}%"
        filters.append(
            (Transaction.stock_code.ilike(search_pattern)) |
            (Transaction.description.ilike(search_pattern))
        )

    # Helper to compute segments for a list of stock codes
    async def compute_segments_for_items(codes):
        if not codes:
            return {}
        
        ref = date.today()
        rfm_data = await compute_rfm(db, ref, start_date, end_date)
        customer_segments = {
            c["customer_id"]: _map_segment_label(c.get("segment", ""))
            for c in rfm_data
        }

        customer_query = (
            select(
                Transaction.stock_code,
                Transaction.customer_id,
                func.count().label("cnt"),
            )
            .where(
                Transaction.stock_code.in_(codes),
                Transaction.customer_id.isnot(None),
                *filters,
            )
            .group_by(Transaction.stock_code, Transaction.customer_id)
        )
        customer_result = await db.execute(customer_query)

        stock_segment_counts = defaultdict(lambda: defaultdict(int))
        for row in customer_result.all():
            segment = customer_segments.get(row.customer_id, "Lost")
            stock_segment_counts[row.stock_code][segment] += row.cnt

        primary_segments = {}
        for code in codes:
            seg_counts = stock_segment_counts.get(code)
            if seg_counts:
                primary_segments[code] = max(seg_counts, key=seg_counts.get)
            else:
                primary_segments[code] = "Unknown"
        return primary_segments

    # Helper to get aggregates (qty, rev) for a list of stock codes
    async def get_aggregates(codes):
        if not codes:
            return {}
        agg_query = (
            select(
                Transaction.stock_code,
                func.sum(Transaction.quantity).label("total_qty"),
                func.sum(Transaction.quantity * Transaction.unit_price).label("total_rev")
            )
            .where(Transaction.stock_code.in_(codes), *filters)
            .group_by(Transaction.stock_code)
        )
        agg_result = await db.execute(agg_query)
        return {
            row.stock_code: {"qty": row.total_qty or 0, "rev": float(row.total_rev or 0)}
            for row in agg_result.all()
        }

    final_stock_codes = []
    total_count = 0
    page_segments = {}
    page_aggregates = {}

    if segment_filter:
        # 1. Fetch ALL matching stock codes
        all_codes_query = (
            select(Transaction.stock_code)
            .where(*filters)
            .group_by(Transaction.stock_code)
        )
        all_codes_result = await db.execute(all_codes_query)
        all_codes = [row[0] for row in all_codes_result.all()]
        
        if not all_codes:
             return StockItemGridResponse(total=0, items=[])

        # 2. Compute segments
        segments_map = await compute_segments_for_items(all_codes)
        
        # 3. Filter
        filtered_codes = [
            code for code in all_codes 
            if segments_map.get(code) == segment_filter
        ]
        total_count = len(filtered_codes)
        
        if not filtered_codes:
             return StockItemGridResponse(total=0, items=[])

        # 4. Get aggregates for sorting
        aggregates_map = await get_aggregates(filtered_codes)
        
        # 5. Sort
        def get_sort_key(code):
            agg = aggregates_map.get(code, {"qty": 0, "rev": 0})
            if sort_by == "quantity_asc":
                return agg["qty"]
            elif sort_by == "quantity_desc":
                return -agg["qty"]
            elif sort_by == "revenue_asc":
                return agg["rev"]
            elif sort_by == "revenue_desc":
                return -agg["rev"]
            return code

        filtered_codes.sort(key=get_sort_key)
        
        # 6. Paginate
        final_stock_codes = filtered_codes[sanitized_offset : sanitized_offset + sanitized_limit]
        
        page_segments = segments_map
        page_aggregates = aggregates_map

    else:
        # No segment filter - use SQL optimization
        
        # Count total
        count_query = (
            select(func.count(func.distinct(Transaction.stock_code)))
            .where(*filters)
        )
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0
        
        if total_count == 0:
            return StockItemGridResponse(total=0, items=[])

        # Build query with sorting
        stock_query = (
            select(
                Transaction.stock_code,
                func.sum(Transaction.quantity).label("total_qty"),
                func.sum(Transaction.quantity * Transaction.unit_price).label("total_rev")
            )
            .where(*filters)
            .group_by(Transaction.stock_code)
        )
        
        if sort_by == "quantity_asc":
            stock_query = stock_query.order_by(func.sum(Transaction.quantity).asc())
        elif sort_by == "quantity_desc":
            stock_query = stock_query.order_by(func.sum(Transaction.quantity).desc())
        elif sort_by == "revenue_asc":
            stock_query = stock_query.order_by(func.sum(Transaction.quantity * Transaction.unit_price).asc())
        elif sort_by == "revenue_desc":
            stock_query = stock_query.order_by(func.sum(Transaction.quantity * Transaction.unit_price).desc())
        else:
            stock_query = stock_query.order_by(Transaction.stock_code)
            
        stock_query = stock_query.offset(sanitized_offset).limit(sanitized_limit)
        
        stock_result = await db.execute(stock_query)
        rows = stock_result.all()
        final_stock_codes = [row.stock_code for row in rows]
        
        page_aggregates = {
            row.stock_code: {"qty": row.total_qty or 0, "rev": float(row.total_rev or 0)}
            for row in rows
        }
        
        page_segments = await compute_segments_for_items(final_stock_codes)

    if not final_stock_codes:
        return StockItemGridResponse(total=total_count, items=[])

    # Get elasticity data
    elasticity_response = await calculate_elasticity(
        db=db,
        stock_codes=final_stock_codes,
        start_date=start_date,
        end_date=end_date,
        limit=len(final_stock_codes),
    )
    elasticity_map = {r.stock_code: r for r in elasticity_response.results}

    # Get purchase frequency (distinct invoices)
    freq_query = (
        select(
            Transaction.stock_code,
            func.count(func.distinct(Transaction.invoice_no)).label("freq"),
        )
        .where(Transaction.stock_code.in_(final_stock_codes), *filters)
        .group_by(Transaction.stock_code)
    )
    freq_result = await db.execute(freq_query)
    freq_map = {row.stock_code: row.freq for row in freq_result.all()}

    # Get descriptions
    desc_query = (
        select(
            Transaction.stock_code,
            func.max(Transaction.description).label("description"),
        )
        .where(Transaction.stock_code.in_(final_stock_codes))
        .group_by(Transaction.stock_code)
    )
    desc_result = await db.execute(desc_query)
    desc_map = {row.stock_code: row.description for row in desc_result.all()}

    # Build response items
    items = []
    for stock_code in final_stock_codes:
        elasticity_data = elasticity_map.get(stock_code)
        frequency = freq_map.get(stock_code, 0)
        segment = page_segments.get(stock_code, "Unknown")
        description = desc_map.get(stock_code, "")
        agg = page_aggregates.get(stock_code, {"qty": 0, "rev": 0})

        if elasticity_data:
            elasticity = elasticity_data.elasticity
            revenue_potential = elasticity * -1
        else:
            elasticity = 0.0
            revenue_potential = 0.0

        items.append(StockItemGridItem(
            id=stock_code,
            itemName=description or stock_code,
            elasticity=round(elasticity, 3),
            purchaseFrequency=frequency,
            revenuePotential=round(revenue_potential, 3),
            segment=segment,
            totalQuantity=agg["qty"],
            totalRevenue=round(agg["rev"], 2)
        ))

    return StockItemGridResponse(total=total_count, items=items)


async def get_stock_item_detail(
    db: AsyncSession,
    stock_code: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Optional[StockItemDetail]:
    """
    Get detailed stock item info with elasticity data.

    Args:
        db: Database session
        stock_code: Product SKU
        start_date: Start of analysis period
        end_date: End of analysis period

    Returns:
        StockItemDetail or None if not found
    """
    elasticity_response = await calculate_elasticity(
        db=db,
        stock_codes=[stock_code],
        start_date=start_date,
        end_date=end_date,
        limit=1,
    )

    if not elasticity_response.results:
        # Check if stock code exists at all
        check_query = (
            select(
                Transaction.stock_code,
                func.max(Transaction.description).label("description"),
                func.avg(Transaction.unit_price).label("avg_price"),
                func.sum(Transaction.quantity).label("total_qty"),
                func.sum(Transaction.quantity * Transaction.unit_price).label("revenue"),
            )
            .where(Transaction.stock_code == stock_code)
            .group_by(Transaction.stock_code)
        )
        check_result = await db.execute(check_query)
        row = check_result.first()

        if not row:
            return None

        return StockItemDetail(
            id=stock_code,
            itemName=row.description or stock_code,
            elasticity=0.0,
            rSquared=0.0,
            avgPrice=round(float(row.avg_price or 0), 2),
            totalQuantity=int(row.total_qty or 0),
            totalRevenue=round(float(row.revenue or 0), 2),
            sampleSize=0,
        )

    result = elasticity_response.results[0]
    total_revenue = result.avg_price * result.total_quantity

    return StockItemDetail(
        id=result.stock_code,
        itemName=result.description or stock_code,
        elasticity=result.elasticity,
        rSquared=result.r_squared,
        avgPrice=result.avg_price,
        totalQuantity=result.total_quantity,
        totalRevenue=round(total_revenue, 2),
        sampleSize=result.sample_size,
    )
