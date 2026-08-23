"""Seed the conditioning movements the catalogue has no row for.

The CSV catalogue is a strength catalogue. It carries 80 loaded marches and
carries and a rowing machine, but no rucking, walking or running - so the half
of the product that tracks conditioning had nothing to log against.

Also sets `set_protocol` on the unambiguous static holds. Unlike the march and
carry families, "plank" is not an exact name rule: `Bodyweight Forearm Plank` is
a hold measured in seconds, while `Plank Pull Through` and
`Copenhagen Plank Knee to Elbow` are rep movements that merely share the word.
So the holds are listed by name rather than matched by pattern.

Idempotent. Safe to re-run; it updates in place and never duplicates a row.

    python -m scripts.seed_conditioning
    python -m scripts.seed_conditioning --commit
"""
import argparse
import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.equipment import Equipment
from app.models.exercise import Exercise, SetProtocol, exercise_muscle_groups
from app.models.movement_pattern import ExercisePatternMap, MovementPattern
from app.models.muscle_group import MuscleGroup
from app.services.leverage import CURATED_FRACTIONS

# Locomotion carries the whole body over ground, so `Bodyweight` equipment is
# correct and any pack or vest is logged as added weight - `effective_load`
# already adds it to the leverage-scaled bodyweight.
#
# `target_muscle` is the level-1 group a set is credited to. Locomotion is
# quadriceps-dominant at level 1; the finer contributors are deliberately not
# listed, because volume credits the target role only.
LOCOMOTION = [
    {
        "name": "Rucking",
        "description": "Walking over ground under a loaded pack. Log the pack weight as added weight.",
        "target_muscle": "Quadriceps",
        "body_region": "Lower Body",
        "posture": "Standing",
        "laterality": "Bilateral",
    },
    {
        "name": "Bodyweight Walk",
        "description": "Walking for distance or time, unloaded.",
        "target_muscle": "Quadriceps",
        "body_region": "Lower Body",
        "posture": "Standing",
        "laterality": "Bilateral",
    },
    {
        "name": "Bodyweight Run",
        "description": "Running for distance or time.",
        "target_muscle": "Quadriceps",
        "body_region": "Lower Body",
        "posture": "Standing",
        "laterality": "Bilateral",
    },
]

# Static holds: measured in seconds, never in reps. Named individually because
# the word "plank" alone does not imply a hold.
STATIC_HOLDS = [
    "Bodyweight Forearm Plank",
    "Bodyweight Kneeling Forearm Plank",
    "Bodyweight Side Plank",
    "Bodyweight Kneeling Side Plank",
    "Bodyweight Reverse Plank",
    "Bodyweight Copenhagen Plank",
    "Bodyweight Bent Knee Copenhagen Plank",
]


async def main(commit: bool) -> None:
    async with AsyncSessionLocal() as db:
        bodyweight = (
            await db.execute(select(Equipment).where(Equipment.name == "Bodyweight"))
        ).scalar_one_or_none()
        if bodyweight is None:
            raise SystemExit(
                "error: no 'Bodyweight' equipment row. Run the exercise import first."
            )

        conditioning = (
            await db.execute(
                select(MovementPattern).where(MovementPattern.slug == "conditioning")
            )
        ).scalar_one_or_none()
        if conditioning is None:
            raise SystemExit(
                "error: movement_patterns is empty. Run `python -m scripts.seed_patterns` first."
            )

        muscle_ids = dict(
            (
                await db.execute(
                    select(MuscleGroup.name, MuscleGroup.id).where(MuscleGroup.level == 1)
                )
            ).all()
        )

        created = updated = 0
        for spec in LOCOMOTION:
            existing = (
                await db.execute(select(Exercise).where(Exercise.name == spec["name"]))
            ).scalar_one_or_none()

            fraction = CURATED_FRACTIONS.get(spec["name"])
            if existing is None:
                exercise = Exercise(
                    name=spec["name"],
                    description=spec["description"],
                    primary_equipment_id=bodyweight.id,
                    movement_pattern_1="Conditioning",
                    body_region=spec["body_region"],
                    posture=spec["posture"],
                    laterality=spec["laterality"],
                    mechanics="Compound",
                    force_type="Other",
                    set_protocol=SetProtocol.DISTANCE,
                    bodyweight_fraction=fraction,
                )
                db.add(exercise)
                await db.flush()
                created += 1
                print(f"  created {spec['name']} (fraction {fraction})")
            else:
                exercise = existing
                exercise.set_protocol = SetProtocol.DISTANCE
                exercise.bodyweight_fraction = fraction
                updated += 1
                print(f"  updated {spec['name']} (fraction {fraction})")

            target_id = muscle_ids.get(spec["target_muscle"])
            if target_id is not None:
                linked = (
                    await db.execute(
                        select(exercise_muscle_groups).where(
                            exercise_muscle_groups.c.exercise_id == exercise.id,
                            exercise_muscle_groups.c.muscle_group_id == target_id,
                        )
                    )
                ).first()
                if linked is None:
                    await db.execute(
                        exercise_muscle_groups.insert().values(
                            exercise_id=exercise.id,
                            muscle_group_id=target_id,
                            role="target",
                        )
                    )

            mapped = (
                await db.execute(
                    select(ExercisePatternMap).where(
                        ExercisePatternMap.exercise_id == exercise.id
                    )
                )
            ).scalar_one_or_none()
            if mapped is None:
                db.add(
                    ExercisePatternMap(
                        exercise_id=exercise.id, pattern_id=conditioning.id
                    )
                )
            else:
                mapped.pattern_id = conditioning.id

        holds = 0
        for name in STATIC_HOLDS:
            exercise = (
                await db.execute(select(Exercise).where(Exercise.name == name))
            ).scalar_one_or_none()
            if exercise is None:
                print(f"  skipped {name} - not in the catalogue")
                continue
            if exercise.set_protocol is not SetProtocol.TIME:
                exercise.set_protocol = SetProtocol.TIME
                holds += 1

        print(
            f"\nLocomotion: {created} created, {updated} updated. "
            f"Static holds set to TIME: {holds}."
        )
        if not commit:
            await db.rollback()
            print("DRY RUN - nothing written. Re-run with --commit.")
            return
        await db.commit()
        print("Committed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--commit", action="store_true", help="Write. Without this, reports only."
    )
    args = parser.parse_args()
    asyncio.run(main(args.commit))
