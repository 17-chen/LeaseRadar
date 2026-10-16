"""Durable bounded source attachment download queue."""
from alembic import op
import sqlalchemy as sa
revision='0011'
down_revision='0010'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('document_downloads',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('version_id',sa.Integer(),sa.ForeignKey('listing_versions.id'),nullable=False),
        sa.Column('source_id',sa.String(),sa.ForeignKey('sources.id'),nullable=False),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('url',sa.Text(),nullable=False),sa.Column('format',sa.String(),nullable=False),
        sa.Column('state',sa.String(),nullable=False),sa.Column('attempts',sa.Integer(),nullable=False),
        *[sa.Column(k,sa.String(),nullable=True) for k in ('token','lease_until','retry_at','error','sha256')],
        sa.Column('review_id',sa.Integer(),sa.ForeignKey('document_reviews.id'),nullable=True),
        sa.Column('created_at',sa.String(),nullable=False),sa.UniqueConstraint('version_id','url',name='uq_download_version_url'))
    op.create_index('ix_document_downloads_state','document_downloads',['state'])

def downgrade():
    op.drop_table('document_downloads')
