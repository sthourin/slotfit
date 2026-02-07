"""Add weight_unit to workout_exercises

Revision ID: a1ceab703b44
Revises: 1176bac92d55
Create Date: 2026-01-25 10:42:10.086866

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1ceab703b44'
down_revision = '1176bac92d55'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the enum type first
    weightunit_enum = sa.Enum('KG', 'LBS', name='weightunit')
    weightunit_enum.create(op.get_bind(), checkfirst=True)
    
    # Add weight_unit column with a default for existing rows
    op.add_column('workout_exercises', sa.Column(
        'weight_unit', 
        sa.Enum('KG', 'LBS', name='weightunit'), 
        nullable=False,
        server_default='LBS'  # Default for existing rows
    ))
    
    # Remove server default after column is created (optional - keeps it clean)
    op.alter_column('workout_exercises', 'weight_unit', server_default=None)
    
    # Add duration and distance columns
    op.add_column('workout_sets', sa.Column('duration_seconds', sa.Integer(), nullable=True))
    op.add_column('workout_sets', sa.Column('distance_meters', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('workout_sets', 'distance_meters')
    op.drop_column('workout_sets', 'duration_seconds')
    op.drop_column('workout_exercises', 'weight_unit')
    
    # Drop the enum type
    weightunit_enum = sa.Enum('KG', 'LBS', name='weightunit')
    weightunit_enum.drop(op.get_bind(), checkfirst=True)
