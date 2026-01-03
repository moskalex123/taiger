"""Add timezone to datetimes and new fields to ScheduledPost

Revision ID: 76b2b11fb015
Revises: aa2cabe48113
Create Date: 2025-05-31 16:11:38.284607

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76b2b11fb015'
down_revision: Union[str, None] = 'aa2cabe48113'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
