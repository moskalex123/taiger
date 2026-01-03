"""add payments table

Revision ID: h1234567891
Revises: fcfc4d7d3173
Create Date: 2025-12-29 15:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'h1234567891'
down_revision = 'fcfc4d7d3173'
branch_labels = None
depends_on = None


def upgrade():
    # Создаём таблицу payments
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('currency_type', sa.String(length=50), nullable=False, server_default='stars'),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('batteries_received', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('telegram_invoice_id', sa.String(length=100), nullable=True),
        sa.Column('telegram_pre_checkout_id', sa.String(length=100), nullable=True),
        sa.Column('external_transaction_id', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_pre_checkout_id')
    )
    
    # Создаём индексы для оптимизации запросов
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])
    op.create_index('ix_payments_status', 'payments', ['status'])
    op.create_index('ix_payments_created_at', 'payments', ['created_at'])


def downgrade():
    op.drop_index('ix_payments_created_at', table_name='payments')
    op.drop_index('ix_payments_status', table_name='payments')
    op.drop_index('ix_payments_user_id', table_name='payments')
    op.drop_table('payments')