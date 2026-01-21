"""
Seed data fixtures for tests
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert

from app.models import (
    MuscleGroup,
    Equipment,
    Exercise,
    InjuryType,
    MovementRestriction,
)
from app.models.exercise import DifficultyLevel, exercise_muscle_groups
from app.models.injury import injury_movement_restrictions


async def seed_muscle_groups(session: AsyncSession):
    """Seed basic muscle groups"""
    # Check if already seeded
    result = await session.execute(select(MuscleGroup))
    existing = result.scalars().all()
    if existing:
        return existing
    
    muscle_groups = [
        # Level 1: Target Muscle Groups
        MuscleGroup(name="Chest", level=1, parent_id=None),
        MuscleGroup(name="Back", level=1, parent_id=None),
        MuscleGroup(name="Shoulders", level=1, parent_id=None),
        MuscleGroup(name="Arms", level=1, parent_id=None),
        MuscleGroup(name="Legs", level=1, parent_id=None),
        MuscleGroup(name="Core", level=1, parent_id=None),
    ]
    
    session.add_all(muscle_groups)
    await session.flush()
    
    # Level 2: Prime Movers
    prime_movers = [
        MuscleGroup(name="Pectoralis Major", level=2, parent_id=muscle_groups[0].id),
        MuscleGroup(name="Latissimus Dorsi", level=2, parent_id=muscle_groups[1].id),
        MuscleGroup(name="Deltoids", level=2, parent_id=muscle_groups[2].id),
        MuscleGroup(name="Biceps", level=2, parent_id=muscle_groups[3].id),
        MuscleGroup(name="Quadriceps", level=2, parent_id=muscle_groups[4].id),
        MuscleGroup(name="Rectus Abdominis", level=2, parent_id=muscle_groups[5].id),
    ]
    
    session.add_all(prime_movers)
    await session.flush()
    
    return muscle_groups + prime_movers


async def seed_equipment(session: AsyncSession):
    """Seed basic equipment"""
    result = await session.execute(select(Equipment))
    existing = result.scalars().all()
    if existing:
        return existing
    
    equipment = [
        Equipment(name="Barbell", category="Free Weights"),
        Equipment(name="Dumbbell", category="Free Weights"),
        Equipment(name="Bodyweight", category="Bodyweight"),
        Equipment(name="Resistance Band", category="Accessories"),
        Equipment(name="Kettlebell", category="Free Weights"),
    ]
    
    session.add_all(equipment)
    await session.flush()
    
    return equipment


async def seed_exercises(session: AsyncSession, muscle_groups, equipment):
    """Seed basic exercises"""
    result = await session.execute(select(Exercise))
    existing = result.scalars().all()
    if existing:
        return existing
    
    # Get muscle groups and equipment by name
    chest_mg = next(mg for mg in muscle_groups if mg.name == "Chest")
    back_mg = next(mg for mg in muscle_groups if mg.name == "Back")
    shoulders_mg = next(mg for mg in muscle_groups if mg.name == "Shoulders")
    biceps_mg = next(mg for mg in muscle_groups if mg.name == "Biceps")
    quads_mg = next(mg for mg in muscle_groups if mg.name == "Quadriceps")
    core_mg = next(mg for mg in muscle_groups if mg.name == "Core")
    
    bodyweight_eq = next(eq for eq in equipment if eq.name == "Bodyweight")
    dumbbell_eq = next(eq for eq in equipment if eq.name == "Dumbbell")
    barbell_eq = next(eq for eq in equipment if eq.name == "Barbell")
    
    exercises = [
        Exercise(
            name="Push-up",
            description="Classic bodyweight chest exercise",
            difficulty=DifficultyLevel.EASY,
            primary_equipment_id=bodyweight_eq.id,
            body_region="Upper Body",
            force_type="Push",
            mechanics="Compound",
            laterality="Bilateral",
        ),
        Exercise(
            name="Pull-up",
            description="Bodyweight back exercise",
            difficulty=DifficultyLevel.INTERMEDIATE,
            primary_equipment_id=bodyweight_eq.id,
            body_region="Upper Body",
            force_type="Pull",
            mechanics="Compound",
            laterality="Bilateral",
        ),
        Exercise(
            name="Dumbbell Shoulder Press",
            description="Overhead pressing movement",
            difficulty=DifficultyLevel.INTERMEDIATE,
            primary_equipment_id=dumbbell_eq.id,
            body_region="Upper Body",
            force_type="Push",
            mechanics="Compound",
            laterality="Bilateral",
        ),
        Exercise(
            name="Dumbbell Bicep Curl",
            description="Isolation bicep exercise",
            difficulty=DifficultyLevel.EASY,
            primary_equipment_id=dumbbell_eq.id,
            body_region="Upper Body",
            force_type="Pull",
            mechanics="Isolation",
            laterality="Bilateral",
        ),
        Exercise(
            name="Squat",
            description="Bodyweight squat",
            difficulty=DifficultyLevel.EASY,
            primary_equipment_id=bodyweight_eq.id,
            body_region="Lower Body",
            force_type="Other",
            mechanics="Compound",
            laterality="Bilateral",
        ),
        Exercise(
            name="Plank",
            description="Core stability exercise",
            difficulty=DifficultyLevel.EASY,
            primary_equipment_id=bodyweight_eq.id,
            body_region="Core",
            force_type="Other",
            mechanics="Isolation",
            laterality="Bilateral",
        ),
    ]
    
    session.add_all(exercises)
    await session.flush()
    
    # Link exercises to muscle groups
    associations = [
        # Push-up -> Chest (target), Shoulders (prime mover)
        {"exercise_id": exercises[0].id, "muscle_group_id": chest_mg.id, "role": "target"},
        {"exercise_id": exercises[0].id, "muscle_group_id": shoulders_mg.id, "role": "prime_mover"},
        # Pull-up -> Back (target), Biceps (prime mover)
        {"exercise_id": exercises[1].id, "muscle_group_id": back_mg.id, "role": "target"},
        {"exercise_id": exercises[1].id, "muscle_group_id": biceps_mg.id, "role": "prime_mover"},
        # Shoulder Press -> Shoulders (target)
        {"exercise_id": exercises[2].id, "muscle_group_id": shoulders_mg.id, "role": "target"},
        # Bicep Curl -> Biceps (target)
        {"exercise_id": exercises[3].id, "muscle_group_id": biceps_mg.id, "role": "target"},
        # Squat -> Quads (target), Core (secondary)
        {"exercise_id": exercises[4].id, "muscle_group_id": quads_mg.id, "role": "target"},
        {"exercise_id": exercises[4].id, "muscle_group_id": core_mg.id, "role": "secondary"},
        # Plank -> Core (target)
        {"exercise_id": exercises[5].id, "muscle_group_id": core_mg.id, "role": "target"},
    ]
    
    for assoc in associations:
        stmt = insert(exercise_muscle_groups).values(**assoc)
        await session.execute(stmt)
    
    await session.flush()
    
    return exercises


async def seed_injuries(session: AsyncSession):
    """Seed injury types and restrictions"""
    result = await session.execute(select(InjuryType))
    existing = result.scalars().all()
    if existing:
        return existing
    
    injury_types = [
        InjuryType(
            name="Rotator Cuff Injury",
            body_area="Shoulder",
            description="Injury to the muscles and tendons stabilizing the shoulder joint",
            is_system=True,
        ),
        InjuryType(
            name="Lower Back Pain",
            body_area="Back",
            description="Pain in the lumbar region",
            is_system=True,
        ),
        InjuryType(
            name="Knee Pain",
            body_area="Knee",
            description="General knee discomfort",
            is_system=True,
        ),
    ]
    
    session.add_all(injury_types)
    await session.flush()
    
    # Create some movement restrictions
    restrictions = [
        MovementRestriction(
            restriction_type="movement_pattern",
            restriction_value="Overhead Press",
            severity_threshold="mild",
        ),
        MovementRestriction(
            restriction_type="movement_pattern",
            restriction_value="Deadlift",
            severity_threshold="mild",
        ),
        MovementRestriction(
            restriction_type="movement_pattern",
            restriction_value="Deep Squat",
            severity_threshold="mild",
        ),
    ]
    
    session.add_all(restrictions)
    await session.flush()
    
    # Link restrictions to injury types
    associations = [
        {"injury_type_id": injury_types[0].id, "restriction_id": restrictions[0].id},
        {"injury_type_id": injury_types[1].id, "restriction_id": restrictions[1].id},
        {"injury_type_id": injury_types[2].id, "restriction_id": restrictions[2].id},
    ]
    
    for assoc in associations:
        stmt = insert(injury_movement_restrictions).values(**assoc)
        await session.execute(stmt)
    
    await session.flush()
    
    return injury_types


async def seed_all_data(session: AsyncSession):
    """Seed all test data"""
    muscle_groups = await seed_muscle_groups(session)
    equipment = await seed_equipment(session)
    exercises = await seed_exercises(session, muscle_groups, equipment)
    injuries = await seed_injuries(session)
    
    await session.commit()
    
    return {
        "muscle_groups": muscle_groups,
        "equipment": equipment,
        "exercises": exercises,
        "injuries": injuries,
    }
