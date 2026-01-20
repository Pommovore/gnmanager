"""Add casting validation fields

Revision ID: 2f8a1c3b4d5e
Revises: de72ed8ca734
Create Date: 2026-01-20 22:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f8a1c3b4d5e'
down_revision = 'de72ed8ca734'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_casting_validated to event table
    op.add_column('event', sa.Column('is_casting_validated', sa.Boolean(), nullable=True))
    op.execute("UPDATE event SET is_casting_validated = 0")
    
    # Add score to casting_assignment table
    op.add_column('casting_assignment', sa.Column('score', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('casting_assignment', 'score')
    op.drop_column('event', 'is_casting_validated')
