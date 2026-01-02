"""Transaction CRUD endpoints module."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.database import get_db
from api.models.transaction import Transaction
from api.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionBatchCreate,
    TransactionBatchResponse,
    TransactionListResponse,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction: TransactionCreate,
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Create a single transaction."""
    db_transaction = Transaction(
        invoice_no=transaction.invoice_no,
        stock_code=transaction.stock_code,
        description=transaction.description,
        quantity=transaction.quantity,
        invoice_date=transaction.invoice_date,
        unit_price=transaction.unit_price,
        customer_id=transaction.customer_id,
        country=transaction.country,
    )
    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)
    return TransactionResponse.model_validate(db_transaction)


@router.post("/batch", response_model=TransactionBatchResponse, status_code=status.HTTP_201_CREATED)
async def create_transactions_batch(
    batch: TransactionBatchCreate,
    db: AsyncSession = Depends(get_db),
) -> TransactionBatchResponse:
    """
    Batch create multiple transactions.

    Ideal for uploading CSV/Excel data in bulk.
    """
    db_transactions = [
        Transaction(
            invoice_no=t.invoice_no,
            stock_code=t.stock_code,
            description=t.description,
            quantity=t.quantity,
            invoice_date=t.invoice_date,
            unit_price=t.unit_price,
            customer_id=t.customer_id,
            country=t.country,
        )
        for t in batch.transactions
    ]
    db.add_all(db_transactions)
    await db.commit()
    return TransactionBatchResponse(
        created=len(db_transactions),
        message=f"Successfully created {len(db_transactions)} transaction(s)",
    )


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    stock_code: Optional[str] = Query(None, description="Filter by stock code"),
    country: Optional[str] = Query(None, description="Filter by country"),
    db: AsyncSession = Depends(get_db),
) -> TransactionListResponse:
    """
    List transactions with pagination and optional filters.
    """
    # Build base query
    query = select(Transaction)

    # Apply filters
    if stock_code:
        query = query.where(Transaction.stock_code == stock_code)
    if country:
        query = query.where(Transaction.country == country)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Calculate pagination
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    offset = (page - 1) * page_size

    # Get paginated results
    query = query.offset(offset).limit(page_size).order_by(Transaction.invoice_date.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return TransactionListResponse(
        items=[TransactionResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Get a single transaction by ID."""
    query = select(Transaction).where(Transaction.id == transaction_id)
    result = await db.execute(query)
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {transaction_id} not found",
        )

    return TransactionResponse.model_validate(transaction)


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    transaction_update: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Update a transaction by ID."""
    query = select(Transaction).where(Transaction.id == transaction_id)
    result = await db.execute(query)
    db_transaction = result.scalar_one_or_none()

    if not db_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {transaction_id} not found",
        )

    # Update only provided fields
    update_data = transaction_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_transaction, field, value)

    await db.commit()
    await db.refresh(db_transaction)
    return TransactionResponse.model_validate(db_transaction)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a transaction by ID."""
    query = select(Transaction).where(Transaction.id == transaction_id)
    result = await db.execute(query)
    db_transaction = result.scalar_one_or_none()

    if not db_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {transaction_id} not found",
        )

    await db.delete(db_transaction)
    await db.commit()


@router.delete("", status_code=status.HTTP_200_OK)
async def delete_all_transactions(
    confirm: bool = Query(False, description="Confirm deletion of all transactions"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete all transactions.

    Requires confirm=true query parameter as safety measure.
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please confirm deletion by setting confirm=true",
        )

    result = await db.execute(delete(Transaction))
    await db.commit()
    deleted_count = result.rowcount

    return {"deleted": deleted_count, "message": f"Successfully deleted {deleted_count} transaction(s)"}
