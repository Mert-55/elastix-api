"""Create transactions table

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_no', sa.String(20), nullable=False),
        sa.Column('stock_code', sa.String(20), nullable=False),
        sa.Column('description', sa.String(256), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('invoice_date', sa.DateTime(), nullable=False),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('customer_id', sa.String(20), nullable=True),
        sa.Column('country', sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_invoice_no'), 'transactions', ['invoice_no'], unique=False)
    op.create_index(op.f('ix_transactions_stock_code'), 'transactions', ['stock_code'], unique=False)
    op.create_index(op.f('ix_transactions_invoice_date'), 'transactions', ['invoice_date'], unique=False)
    op.create_index(op.f('ix_transactions_customer_id'), 'transactions', ['customer_id'], unique=False)
    op.create_index(op.f('ix_transactions_country'), 'transactions', ['country'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_transactions_country'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_customer_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_invoice_date'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_stock_code'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_invoice_no'), table_name='transactions')
    op.drop_table('transactions')
