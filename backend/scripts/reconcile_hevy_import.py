"""Rebuild imported sessions whose set count no longer matches the export.

`backfill_workouts` is idempotent per **session** - it skips any workout whose
`started_at` already exists - so a session imported while something was wrong
stays wrong forever. Two things have caused that:

  * a title missing from `hevy/exercise_map.yaml` at import time, whose sets
    were counted as unmapped and dropped;
  * a set shape the schema could not hold - every duration and distance, before
    `workout_sets` had columns for them.

Rather than encode either cause, this compares what the export says a session
should contain against what the database holds, and rebuilds the ones that
disagree. That catches whatever drift exists, including the next kind, and it
recovers set numbering exactly as Hevy recorded it instead of appending
recovered sets after the fact.

Only sessions that actually disagree are touched, and the export is the
authoritative copy of what gets rebuilt.

    python -m scripts.reconcile_hevy_import --device-id setup-verify-0001
    python -m scripts.reconcile_hevy_import --device-id setup-verify-0001 --commit
"""
import argparse
import asyncio
import json
from collections import defaultdict
from pathlib import Path

import yaml
from sqlalchemy import delete, func, select

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.workout import WorkoutExercise, WorkoutSession, WorkoutSet
from app.services.hevy_backfill import (
    backfill_workouts,
    exercises_by_name,
    title_map_from_document,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "hevy"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _records_a_result(raw: dict) -> bool:
    """Mirrors the importer's rule: reps, a duration, or a distance.

    Kept deliberately in step with `backfill_workouts`. If the two disagree,
    this script reports drift that a rebuild cannot fix and would rebuild the
    same sessions on every run.
    """
    return (
        raw.get("reps") is not None
        or raw.get("duration_seconds") is not None
        or raw.get("distance_meters") is not None
    )


def _expected_sets(workout: dict, mapping: dict[str, int]) -> int:
    """Sets the importer would create for this workout, given today's map."""
    return sum(
        1
        for entry in (workout.get("exercises") or [])
        if entry.get("title") in mapping
        for raw in (entry.get("sets") or [])
        if _records_a_result(raw)
    )


async def main(device_id: str, commit: bool) -> None:
    workouts = _load(DATA_DIR / "data" / "workouts.json")
    document = yaml.safe_load((DATA_DIR / "exercise_map.yaml").read_text(encoding="utf-8"))

    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.device_id == device_id))
        ).scalar_one_or_none()
        if user is None:
            raise SystemExit(f"No user with device_id {device_id!r}")

        mapping = title_map_from_document(document, await exercises_by_name(db))

        # Stored set count per session, and the session id, keyed by start time.
        # Hevy start times carry a trailing Z; stored values are naive, so both
        # sides are compared on the naive ISO form.
        stored: dict[str, tuple[int, int]] = {}
        rows = (
            await db.execute(
                select(
                    WorkoutSession.id,
                    WorkoutSession.started_at,
                    func.count(WorkoutSet.id),
                )
                .outerjoin(
                    WorkoutExercise,
                    WorkoutExercise.workout_session_id == WorkoutSession.id,
                )
                .outerjoin(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
                .where(WorkoutSession.user_id == user.id)
                .group_by(WorkoutSession.id, WorkoutSession.started_at)
            )
        ).all()
        for session_id, started_at, set_count in rows:
            if started_at is not None:
                stored[started_at.isoformat()] = (session_id, set_count)

        drift: list[tuple[str, int, int, int]] = []  # (start, session_id, have, want)
        missing_sets = 0
        for workout in workouts:
            key = (workout.get("start_time") or "").replace("Z", "").replace("+00:00", "")
            entry = stored.get(key)
            if entry is None:
                # Never imported. Either it has nothing resolvable, or it is new
                # - a plain backfill run handles both, and rebuilding is not the
                # tool for it.
                continue
            session_id, have = entry
            want = _expected_sets(workout, mapping)
            if want != have:
                drift.append((key, session_id, have, want))
                missing_sets += want - have

        print(f"Imported sessions checked: {len(stored)}")
        print(f"  disagreeing with the export: {len(drift)}")
        print(f"  net sets to recover:         {missing_sets}")

        if not drift:
            print("\nNothing to reconcile.")
            return

        by_shortfall = sorted(drift, key=lambda d: d[2] - d[3])
        for key, _session_id, have, want in by_shortfall[:12]:
            print(f"    {key[:16]}  db {have:3} vs export {want:3}  ({want - have:+d})")
        if len(by_shortfall) > 12:
            print(f"    ... and {len(by_shortfall) - 12} more")

        surplus = [d for d in drift if d[2] > d[3]]
        if surplus:
            # The database holding MORE than the export is not something a
            # rebuild should quietly paper over: it means sets exist that the
            # export cannot account for, and rebuilding would delete them.
            print(
                f"\nWARNING: {len(surplus)} session(s) hold more sets than the export "
                "accounts for. Rebuilding them DELETES those sets. Investigate "
                "before committing - hand-logged sets against an imported "
                "session would look exactly like this."
            )

        if not commit:
            print("\nDRY RUN - nothing written. Re-run with --commit.")
            return

        to_rebuild = [session_id for _key, session_id, _have, _want in drift]

        # Deleted bottom-up, explicitly. The ORM relationships declare
        # cascade="all, delete-orphan", but that is enforced in Python when a
        # loaded parent is deleted - a bulk `delete()` statement goes straight
        # to SQL and trips the foreign key instead. The database has no
        # ON DELETE CASCADE, so the children are removed here by hand.
        exercise_ids = (
            await db.execute(
                select(WorkoutExercise.id).where(
                    WorkoutExercise.workout_session_id.in_(to_rebuild)
                )
            )
        ).scalars().all()

        if exercise_ids:
            await db.execute(
                delete(WorkoutSet).where(
                    WorkoutSet.workout_exercise_id.in_(exercise_ids)
                )
            )
            await db.execute(
                delete(WorkoutExercise).where(WorkoutExercise.id.in_(exercise_ids))
            )
        await db.execute(
            delete(WorkoutSession).where(WorkoutSession.id.in_(to_rebuild))
        )
        await db.commit()
        print(
            f"\nDeleted {len(to_rebuild)} sessions "
            f"({len(exercise_ids)} exercise rows and their sets)."
        )

        sessions, sets, unmapped, setless = await backfill_workouts(
            db, user, workouts, mapping
        )
        print(f"Rebuilt {sessions} sessions with {sets} sets.")
        print(f"  {unmapped} sets skipped (title not in the reviewed map).")
        print(f"  {setless} sets recorded nothing at all.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-id", required=True)
    parser.add_argument(
        "--commit", action="store_true", help="Write. Without this, reports only."
    )
    args = parser.parse_args()
    asyncio.run(main(args.device_id, args.commit))
