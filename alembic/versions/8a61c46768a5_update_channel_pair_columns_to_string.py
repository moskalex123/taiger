"""update_channel_pair_columns_to_string

Revision ID: 8a61c46768a5
Revises: d6fccac46a81
Create Date: 2025-05-30 11:51:04.237874

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a61c46768a5'
down_revision: Union[str, None] = 'd6fccac46a81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
