"""consolidate_difficulty_levels_to_easy_intermediate_advanced

Revision ID: b2b1dbc73460
Revises: e5b14fa30dfc
Create Date: 2026-01-11 10:27:33.489565

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b2b1dbc73460'
down_revision = 'e5b14fa30dfc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create new enum type with consolidated values
    op.execute("CREATE TYPE difficultylevel_new AS ENUM ('Easy', 'Intermediate', 'Advanced')")
    
    # Add temporary column with new enum type
    op.add_column('exercises', sa.Column('difficulty_new', postgresql.ENUM('Easy', 'Intermediate', 'Advanced', name='difficultylevel_new', create_type=False), nullable=True))
    
    # Map old values to new values
    # Easy: Beginner, Novice
    # Intermediate: Intermediate
    # Advanced: Advanced, Expert, Master, Grand Master, Legendary
    op.execute("""
        UPDATE exercises 
        SET difficulty_new = CASE 
            WHEN difficulty::text IN ('BEGINNER', 'NOVICE') THEN 'Easy'::difficultylevel_new
            WHEN difficulty::text = 'INTERMEDIATE' THEN 'Intermediate'::difficultylevel_new
            WHEN difficulty::text IN ('ADVANCED', 'EXPERT') THEN 'Advanced'::difficultylevel_new
            ELSE NULL
        END
        WHERE difficulty IS NOT NULL
    """)
    
    # Drop old column
    op.drop_column('exercises', 'difficulty')
    
    # Rename new column to old name
    op.alter_column('exercises', 'difficulty_new', new_column_name='difficulty')
    
    # Drop old enum type
    op.execute("DROP TYPE difficultylevel")
    
    # Rename new enum type to old name
    op.execute("ALTER TYPE difficultylevel_new RENAME TO difficultylevel")


def downgrade() -> None:
    # Create old enum type
    op.execute("CREATE TYPE difficultylevel_old AS ENUM ('BEGINNER', 'NOVICE', 'INTERMEDIATE', 'ADVANCED', 'EXPERT')")
    
    # Add temporary column with old enum type
    op.add_column('exercises', sa.Column('difficulty_old', postgresql.ENUM('BEGINNER', 'NOVICE', 'INTERMEDIATE', 'ADVANCED', 'EXPERT', name='difficultylevel_old', create_type=False), nullable=True))
    
    # Map new values back to old values (best guess - Easy -> Beginner, Intermediate -> Intermediate, Advanced -> Advanced)
    op.execute("""
        UPDATE exercises 
        SET difficulty_old = CASE 
            WHEN difficulty::text = 'Easy' THEN 'BEGINNER'::difficultylevel_old
            WHEN difficulty::text = 'Intermediate' THEN 'INTERMEDIATE'::difficultylevel_old
            WHEN difficulty::text = 'Advanced' THEN 'ADVANCED'::difficultylevel_old
            ELSE NULL
        END
    """)
    
    # Drop new column
    op.drop_column('exercises', 'difficulty')
    
    # Rename old column to original name
    op.alter_column('exercises', 'difficulty_old', new_column_name='difficulty')
    
    # Drop new enum type
    op.execute("DROP TYPE difficultylevel")
    
    # Rename old enum type to original name
    op.execute("ALTER TYPE difficultylevel_old RENAME TO difficultylevel")
