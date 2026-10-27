from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0002_pattern_ai_results'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

COLUMNS = [
    sa.Column('cps', sa.Float(), nullable=True),
    sa.Column('accuracy_component', sa.Float(), nullable=True),
    sa.Column('reaction_component', sa.Float(), nullable=True),
    sa.Column('completion_component', sa.Float(), nullable=True),
    sa.Column('consistency_component', sa.Float(), nullable=True),
    sa.Column('recommended_difficulty', sa.Integer(), nullable=True),
    sa.Column('recommendation_model', sa.String(length=40), nullable=True),
    sa.Column('caregiver_notification', sa.Boolean(), nullable=False, server_default=sa.false()),
]

def upgrade():
    existing = {column['name'] for column in inspect(op.get_bind()).get_columns('game_results')}
    for column in COLUMNS:
        if column.name not in existing:
            op.add_column('game_results', column)

def downgrade():
    existing = {column['name'] for column in inspect(op.get_bind()).get_columns('game_results')}
    for column in reversed(COLUMNS):
        if column.name in existing:
            op.drop_column('game_results', column.name)
