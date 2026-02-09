"""
Assign muscle groups to imported exercises that lack associations.

Usage:
    cd backend
    python scripts/hevy_import/assign_muscle_groups.py --dry-run
    python scripts/hevy_import/assign_muscle_groups.py
"""
import asyncio
import sys
import io
from pathlib import Path
import argparse

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, text
from app.core.config import settings

# Top-level muscle group IDs (level=1)
MG = {
    "Abdominals": 1,
    "Glutes": 5,
    "Chest": 17,
    "Hip Flexors": 20,
    "Shoulders": 25,
    "Back": 27,
    "Adductors": 29,
    "Biceps": 31,
    "Quadriceps": 38,
    "Hamstrings": 46,
    "Abductors": 51,
    "Trapezius": 58,
    "Triceps": 64,
    "Forearms": 71,
    "Calves": 118,
    "Shins": 128,
}

# Exercise name -> (target_mg_key, [secondary_mg_keys])
# Based on exercise science / biomechanics
EXERCISE_MUSCLE_MAP: dict[str, tuple[str, list[str]]] = {
    # ===== CHEST =====
    "1-arm bench press": ("Chest", ["Shoulders", "Triceps"]),
    "1-arm cable fly": ("Chest", []),
    "Bench Press (Barbell)": ("Chest", ["Shoulders", "Triceps"]),
    "Bench Press (Dumbbell)": ("Chest", ["Shoulders", "Triceps"]),
    "Cable Fly Crossovers": ("Chest", ["Shoulders"]),
    "Chest Fly (Machine)": ("Chest", []),
    "Chest Press (Machine)": ("Chest", ["Shoulders", "Triceps"]),
    "Decline Bench Press (Dumbbell)": ("Chest", ["Shoulders", "Triceps"]),
    "Decline Bench Press (Machine)": ("Chest", ["Shoulders", "Triceps"]),
    "Decline Cable Press": ("Chest", ["Shoulders", "Triceps"]),
    "Floor Press (Dumbbell)": ("Chest", ["Triceps", "Shoulders"]),
    "Incline Bench Press (Dumbbell)": ("Chest", ["Shoulders", "Triceps"]),
    "Incline Chest Fly (Dumbbell)": ("Chest", ["Shoulders"]),
    "Incline Chest Press (Machine)": ("Chest", ["Shoulders", "Triceps"]),
    "Incline Push Ups": ("Chest", ["Shoulders", "Triceps"]),
    "Iso-Lateral Chest Press (Machine)": ("Chest", ["Shoulders", "Triceps"]),
    "Iso-lateral Press+Sit-up": ("Chest", ["Abdominals", "Shoulders"]),
    "Push Up": ("Chest", ["Shoulders", "Triceps"]),
    "Kettlebell push-up": ("Chest", ["Shoulders", "Triceps"]),
    "Pullover (Dumbbell)": ("Chest", ["Back"]),

    # ===== BACK =====
    "Back Extension (Hyperextension)": ("Back", ["Glutes", "Hamstrings"]),
    "Back Extension (Weighted Hyperextension)": ("Back", ["Glutes", "Hamstrings"]),
    "Bent Over Row (Barbell)": ("Back", ["Biceps"]),
    "Bent Over Row (Dumbbell)": ("Back", ["Biceps"]),
    "Chin Up": ("Back", ["Biceps"]),
    "Dumbbell Row": ("Back", ["Biceps"]),
    "Gorilla Row (Kettlebell)": ("Back", ["Biceps"]),
    "Landmine Row": ("Back", ["Biceps"]),
    "Lat Pulldown (Cable)": ("Back", ["Biceps"]),
    "Lat Pulldown (Cable) Single Pulley": ("Back", ["Biceps"]),
    "Lat Pulldown - Close Grip (Cable)": ("Back", ["Biceps"]),
    "Pull Up": ("Back", ["Biceps"]),
    "Rope Straight Arm Pulldown": ("Back", []),
    "Rowing Machine": ("Back", ["Shoulders", "Biceps"]),
    "Scap pull-ups": ("Back", ["Shoulders"]),
    "Seated Cable Row": ("Back", ["Biceps"]),
    "Seated Cable Row - Bar Grip": ("Back", ["Biceps"]),
    "Seated Cable row - Single Arm": ("Back", ["Biceps"]),
    "Seated Cable Row - V Grip (Cable)": ("Back", ["Biceps"]),
    "Seated Cable Row - Wide Grip": ("Back", ["Biceps", "Shoulders"]),
    "Single Arm Cable Row": ("Back", ["Biceps"]),
    "Single Arm Lat Pulldown": ("Back", ["Biceps"]),
    "T Bar Row": ("Back", ["Biceps"]),
    "HIIT Alternating DB Rows": ("Back", ["Biceps"]),
    "Superman": ("Back", ["Glutes"]),

    # ===== SHOULDERS =====
    "Arnold Press (Dumbbell)": ("Shoulders", ["Triceps"]),
    "Bent Elbow Lateral Raise": ("Shoulders", []),
    "Chest Supported Reverse Fly (Dumbbell)": ("Shoulders", ["Back"]),
    "Chest Supported T": ("Shoulders", ["Back"]),
    "Chest Supported Ws": ("Shoulders", ["Back"]),
    "Chest Supported Y Raise (Dumbbell)": ("Shoulders", ["Trapezius"]),
    "DB Bent Over Rear Raise": ("Shoulders", ["Back"]),
    "DB Push Press": ("Shoulders", ["Triceps", "Quadriceps"]),
    "External rotation": ("Shoulders", []),
    "Face Pull": ("Shoulders", ["Back"]),
    "Front Raise (Cable)": ("Shoulders", []),
    "Front Raise (Dumbbell)": ("Shoulders", []),
    "HIIT Bent Over Reverse Ys": ("Shoulders", ["Back"]),
    "HIIT DB Push Press": ("Shoulders", ["Triceps", "Quadriceps"]),
    "HIIT Neutral Grip DB Front Raise": ("Shoulders", []),
    "HIIT Shoulder Taps": ("Shoulders", ["Abdominals"]),
    "HIIT Y Raise": ("Shoulders", ["Trapezius"]),
    "Lateral Raise (Cable)": ("Shoulders", []),
    "Lateral Raise (Dumbbell)": ("Shoulders", []),
    "Push Press": ("Shoulders", ["Triceps", "Quadriceps"]),
    "Rear Delt Reverse Fly (Dumbbell)": ("Shoulders", []),
    "Rear Delt Reverse Fly (Machine)": ("Shoulders", []),
    "Reverse Fly Single Arm (Cable)": ("Shoulders", []),
    "Shoulder Press (Dumbbell)": ("Shoulders", ["Triceps"]),
    "Single Arm Landmine Press (Barbell)": ("Shoulders", ["Chest", "Triceps"]),
    "Single Arm Overhead Carry": ("Shoulders", ["Abdominals"]),
    "Upright Row (Barbell)": ("Shoulders", ["Trapezius"]),
    "Arm Circles": ("Shoulders", []),
    "Shrug (Dumbbell)": ("Trapezius", ["Shoulders"]),

    # ===== BICEPS =====
    "Bicep Curl (Barbell)": ("Biceps", ["Forearms"]),
    "Bicep Curl (Cable)": ("Biceps", ["Forearms"]),
    "Bicep Curl (Dumbbell)": ("Biceps", ["Forearms"]),
    "Hammer Curl (Dumbbell)": ("Biceps", ["Forearms"]),

    # ===== TRICEPS =====
    "Seated Triceps Press": ("Triceps", []),
    "Single Arm Tricep Extension (Dumbbell)": ("Triceps", []),
    "Single Arm Triceps Pushdown (Cable)": ("Triceps", []),
    "Skullcrusher (Barbell)": ("Triceps", []),
    "Triceps Extension (Barbell)": ("Triceps", []),
    "Triceps Extension (Cable)": ("Triceps", []),
    "Triceps Extension (Dumbbell)": ("Triceps", []),
    "Triceps Kickback (Dumbbell)": ("Triceps", []),
    "Triceps Pushdown": ("Triceps", []),
    "Triceps Rope Pushdown": ("Triceps", []),

    # ===== QUADRICEPS / LEGS =====
    "Bulgarian Split Squat": ("Quadriceps", ["Glutes"]),
    "Front Squat": ("Quadriceps", ["Glutes", "Abdominals"]),
    "Goblet Squat": ("Quadriceps", ["Glutes"]),
    "Hack Squat": ("Quadriceps", ["Glutes"]),
    "Hack Squat (Machine)": ("Quadriceps", []),
    "Leg Extension (Machine)": ("Quadriceps", []),
    "Leg Press (Machine)": ("Quadriceps", ["Glutes"]),
    "Leg Press Wide Stance (Machine)": ("Quadriceps", ["Glutes", "Adductors"]),
    "Lunge": ("Quadriceps", ["Glutes"]),
    "Walking Lunge": ("Quadriceps", ["Glutes"]),
    "Lateral Lunge Weighted": ("Quadriceps", ["Adductors", "Glutes"]),
    "Pistol Squat": ("Quadriceps", ["Glutes"]),
    "Sissy Squat (Weighted)": ("Quadriceps", []),
    "Smith Machine Deficit Lunge": ("Quadriceps", ["Glutes"]),
    "Split Squat (Dumbbell)": ("Quadriceps", ["Glutes"]),
    "Split squat (Smith machine)": ("Quadriceps", ["Glutes"]),
    "Squat (Barbell)": ("Quadriceps", ["Glutes", "Hamstrings"]),
    "Squat (Bodyweight)": ("Quadriceps", ["Glutes"]),
    "Squat (Smith Machine)": ("Quadriceps", ["Glutes"]),
    "Jump Squat": ("Quadriceps", ["Glutes", "Calves"]),
    "HIIT Jump Squat": ("Quadriceps", ["Glutes", "Calves"]),
    "HIIT Box Step Ups": ("Quadriceps", ["Glutes"]),
    "HIIT DB Step Ups": ("Quadriceps", ["Glutes"]),
    "Smith Iso-Bulgarian Glutes": ("Glutes", ["Quadriceps"]),
    "Smith Machine Iso Bulgarian - Upright": ("Quadriceps", ["Glutes"]),
    "454|Smith Machine Deficit Lunge": ("Quadriceps", ["Glutes"]),
    "Stair Machine (Steps)": ("Quadriceps", ["Glutes", "Calves"]),

    # ===== HAMSTRINGS =====
    "Deadlift (Barbell)": ("Hamstrings", ["Back", "Glutes"]),
    "Deadlift (Dumbbell)": ("Hamstrings", ["Back", "Glutes"]),
    "Deadlift (Trap bar)": ("Hamstrings", ["Back", "Glutes", "Quadriceps"]),
    "Romanian Deadlift (Dumbbell)": ("Hamstrings", ["Glutes", "Back"]),
    "Single Leg Romanian Deadlift (Dumbbell)": ("Hamstrings", ["Glutes"]),
    "Seated Leg Curl (Machine)": ("Hamstrings", []),
    "Glute Ham Raise": ("Hamstrings", ["Glutes"]),

    # ===== GLUTES =====
    "Glute Bridge": ("Glutes", ["Hamstrings"]),
    "Single Leg Glute Bridge": ("Glutes", ["Hamstrings"]),
    "Hip Thrust (Barbell)": ("Glutes", ["Hamstrings"]),
    "Clamshell": ("Glutes", ["Abductors"]),

    # ===== CALVES =====
    "Seated Calf Raise": ("Calves", []),
    "Standing Calf Raise (Machine)": ("Calves", []),
    "Standing Calf Raise (Smith)": ("Calves", []),

    # ===== ABDOMINALS / CORE =====
    "Ab toe touch ": ("Abdominals", []),
    "Bicycle Crunch Raised Legs": ("Abdominals", []),
    "Cable Twist (Down to up)": ("Abdominals", []),
    "Chinnies": ("Abdominals", []),
    "Crunch": ("Abdominals", []),
    "Crunch (Weighted)": ("Abdominals", []),
    "Dead Bug": ("Abdominals", []),
    "Elevated Plank DB Drag Across": ("Abdominals", ["Shoulders"]),
    "Flutter Kicks": ("Abdominals", ["Hip Flexors"]),
    "Lying Alternating Toe Touches": ("Abdominals", []),
    "Oblique Crunch": ("Abdominals", []),
    "Paloff Press - Cable": ("Abdominals", []),
    "Plank": ("Abdominals", ["Shoulders"]),
    "Plank Hip Touchdowns": ("Abdominals", []),
    "Plank Jacks": ("Abdominals", ["Shoulders"]),
    "HIIT Plank Jacks": ("Abdominals", ["Shoulders"]),
    "Russian Twist (Weighted)": ("Abdominals", []),
    "Side Plank": ("Abdominals", []),
    "Side Plank Knee To Elbow": ("Abdominals", []),
    "Sit Up": ("Abdominals", []),
    "Swiss Ball Crunch": ("Abdominals", []),
    "Toe Touch": ("Abdominals", []),
    "Toes to Bar": ("Abdominals", ["Hip Flexors"]),
    "V Up": ("Abdominals", ["Hip Flexors"]),
    "Heel Clicks": ("Abdominals", []),
    "Heel Taps": ("Abdominals", []),

    # ===== HIP FLEXORS / ABDUCTORS / ADDUCTORS =====
    "Hip Flexor Lift Offs": ("Hip Flexors", []),
    "Lateral Leg Raises": ("Abductors", []),
    "Medial Leg Raises": ("Adductors", []),
    "High Knees": ("Hip Flexors", ["Quadriceps"]),

    # ===== FOREARMS =====
    "Farmers Walk": ("Forearms", ["Trapezius", "Shoulders"]),
    "Farmers Walk 4 Time": ("Forearms", ["Trapezius", "Shoulders"]),

    # ===== FULL BODY / HIIT / COMPOUND =====
    "Air Bike": ("Quadriceps", ["Shoulders", "Hamstrings"]),
    "Burpee": ("Chest", ["Quadriceps", "Shoulders"]),
    "HIIT Burpee": ("Chest", ["Quadriceps", "Shoulders"]),
    "HIIT Bear Crawl": ("Shoulders", ["Abdominals", "Quadriceps"]),
    "HIIT Crab Walk": ("Triceps", ["Shoulders", "Glutes"]),
    "HIIT Inchworm": ("Shoulders", ["Hamstrings", "Abdominals"]),
    "HIIT Kettlebell Swings": ("Glutes", ["Hamstrings", "Shoulders"]),
    "HIIT KB Swings": ("Glutes", ["Hamstrings", "Shoulders"]),
    "HIIT Alt'g KB Clean": ("Shoulders", ["Quadriceps", "Glutes"]),
    "HIIT Skater Jumps": ("Quadriceps", ["Glutes"]),
    "HIIT Speedskater Jumps": ("Quadriceps", ["Glutes"]),
    "HIIT Toe Taps": ("Quadriceps", ["Calves"]),
    "HIIT Wall Ball": ("Quadriceps", ["Shoulders"]),
    "HIIT Racked KB March": ("Shoulders", ["Abdominals", "Quadriceps"]),
    "HIIT DB Punches": ("Shoulders", []),
    "HIIT Cable Punches": ("Shoulders", []),
    "HIIT Mountain Climber": ("Abdominals", ["Shoulders", "Hip Flexors"]),
    "Mountain Climber": ("Abdominals", ["Shoulders", "Hip Flexors"]),
    "HIIT DB Up And Arounds": ("Shoulders", ["Abdominals"]),
    "DB Up And Arounds": ("Shoulders", ["Abdominals"]),
    "Kettlebell Clean": ("Shoulders", ["Quadriceps", "Glutes"]),
    "Man Maker Cleans": ("Shoulders", ["Chest", "Quadriceps", "Back"]),
    "Power Clean": ("Shoulders", ["Quadriceps", "Glutes", "Back"]),
    "Treadmill": ("Quadriceps", ["Hamstrings", "Calves"]),

    # ===== COMPLEX / MULTI-JOINT =====
    "1-Leg Deadlift Curl Press": ("Hamstrings", ["Biceps", "Shoulders"]),
    "1-leg deadlift curl press on BOSU": ("Hamstrings", ["Biceps", "Shoulders"]),
    "1-leg Deadlift on bosu ": ("Hamstrings", ["Glutes"]),
    "1-leg squat-curl-press": ("Quadriceps", ["Biceps", "Shoulders"]),
    "kettle bell 1 leg arounds": ("Shoulders", ["Abdominals"]),
    "Seated Triceps Press": ("Triceps", []),

    # ===== AMBIGUOUS - flagged for user review =====
    # Chest Pulls (Cable) - could be cable pullover or cable chest fly
    "Chest Pulls (Cable)": ("Chest", ["Back"]),

    # ===== NO MUSCLE GROUPS (mobility/rest) =====
    "Rest": ("Abdominals", []),  # placeholder - flagged for user
    "Stretching": ("Abdominals", []),  # placeholder - flagged for user
}

