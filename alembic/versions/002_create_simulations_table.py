"""Create simulations table

Revision ID: 002
Revises: 001
Create Date: 2026-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'simulations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('stock_item_ref', sa.String(20), nullable=False),
        sa.Column('price_range', postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_simulations_stock_item_ref'),
        'simulations',
        ['stock_item_ref'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_simulations_stock_item_ref'), table_name='simulations')
    op.drop_table('simulations')
