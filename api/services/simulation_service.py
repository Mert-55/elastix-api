"""Simulation service module.

Implements price change simulation using elasticity theory.
Formula: %ΔQ ≈ ε × %ΔP (Paczkowski, 2018)

Provides:
- Quick simulation for single product
- CRUD operations for saved simulations
- Segment-based simulation metrics
"""
from collections import defaultdict
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.simulation import Simulation
from api.models.transaction import Transaction
from api.schemas.simulation import (
    SimulationRequest,
    SimulationResult,
    SimulationCreate,
    SimulationUpdate,
    SimulationResponse,
    SimulationListResponse,
    SimulationMetricsResponse,
    SegmentSimulationMetrics,
)
from api.services.elasticity_service import calculate_elasticity
from api.services.rfm_service import compute_rfm
from api.services.segmented_elasticity_service import elasticity_by_segment
from api.services.dashboard_service import _map_segment_label, RFM_SEGMENT_MAP


async def simulate_price_change(
    db: AsyncSession,
    request: SimulationRequest,
) -> SimulationResult | None:
    """
    Simulate demand and revenue impact of a price change.

    Uses the product's elasticity to project:
    - New quantity: Q_new = Q_current × (1 + ε × %ΔP/100)
    - New revenue: R_new = P_new × Q_new
    """
    # Get elasticity for the product
    elasticity_response = await calculate_elasticity(
        db=db,
        stock_codes=[request.stock_code],
    )

    if not elasticity_response.results:
        return None

    product = elasticity_response.results[0]

    # Current state
    current_price = product.avg_price
    current_quantity = product.total_quantity
    current_revenue = current_price * current_quantity
    elasticity = product.elasticity

    # Calculate projections: %ΔQ = ε × %ΔP
    price_change_ratio = request.price_change_percent / 100
    quantity_change_ratio = elasticity * price_change_ratio

    projected_price = current_price * (1 + price_change_ratio)
    projected_quantity = max(0, round(current_quantity * (1 + quantity_change_ratio)))
    projected_revenue = projected_price * projected_quantity

    # Deltas
    quantity_change_percent = quantity_change_ratio * 100
    revenue_delta = projected_revenue - current_revenue
    revenue_change_percent = (
        (revenue_delta / current_revenue * 100) if current_revenue > 0 else 0.0
    )

    return SimulationResult(
        stock_code=product.stock_code,
        description=product.description,
        current_price=round(current_price, 2),
        current_quantity=current_quantity,
        current_revenue=round(current_revenue, 2),
        price_change_percent=request.price_change_percent,
        elasticity=product.elasticity,
        r_squared=product.r_squared,
        projected_price=round(projected_price, 2),
        projected_quantity=projected_quantity,
        projected_revenue=round(projected_revenue, 2),
        quantity_change_percent=round(quantity_change_percent, 2),
        revenue_change_percent=round(revenue_change_percent, 2),
        revenue_delta=round(revenue_delta, 2),
    )


# --- CRUD Operations for Saved Simulations ---


async def create_simulation(
    db: AsyncSession,
    data: SimulationCreate,
) -> SimulationResponse:
    """Create a new saved simulation."""
    simulation = Simulation(
        name=data.name,
        description=data.description,
        stock_item_ref=data.stock_item_ref,
        price_range=data.price_range,
    )
    db.add(simulation)
    await db.commit()
    await db.refresh(simulation)

    return SimulationResponse(
        simulationId=simulation.id,
        name=simulation.name,
        description=simulation.description,
        stockItemRef=simulation.stock_item_ref,
        priceRange=simulation.price_range,
    )


async def get_simulation(
    db: AsyncSession,
    simulation_id: UUID,
) -> Optional[SimulationResponse]:
    """Get a simulation by ID."""
    query = select(Simulation).where(Simulation.id == simulation_id)
    result = await db.execute(query)
    simulation = result.scalar_one_or_none()

    if not simulation:
        return None

    return SimulationResponse(
        simulationId=simulation.id,
        name=simulation.name,
        description=simulation.description,
        stockItemRef=simulation.stock_item_ref,
        priceRange=simulation.price_range,
    )