# Exercises that should be skipped entirely (no muscle groups applicable)
SKIP_EXERCISES = {"Rest", "Stretching"}


async def main() -> None:
    parser = argparse.ArgumentParser(description="Assign muscle groups to imported exercises")
    parser.add_argument("--dry-run", action="store_true", help="Don't make database changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Find exercises without muscle groups that were imported
        result = await session.execute(text("""
            SELECT e.id, e.name
            FROM exercises e
            LEFT JOIN exercise_muscle_groups emg ON e.id = emg.exercise_id
            WHERE emg.exercise_id IS NULL
            AND e.description = 'Imported from Hevy app'
            ORDER BY e.name
        """))
        exercises_without_mg = {row[1]: row[0] for row in result.fetchall()}

        print(f"Found {len(exercises_without_mg)} exercises without muscle groups")

        assigned = 0
        skipped = 0
        not_mapped = []

        for ex_name, ex_id in exercises_without_mg.items():
            if ex_name in SKIP_EXERCISES:
                skipped += 1
                if args.verbose:
                    print(f"  SKIP: {ex_name}")
                continue

            mapping = EXERCISE_MUSCLE_MAP.get(ex_name)
            if not mapping:
                not_mapped.append(ex_name)
                continue

            target_key, secondary_keys = mapping
            target_id = MG[target_key]

            if args.verbose:
                sec_str = ", ".join(secondary_keys) if secondary_keys else "none"
                print(f"  {ex_name}: target={target_key}, secondary={sec_str}")

            if not args.dry_run:
                # Insert target association
                await session.execute(text(
                    "INSERT INTO exercise_muscle_groups (exercise_id, muscle_group_id, role) "
                    "VALUES (:eid, :mgid, 'target') ON CONFLICT DO NOTHING"
                ), {"eid": ex_id, "mgid": target_id})

                # Insert secondary associations
                for sec_key in secondary_keys:
                    sec_id = MG[sec_key]
                    await session.execute(text(
                        "INSERT INTO exercise_muscle_groups (exercise_id, muscle_group_id, role) "
                        "VALUES (:eid, :mgid, 'secondary') ON CONFLICT DO NOTHING"
                    ), {"eid": ex_id, "mgid": sec_id})

            assigned += 1

        if not args.dry_run:
            await session.commit()
            print(f"\nAssigned muscle groups to {assigned} exercises")
        else:
            print(f"\n[DRY RUN] Would assign muscle groups to {assigned} exercises")

        print(f"Skipped: {skipped}")

        if not_mapped:
            print(f"\nNOT MAPPED ({len(not_mapped)} exercises - need manual assignment):")
            for name in sorted(not_mapped):
                print(f"  - {name}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
