"""Resumable backfill and bounded retry."""
from alembic import op
import sqlalchemy as sa
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

def upgrade():
    # 0002 on older installations may create jobs from current metadata.
    columns = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('jobs')}
    for name, type_, default in [('kind', sa.String(), 'front'), ('attempts', sa.Integer(), '0'), ('retry_at', sa.String(), None)]:
        if name not in columns:
            op.add_column('jobs', sa.Column(name, type_, nullable=default is None, server_default=default))
    op.add_column('sources', sa.Column('backfill_page', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('sources', sa.Column('backfill_at', sa.String(), nullable=True))
    op.add_column('sources', sa.Column('total_pages', sa.Integer(), nullable=True))

def downgrade():
    raise RuntimeError('Restore a backup instead of destructive downgrade.')
