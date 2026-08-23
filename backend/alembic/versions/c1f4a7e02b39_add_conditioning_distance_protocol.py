"""add distance protocol and conditioning result columns

Revision ID: c1f4a7e02b39
Revises: 11ddf1911138
Create Date: 2026-08-23 00:00:00.000000

Conditioning results (duration, distance) had nowhere to live. `entry_sets`
carried `time_seconds` but no distance, and `workout_sets` carried neither, so
three years of imported rowing was dropped as "no reps".

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1f4a7e02b39'
down_revision = '11ddf1911138'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL cannot use a new enum label in the same transaction that adds
    # it, so the ALTER commits on its own before the backfill below reads it.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE setprotocol ADD VALUE IF NOT EXISTS 'distance'")

    op.add_column('entry_sets', sa.Column('distance_meters', sa.Float(), nullable=True))
    op.add_column('workout_sets', sa.Column('time_seconds', sa.Integer(), nullable=True))
    op.add_column('workout_sets', sa.Column('distance_meters', sa.Float(), nullable=True))

    # Named backfills only, following the precedent set by b7c14e2a9f30: no
    # inference across the catalogue.
    #
    # The march/carry family is exact rather than inferred. Every one of the 80
    # names ending in " March" or " Carry" sits in the `carry` or `conditioning`
    # pattern - verified zero matches outside them - and none of them is
    # performed for reps. A farmer's carry is distance or time, never "10 reps".
    op.execute(
        """
        UPDATE exercises
           SET set_protocol = 'distance'
         WHERE name LIKE '%% March' OR name LIKE '%% Carry'
        """
    )

    # The rower logs 500m against a clock. It was 'time' because distance had no
    # column; now that it does, the distance is the point - it is what makes the
    # time comparable between sessions.
    op.execute("UPDATE exercises SET set_protocol = 'distance' WHERE name = 'Rowing Machine'")


def downgrade() -> None:
    op.execute(
        """
        UPDATE exercises
           SET set_protocol = 'reps'
         WHERE name LIKE '%% March' OR name LIKE '%% Carry'
        """
    )
    op.execute("UPDATE exercises SET set_protocol = 'time' WHERE name = 'Rowing Machine'")

    op.drop_column('workout_sets', 'distance_meters')
    op.drop_column('workout_sets', 'time_seconds')
    op.drop_column('entry_sets', 'distance_meters')

    # The 'distance' label stays on the enum type. PostgreSQL cannot drop an
    # enum value, and recreating the type would require rewriting every column
    # that uses it - far more destructive than leaving an unused label behind.
