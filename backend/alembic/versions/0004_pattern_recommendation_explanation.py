from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0004_pattern_recommendation_explanation'
down_revision = '0003_pattern_recommended_activity'
branch_labels = None
depends_on = None

def upgrade():
    columns = {column['name'] for column in inspect(op.get_bind()).get_columns('game_results')}
    if 'recommendation_explanation' not in columns:
        op.add_column('game_results', sa.Column('recommendation_explanation', sa.Text(), nullable=True))

def downgrade():
    columns = {column['name'] for column in inspect(op.get_bind()).get_columns('game_results')}
    if 'recommendation_explanation' in columns:
        op.drop_column('game_results', 'recommendation_explanation')
