"""Preserve source attachment provenance and content identity."""
from alembic import op
import sqlalchemy as sa
revision='0010'
down_revision='0009'
branch_labels=None
depends_on=None

def upgrade():
    with op.batch_alter_table('document_reviews') as batch:
        batch.add_column(sa.Column('origin_version_id',sa.Integer(),nullable=True))
        batch.add_column(sa.Column('origin_url',sa.Text(),nullable=True))
        batch.create_foreign_key('fk_document_origin_version','listing_versions',['origin_version_id'],['id'])
        batch.create_unique_constraint('uq_document_origin_content',['listing_id','origin_url','sha256'])

def downgrade():
    with op.batch_alter_table('document_reviews') as batch:
        batch.drop_constraint('uq_document_origin_content',type_='unique')
        batch.drop_constraint('fk_document_origin_version',type_='foreignkey')
        batch.drop_column('origin_url')
        batch.drop_column('origin_version_id')
