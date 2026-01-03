"""Change original_message_id to BigInteger

Revision ID: g1234567890
Revises: fcfc4d7d3173
Create Date: 2025-12-13 15:06:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g1234567890'
down_revision: Union[str, None] = 'fcfc4d7d3173'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change original_message_id from String to BigInteger
    op.alter_column('scheduled_posts', 'original_message_id',
                    existing_type=sa.String(),
                    type_=sa.BigInteger(),
                    existing_nullable=True)


def downgrade() -> None:
    # Change original_message_id back from BigInteger to String
    op.alter_column('scheduled_posts', 'original_message_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.String(),
                    existing_nullable=True)