"""Make hash-named HTML snapshots portable across DATA_DIR restores."""
from alembic import op
import sqlalchemy as sa
import re
revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    rows = bind.execute(sa.text('SELECT id,sha256,snapshot_path FROM raw_documents')).all()
    for identity, digest, path in rows:
        if re.fullmatch(r'[a-f0-9]{64}', digest) and path.replace('\\', '/').endswith('/snapshots/' + digest + '.html'):
            bind.execute(sa.text('UPDATE raw_documents SET snapshot_path=:path WHERE id=:id'),
                         {'path':'snapshots/' + digest + '.html', 'id':identity})

def downgrade():
    raise RuntimeError('Restore a backup instead of inventing an old host path.')
