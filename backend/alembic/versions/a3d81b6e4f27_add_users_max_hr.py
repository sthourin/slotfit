"""add users.max_hr

Revision ID: a3d81b6e4f27
Revises: c1f4a7e02b39
Create Date: 2026-08-24 00:00:00.000000

Heart-rate zones are a share of maximum heart rate, and there was nowhere to
record it. Deliberately a single nullable column rather than a dated log like
`bodyweight_readings`: a past weigh-in was *true at the time*, so a new one must
not rewrite history, whereas max HR is an *estimate* - when it changes the old
figure was simply wrong, and the correction should propagate backward. Zones are
derived from `bpm` at compute time rather than stored, so that propagation is
just a recompute.

Nullable because the honest default is no zones at all. A guessed maximum
silently defines every zone boundary while looking authoritative; with no value,
`bpm`, average, peak and minimum are all still reported. Same rule as bodyweight
work with no weigh-in: report what is known, guess nothing.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3d81b6e4f27'
down_revision = 'c1f4a7e02b39'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('max_hr', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'max_hr')
