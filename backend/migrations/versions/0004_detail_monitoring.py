"""Active detail checks and idempotent, configurable deadline reminders."""
from alembic import op
import sqlalchemy as sa
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('sources', sa.Column('detail_next_run_at', sa.String(), nullable=True))
    op.add_column('sources', sa.Column('detail_last_success_at', sa.String(), nullable=True))
    op.add_column('sources', sa.Column('detail_checked', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('crawl_runs', sa.Column('kind', sa.String(), nullable=False, server_default='legacy'))
    op.add_column('subscriptions', sa.Column('reminder_hours', sa.JSON(), nullable=False, server_default='[72,24]'))
    op.create_table('deadline_reminders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('subscription_id', sa.Integer(), sa.ForeignKey('subscriptions.id'), nullable=False),
        sa.Column('listing_id', sa.Integer(), sa.ForeignKey('listing_rounds.id'), nullable=False),
        sa.Column('version_id', sa.Integer(), sa.ForeignKey('listing_versions.id'), nullable=False),
        sa.Column('deadline', sa.String(50), nullable=False),
        sa.Column('lead_hours', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.UniqueConstraint('subscription_id', 'listing_id', 'deadline', 'lead_hours'))
    # Batch rebuild makes nullability/FK/unique changes work on existing SQLite too.
    with op.batch_alter_table('notification_outbox') as batch:
        batch.alter_column('event_id', existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column('reminder_id', sa.Integer(), nullable=True))
        batch.create_foreign_key('fk_outbox_reminder', 'deadline_reminders', ['reminder_id'], ['id'])
        batch.create_unique_constraint('uq_outbox_reminder_channel', ['reminder_id', 'channel'])
        batch.create_check_constraint('outbox_one_origin', '(event_id IS NOT NULL AND reminder_id IS NULL) OR (event_id IS NULL AND reminder_id IS NOT NULL)')

def downgrade():
    raise RuntimeError('Restore a backup instead of destructive downgrade.')
