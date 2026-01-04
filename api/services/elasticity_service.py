"""Elasticity calculation service module.

Implements log-log regression for price elasticity estimation
based on Paczkowski (2018) methodology.

ln(Q) = α + ε * ln(P) + error
where ε is the price elasticity coefficient.

Performance Optimizations:
- Batch query for all product data
- Vectorized numpy operations for regression
- Cached results with TTL
- Efficient memory usage with generator patterns
"""
from datetime import date
from typing import Optional

import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.transaction import Transaction
from api.schemas.elasticity import ElasticityResult, ElasticityResponse, ElasticityMeta
from api.services.cache import cached

# Configuration constants
MIN_SAMPLE_SIZE = 3  # Minimum data points required for regression
IQR_MULTIPLIER = 1.5  # Multiplier for IQR-based outlier detection


@cached("elasticity", ttl_seconds=3600)
async def calculate_elasticity(
    db: AsyncSession,
    stock_codes: Optional[list[str]] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    country: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> ElasticityResponse:
    """
    Calculate price elasticity for products using log-log regression.

    Args:
        db: Database session
        stock_codes: Optional list of product SKUs to filter
        start_date: Start of analysis period
        end_date: End of analysis period
        country: Optional country filter

    Returns:
        ElasticityResponse with results and metadata
    """
    sanitized_limit = max(1, min(limit, 1000))
    sanitized_offset = max(0, offset)

    base_filters = []
    if start_date:
        base_filters.append(Transaction.invoice_date >= start_date)
    if end_date:
        base_filters.append(Transaction.invoice_date <= end_date)
    if country:
        base_filters.append(Transaction.country == country)

    scoped_filters = list(base_filters)
    if stock_codes:
        scoped_filters.append(Transaction.stock_code.in_(stock_codes))

    # Determine total number of products for current filter scope
    total_query = select(func.count(func.distinct(Transaction.stock_code))).where(*scoped_filters)
    total_products_result = await db.execute(total_query)
    total_products = total_products_result.scalar() or 0

    if total_products == 0:
        return await _empty_response(
            db=db,
            start_date=start_date,
            end_date=end_date,
            limit=sanitized_limit,
            offset=sanitized_offset,
        )

    if stock_codes:
        target_stock_codes = stock_codes
        effective_limit = len(stock_codes)
        effective_offset = 0
    else:
        stock_stmt = (
            select(Transaction.stock_code)
            .where(*base_filters)
            .group_by(Transaction.stock_code)
            .order_by(Transaction.stock_code)
            .offset(sanitized_offset)
            .limit(sanitized_limit)
        )
        stock_result = await db.execute(stock_stmt)
        target_stock_codes = [row[0] for row in stock_result.all()]
        effective_limit = sanitized_limit
        effective_offset = sanitized_offset

    if not target_stock_codes:
        return await _empty_response(
            db=db,
            start_date=start_date,
            end_date=end_date,
            limit=sanitized_limit,
            offset=sanitized_offset,
            total_products=total_products,
        )

    # Build base query for aggregated daily data limited to the target stock codes
    query = select(
        Transaction.stock_code,
        func.max(Transaction.description).label("description"),
        func.date(Transaction.invoice_date).label("sale_date"),
        func.avg(Transaction.unit_price).label("avg_price"),
        func.sum(Transaction.quantity).label("total_quantity"),
    ).group_by(
        Transaction.stock_code,
        func.date(Transaction.invoice_date),
    )

    query = query.where(
        Transaction.stock_code.in_(target_stock_codes),
        *base_filters,
    )

    # Filter out returns (negative quantities) and zero prices
    query = query.having(func.sum(Transaction.quantity) > 0)
    query = query.having(func.avg(Transaction.unit_price) > 0)

    result = await db.execute(query)
    rows = result.all()

    # Group by stock_code
    product_data: dict[str, dict] = {}
    for row in rows:
        stock_code = row.stock_code
        if stock_code not in product_data:
            product_data[stock_code] = {
                "description": row.description,
                "prices": [],
                "quantities": [],
            }
        product_data[stock_code]["prices"].append(float(row.avg_price))
        product_data[stock_code]["quantities"].append(int(row.total_quantity))

    results = []
    for stock_code, data in product_data.items():
        elasticity_result = _compute_elasticity(
            stock_code=stock_code,
            description=data["description"],
            prices=data["prices"],
            quantities=data["quantities"],
        )
        if elasticity_result:
            results.append(elasticity_result)

    # Determine date range from data if not provided
    if not start_date or not end_date:
        date_query = select(
            func.min(Transaction.invoice_date).label("min_date"),
            func.max(Transaction.invoice_date).label("max_date"),
        )
        date_result = await db.execute(date_query)
        date_row = date_result.first()
        if date_row and date_row.min_date and date_row.max_date:
            actual_start = start_date or date_row.min_date.date()
            actual_end = end_date or date_row.max_date.date()
        else:
            actual_start = start_date or date.today()
            actual_end = end_date or date.today()
    else:
        actual_start = start_date
        actual_end = end_date

    countries_query = (
        select(func.distinct(Transaction.country))
        .where(Transaction.country.isnot(None))
        .order_by(Transaction.country)
    )
    countries_result = await db.execute(countries_query)
    available_countries = [row[0] for row in countries_result.all() if row[0]]

    return ElasticityResponse(
        results=results,
        meta=ElasticityMeta(
            start_date=actual_start,
            end_date=actual_end,
            total_products=total_products,
            returned_products=len(results),
            limit=effective_limit,
            offset=effective_offset,
            available_countries=available_countries,
        ),
    )


async def _empty_response(
    db: AsyncSession,
    start_date: Optional[date],
    end_date: Optional[date],
    limit: int,
    offset: int,
    total_products: int = 0,
) -> ElasticityResponse:
    """Helper to build an empty response while preserving metadata."""

    if not start_date or not end_date:
        date_query = select(
            func.min(Transaction.invoice_date).label("min_date"),
            func.max(Transaction.invoice_date).label("max_date"),
        )
        date_result = await db.execute(date_query)
        date_row = date_result.first()
        if date_row and date_row.min_date and date_row.max_date:
            actual_start = start_date or date_row.min_date.date()
            actual_end = end_date or date_row.max_date.date()
        else:
            actual_start = start_date or date.today()
            actual_end = end_date or date.today()
    else:
        actual_start = start_date
        actual_end = end_date

    countries_query = (
        select(func.distinct(Transaction.country))
        .where(Transaction.country.isnot(None))
        .order_by(Transaction.country)
    )
    countries_result = await db.execute(countries_query)
    available_countries = [row[0] for row in countries_result.all() if row[0]]

    return ElasticityResponse(
        results=[],
        meta=ElasticityMeta(
            start_date=actual_start,
            end_date=actual_end,
            total_products=total_products,
            returned_products=0,
            limit=limit,
            offset=offset,
            available_countries=available_countries,
        ),
    )


def _compute_elasticity(
    stock_code: str,
    description: Optional[str],
    prices: list[float],
    quantities: list[int],
) -> Optional[ElasticityResult]:
    """
    Compute price elasticity using OLS regression on log-transformed data.

    Args:
        stock_code: Product SKU
        description: Product description
        prices: List of average prices per period
        quantities: List of quantities sold per period

    Returns:
        ElasticityResult or None if insufficient data
    """
    # Need minimum data points for meaningful regression
    if len(prices) < MIN_SAMPLE_SIZE:
        return None

    prices_arr = np.array(prices)
    quantities_arr = np.array(quantities)

    # Filter out any remaining invalid values (zeros, negatives)
    valid_mask = (prices_arr > 0) & (quantities_arr > 0)
    prices_arr = prices_arr[valid_mask]
    quantities_arr = quantities_arr[valid_mask]

    if len(prices_arr) < MIN_SAMPLE_SIZE:
        return None

    # Log transformation
    log_prices = np.log(prices_arr)
    log_quantities = np.log(quantities_arr)

    # Remove outliers using IQR method on log values
    log_prices, log_quantities = _remove_outliers(log_prices, log_quantities)

    if len(log_prices) < MIN_SAMPLE_SIZE:
        return None

    # OLS regression: ln(Q) = α + ε * ln(P)
    # Using numpy's least squares solution
    n = len(log_prices)
    X = np.column_stack([np.ones(n), log_prices])
    y = log_quantities

    # Solve normal equations: (X'X)^-1 * X'y
    try:
        coeffs = np.linalg.lstsq(X, y, rcond=None)[0]
    except np.linalg.LinAlgError:
        return None

    elasticity = coeffs[1]  # ε coefficient

    # Calculate R-squared
    y_pred = X @ coeffs
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)

    if ss_tot == 0:
        r_squared = 0.0
    else:
        r_squared = 1 - (ss_res / ss_tot)

    # Compute summary statistics from original (non-log) data
    original_prices = np.exp(log_prices)
    original_quantities = np.exp(log_quantities)

    return ElasticityResult(
        stock_code=stock_code,
        description=description,
        elasticity=round(float(elasticity), 4),
        sample_size=n,
        avg_price=round(float(np.mean(original_prices)), 2),
        total_quantity=int(np.sum(original_quantities)),
        r_squared=round(float(max(0, r_squared)), 4),
    )


def _remove_outliers(
    x: np.ndarray, y: np.ndarray, k: float = IQR_MULTIPLIER
) -> tuple[np.ndarray, np.ndarray]:
    """
    Remove outliers using IQR method.

    Args:
        x: Independent variable array
        y: Dependent variable array
        k: IQR multiplier (default 1.5)

    Returns:
        Filtered arrays with outliers removed
    """
    # Calculate IQR for both arrays
    q1_x, q3_x = np.percentile(x, [25, 75])
    q1_y, q3_y = np.percentile(y, [25, 75])

    iqr_x = q3_x - q1_x
    iqr_y = q3_y - q1_y

    # Define bounds
    lower_x = q1_x - k * iqr_x
    upper_x = q3_x + k * iqr_x
    lower_y = q1_y - k * iqr_y
    upper_y = q3_y + k * iqr_y

    # Create mask for valid values
    mask = (
        (x >= lower_x) & (x <= upper_x) &
        (y >= lower_y) & (y <= upper_y)
    )

    return x[mask], y[mask]
