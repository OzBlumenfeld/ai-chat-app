"""add_request_history_table

Revision ID: e9656007d6d5
Revises: eba4b5a3506f
Create Date: 2026-02-10 18:06:33.518574

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e9656007d6d5'
down_revision: Union[str, Sequence[str], None] = 'eba4b5a3506f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'request_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('response_file_path', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['request_id'], ['requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_request_history_user_id'), 'request_history', ['user_id'], unique=False)
    op.create_index(op.f('ix_request_history_request_id'), 'request_history', ['request_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_request_history_request_id'), table_name='request_history')
    op.drop_index(op.f('ix_request_history_user_id'), table_name='request_history')
    op.drop_table('request_history')
