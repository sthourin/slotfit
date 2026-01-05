"""
Exercise API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, desc, asc
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.core.database import get_db
from app.models import Exercise, MuscleGroup, Equipment, WorkoutExercise
from app.schemas.exercise import Exercise as ExerciseSchema, ExerciseListResponse, ExerciseDuplicate
from fastapi import HTTPException
import traceback

router = APIRouter()

@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify server is running latest code"""
    return {"message": "Exercises endpoint is loaded", "version": "2026-01-02-fixed"}


@router.get("/", response_model=ExerciseListResponse)
async def list_exercises(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    muscle_group_id: Optional[int] = None,
    muscle_group_ids: Optional[str] = None,  # Comma-separated list of IDs
    equipment_id: Optional[int] = None,
    difficulty: Optional[str] = None,
    body_region: Optional[str] = None,
    mechanics: Optional[str] = None,  # "Compound" or "Isolation"
    routine_type: Optional[str] = None,  # "anterior", "posterior", "full_body", "custom"
    workout_style: Optional[str] = None,  # "5x5", "HIIT", "volume", "strength", "custom"
    variant_type: Optional[str] = None,  # Filter by variant type: "HIIT", "Strength", etc.
    base_exercise_id: Optional[int] = None,  # Get all variants of a base exercise
    include_variants: Optional[bool] = Query(True, description="Include exercise variants in results"),
    sort_by: Optional[str] = Query("name", description="Sort by: name, difficulty, last_performed, equipment"),
    sort_order: Optional[str] = Query("asc", description="Sort order: asc or desc"),
    db: AsyncSession = Depends(get_db),
):
    """
    List exercises with optional filtering and sorting
    Supports filtering by single muscle_group_id or multiple muscle_group_ids (comma-separated)
    Sorting options: name, difficulty, last_performed, equipment
    """
    try:
        query = select(Exercise).options(
            selectinload(Exercise.primary_equipment),
            selectinload(Exercise.secondary_equipment),
            selectinload(Exercise.muscle_groups),
        )
        
        # Filter by variant type or base exercise
        if variant_type:
            query = query.where(Exercise.variant_type == variant_type)
        elif base_exercise_id:
            # Get all variants of a base exercise
            query = query.where(
                or_(
                    Exercise.id == base_exercise_id,
                    Exercise.base_exercise_id == base_exercise_id
                )
            )
        elif not include_variants:
            # Exclude variants (only show base exercises)
            query = query.where(Exercise.base_exercise_id.is_(None))
        
        # Apply filters
        if search:
            query = query.where(Exercise.name.ilike(f"%{search}%"))
        
        # Collect all muscle group IDs to filter by (from both muscle_group_ids and routine_type)
        target_mg_ids = []
        
        # Support both single muscle_group_id and multiple muscle_group_ids
        if muscle_group_ids:
            # Parse comma-separated IDs
            try:
                mg_ids = [int(id.strip()) for id in muscle_group_ids.split(',') if id.strip()]
                target_mg_ids.extend(mg_ids)
            except ValueError:
                pass  # Invalid IDs, ignore filter
        elif muscle_group_id:
            target_mg_ids.append(muscle_group_id)
        
        if equipment_id:
            query = query.where(
                or_(
                    Exercise.primary_equipment_id == equipment_id,
                    Exercise.secondary_equipment_id == equipment_id,
                )
            )
        
        if difficulty:
            from app.models.exercise import DifficultyLevel
            try:
                diff_enum = DifficultyLevel(difficulty)
                query = query.where(Exercise.difficulty == diff_enum)
            except ValueError:
                pass  # Invalid difficulty, ignore filter
        
        if body_region:
            query = query.where(Exercise.body_region == body_region)
        
        if mechanics:
            query = query.where(Exercise.mechanics == mechanics)
        
        # Filter by routine_type (anterior/posterior)
        # This filters exercises to only those targeting anterior or posterior muscle groups
        if routine_type and routine_type.lower() in ["anterior", "posterior"]:
            # Define anterior and posterior muscle groups
            # Anterior: Chest, Shoulders (anterior deltoids), Quadriceps, Abdominals, Biceps
            # Posterior: Back, Hamstrings, Glutes, Triceps, Calves
            anterior_muscle_groups = ["Chest", "Shoulders", "Quadriceps", "Abdominals", "Biceps"]
            posterior_muscle_groups = ["Back", "Hamstrings", "Glutes", "Triceps", "Calves"]
            
            target_groups = anterior_muscle_groups if routine_type.lower() == "anterior" else posterior_muscle_groups
            
            # Get muscle group IDs for the target groups
            mg_query = select(MuscleGroup).where(
                MuscleGroup.name.in_(target_groups),
                MuscleGroup.level == 1  # Level 1 = Target Muscle Group
            )
            mg_result = await db.execute(mg_query)
            routine_mg_ids = [mg.id for mg in mg_result.scalars().all()]
            
            if routine_mg_ids:
                # If we already have muscle group IDs from muscle_group_ids parameter,
                # intersect them with routine_type muscle groups
                if target_mg_ids:
                    # Only include exercises that match BOTH the specified muscle groups AND routine type
                    target_mg_ids = list(set(target_mg_ids) & set(routine_mg_ids))
                else:
                    # Use routine type muscle groups
                    target_mg_ids = routine_mg_ids
        
        # Apply muscle group filter if we have any target IDs
        if target_mg_ids:
            query = query.join(Exercise.muscle_groups).where(MuscleGroup.id.in_(target_mg_ids))
        
        # Filter by workout_style (HIIT, etc.)
        if workout_style and workout_style.upper() == "HIIT":
            # HIIT exercises typically have certain characteristics
            # Check exercise_classification for HIIT-related terms
            query = query.where(
                or_(
                    Exercise.exercise_classification.ilike("%HIIT%"),
                    Exercise.exercise_classification.ilike("%Cardio%"),
                    Exercise.exercise_classification.ilike("%Conditioning%"),
                    Exercise.name.ilike("%burpee%"),
                    Exercise.name.ilike("%sprint%"),
                    Exercise.name.ilike("%jump%"),
                )
            )
        
        # Apply sorting (before fetching last_performed)
        sort_order_func = desc if sort_order.lower() == "desc" else asc
        if sort_by == "name":
            query = query.order_by(sort_order_func(Exercise.name))
        elif sort_by == "difficulty":
            # Order by difficulty enum value
            query = query.order_by(sort_order_func(Exercise.difficulty))
        elif sort_by == "equipment":
            query = query.order_by(sort_order_func(Exercise.primary_equipment_id))
        else:
            # Default: sort by name
            query = query.order_by(asc(Exercise.name))
        
        # Get total count (before pagination)
        # Rebuild the same filters for count query
        count_query = select(Exercise)
        
        # Apply variant filtering to count query
        if variant_type:
            count_query = count_query.where(Exercise.variant_type == variant_type)
        elif base_exercise_id:
            count_query = count_query.where(
                or_(
                    Exercise.id == base_exercise_id,
                    Exercise.base_exercise_id == base_exercise_id
                )
            )
        elif not include_variants:
            count_query = count_query.where(Exercise.base_exercise_id.is_(None))
        
        if search:
            count_query = count_query.where(Exercise.name.ilike(f"%{search}%"))
        
        # Rebuild muscle group filter for count query (same logic as main query)
        count_target_mg_ids = []
        if muscle_group_ids:
            try:
                mg_ids = [int(id.strip()) for id in muscle_group_ids.split(',') if id.strip()]
                count_target_mg_ids.extend(mg_ids)
            except ValueError:
                pass
        elif muscle_group_id:
            count_target_mg_ids.append(muscle_group_id)
        # Apply routine_type filter to count query (same logic as main query)
        if routine_type and routine_type.lower() in ["anterior", "posterior"]:
            anterior_muscle_groups = ["Chest", "Shoulders", "Quadriceps", "Abdominals", "Biceps"]
            posterior_muscle_groups = ["Back", "Hamstrings", "Glutes", "Triceps", "Calves"]
            target_groups = anterior_muscle_groups if routine_type.lower() == "anterior" else posterior_muscle_groups
            mg_query = select(MuscleGroup).where(
                MuscleGroup.name.in_(target_groups),
                MuscleGroup.level == 1
            )
            mg_result = await db.execute(mg_query)
            routine_mg_ids = [mg.id for mg in mg_result.scalars().all()]
            if routine_mg_ids:
                if count_target_mg_ids:
                    count_target_mg_ids = list(set(count_target_mg_ids) & set(routine_mg_ids))
                else:
                    count_target_mg_ids = routine_mg_ids
        
        # Apply muscle group filter to count query
        if count_target_mg_ids:
            count_query = count_query.join(Exercise.muscle_groups).where(MuscleGroup.id.in_(count_target_mg_ids))
        
        if equipment_id:
            count_query = count_query.where(
                or_(
                    Exercise.primary_equipment_id == equipment_id,
                    Exercise.secondary_equipment_id == equipment_id,
                )
            )
        if difficulty:
            from app.models.exercise import DifficultyLevel
            try:
                diff_enum = DifficultyLevel(difficulty)
                count_query = count_query.where(Exercise.difficulty == diff_enum)
            except ValueError:
                pass
        if body_region:
            count_query = count_query.where(Exercise.body_region == body_region)
        if mechanics:
            count_query = count_query.where(Exercise.mechanics == mechanics)
        
        if workout_style and workout_style.upper() == "HIIT":
            count_query = count_query.where(
                or_(
                    Exercise.exercise_classification.ilike("%HIIT%"),
                    Exercise.exercise_classification.ilike("%Cardio%"),
                    Exercise.exercise_classification.ilike("%Conditioning%"),
                    Exercise.name.ilike("%burpee%"),
                    Exercise.name.ilike("%sprint%"),
                    Exercise.name.ilike("%jump%"),
                )
            )
        
        total_result = await db.execute(count_query)
        total = len(total_result.scalars().unique().all())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        exercises = result.scalars().unique().all()
        
        # Get last_performed dates for the returned exercises
        exercise_ids = [ex.id for ex in exercises]
        last_performed_map = {}
        if exercise_ids:
            last_performed_query = (
                select(
                    WorkoutExercise.exercise_id,
                    func.max(WorkoutExercise.started_at).label('last_performed')
                )
                .where(
                    WorkoutExercise.exercise_id.in_(exercise_ids),
                    WorkoutExercise.started_at.isnot(None)
                )
                .group_by(WorkoutExercise.exercise_id)
            )
            last_performed_result = await db.execute(last_performed_query)
            last_performed_map = {}
            for row in last_performed_result.all():
                # Access Row object by index (most reliable)
                # row[0] = exercise_id, row[1] = last_performed
                last_performed_map[row[0]] = row[1]
        
        # Build response with last_performed
        exercise_list = []
        for ex in exercises:
            ex_schema = ExerciseSchema.model_validate(ex)
            # Add last_performed to the model dict
            ex_dict = ex_schema.model_dump()
            ex_dict['last_performed'] = last_performed_map.get(ex.id)
            # Re-validate with last_performed included
            exercise_list.append(ExerciseSchema.model_validate(ex_dict))
        
        # If sorting by last_performed, do it after fetching dates
        if sort_by == "last_performed":
            exercise_list.sort(key=lambda e: (
                e.last_performed if e.last_performed else datetime.min,
            ), reverse=(sort_order.lower() == "desc"))
            # Move nulls to end
            exercise_list.sort(key=lambda e: e.last_performed is None)

        return ExerciseListResponse(
            exercises=exercise_list,
            total=total,
            page=skip // limit + 1 if limit > 0 else 1,
            page_size=limit,
        )
    except Exception as e:
        # Log the error for debugging
        error_msg = f"Error in list_exercises: {str(e)}\n{traceback.format_exc()}"
        print(error_msg, flush=True)
        import sys
        import traceback
        traceback.print_exc(file=sys.stderr)
        # Also write to file for debugging
        try:
            with open('backend_error.log', 'a') as f:
                f.write(f"\n{error_msg}\n")
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# IMPORTANT: More specific routes must be defined before more general ones
# Routes with sub-paths like /{exercise_id}/variants and /{exercise_id}/duplicate
# must come before /{exercise_id} to avoid route matching conflicts

