"""Notification scheduling, review workflows and measured source coverage."""
from alembic import op
import sqlalchemy as sa
revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('sources',sa.Column('lease_token',sa.String(),nullable=True))
    op.add_column('jobs',sa.Column('lease_token',sa.String(),nullable=True))
    op.add_column('sources',sa.Column('daily_page_budget',sa.Integer(),nullable=False,server_default='48'))
    op.add_column('sources',sa.Column('backfill_batch_pages',sa.Integer(),nullable=False,server_default='3'))
    op.create_table('notification_preferences',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True, nullable=False),
        sa.Column('mode', sa.String(), primary_key=False, nullable=False),
        sa.Column('timezone', sa.String(), primary_key=False, nullable=False),
        sa.Column('digest_time', sa.String(), primary_key=False, nullable=False),
        sa.Column('quiet_start', sa.String(), primary_key=False, nullable=True),
        sa.Column('quiet_end', sa.String(), primary_key=False, nullable=True),
        sa.Column('urgent_override', sa.Boolean(), primary_key=False, nullable=False),
    )
    op.create_table('notification_digests',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=False, nullable=False),
        sa.Column('created_at', sa.String(), primary_key=False, nullable=False),
        sa.Column('window_start', sa.String(), primary_key=False, nullable=False),
        sa.Column('window_end', sa.String(), primary_key=False, nullable=False),
        sa.Column('representative_id', sa.Integer(), sa.ForeignKey('notification_outbox.id'), primary_key=False, nullable=False),
        sa.Column('sources', sa.JSON(), primary_key=False, nullable=False),
        sa.UniqueConstraint('representative_id'),
    )
    op.create_table('notification_digest_items',
        sa.Column('outbox_id', sa.Integer(), sa.ForeignKey('notification_outbox.id'), primary_key=True, nullable=False),
        sa.Column('digest_id', sa.Integer(), sa.ForeignKey('notification_digests.id'), primary_key=False, nullable=False),
    )
    op.create_table('corrections',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('listing_id', sa.Integer(), sa.ForeignKey('listing_rounds.id'), primary_key=False, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=False, nullable=False),
        sa.Column('field', sa.String(), primary_key=False, nullable=False),
        sa.Column('value', sa.JSON(), primary_key=False, nullable=True),
        sa.Column('original', sa.JSON(), primary_key=False, nullable=True),
        sa.Column('quote', sa.Text(), primary_key=False, nullable=False),
        sa.Column('reason', sa.Text(), primary_key=False, nullable=False),
        sa.Column('base_version_id', sa.Integer(), sa.ForeignKey('listing_versions.id'), primary_key=False, nullable=False),
        sa.Column('version_id', sa.Integer(), sa.ForeignKey('listing_versions.id'), primary_key=False, nullable=True),
        sa.Column('state', sa.String(), primary_key=False, nullable=False),
        sa.Column('created_at', sa.String(), primary_key=False, nullable=False),
        sa.Column('resolved_at', sa.String(), primary_key=False, nullable=True),
    )
    op.create_table('listing_relations',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('left_id', sa.Integer(), sa.ForeignKey('listing_rounds.id'), primary_key=False, nullable=False),
        sa.Column('right_id', sa.Integer(), sa.ForeignKey('listing_rounds.id'), primary_key=False, nullable=False),
        sa.Column('kind', sa.String(), primary_key=False, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=False, nullable=False),
        sa.Column('reason', sa.Text(), primary_key=False, nullable=False),
        sa.Column('state', sa.String(), primary_key=False, nullable=False),
        sa.Column('created_at', sa.String(), primary_key=False, nullable=False),
        sa.Column('resolved_at', sa.String(), primary_key=False, nullable=True),
        sa.UniqueConstraint('left_id','right_id','kind'),
        sa.CheckConstraint('left_id < right_id',name='relation_order'),
    )
    op.create_table('audit_actions',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=False, nullable=False),
        sa.Column('kind', sa.String(), primary_key=False, nullable=False),
        sa.Column('object_id', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('reason', sa.Text(), primary_key=False, nullable=False),
        sa.Column('created_at', sa.String(), primary_key=False, nullable=False),
    )
    op.create_table('source_incidents',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('source_id', sa.String(length=50), sa.ForeignKey('sources.id'), primary_key=False, nullable=False),
        sa.Column('kind', sa.String(), primary_key=False, nullable=False),
        sa.Column('state', sa.String(), primary_key=False, nullable=False),
        sa.Column('message', sa.Text(), primary_key=False, nullable=False),
        sa.Column('opened_at', sa.String(), primary_key=False, nullable=False),
        sa.Column('resolved_at', sa.String(), primary_key=False, nullable=True),
    )
    op.create_table('source_page_observations',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('source_id', sa.String(length=50), sa.ForeignKey('sources.id'), primary_key=False, nullable=False),
        sa.Column('page', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('checked_at', sa.String(), primary_key=False, nullable=False),
        sa.UniqueConstraint('source_id','page'),
    )

def downgrade():
    op.drop_table('source_page_observations')
    op.drop_table('source_incidents')
    op.drop_table('audit_actions')
    op.drop_table('listing_relations')
    op.drop_table('corrections')
    op.drop_table('notification_digest_items')
    op.drop_table('notification_digests')
    op.drop_table('notification_preferences')
    op.drop_column('sources','backfill_batch_pages')
    op.drop_column('sources','daily_page_budget')
    op.drop_column('jobs','lease_token')
    op.drop_column('sources','lease_token')
