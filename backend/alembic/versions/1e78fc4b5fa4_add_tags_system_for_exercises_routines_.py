"""add_tags_system_for_exercises_routines_workouts

Revision ID: 1e78fc4b5fa4
Revises: b2b1dbc73460
Create Date: 2026-01-11 10:33:44.280160

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1e78fc4b5fa4'
down_revision = 'b2b1dbc73460'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tags_id'), 'tags', ['id'], unique=False)
    op.create_index(op.f('ix_tags_name'), 'tags', ['name'], unique=True)
    op.create_index(op.f('ix_tags_category'), 'tags', ['category'], unique=False)
    
    # Create junction tables
    op.create_table(
        'exercise_tags',
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('exercise_id', 'tag_id')
    )
    
    op.create_table(
        'routine_template_tags',
        sa.Column('routine_template_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['routine_template_id'], ['routine_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('routine_template_id', 'tag_id')
    )
    
    op.create_table(
        'workout_session_tags',
        sa.Column('workout_session_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['workout_session_id'], ['workout_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workout_session_id', 'tag_id')
    )
    
    # Migrate existing exercise_classification values to tags
    op.execute("""
        INSERT INTO tags (name, category)
        SELECT DISTINCT exercise_classification, 'classification'
        FROM exercises
        WHERE exercise_classification IS NOT NULL
        AND exercise_classification != ''
        ON CONFLICT (name) DO NOTHING
    """)
    
    op.execute("""
        INSERT INTO exercise_tags (exercise_id, tag_id)
        SELECT e.id, t.id
        FROM exercises e
        JOIN tags t ON t.name = e.exercise_classification
        WHERE e.exercise_classification IS NOT NULL
        AND e.exercise_classification != ''
    """)
    
    # Migrate routine_type values to tags
    op.execute("""
        INSERT INTO tags (name, category)
        SELECT DISTINCT routine_type, 'routine_type'
        FROM routine_templates
        WHERE routine_type IS NOT NULL
        AND routine_type != ''
        ON CONFLICT (name) DO NOTHING
    """)
    
    op.execute("""
        INSERT INTO routine_template_tags (routine_template_id, tag_id)
        SELECT r.id, t.id
        FROM routine_templates r
        JOIN tags t ON t.name = r.routine_type
        WHERE r.routine_type IS NOT NULL
        AND r.routine_type != ''
    """)
    
    # Migrate workout_style values to tags
    op.execute("""
        INSERT INTO tags (name, category)
        SELECT DISTINCT workout_style, 'workout_style'
        FROM routine_templates
        WHERE workout_style IS NOT NULL
        AND workout_style != ''
        ON CONFLICT (name) DO NOTHING
    """)
    
    op.execute("""
        INSERT INTO routine_template_tags (routine_template_id, tag_id)
        SELECT r.id, t.id
        FROM routine_templates r
        JOIN tags t ON t.name = r.workout_style
        WHERE r.workout_style IS NOT NULL
        AND r.workout_style != ''
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    # Drop junction tables
    op.drop_table('workout_session_tags')
    op.drop_table('routine_template_tags')
    op.drop_table('exercise_tags')
    
    # Drop tags table
    op.drop_index(op.f('ix_tags_category'), table_name='tags')
    op.drop_index(op.f('ix_tags_name'), table_name='tags')
    op.drop_index(op.f('ix_tags_id'), table_name='tags')
    op.drop_table('tags')
