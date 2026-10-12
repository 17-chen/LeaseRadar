"""Private document queue; extraction never overwrites source fields."""
from alembic import op
import sqlalchemy as sa
revision='0008'
down_revision='0007'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('document_reviews',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('listing_id',sa.Integer(),sa.ForeignKey('listing_rounds.id'),nullable=True),
        sa.Column('filename',sa.String(),nullable=False),sa.Column('sha256',sa.String(64),nullable=False),
        sa.Column('format',sa.String(),nullable=False),sa.Column('state',sa.String(),nullable=False),
        sa.Column('pages',sa.JSON(),nullable=False),sa.Column('error',sa.Text(),nullable=True),sa.Column('created_at',sa.String(),nullable=False))
def downgrade():op.drop_table('document_reviews')
