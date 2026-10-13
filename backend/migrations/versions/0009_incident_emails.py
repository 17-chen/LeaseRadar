"""Separate opt-in admin incident receipts; no fake listing events."""
from alembic import op
import sqlalchemy as sa
revision='0009'
down_revision='0008'
branch_labels=None
depends_on=None
def upgrade():
    op.add_column('email_deliveries',sa.Column('manual_retry',sa.Boolean(),nullable=False,server_default=sa.false()))
    op.add_column('email_deliveries',sa.Column('message_id',sa.String(),nullable=True))
    op.add_column('email_deliveries',sa.Column('sender_address',sa.String(),nullable=True))
    op.create_table('incident_emails',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('incident_id',sa.Integer(),sa.ForeignKey('source_incidents.id'),nullable=False),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('phase',sa.String(),nullable=False),sa.Column('recipient',sa.String(),nullable=False),
        sa.Column('manual_retry',sa.Boolean(),nullable=False),sa.Column('state',sa.String(),nullable=False),sa.Column('attempts',sa.Integer(),nullable=False),
        *[sa.Column(k,sa.String(),nullable=True) for k in ('retry_at','lease_until','token','error','accepted_at','message_id','sender_address')],
        sa.Column('created_at',sa.String(),nullable=False),sa.UniqueConstraint('incident_id','phase'))
def downgrade():
    op.drop_table('incident_emails')
    op.drop_column('email_deliveries','sender_address')
    op.drop_column('email_deliveries','message_id')
    op.drop_column('email_deliveries','manual_retry')
