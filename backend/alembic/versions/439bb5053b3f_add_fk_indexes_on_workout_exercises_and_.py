"""add FK indexes on workout_exercises and workout_sets

Revision ID: 439bb5053b3f
Revises: 93a81aa99814
Create Date: 2026-02-25 23:24:24.226248

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '439bb5053b3f'
down_revision = '93a81aa99814'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_workout_exercises_workout_session_id', 'workout_exercises', ['workout_session_id'])
    op.create_index('ix_workout_exercises_exercise_id', 'workout_exercises', ['exercise_id'])
    op.create_index('ix_workout_sets_workout_exercise_id', 'workout_sets', ['workout_exercise_id'])


def downgrade() -> None:
    op.drop_index('ix_workout_sets_workout_exercise_id', 'workout_sets')
    op.drop_index('ix_workout_exercises_exercise_id', 'workout_exercises')
    op.drop_index('ix_workout_exercises_workout_session_id', 'workout_exercises')