@router.get("/{exercise_id}/variants", response_model=ExerciseListResponse)
async def get_exercise_variants(
    exercise_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all variants of an exercise (including the base exercise if it has variants)
    """
    # Get the base exercise
    base_query = select(Exercise).where(Exercise.id == exercise_id).options(
        selectinload(Exercise.primary_equipment),
        selectinload(Exercise.secondary_equipment),
        selectinload(Exercise.muscle_groups),
    )
    base_result = await db.execute(base_query)
    base_exercise = base_result.scalar_one_or_none()
    
    if not base_exercise:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Determine the actual base exercise ID (if this is a variant, get its base)
    actual_base_id = base_exercise.base_exercise_id if base_exercise.base_exercise_id else base_exercise.id
    
    # Get all variants (including the base if it has variants)
    variants_query = select(Exercise).where(
        or_(
            Exercise.id == actual_base_id,
            Exercise.base_exercise_id == actual_base_id
        )
    ).options(
        selectinload(Exercise.primary_equipment),
        selectinload(Exercise.secondary_equipment),
        selectinload(Exercise.muscle_groups),
    )
    
    variants_result = await db.execute(variants_query)
    variants = variants_result.scalars().unique().all()
    
    # Get last_performed dates
    variant_ids = [v.id for v in variants]
    last_performed_map = {}
    if variant_ids:
        last_performed_query = (
            select(
                WorkoutExercise.exercise_id,
                func.max(WorkoutExercise.started_at).label('last_performed')
            )
            .where(
                WorkoutExercise.exercise_id.in_(variant_ids),
                WorkoutExercise.started_at.isnot(None)
            )
            .group_by(WorkoutExercise.exercise_id)
        )
        last_performed_result = await db.execute(last_performed_query)
        last_performed_map = {}
        for row in last_performed_result.all():
            # Access Row object by index (most reliable)
            # row[0] = exercise_id, row[1] = last_performed
            last_performed_map[row[0]] = row[1]
    
    exercise_list = []
    for ex in variants:
        ex_dict = ExerciseSchema.model_validate(ex).model_dump()
        ex_dict['last_performed'] = last_performed_map.get(ex.id)
        exercise_list.append(ExerciseSchema.model_validate(ex_dict))
    
    return ExerciseListResponse(
        exercises=exercise_list,
        total=len(exercise_list),
        page=1,
        page_size=len(exercise_list),
    )


@router.post("/{exercise_id}/duplicate", response_model=ExerciseSchema)
async def duplicate_exercise(
    exercise_id: int,
    variant_data: ExerciseDuplicate,
    db: AsyncSession = Depends(get_db),
):
    """
    Duplicate an exercise to create a custom variant for context-aware history tracking
    """
    
    # Get the original exercise
    query = select(Exercise).where(Exercise.id == exercise_id).options(
        selectinload(Exercise.muscle_groups),
    )
    result = await db.execute(query)
    original = result.scalar_one_or_none()
    
    if not original:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Determine base exercise ID (if original is already a variant, use its base)
    base_exercise_id = original.base_exercise_id if original.base_exercise_id else original.id
    
    # Generate variant name if not provided
    variant_name = variant_data.name
    if not variant_name:
        variant_name = f"{original.name} ({variant_data.variant_type})"
    
    # Check if variant name already exists
    existing_check = select(Exercise).where(Exercise.name == variant_name)
    existing_result = await db.execute(existing_check)
    if existing_result.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400, 
            detail=f"Exercise with name '{variant_name}' already exists"
        )
    
    # Create new exercise variant
    variant = Exercise(
        name=variant_name,
        description=original.description,
        difficulty=original.difficulty,
        exercise_classification=original.exercise_classification,
        primary_equipment_id=original.primary_equipment_id,
        secondary_equipment_id=original.secondary_equipment_id,
        primary_equipment_count=original.primary_equipment_count,
        secondary_equipment_count=original.secondary_equipment_count,
        posture=original.posture,
        movement_pattern_1=original.movement_pattern_1,
        movement_pattern_2=original.movement_pattern_2,
        movement_pattern_3=original.movement_pattern_3,
        plane_of_motion_1=original.plane_of_motion_1,
        plane_of_motion_2=original.plane_of_motion_2,
        plane_of_motion_3=original.plane_of_motion_3,
        body_region=original.body_region,
        force_type=original.force_type,
        mechanics=original.mechanics,
        laterality=original.laterality,
        short_demo_url=original.short_demo_url,
        in_depth_url=original.in_depth_url,
        instructions=original.instructions,
        base_exercise_id=base_exercise_id,
        variant_type=variant_data.variant_type,
        is_custom=True,
        default_sets=variant_data.default_sets,
        default_reps=variant_data.default_reps,
        default_weight=variant_data.default_weight,
        default_time_seconds=variant_data.default_time_seconds,
        default_rest_seconds=variant_data.default_rest_seconds,
    )
    
    db.add(variant)
    await db.flush()
    
    # Copy muscle group associations
    for mg in original.muscle_groups:
        # Get the association table
        from app.models.exercise import exercise_muscle_groups
        from sqlalchemy import insert
        # We need to get the role from the association table
        assoc_query = select(exercise_muscle_groups).where(
            exercise_muscle_groups.c.exercise_id == original.id,
            exercise_muscle_groups.c.muscle_group_id == mg.id
        )
        assoc_result = await db.execute(assoc_query)
        assoc_row = assoc_result.first()
        if assoc_row:
            role = assoc_row.role
            # Insert new association
            await db.execute(
                insert(exercise_muscle_groups).values(
                    exercise_id=variant.id,
                    muscle_group_id=mg.id,
                    role=role
                )
            )
    
    await db.commit()
    await db.refresh(variant)
    
    # Reload with relationships
    variant_query = select(Exercise).where(Exercise.id == variant.id).options(
        selectinload(Exercise.primary_equipment),
        selectinload(Exercise.secondary_equipment),
        selectinload(Exercise.muscle_groups),
    )
    variant_result = await db.execute(variant_query)
    variant = variant_result.scalar_one()
    
    return ExerciseSchema.model_validate(variant)


@router.get("/{exercise_id}", response_model=ExerciseSchema)
async def get_exercise(
    exercise_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single exercise by ID
    """
    query = select(Exercise).where(Exercise.id == exercise_id).options(
        selectinload(Exercise.primary_equipment),
        selectinload(Exercise.secondary_equipment),
        selectinload(Exercise.muscle_groups),
    )
    
    result = await db.execute(query)
    exercise = result.scalar_one_or_none()
    
    if not exercise:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Get last_performed date
    last_performed_query = (
        select(func.max(WorkoutExercise.started_at).label('last_performed'))
        .where(
            WorkoutExercise.exercise_id == exercise_id,
            WorkoutExercise.started_at.isnot(None)
        )
    )
    last_performed_result = await db.execute(last_performed_query)
    last_performed = last_performed_result.scalar_one_or_none()
    
    ex_dict = ExerciseSchema.model_validate(exercise).model_dump()
    ex_dict['last_performed'] = last_performed if last_performed else None
    
    return ExerciseSchema.model_validate(ex_dict)
