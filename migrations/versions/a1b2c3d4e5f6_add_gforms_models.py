"""Add GForms models

Revision ID: a1b2c3d4e5f6
Revises: 30c55a7b1cdd
Create Date: 2026-02-07 09:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '30c55a7b1cdd'
branch_labels = None
depends_on = None


def upgrade():
    # Helper to check if table exists (to avoid failure if already manually created)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    # 1. GFormsCategory
    if 'gforms_category' not in tables:
        op.create_table('gforms_category',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('event_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('color', sa.String(length=20), nullable=True),
            sa.Column('position', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['event_id'], ['event.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    # 2. GFormsFieldMapping
    if 'gforms_field_mapping' not in tables:
        op.create_table('gforms_field_mapping',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('event_id', sa.Integer(), nullable=False),
            sa.Column('field_name', sa.String(length=200), nullable=False),
            sa.Column('category_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['category_id'], ['gforms_category.id'], ),
            sa.ForeignKeyConstraint(['event_id'], ['event.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('event_id', 'field_name', name='uq_event_field')
        )

    # 3. GFormsSubmission
    if 'gforms_submission' not in tables:
        op.create_table('gforms_submission',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('event_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('email', sa.String(length=120), nullable=False),
            sa.Column('timestamp', sa.DateTime(), nullable=False),
            sa.Column('type_ajout', sa.String(length=20), nullable=True),
            sa.Column('form_response_id', sa.Integer(), nullable=True),
            sa.Column('raw_data', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['event_id'], ['event.id'], ),
            sa.ForeignKeyConstraint(['form_response_id'], ['form_response.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes
        op.create_index('idx_gforms_submission_email', 'gforms_submission', ['email'], unique=False)
        op.create_index('idx_gforms_submission_event', 'gforms_submission', ['event_id'], unique=False)
        op.create_index('idx_gforms_submission_timestamp', 'gforms_submission', ['timestamp'], unique=False)


def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    if 'gforms_submission' in tables:
        op.drop_index('idx_gforms_submission_timestamp', table_name='gforms_submission')
        op.drop_index('idx_gforms_submission_event', table_name='gforms_submission')
        op.drop_index('idx_gforms_submission_email', table_name='gforms_submission')
        op.drop_table('gforms_submission')
    
    if 'gforms_field_mapping' in tables:
        op.drop_table('gforms_field_mapping')
    
    if 'gforms_category' in tables:
        op.drop_table('gforms_category')
