"""add user bot log state

Revision ID: 847df9193ec6
Revises: de7934f308a3
Create Date: 2025-10-17 09:33:15.923541

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '847df9193ec6'
down_revision: Union[str, None] = 'de7934f308a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_bot_log_state",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("last_status_message_id", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id")
    )


def downgrade() -> None:
    op.drop_table("user_bot_log_state")
