"""preference levels

Replaces the numeric nutrition targets, hard-limit flags and ranking weights on user_preferences with
coarse levels: nutrient_levels, time_preference, meal_types and meal_size. The dropped columns were not
read or written anywhere, so no data is migrated.

Revision ID: 267145737384
Revises: 5491ac21718d
Create Date: 2026-10-24 15:46:31.579728

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '267145737384'
down_revision: Union[str, Sequence[str], None] = '5491ac21718d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REMOVED_FLAGS = ('cooking_time_is_hard_limit', 'protein_is_hard_limit', 'calorie_is_hard_limit', 'fat_is_hard_limit')
REMOVED_NUMBERS = ('protein_target_g', 'calorie_target', 'fat_target_g', 'budget_target_per_serving')


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('user_preferences', schema=None) as batch_op:
        # Server defaults let this run against a database that already has a preferences row.
        batch_op.add_column(sa.Column('nutrient_levels', sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column('time_preference', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('meal_types', sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch_op.add_column(sa.Column('meal_size', sa.String(length=16), nullable=True))
        for name in REMOVED_FLAGS + REMOVED_NUMBERS + (
            'primary_goal', 'carbohydrate_preference', 'maximum_cooking_time_min', 'default_servings', 'ranking_weights',
        ):
            batch_op.drop_column(name)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('user_preferences', schema=None) as batch_op:
        batch_op.add_column(sa.Column('primary_goal', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('carbohydrate_preference', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('maximum_cooking_time_min', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('default_servings', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('ranking_weights', sa.JSON(), nullable=True))
        for name in REMOVED_NUMBERS:
            batch_op.add_column(sa.Column(name, sa.Float(), nullable=True))
        for name in REMOVED_FLAGS:
            batch_op.add_column(sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false()))
        for name in ('meal_size', 'meal_types', 'time_preference', 'nutrient_levels'):
            batch_op.drop_column(name)
