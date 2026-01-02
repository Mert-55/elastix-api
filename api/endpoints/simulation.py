"""Simulation endpoint module.

Provides endpoints for:
- Quick simulation (POST /simulate)
- CRUD operations for saved simulations
- Segment-based simulation metrics
"""
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.database import get_db
from api.schemas.simulation import (
    SimulationRequest,
    SimulationResult,
    SimulationCreate,
    SimulationUpdate,
    SimulationResponse,
    SimulationListResponse,
    SimulationMetricsResponse,
)
from api.services.simulation_service import (
    simulate_price_change,
    create_simulation,
    get_simulation,
    list_simulations,
    update_simulation,
    delete_simulation,
    compute_simulation_metrics,
)

router = APIRouter(tags=["simulation"])


# --- Quick Simulation ---


@router.post("/simulate", response_model=SimulationResult)
async def run_simulation(
    request: SimulationRequest,
    db: AsyncSession = Depends(get_db),
) -> SimulationResult:
    """
    Simulate the impact of a price change on demand and revenue.

    Uses the product's calculated price elasticity to project:
    - Expected quantity change (based on elasticity × price change)
    - Expected revenue change

    Formula: %ΔQuantity ≈ Elasticity × %ΔPrice (Paczkowski, 2018)
    """
    result = await simulate_price_change(db=db, request=request)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{request.stock_code}' not found or insufficient data",
        )

    return result


# --- CRUD for Saved Simulations ---


@router.get("/simulations", response_model=SimulationListResponse)
async def get_simulations(
    limit: int = Query(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of simulations to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of simulations to skip (for pagination)",
    ),
    db: AsyncSession = Depends(get_db),
) -> SimulationListResponse:
    """
    List all saved simulations.

    Returns paginated list of simulation configurations.
    """
    return await list_simulations(db=db, limit=limit, offset=offset)


@router.post(
    "/simulations",
    response_model=SimulationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_simulation(
    data: SimulationCreate,
    db: AsyncSession = Depends(get_db),
) -> SimulationResponse:
    """
    Create a new saved simulation.

    Required fields:
    - **name**: Simulation name
    - **stockItemRef**: Stock code / SKU reference
    - **priceRange**: Price range as [from, to, step] percentage values

    Optional fields:
    - **description**: Optional description
    """
    return await create_simulation(db=db, data=data)


@router.get("/simulations/{simulation_id}", response_model=SimulationResponse)
async def get_simulation_by_id(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SimulationResponse:
    """
    Get a saved simulation by ID.
    """
    result = await get_simulation(db=db, simulation_id=simulation_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation '{simulation_id}' not found",
        )

    return result


@router.put("/simulations/{simulation_id}", response_model=SimulationResponse)
async def update_simulation_by_id(
    simulation_id: UUID,
    data: SimulationUpdate,
    db: AsyncSession = Depends(get_db),
) -> SimulationResponse:
    """
    Update a saved simulation.

    All fields are optional (partial update supported):
    - **name**: Simulation name
    - **description**: Optional description
    - **priceRange**: Price range as [from, to, step]
    """
    result = await update_simulation(db=db, simulation_id=simulation_id, data=data)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation '{simulation_id}' not found",
        )

    return result


@router.delete(
    "/simulations/{simulation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_simulation_by_id(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a saved simulation.
    """
    deleted = await delete_simulation(db=db, simulation_id=simulation_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation '{simulation_id}' not found",
        )


# --- Simulation Metrics ---


@router.get(
    "/simulations/{simulation_id}/metrics",
    response_model=SimulationMetricsResponse,
)
async def get_simulation_metrics(
    simulation_id: UUID,
    start_date: Optional[date] = Query(
        default=None,
        description="Start of analysis period (ISO 8601 format)",
    ),
    end_date: Optional[date] = Query(
        default=None,
        description="End of analysis period (ISO 8601 format)",
    ),
    db: AsyncSession = Depends(get_db),
) -> SimulationMetricsResponse:
    """
    Get segment-based simulation metrics.

    Calculates the projected impact of the simulation's price change
    on each customer segment using elasticity theory.

    Returns per-segment metrics:
    - **priceChangePercent**: Applied price change
    - **quantity**: Projected quantity
    - **revenue**: Projected revenue
    - **deltaQuantityPercent**: Quantity change percentage
    - **deltaRevenuePercent**: Revenue change percentage
    """
    result = await compute_simulation_metrics(
        db=db,
        simulation_id=simulation_id,
        start_date=start_date,
        end_date=end_date,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation '{simulation_id}' not found",
        )

    return result
