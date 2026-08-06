"""add set_protocol to exercises and round_entries

Revision ID: b7c14e2a9f30
Revises: 59af238ed19e
Create Date: 2026-08-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c14e2a9f30'
down_revision = '59af238ed19e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    set_protocol = sa.Enum('reps', 'time', 'amrap', 'emom', name='setprotocol')
    set_protocol.create(op.get_bind(), checkfirst=True)

    # server_default keeps every existing row valid without a data pass.
    op.add_column(
        'exercises',
        sa.Column('set_protocol', set_protocol, nullable=False, server_default='reps'),
    )
    op.add_column(
        'round_entries',
        sa.Column('set_protocol', set_protocol, nullable=False, server_default='reps'),
    )

    # Two narrow, named backfills. No inference across the catalogue: guessing
    # from default_time_seconds would silently reclassify unreviewed exercises.
    #
    # The six HIIT variants are relabelled as well as reclassified. Bare "HIIT"
    # no longer implies a protocol, so leaving the label alone would silently
    # drop them to 'reps'. Renaming is safe: staples and round entries reference
    # exercises by id, never by name.
    op.execute(
        """
        UPDATE exercises
           SET name = replace(name, ' (HIIT)', ' (HIIT AMRAP)'),
               variant_type = 'HIIT AMRAP',
               set_protocol = 'amrap'
         WHERE variant_type = 'HIIT'
        """
    )
    op.execute("UPDATE exercises SET set_protocol = 'time' WHERE name = 'Rowing Machine'")


def downgrade() -> None:
    op.execute(
        """
        UPDATE exercises
           SET name = replace(name, ' (HIIT AMRAP)', ' (HIIT)'),
               variant_type = 'HIIT'
         WHERE variant_type = 'HIIT AMRAP'
        """
    )
    op.drop_column('round_entries', 'set_protocol')
    op.drop_column('exercises', 'set_protocol')
    sa.Enum(name='setprotocol').drop(op.get_bind(), checkfirst=True)