async def list_simulations(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> SimulationListResponse:
    """List all saved simulations."""
    # Count total
    count_query = select(func.count()).select_from(Simulation)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Fetch items
    query = (
        select(Simulation)
        .order_by(Simulation.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    simulations = result.scalars().all()

    items = [
        SimulationResponse(
            simulationId=s.id,
            name=s.name,
            description=s.description,
            stockItemRef=s.stock_item_ref,
            priceRange=s.price_range,
        )
        for s in simulations
    ]

    return SimulationListResponse(total=total, items=items)


async def update_simulation(
    db: AsyncSession,
    simulation_id: UUID,
    data: SimulationUpdate,
) -> Optional[SimulationResponse]:
    """Update a saved simulation."""
    query = select(Simulation).where(Simulation.id == simulation_id)
    result = await db.execute(query)
    simulation = result.scalar_one_or_none()

    if not simulation:
        return None

    if data.name is not None:
        simulation.name = data.name
    if data.description is not None:
        simulation.description = data.description
    if data.price_range is not None:
        simulation.price_range = data.price_range

    await db.commit()
    await db.refresh(simulation)

    return SimulationResponse(
        simulationId=simulation.id,
        name=simulation.name,
        description=simulation.description,
        stockItemRef=simulation.stock_item_ref,
        priceRange=simulation.price_range,
    )


async def delete_simulation(
    db: AsyncSession,
    simulation_id: UUID,
) -> bool:
    """Delete a saved simulation. Returns True if deleted."""
    query = select(Simulation).where(Simulation.id == simulation_id)
    result = await db.execute(query)
    simulation = result.scalar_one_or_none()

    if not simulation:
        return False

    await db.delete(simulation)
    await db.commit()
    return True


# --- Segment-Based Simulation Metrics ---


async def compute_simulation_metrics(
    db: AsyncSession,
    simulation_id: UUID,
    reference_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Optional[SimulationMetricsResponse]:
    """
    Compute segment-based simulation metrics for a saved simulation.

    Uses the simulation's price_range to calculate impact on each segment.
    Applies elasticity formula: %ΔQ = ε × %ΔP

    Args:
        db: Database session
        simulation_id: UUID of the saved simulation
        reference_date: Date for RFM recency calculation
        start_date: Start of analysis period
        end_date: End of analysis period

    Returns:
        SimulationMetricsResponse with per-segment metrics or None if not found
    """
    # Get the simulation
    simulation = await get_simulation(db, simulation_id)
    if not simulation:
        return None

    stock_code = simulation.stock_item_ref
    price_range = simulation.price_range  # [from, to, step]

    # Use the middle of the price range for calculation
    price_change_percent = (price_range[0] + price_range[1]) / 2

    ref = reference_date or date.today()

    # Get current data per segment
    rfm_data = await compute_rfm(db, ref, start_date, end_date)

    # Group customers by segment
    customer_segments = {
        c["customer_id"]: _map_segment_label(c.get("segment", ""))
        for c in rfm_data
    }

    # Get transactions for this stock code grouped by customer
    filters = [
        Transaction.stock_code == stock_code,
        Transaction.customer_id.isnot(None),
    ]
    if start_date:
        filters.append(Transaction.invoice_date >= start_date)
    if end_date:
        filters.append(Transaction.invoice_date <= end_date)

    query = (
        select(
            Transaction.customer_id,
            func.sum(Transaction.quantity).label("qty"),
            func.sum(Transaction.quantity * Transaction.unit_price).label("revenue"),
        )
        .where(*filters)
        .group_by(Transaction.customer_id)
        .having(func.sum(Transaction.quantity) > 0)
    )

    result = await db.execute(query)
    rows = result.all()

    # Aggregate by segment
    segment_data: dict[str, dict] = defaultdict(
        lambda: {"quantity": 0, "revenue": 0.0}
    )

    for row in rows:
        segment = customer_segments.get(row.customer_id, "Lost")
        segment_data[segment]["quantity"] += int(row.qty)
        segment_data[segment]["revenue"] += float(row.revenue)

    # Get elasticity per segment
    segment_elasticities: dict[str, float] = {}
    for raw_segment in set(RFM_SEGMENT_MAP.keys()):
        try:
            elasticity_results = await elasticity_by_segment(
                db, raw_segment, reference_date, start_date, end_date
            )
            # Find elasticity for our stock code
            for r in elasticity_results:
                if r.stock_code == stock_code:
                    label = _map_segment_label(raw_segment)
                    segment_elasticities[label] = r.elasticity
                    break
        except Exception:
            pass

    # Compute metrics for each segment
    def _compute_segment_metrics(segment_name: str) -> SegmentSimulationMetrics:
        data = segment_data.get(segment_name, {"quantity": 0, "revenue": 0.0})
        current_qty = data["quantity"]
        current_revenue = data["revenue"]

        # Get segment elasticity or use average
        elasticity = segment_elasticities.get(segment_name, -1.0)

        # Calculate projections: %ΔQ = ε × %ΔP
        price_change_ratio = price_change_percent / 100
        quantity_change_ratio = elasticity * price_change_ratio

        projected_qty = max(0, round(current_qty * (1 + quantity_change_ratio)))
        # Revenue changes with both price and quantity
        projected_revenue = current_revenue * (1 + price_change_ratio) * (1 + quantity_change_ratio)

        delta_qty_pct = quantity_change_ratio * 100
        delta_rev_pct = (
            ((projected_revenue - current_revenue) / current_revenue * 100)
            if current_revenue > 0
            else 0.0
        )

        return SegmentSimulationMetrics(
            priceChangePercent=round(price_change_percent, 1),
            quantity=projected_qty,
            revenue=round(projected_revenue, 2),
            deltaQuantityPercent=round(delta_qty_pct, 1),
            deltaRevenuePercent=round(delta_rev_pct, 1),
        )

    return SimulationMetricsResponse(
        Champions=_compute_segment_metrics("Champion"),
        LoyalCustomers=_compute_segment_metrics("LoyalCustomers"),
        PotentialLoyalists=_compute_segment_metrics("PotentialLoyalists"),
        AtRisk=_compute_segment_metrics("AtRisk"),
        Hibernating=_compute_segment_metrics("Hibernating"),
        Lost=_compute_segment_metrics("Lost"),
    )
