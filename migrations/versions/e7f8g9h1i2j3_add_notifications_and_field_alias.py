"""Add notifications and gforms field alias

Revision ID: e7f8g9h1i2j3
Revises: a1b2c3d4e5f6
Create Date: 2026-02-07 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7f8g9h1i2j3'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add field_alias to gforms_field_mapping
    with op.batch_alter_table('gforms_field_mapping', schema=None) as batch_op:
        batch_op.add_column(sa.Column('field_alias', sa.String(length=100), nullable=True))

    # 2. Create event_notification table
    op.create_table('event_notification',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['event.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('event_notification')
    
    with op.batch_alter_table('gforms_field_mapping', schema=None) as batch_op:
        batch_op.drop_column('field_alias')
