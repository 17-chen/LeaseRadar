"""Durable jobs and next source schedule."""
from alembic import op
from sqlalchemy import inspect, Column, String
from app.db import Job
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    # Initial metadata migration includes these on a brand-new install.
    if 'next_run_at' not in {c['name'] for c in inspect(bind).get_columns('sources')}:
        op.add_column('sources', Column('next_run_at', String(), nullable=True))
    Job.__table__.create(bind, checkfirst=True)

def downgrade():
    raise RuntimeError('Restore a backup instead of destructive downgrade.')
