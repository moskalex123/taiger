"""Add provider column to models table

Revision ID: fcfc4d7d3173
Revises: 4c7045ec4da8
Create Date: 2025-08-05 11:47:23.386859

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fcfc4d7d3173'
down_revision: Union[str, None] = '4c7045ec4da8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем столбец provider в таблицу models
    op.add_column('models', sa.Column('provider', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    # Удаляем столбец provider из таблицы models
    op.drop_column('models', 'provider')
