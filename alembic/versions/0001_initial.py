from alembic import op
from sqlalchemy import inspect
from app.database import Base
from app import models

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing: table.create(bind=bind)

def downgrade():
    bind = op.get_bind()
    for table in reversed(Base.metadata.sorted_tables): table.drop(bind=bind, checkfirst=True)
