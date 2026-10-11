"""Independent email receipts, preserving the business outbox."""
from alembic import op
import sqlalchemy as sa
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('email_deliveries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('outbox_id', sa.Integer(), sa.ForeignKey('notification_outbox.id'), nullable=False, unique=True),
        sa.Column('recipient', sa.String(), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        *[sa.Column(name, sa.String(), nullable=True) for name in
          ('retry_at', 'lease_until', 'token', 'error', 'accepted_at')])

def downgrade():
    op.drop_table('email_deliveries')
