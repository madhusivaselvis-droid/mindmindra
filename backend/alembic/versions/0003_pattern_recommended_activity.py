from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0003_pattern_recommended_activity'
down_revision = '0002_pattern_ai_results'
branch_labels = None
depends_on = None

def upgrade():
    columns = {column['name'] for column in inspect(op.get_bind()).get_columns('game_results')}
    if 'recommended_activity' not in columns:
        op.add_column('game_results', sa.Column('recommended_activity', sa.String(length=50), nullable=True))

def downgrade():
    columns = {column['name'] for column in inspect(op.get_bind()).get_columns('game_results')}
    if 'recommended_activity' in columns:
        op.drop_column('game_results', 'recommended_activity')
